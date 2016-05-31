import os
import shutil
import subprocess

import requests
from django.core.urlresolvers import reverse
from django.utils import timezone

from interface import linters
from interface.models import Build, Repo


def build_handler(body, base_url):
    try:
        repo = Repo.objects.get(full_name=body['repository']['full_name'])
    except Repo.DoesNotExist:
        return 'Repo not registered'

    auth = repo.user.get_auth()
    if not auth:
        return 'User for repo not logged in'

    # get necessary vars
    clone_url = body['repository']['clone_url']
    clone_url = clone_url.replace('github.com', '%s:%s@github.com' % auth)
    branch = body['ref'].replace('refs/heads/', '')
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
    directory = build.directory
    if os.path.exists(directory):
        shutil.rmtree(directory)
    subprocess.call(['git', 'clone', clone_url, directory])
    subprocess.call(['git', '--git-dir=%s/.git' % directory, '--work-tree=%s' % directory, 'fetch', clone_url])
    subprocess.call(['git', '--git-dir=%s/.git' % directory, '--work-tree=%s' % directory, 'checkout', branch])

    # run linting
    passing = linters.lint(build)

    # clean up
    shutil.rmtree(build.directory)

    if passing:
        publish_status('success', 'Your code passed linting.')
    else:
        path = reverse('build_detail', kwargs={'pk': build.id})
        url = base_url + path
        publish_status('error', 'Your code has lint failures. See Details.', target_url=url)

    # update build record
    build.status = 'success' if passing else 'error'
    build.finished_at = timezone.now()
    build.save()

    return 'Build finished'
