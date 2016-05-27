from django.conf.urls import url

from interface import views

urlpatterns = [
    url(r'^add/(?P<full_name>(.*))$', views.ProcessRepo, name='process_repo'),
    url(r'^repos$', views.RepoListView.as_view(), name='repo_list'),
    url(
        r'^repo/(?P<full_name>[\w|/]+)/badge.svg$',
        views.BadgeView.as_view(content_type='image/svg+xml'),
        name='badge'
    ),
    url(r'^repo/(?P<full_name>[\w|/]+)/delete$', views.RepoDeleteView.as_view(), name='delete_repo'),
    url(r'^repo/(?P<full_name>[\w|/]+)$', views.RepoDetailView.as_view(), name='repo_detail'),
    url(r'^build/(?P<pk>[0-9]+)$', views.BuildDetailView.as_view(), name='build_detail'),
    url(r'^webhook$', views.WebhookView, name='webhook')
]
