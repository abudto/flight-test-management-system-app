"""Grouped sidebar navigation preserves existing routes and permission rules."""

from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from programs.workspace import RESOURCES
from testing.test_support import PlanningDataMixin


class SidebarMarkup(HTMLParser):
    def __init__(self, response):
        super().__init__()
        self.in_navigation = False
        self.links = []
        self.feed(response.content.decode())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "nav" and attrs.get("aria-label") == "Main navigation":
            self.in_navigation = True
        if self.in_navigation and tag == "a":
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == "nav":
            self.in_navigation = False


class SidebarNavigationTests(PlanningDataMixin, TestCase):
    def test_resources_are_grouped_once_with_no_lost_destinations(self):
        response = self.client.get(reverse("home"))
        groups = response.context["navigation_groups"]
        self.assertEqual([group["title"] for group in groups],
                         ["Workspace", "Test Planning", "Safety", "Reference Data"])
        keys = [item["key"] for group in groups for item in group["items"]]
        self.assertCountEqual(keys, list(RESOURCES))
        self.assertEqual(len(keys), len(set(keys)))
        navigation = SidebarMarkup(response)
        hrefs = [link["href"] for link in navigation.links]
        for key in RESOURCES:
            url = reverse("programs:program_list") if key == "programs" else reverse(
                "record_list", args=[key],
            )
            self.assertIn(url, hrefs)

    def test_only_one_sidebar_destination_is_current_for_each_page(self):
        cases = [
            (reverse("home"), reverse("home")),
            (reverse("programs:program_detail", args=[self.program_a.pk]),
             reverse("programs:program_list")),
            (reverse("record_list", args=["points"]), reverse("record_list", args=["points"])),
            (reverse("record_edit", args=["cards", self.card_a.pk]), reverse("record_list", args=["cards"])),
            (reverse("test_detail", args=[self.program_a.pk, self.test_a.pk]),
             reverse("test_list", args=[self.program_a.pk])),
            (reverse("test_matrix", args=[self.program_a.pk]),
             reverse("test_matrix", args=[self.program_a.pk])),
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                page = self.client.get(url)
                self.assertEqual(page.status_code, 200)
                active = [link["href"] for link in SidebarMarkup(page).links
                          if link.get("aria-current") == "page"]
                self.assertEqual(active, [expected])

    def test_restricted_reader_sees_only_authorized_groups_and_links(self):
        user = get_user_model().objects.create_user("synthetic-sidebar-reader")
        user.user_permissions.add(Permission.objects.get(
            content_type__app_label="programs", codename="view_program",
        ))
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual([group["title"] for group in response.context["navigation_groups"]],
                         ["Workspace"])
        self.assertEqual([link["href"] for link in SidebarMarkup(response).links],
                         [reverse("home"), reverse("programs:program_list")])
        self.assertNotContains(response, 'id="nav-administration"')

    def test_account_without_model_permissions_keeps_home_and_account_controls(self):
        user = get_user_model().objects.create_user("synthetic-no-permissions")
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual([link["href"] for link in SidebarMarkup(response).links], [reverse("home")])
        self.assertContains(response, f'href="{reverse("password_change")}"')
        self.assertContains(response, f'action="{reverse("logout")}"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_mobile_controls_and_skip_link_target_existing_landmarks(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'id="app-sidebar"', count=1)
        self.assertContains(response, 'aria-controls="app-sidebar"')
        self.assertContains(response, 'id="navigation-toggle"', count=1)
        self.assertContains(response, 'id="navigation-close"', count=1)
        self.assertContains(response, 'id="navigation-backdrop"', count=1)
        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'id="main-content"', count=1)

    def test_header_labels_program_context_and_unfiltered_workspace(self):
        response = self.client.get(reverse("programs:program_detail", args=[self.program_a.pk]))
        self.assertContains(response, f'Program: {self.program_a.name}')
        response = self.client.get(reverse("record_list", args=["tests"]))
        self.assertContains(response, "All programs")
        response = self.client.get(reverse("record_list", args=["tests"]),
                                   {"program": self.program_b.pk})
        self.assertContains(response, f"Program ID {self.program_b.pk}")

    def test_login_page_renders_navigation_and_sign_in_without_staff_links(self):
        self.client.logout()
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([link["href"] for link in SidebarMarkup(response).links], [reverse("home")])
        self.assertNotContains(response, 'id="nav-administration"')
