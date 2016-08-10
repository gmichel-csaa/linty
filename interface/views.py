import hashlib
import hmac
import json

import django_rq
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponse, Http404
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from github import UnknownObjectException, BadCredentialsException
from social.apps.django_app.default.models import UserSocialAuth
from social.apps.django_app.views import auth

from interface.models import Build, Repo
from interface.tasks import build_handler
from interface.utils import get_github, get_page_number_list


class BuildDetailView(generic.DetailView):
    model = Build

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        context['repo'] = self.object.repo
        is_collab = context['repo'].user_is_collaborator(request.user)
        context['is_owner'] = is_collab
        context['issues'] = self.object.get_issues(request.user)

        if context['repo'].is_private and not is_collab:
            raise Http404('You are not allowed to view this Build')

        context['results'] = self.object.results.all()

        return self.render_to_response(context)


class RepoDetailView(generic.DetailView):
    model = Repo
    slug_field = 'full_name'
    slug_url_kwarg = 'full_name'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)

        is_collab = self.object.user_is_collaborator(request.user)
        context['is_owner'] = is_collab

        if self.object.is_private and not is_collab:
            raise Http404('You are not allowed to view this Repo')

        url = reverse('badge', kwargs={'full_name': self.object.full_name})
        context['absolute_url'] = self.request.build_absolute_uri(self.request.path)
        context['badge_url'] = self.request.build_absolute_uri(url)

        ref = request.GET.get('ref', False)
        context['ref'] = ref
        if ref:
            build_results = Build.objects.filter(repo=self.object, ref=ref)
        else:
            build_results = Build.objects.filter(repo=self.object)
        paginator = Paginator(build_results, 20)

        page = self.request.GET.get('page')
        try:
            context['builds'] = paginator.page(page)
        except PageNotAnInteger:
            context['builds'] = paginator.page(1)
        except EmptyPage:
            context['builds'] = paginator.page(paginator.num_pages)

        if paginator.num_pages > 1:
            context['pages'] = get_page_number_list(context['builds'].number, paginator.num_pages)

        context['num_objects'] = paginator.count

        return self.render_to_response(context)


class RepoListView(LoginRequiredMixin, generic.ListView):
    template_name = 'interface/repo_list.html'

    def get(self, request, *args, **kwargs):
        g = get_github(self.request.user)
        try:
            repos = [r for r in g.get_user().get_repos()]
        except BadCredentialsException:
            UserSocialAuth.objects.filter(user=request.user).delete()
            return redirect(reverse('login'))

        self.object_list = Repo.objects.filter(
            full_name__in=[i.full_name for i in repos],
            webhook_id__isnull=False
        ).annotate(builds_count=Count('builds'))

        names = [x.full_name for x in self.object_list]

        filtered = []
        for repo in repos:
            if repo.full_name not in names:
                filtered.append(repo)

        context = self.get_context_data()
        context['repos'] = filtered

        return self.render_to_response(context)


class RepoDeleteView(generic.DetailView):
    model = Repo
    slug_field = 'full_name'
    slug_url_kwarg = 'full_name'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(RepoDeleteView, self).dispatch(request, *args, **kwargs)

    def soft_delete(self, request):
        obj = self.get_object()

        if not obj.user_is_collaborator(request.user):
            raise Http404('You are not allowed to delete this repo')

        obj.soft_delete()

    def get(self, request, *args, **kwargs):
        self.soft_delete(request)
        return redirect(reverse('repo_list'))

    def delete(self, request, *args, **kwargs):
        self.soft_delete(request)
        return HttpResponse(status=204)


@login_required
def ProcessRepo(request, full_name):
    user = request.user
    g = get_github(request.user)
    grepo = g.get_repo(full_name)

    if not grepo.full_name:
        raise Http404('Repo not found')

    guser = g.get_user(user.username)
    is_collab = grepo.has_in_collaborators(guser)

    try:
        repo = Repo.objects.get(full_name=grepo.full_name)
    except Repo.DoesNotExist:
        repo = None

    if not is_collab:
        if grepo.private or not repo:
            raise Http404('You are not a collaborator of this repo')
    else:
        if not repo:
            repo = Repo.objects.create(full_name=grepo.full_name, user=user)

        if not repo.webhook_id:
            try:
                repo.add_webhook(request)
            except UnknownObjectException:
                raise Http404('Github failed to create a hook')

    url = reverse('repo_detail', kwargs={'full_name': repo.full_name})
    return redirect(url)


@csrf_exempt
def WebhookView(request):
    if 'HTTP_X_HUB_SIGNATURE' not in request.META:
        return HttpResponse(status=403)

    sig = request.META['HTTP_X_HUB_SIGNATURE']
    text = request.body

    secret = str.encode(settings.WEBHOOK_SECRET)
    signature = 'sha1=' + hmac.new(secret, msg=text, digestmod=hashlib.sha1).hexdigest()

    if not hmac.compare_digest(sig, signature):
        return HttpResponse(status=403)

    try:
        body = json.loads(text.decode('utf-8'))
        assert body
    except ValueError:
        return HttpResponse('Invalid JSON body.', status=400)

    if 'ref' not in body or not body['head_commit']:
        return HttpResponse(status=204)

    base_url = request.build_absolute_uri('/')[:-1]

    django_rq.enqueue(build_handler, body, base_url)

    return HttpResponse(status=202)


class BadgeView(generic.DetailView):
    model = Repo
    slug_field = 'full_name'
    slug_url_kwarg = 'full_name'

    def get_template_names(self):
        repo = self.object
        build = repo.get_head_build()
        if build:
            if build.status == 'success':
                return ['interface/badges/pass.svg']
            elif build.status == 'error':
                return ['interface/badges/fail.svg']
        return ['interface/badges/unknown.svg']


def LoginView(request):
    return auth(request, 'github')


def LogoutView(request):
    next = request.GET.get('next', '/')
    logout(request)
    return redirect(next)


def handler404(request):
    response = render(request, 'interface/404.html')
    response.status_code = 404
    return response


def handler500(request):
    response = render(request, 'interface/500.html')
    response.status_code = 500
    return response
