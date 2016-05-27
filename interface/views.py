import json
import os
import shutil
import subprocess

import requests
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from social.apps.django_app.default.models import UserSocialAuth

from interface.models import Build, Repo
from interface.utils import get_github


class BuildDetailView(generic.DetailView):
    model = Build


class RepoDetailView(LoginRequiredMixin, generic.DetailView):
    model = Repo
    slug_field = 'full_name'
    slug_url_kwarg = 'full_name'

    def get_context_data(self, **kwargs):
        object = self.object
        url = reverse('badge', kwargs={'full_name': object.full_name})

        kwargs['absolute_url'] = self.request.build_absolute_uri(self.request.path)
        kwargs['builds'] = Build.objects.filter(repo=object)
        kwargs['badge_url'] = self.request.build_absolute_uri(url)

        return super(RepoDetailView, self).get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        object = self.get_object()
        if object.user != request.user:
            return HttpResponse(status=403)
        return super(RepoDetailView, self).get(request, *args, **kwargs)


class RepoListView(LoginRequiredMixin, generic.ListView):
    template_name = 'interface/repo_list.html'

    def get_queryset(self):
        return Repo.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', self.object_list)
        names = [x[0] for x in queryset.values_list('full_name')]
        # Get list of user repos
        g = get_github(self.request.user)
        repos = [r for r in g.get_user().get_repos()]
        filtered = []
        for repo in repos:
            if repo.full_name not in names:
                filtered.append(repo)

        kwargs['repos'] = filtered

        return super(RepoListView, self).get_context_data(**kwargs)


class RepoDeleteView(LoginRequiredMixin, generic.DeleteView):
    success_url = reverse_lazy('repo_list')
    model = Repo
    slug_field = 'full_name'
    slug_url_kwarg = 'full_name'

    def get(self, request, *args, **kwargs):
        obj = self.get_object()

        if obj.user != self.request.user:
            return HttpResponse(status=403)

        obj.delete()

        return redirect(reverse('repo_list'))


@login_required
def ProcessRepo(request, full_name):
    user = request.user
    g = get_github(user)

    grepo = g.get_repo(full_name)

    hook = grepo.create_hook(
        'web',
        {
            'content_type': 'json',
            'url': request.build_absolute_uri(reverse('webhook'))
        },
        events=['push'],
        active=True
    )

    Repo.objects.create(full_name=grepo.full_name, user=user, webhook_id=hook.id)

    url = reverse('repo_detail', kwargs={'full_name': grepo.full_name})
    return redirect(url)


@csrf_exempt
def WebhookView(request):
    try:
        body = json.loads(request.body)
    except ValueError:
        return HttpResponse('Invalid JSON body.', status=400)

    if 'ref' not in body:
        return HttpResponse(status=204)

    try:
        repo = Repo.objects.get(full_name=body['repository']['full_name'])
    except Repo.DoesNotExist:
        return HttpResponse(status=204)

    try:
        data = UserSocialAuth.objects.filter(user=repo.user).values_list('extra_data')[0][0]
    except:
        raise Exception('Fail')

    username = data['login']
    password = data['access_token']
    auth = (username, password)

    # get necessary vars
    clone_url = body['repository']['clone_url']
    clone_url = clone_url.replace('github.com', '%s:%s@github.com' % (username, password))
    branch = body['ref'].replace('refs/heads/', '')

    if 'head_commit' not in body:
        return HttpResponse(status=204)

    sha = body['head_commit']['id']
    status_url = body['repository']['statuses_url'].replace('{sha}', sha)

    build = Build.objects.create(
        repo=repo,
        ref=branch,
        sha=sha,
        status=Build.PENDING
    )

    def publish_status(state, description, target_url=None):
        data = {
            'state': state,
            'description': description,
            'target_url': target_url,
            'context': 'linty'
        }
        requests.post(status_url, json=data, auth=auth)

    publish_status('pending', 'Linting your code...')

    # download repo
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    directory = 'tmp/%s' % sha[:7]
    if os.path.exists(directory):
        shutil.rmtree(directory)
    subprocess.call(['git', 'clone', clone_url, directory])
    subprocess.call(['git', '--git-dir=%s/.git' % directory, '--work-tree=%s' % directory, 'fetch', clone_url])
    subprocess.call(['git', '--git-dir=%s/.git' % directory, '--work-tree=%s' % directory, 'checkout', branch])

    # run linting
    output = None
    try:
        subprocess.check_output(['pep8', directory])
    except subprocess.CalledProcessError as e:
        # pep8 returns a non-zero code when it finds issues, so we have to catch the error to get the output
        output = e.output

    # nuke files
    shutil.rmtree(directory)

    # process output
    if not output:
        status = 'success'
        publish_status(status, 'Your code passed linting.')
    else:
        status = 'error'
        output = output.replace(directory, '')
        path = reverse('build_detail', kwargs={'pk': build.id})
        url = request.build_absolute_uri(path)
        publish_status(status, 'Your code has lint failures. See Details.', target_url=url)

    # update build record
    build.status = status
    build.result = output
    build.finished_at = timezone.now()
    build.save()

    return HttpResponse(status=204)


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
