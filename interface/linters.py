import subprocess

from django.apps import apps


PYCODESTYLE = 'pycodestyle'
ESLINT = 'eslint'

LINTER_CHOICES = (
    (PYCODESTYLE, PYCODESTYLE),
    (ESLINT, ESLINT)
)


def lint(build):
    passing = True

    def run_linter(linter):
        result = linter(build)
        return True if result and passing else False

    passing = run_linter(pycodestyle)
    # passing = run_linter(eslint)

    return passing


def pycodestyle(build):
    try:
        output = subprocess.check_output(['pycodestyle', build.directory])
    except subprocess.CalledProcessError as e:
        # pycodestyle returns a non-zero code when it finds issues,
        # so we have to catch the error to get the output
        output = e.output

    passing = True
    output = str(output).replace(build.directory, '')
    Result = apps.get_model('interface', 'Result')
    Result.objects.create(build=build, linter=PYCODESTYLE, output=output)
    if output:
        passing = False

    return passing


def eslint(build):
    try:
        output = subprocess.check_output(['eslint', build.directory])
    except subprocess.CalledProcessError as e:
        output = e.output

    passing = True
    if output:
        output = str(output).replace(build.directory, '')
        Result = apps.get_model('interface', 'Result')
        Result.objects.create(build=build, linter=ESLINT, output=output)
        passing = False

    return passing
