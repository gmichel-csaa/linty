from django.views import generic

from interface.mixins import StaffRequiredMixin
from interface.models import Build, UserProxy, Repo


class TimelineView(StaffRequiredMixin, generic.ListView):
    template_name = 'actions/timeline.html'

    def get_queryset(self):
        builds = Build.objects \
             .select_related('repo') \
             .order_by('-created_at') \
             .values('id', 'repo__full_name', 'created_at', 'finished_at')[:500]
        repos = Repo.objects \
            .order_by('-created_at') \
            .values('id', 'full_name', 'created_at')[:500]

        object_list = [
            {
                'id': obj['id'],
                'type': 'build',
                'repo_name': obj['repo__full_name'],
                'created_at': obj['created_at'],
                'finished_at': obj['finished_at']
            } for obj in builds
        ]
        object_list.extend([
            {
                'id': obj['id'],
                'type': 'repo',
                'full_name': obj['full_name'],
                'created_at': obj['created_at']
            } for obj in repos
        ])
        object_list.sort(key=lambda i: i['created_at'], reverse=True)
        return object_list[:500]

    def get_context_data(self, **kwargs):
        context = super(TimelineView, self).get_context_data(**kwargs)
        context['user_count'] = UserProxy.objects.count()
        context['repo_count'] = Repo.objects.count()
        context['build_count'] = Build.objects.count()
        return context
