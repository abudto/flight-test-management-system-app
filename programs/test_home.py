"""Homepage and shared navigation tests with synthetic program records."""

from html.parser import HTMLParser
from urllib.parse import urlsplit

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from programs.models import Program
from testing.test_support import PlanningDataMixin


class PageLinks(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs).get("href"))


class HomePageTests(PlanningDataMixin, TestCase):
    def test_root_renders_home_with_shared_base(self):
        self.assertEqual(reverse("home"), "/")
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "programs/home.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Flight Test Management System")
        self.assertContains(response, '<main id="main-content"', count=1)
        self.assertContains(response, 'aria-label="Main navigation"')
        self.assertContains(response, '<a href="/" aria-current="page">Home</a>', html=True)

    def test_each_program_links_to_its_existing_matrix(self):
        response = self.client.get(reverse("home"))
        for program in [self.program_a, self.program_b]:
            with self.subTest(program=program.name):
                self.assertContains(response, program.name)
                self.assertContains(response, f'href="{reverse("test_matrix", args=[program.pk])}"')
        self.assertQuerySetEqual(response.context["programs"], [self.program_a, self.program_b])

    def test_programs_are_ordered_by_name(self):
        first = Program.objects.create(name="Aardvark synthetic")
        response = self.client.get(reverse("home"))
        self.assertQuerySetEqual(response.context["programs"],
                                 [first, self.program_a, self.program_b])

    def test_empty_database_has_helpful_state_without_invented_matrix_links(self):
        # Deletions apply only to this TestCase's in-memory database.
        Program.objects.all().delete()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No programs yet.")
        self.assertContains(response, "Create a program in Django Admin")
        self.assertNotContains(response, "/testing/program/")

    def test_unimplemented_navigation_entries_are_not_links(self):
        response = self.client.get(reverse("home"))
        for label in ["Programs", "Test Cards", "Test Sequences", "Hazard Analysis"]:
            with self.subTest(label=label):
                self.assertContains(response,
                    f'<span class="nav-unavailable" aria-disabled="true">{label} '
                    '<small>Coming Soon</small></span>', html=True)
        self.assertContains(response, '<a href="/#test-matrices">Test Matrix</a>', html=True)
        self.assertContains(response, 'id="test-matrices"')

    def test_homepage_links_resolve_to_working_pages_or_anchors(self):
        response = self.client.get(reverse("home"))
        for href in set(PageLinks(response.content.decode()).links):
            with self.subTest(href=href):
                target = urlsplit(href)
                self.assertFalse(target.netloc)
                page = self.client.get(target.path or reverse("home"), follow=True)
                self.assertEqual(page.status_code, 200)
                if target.fragment:
                    self.assertContains(page, f'id="{target.fragment}"')

    def test_stylesheet_is_discoverable_without_dependencies(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, '/static/programs/css/ftms.css')
        self.assertIsNotNone(finders.find("programs/css/ftms.css"))
        self.assertContains(response, 'name="viewport"')
        self.assertNotContains(response, "<script")

    def test_program_text_is_escaped(self):
        self.program_a.name = '<script>alert("synthetic")</script>'
        self.program_a.save()
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, '<script>alert("synthetic")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_matrix_reuses_base_and_preserves_export_navigation(self):
        url = reverse("test_matrix", args=[self.program_a.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, f'<a href="{url}" aria-current="page">Test Matrix</a>',
                            html=True)
        self.assertContains(response, f'<a href="{reverse("export_test_matrix", args=[self.program_a.pk])}">Export Excel</a>',
                            html=True)
        self.assertContains(response, '<a href="/">Home</a>', html=True)
