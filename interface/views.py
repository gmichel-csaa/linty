import hashlib
import hmac
import json

import django_rq
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
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
from interface.utils import get_github


class BuildDetailView(generic.DetailView):
    model = Build

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        context['repo'] = self.object.repo
        context['is_owner'] = request.user == context['repo'].user

        if context['repo'].is_private and not context['is_owner']:
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

        context['is_owner'] = self.request.user == self.object.user
        if self.object.is_private and not context['is_owner']:
            raise Http404('You are not allowed to view this Repo')

        url = reverse('badge', kwargs={'full_name': self.object.full_name})
        context['absolute_url'] = self.request.build_absolute_uri(self.request.path)
        context['builds'] = Build.objects.filter(repo=self.object)
        context['badge_url'] = self.request.build_absolute_uri(url)

        return self.render_to_response(context)


class RepoListView(LoginRequiredMixin, generic.ListView):
    template_name = 'interface/repo_list.html'

    def get_queryset(self):
        repos = Repo.objects.filter(
            user=self.request.user,
            webhook_id__isnull=False
        ).annotate(builds_count=Count('builds'))
        return repos

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()

        names = [x[0] for x in self.object_list.values_list('full_name')]
        # Get list of user repos
        g = get_github(self.request.user)
        try:
            repos = [r for r in g.get_user().get_repos()]
        except BadCredentialsException:
            UserSocialAuth.objects.filter(user=request.user).delete()
            return redirect(reverse('login'))

        filtered = []
        for repo in repos:
            if repo.full_name not in names:
                filtered.append(repo)

        context['repos'] = filtered

        return self.render_to_response(context)


class RepoDeleteView(generic.DetailView):
    model = Repo
    slug_field = 'full_name'
    slug_url_kwarg = 'full_name'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(RepoDeleteView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        obj = self.get_object()

        if obj.user != self.request.user:
            raise Http404('You are not allowed to delete this repo')

        obj.soft_delete()

        return redirect(reverse('repo_list'))

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()

        if obj.user != self.request.user:
            raise Http404('You are not allowed to delete this repo')

        obj.soft_delete()

        return HttpResponse(status=204)


@login_required
def ProcessRepo(request, full_name):
    user = request.user
    g = get_github(user)
    grepo = g.get_repo(full_name)

    if not grepo.full_name:
        raise Http404('Repo not found')

    repo, _created = Repo.objects.get_or_create(full_name=grepo.full_name, user=user)

    try:
        hook = grepo.create_hook(
            'web',
            {
                'content_type': 'json',
                'url': request.build_absolute_uri(reverse('webhook')),
                'secret': settings.WEBHOOK_SECRET
            },
            events=['push'],
            active=True
        )
    except UnknownObjectException:
        raise Http404('Github failed to create a hook')

    repo.webhook_id = hook.id
    repo.is_private = grepo.private
    repo.save()

    url = reverse('repo_detail', kwargs={'full_name': repo.full_name})
    return redirect(url)


@csrf_exempt
def WebhookView(request):
    if 'HTTP_X_HUB_SIGNATURE' not in request.META:
        return HttpResponse(status=403)

    sig = request.META['HTTP_X_HUB_SIGNATURE']
    text = request.body

    signature = 'sha1=' + hmac.new(settings.WEBHOOK_SECRET, msg=text, digestmod=hashlib.sha1).hexdigest()

    if not hmac.compare_digest(sig, signature):
        return HttpResponse(status=403)

    try:
        body = json.loads(request.body)
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
