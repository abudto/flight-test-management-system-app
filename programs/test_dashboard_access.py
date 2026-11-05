"""Dashboard integration must preserve the workspace's model permissions."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from programs.models import Aircraft
from testing.test_support import PlanningDataMixin


class DashboardAccessTests(PlanningDataMixin, TestCase):
    def reader(self, *permissions):
        user = get_user_model().objects.create_user("synthetic-reader", password="synthetic-only")
        for permission in permissions:
            app_label, codename = permission.split(".")
            user.user_permissions.add(Permission.objects.get(
                content_type__app_label=app_label, codename=codename,
            ))
        self.client.force_login(user)
        return user

    def urls(self):
        return [reverse("programs:program_list"),
                reverse("programs:program_detail", args=[self.program_a.pk]),
                reverse("test_list", args=[self.program_a.pk]),
                reverse("test_detail", args=[self.program_a.pk, self.test_a.pk])]

    def test_anonymous_requests_require_login(self):
        self.client.logout()
        for url in self.urls():
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), reverse("login") + "?next=" + url)

    def test_accounts_without_permissions_cannot_read_restored_pages(self):
        self.reader()
        for url in self.urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_program_reader_cannot_see_other_model_counts_or_aircraft(self):
        Aircraft.objects.create(program=self.program_a, aircraft_number="RESTRICTED-AC",
                                aircraft_type="Synthetic restricted type")
        self.reader("programs.view_program")
        response = self.client.get(self.urls()[1])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["counts"], {})
        self.assertEqual(response.context["workspaces"], [])
        self.assertEqual(response.context["aircraft"], [])
        self.assertNotContains(response, "RESTRICTED-AC")
        self.assertNotContains(response, 'class="metric-card"')
        self.assertNotContains(response, f'href="{reverse("test_matrix", args=[self.program_a.pk])}"')
        self.assertNotContains(response, f'href="{reverse("admin:index")}"')
        self.assertEqual(self.client.get(self.urls()[0]).status_code, 200)

    def test_dashboard_only_counts_models_the_account_can_view(self):
        self.reader("programs.view_program", "testing.view_test")
        response = self.client.get(self.urls()[1])
        self.assertEqual(response.context["counts"], {"Tests": 1})
        self.assertEqual([item["title"] for item in response.context["workspaces"]], ["Tests"])
        self.assertContains(response,
            f'href="{reverse("record_list", args=["tests"])}?program={self.program_a.pk}"')

    def test_aircraft_permission_shows_only_the_requested_program_aircraft(self):
        local = Aircraft.objects.create(program=self.program_a, aircraft_number="ALPHA-AC",
                                        aircraft_type="Synthetic")
        Aircraft.objects.create(program=self.program_b, aircraft_number="BRAVO-AC",
                                aircraft_type="Synthetic")
        self.reader("programs.view_program", "programs.view_aircraft")
        response = self.client.get(self.urls()[1])
        self.assertQuerySetEqual(response.context["aircraft"], [local])
        self.assertNotContains(response, "BRAVO-AC")

    def test_test_list_does_not_reveal_point_counts_without_permission(self):
        self.reader("programs.view_program", "testing.view_test",
                    "testing.view_engineeringtestrequirement")
        response = self.client.get(self.urls()[2])
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(response.context["tests"][0], "point_count"))
        self.assertContains(response, "View permission required")
        self.assertNotContains(response, f'href="{self.urls()[3]}"')
        self.assertContains(response,
            f'href="{reverse("record_detail", args=["tests", self.test_a.pk])}"')
        self.assertEqual(self.client.get(self.urls()[3]).status_code, 403)

    def test_full_specification_requires_permission_to_read_conditions(self):
        self.reader("programs.view_program", "testing.view_test",
                    "testing.view_engineeringtestrequirement", "testing.view_testpoint")
        self.assertEqual(self.client.get(self.urls()[2]).status_code, 200)
        self.assertEqual(self.client.get(self.urls()[3]).status_code, 403)

    def test_read_only_engineer_can_read_full_specification_but_cannot_post(self):
        self.reader("programs.view_program", "testing.view_test",
                    "testing.view_engineeringtestrequirement", "testing.view_testpoint",
                    "testing.view_testpointcondition")
        for url in self.urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(self.client.post(url, {"name": "Forged change"}).status_code, 405)
        self.program_a.refresh_from_db()
        self.assertEqual(self.program_a.name, "Synthetic Alpha")

    def test_workspace_program_detail_links_back_to_dashboard(self):
        response = self.client.get(reverse("record_detail", args=["programs", self.program_a.pk]))
        self.assertContains(response,
            f'<a class="button" href="{self.urls()[1]}">Open Program Dashboard</a>', html=True)

    def test_program_reader_can_follow_homepage_links_without_forbidden_matrix_links(self):
        self.reader("programs.view_program")
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{self.urls()[0]}"')
        self.assertContains(response, f'href="{self.urls()[1]}"')
        self.assertNotContains(response,
            f'href="{reverse("test_matrix", args=[self.program_a.pk])}"')
