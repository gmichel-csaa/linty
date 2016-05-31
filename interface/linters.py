import subprocess

from interface.models import Result


PEP8 = 'PEP8'

LINTER_CHOICES = (
    (PEP8, PEP8)
)

def lint(build, linter):
    if linter == PEP8:
        return pep8(build)


def pep8(build):
    output = None
    try:
        subprocess.check_output(['pep8', build.directory])
    except subprocess.CalledProcessError as e:
        # pep8 returns a non-zero code when it finds issues,
        # so we have to catch the error to get the output
        output = e.output

    passing = True
    if output:
        output = output.replace(build.directory, '')
        Result.objects.create(build=build, linter=PEP8, output=output)
        passing = False

    return passing
