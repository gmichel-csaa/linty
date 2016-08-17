from django.apps import apps


def build_handler(build_id):
    Build = apps.get_model('interface.Build')
    Result = apps.get_model('interface.Result')
    try:
        build = Build.objects.get(id=build_id)
    except Build.DoesNotExist:
        return 'Invalid build ID'

    auth = build.repo.user.get_auth()
    try:
        build.clone(auth)
        passing = build.lint()
        build.clean_directory()

        if not Result.objects.filter(build=build).exists():
            build.set_status(auth, Build.CANCELLED)
            return 'Build cancelled'

        if passing:
            build.set_status(auth, Build.SUCCESS)
        else:
            build.set_status(auth, Build.ERROR)

        return 'Build finished'
    except Exception as e:
        print(e)
        build.set_status(auth, Build.CANCELLED)
        return 'Build failed'
