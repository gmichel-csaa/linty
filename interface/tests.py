import mock as mock
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase

from interface import linters
from interface.models import Repo, Build, Result, UserProxy


class LintTestCase(TestCase):
    def setUp(self):
        self.user = UserProxy.objects.create(
            username='test',
            password='test'
        )
        self.repo = Repo.objects.create(
            user=self.user,
            full_name='Test/Test',
            is_private=True,
            webhook_id=1,
        )
        self.build = Build.objects.create(
            repo=self.repo,
            ref='master',
            sha='2278cd53905d74f01d2ec5bae3cf136ad66e7393',
            status=Build.ERROR
        )
        self.result = Result.objects.create(
            build=self.build,
            linter=linters.PYCODESTYLE,
            output='/interface/views.py:34:1: E303 too many blank lines (3)'
        )


class HomePageTests(LintTestCase):
    def test_home_unauth_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_home_auth_200(self):
        self.client.force_login(self.user, backend=settings.AUTHENTICATION_BACKENDS[0])
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)


class RepoListTests(LintTestCase):
    def setUp(self):
        super(RepoListTests, self).setUp()
        self.url = reverse('repo_list')

    def test_repo_list_unauth_302(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    # Disabled because the view requires OAuth with Github
    # def test_repo_list_auth_200(self):
    #     self.client.force_login(self.user, backend=settings.AUTHENTICATION_BACKENDS[0])
    #     response = self.client.get(self.url)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, self.repo.full_name)


class RepoDetailTests(LintTestCase):
    def setUp(self):
        super(RepoDetailTests, self).setUp()
        self.url = reverse('repo_detail', kwargs={'full_name': self.repo.full_name})

    def test_repo_detail_404(self):
        url = reverse('repo_detail', kwargs={'full_name': 'Test/404'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_repo_detail_private_unauth_404(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_repo_list_auth_200(self):
        self.client.force_login(self.user, backend=settings.AUTHENTICATION_BACKENDS[0])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.repo.full_name)
        self.assertContains(response, self.build.id)

    def test_build_results_paginated(self):
        for _ in range(49):
            Build.objects.create(
                repo=self.repo,
                ref='master',
                sha='2278cd53905d74f01d2ec5bae3cf136ad66e7393',
                status=Build.ERROR
            )

        self.client.force_login(self.user, backend=settings.AUTHENTICATION_BACKENDS[0])
        response = self.client.get(self.url)
        self.assertEqual(Build.objects.count(), 50)
        self.assertEqual(len(response.context_data['builds']), 20)


class RepoDeleteTests(LintTestCase):
    def setUp(self):
        super(RepoDeleteTests, self).setUp()
        self.url = reverse('repo_delete', kwargs={'full_name': self.repo.full_name})

    def test_repo_delete_404(self):
        url = reverse('repo_delete', kwargs={'full_name': 'Test/404'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_repo_delete_unauth_404(self):
        response = self.client.get(self.url)
        self.assertIsNotNone(self.repo.webhook_id)
        self.assertEqual(response.status_code, 404)

    # Disabled because requires OAuth
    # def test_repo_delete_auth_302(self):
    #     self.client.force_login(self.user)
    #     response = self.client.get(self.url)
    #     self.assertIsNone(self.repo.webhook_id)
    #     self.assertEqual(response.status_code, 302)


class BuildDetailTests(LintTestCase):
    def setUp(self):
        super(BuildDetailTests, self).setUp()
        self.url = reverse('build_detail', kwargs={'pk': self.build.pk})

    def test_build_detail_404(self):
        url = reverse('build_detail', kwargs={'pk': 999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @mock.patch('interface.models.Build.get_issues')
    def test_build_detail_public_200(self, mock_get_issues):
        mock_get_issues.return_value = []

        self.repo.is_private = False
        self.repo.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_build_detail_private_uauth_404(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    @mock.patch('interface.models.Build.get_issues')
    def test_build_detail_owner_200(self, mock_get_issues):
        mock_get_issues.return_value = []

        self.client.force_login(self.user, backend=settings.AUTHENTICATION_BACKENDS[0])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @mock.patch('interface.models.Build.get_issues')
    def test_build_detail_contains_results(self, mock_get_issues):
        mock_get_issues.return_value = []

        self.client.force_login(self.user, backend=settings.AUTHENTICATION_BACKENDS[0])
        response = self.client.get(self.url)
        self.assertContains(response, self.result.output)


class BadgeTests(LintTestCase):
    def setUp(self):
        super(BadgeTests, self).setUp()
        self.url = reverse('badge', kwargs={'full_name': self.repo.full_name})

    def test_badge_unknown_200(self):
        self.build.status = Build.PENDING
        self.build.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertIn('interface/badges/unknown.svg', response.template_name)

    def test_badge_fail_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertIn('interface/badges/fail.svg', response.template_name)

    def test_badge_pass_200(self):
        self.build.status = Build.SUCCESS
        self.build.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertIn('interface/badges/pass.svg', response.template_name)
