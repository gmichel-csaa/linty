import os
import subprocess

from django.apps import apps


PYCODESTYLE = 'pycodestyle'
NPM_LINT = 'npm_lint'

LINTER_CHOICES = (
    (PYCODESTYLE, PYCODESTYLE),
    (NPM_LINT, 'NPM Lint')
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
        passing = run_linter(npm_lint, cwd)

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


def npm_lint(build, cwd):
    my_env = os.environ.copy()
    my_env["PATH"] = "/usr/local/bin:" + my_env["PATH"]

    try:
        # TODO: only install whatever the linter needs
        subprocess.call('npm install --ignore-scripts', cwd=cwd, shell=True, env=my_env)
        output = subprocess.check_output('npm run lint', cwd=cwd, shell=True, env=my_env)
        passing = True
    except subprocess.CalledProcessError as e:
        output = e.output
        passing = False

    if output:
        # Strip directory
        output = output.decode("utf-8").replace(cwd, '')
        # Remove junk npm call lines
        output = output.split('\n', 1)[1]
        Result = apps.get_model('interface', 'Result')
        Result.objects.create(build=build, linter=NPM_LINT, output=output)

    return passing
