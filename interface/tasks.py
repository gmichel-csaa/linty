import os
import shutil
import subprocess

import requests
from django.core.urlresolvers import reverse
from django.utils import timezone
from social.apps.django_app.default.models import UserSocialAuth

from interface.models import Build, Repo, Result


def build_handler(body, base_url):
    try:
        repo = Repo.objects.get(full_name=body['repository']['full_name'])
    except Repo.DoesNotExist:
        return 'Repo not registered'

    try:
        data = UserSocialAuth.objects.filter(user=repo.user).values_list('extra_data')[0][0]
    except:
        return 'User for repo not logged in'

    username = data['login']
    password = data['access_token']
    auth = (username, password)

    # get necessary vars
    clone_url = body['repository']['clone_url']
    clone_url = clone_url.replace('github.com', '%s:%s@github.com' % (username, password))
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
        url = base_url + path
        publish_status(status, 'Your code has lint failures. See Details.', target_url=url)

    # save result
    Result.objects.create(build=build, linter=Result.PEP8, output=output)

    # update build record
    build.status = status
    build.finished_at = timezone.now()
    build.save()

    return 'Build finished'
