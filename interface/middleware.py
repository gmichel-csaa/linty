from django.http import HttpResponseRedirect

from interface.models import UserProxy


class UserProxyMiddleware(object):
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated():
            request.user.__class__ = UserProxy


class SubdomainMiddleware(object):
    """
    A middleware class that adds a ``subdomain`` attribute to the current request.
    """

    def process_request(self, request):
        """
        Redirects www to apex
        """
        if request.META.get('HTTP_HOST', '').startswith('www'):
            return HttpResponseRedirect(
                'https://lintyapp.com/' + request.get_full_path()
            )
