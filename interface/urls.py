from django.conf.urls import url

from interface import views

urlpatterns = [
    url(r'^add/(?P<full_name>.*)$', views.ProcessRepo, name='process_repo'),
    url(r'^repos$', views.RepoListView.as_view(), name='repo_list'),
    url(r'^repo/(?P<pk>[0-9]+)/builds$', views.BuildListView.as_view(), name='build_list'),
    url(r'^repo/(?P<pk>[0-9]+)/delete$', views.RepoDeleteView.as_view(), name='delete_repo'),
    url(r'^build/(?P<pk>[0-9]+)$', views.BuildDetailView.as_view(), name='build_detail'),
    url(r'^webhook$', views.WebhookView, name='webhook')
]
