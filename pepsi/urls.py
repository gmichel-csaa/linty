from django.conf.urls import url, include

urlpatterns = [
    url('', include('interface.urls')),
]
