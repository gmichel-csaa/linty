from interface.models import Build


def build_handler(build_id):
    try:
        build = Build.objects.get(id=build_id)
    except Build.DoesNotExist:
        return 'Invalid build ID'

    auth = build.repo.user.get_auth()
    try:
        build.set_status(auth, Build.PENDING)
        build.clone(auth)
        passing = build.lint()
        build.clean_directory()

        if passing:
            build.set_status(auth, Build.SUCCESS)
        else:
            build.set_status(auth, Build.ERROR)

        return 'Build finished'
    except:
        build.set_status(Build.CANCELLED)
        return 'Build failed'