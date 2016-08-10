import subprocess

from django.apps import apps


FLAKE8 = 'flake8'
ESLINT = 'eslint'

LINTER_CHOICES = (
    (FLAKE8, FLAKE8),
    (ESLINT, ESLINT)
)


def lint(build):
    passing = True

    def run_linter(linter):
        result = linter(build)
        return True if result and passing else False

    passing = run_linter(flake8)
    # passing = run_linter(eslint)

    return passing


def flake8(build):
    try:
        output = subprocess.check_output(['flake8', build.directory])
        passing = True
    except subprocess.CalledProcessError as e:
        output = e.output
        passing = False

    output = output.decode("utf-8").replace(build.directory, '')
    Result = apps.get_model('interface', 'Result')
    Result.objects.create(build=build, linter=FLAKE8, output=output)

    return passing


def eslint(build):
    try:
        output = subprocess.check_output(['eslint', build.directory])
        passing = True
    except subprocess.CalledProcessError as e:
        output = e.output
        passing = False

    if output:
        output = output.decode("utf-8").replace(build.directory, '')
        Result = apps.get_model('interface', 'Result')
        Result.objects.create(build=build, linter=ESLINT, output=output)

    return passing
