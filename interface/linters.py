import os
import subprocess

from django.apps import apps
from django.conf import settings

PYCODESTYLE = 'pycodestyle'
ESLINT = 'eslint'

LINTER_CHOICES = (
    (PYCODESTYLE, PYCODESTYLE),
    (ESLINT, ESLINT)
)


def lint(build):
    passing = True

    def run_linter(linter, cwd):
        result = linter(build, cwd)
        return True if result and passing else False

    cwd = os.path.join(os.getcwd(), build.directory)
    if os.path.isfile(os.path.join(cwd, 'requirements.txt')):
        passing = run_linter(pycodestyle, cwd)
    elif os.path.isfile(os.path.join(cwd, 'package.json')):
        passing = run_linter(eslint, cwd)

    return passing


def pycodestyle(build, cwd):
    # TODO: Allow the user to specify their preferred version of pycodestyle
    try:
        output = subprocess.check_output(['pycodestyle', cwd])
        passing = True
    except subprocess.CalledProcessError as e:
        output = e.output
        passing = False

    output = output.decode("utf-8").replace(cwd, '')
    Result = apps.get_model('interface', 'Result')
    Result.objects.create(build=build, linter=PYCODESTYLE, output=output)

    return passing


def eslint(build, cwd):
    path = "/usr/local/bin:" + os.environ['PATH']
    my_env = {'PATH': path}
    binary = os.path.join(settings.BASE_DIR, 'node_modules/eslint/bin/eslint.js')
    try:
        result = subprocess.run(
            [binary, cwd],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=my_env,
            universal_newlines=True
        )
        output = result.stdout
        passing = True
    except subprocess.CalledProcessError as e:
        output = e.stdout
        passing = False

    if not output:
        output = ''
    else:
        # Strip directory
        output = output.replace(cwd, '')

    Result = apps.get_model('interface', 'Result')
    Result.objects.create(build=build, linter=ESLINT, output=output)

    return passing
