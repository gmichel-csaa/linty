import subprocess

from interface.models import Result


PEP8 = 'PEP8'
ESLINT = 'eslint'

LINTER_CHOICES = (
    (PEP8, PEP8),
    (ESLINT, ESLINT)
)


def lint(build):
    passing = True

    def run_linter(linter):
        result = linter(build)
        return True if result and passing else False

    run_linter(pep8)
    # run_linter(eslint)

    return passing


def pep8(build):
    try:
        output = subprocess.check_output(['pep8', build.directory])
    except subprocess.CalledProcessError as e:
        # pep8 returns a non-zero code when it finds issues,
        # so we have to catch the error to get the output
        output = e.output

    passing = True
    output = output.replace(build.directory, '')
    Result.objects.create(build=build, linter=PEP8, output=output)
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
        output = output.replace(build.directory, '')
        Result.objects.create(build=build, linter=ESLINT, output=output)
        passing = False

    return passing
