from django.conf.urls import url
from django.views.generic import TemplateView

from interface import views

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='index.html'), name='index'),
    url(r'^add/(?P<full_name>[\w/.-]+)$', views.ProcessRepo, name='process_repo'),
    url(r'^repos$', views.RepoListView.as_view(), name='repo_list'),
    url(
        r'^repo/(?P<full_name>[\w/.-]+)/badge.svg$',
        views.BadgeView.as_view(content_type='image/svg+xml'),
        name='badge'
    ),
    url(r'^repo/(?P<full_name>[\w/.-]+)/delete$', views.RepoDeleteView.as_view(), name='repo_delete'),
    url(r'^repo/(?P<full_name>[\w/.-]+)$', views.RepoDetailView.as_view(), name='repo_detail'),
    url(r'^build/(?P<pk>[0-9]+)$', views.BuildDetailView.as_view(), name='build_detail'),
    url(r'^webhook$', views.WebhookView, name='webhook'),
    url(r'^logout', views.LogoutView, name='logout'),
    url(r'^login', views.LoginView, name='login')
]
