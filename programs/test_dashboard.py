"""Program dashboards use existing planning relationships and synthetic data."""

from django.test import TestCase
from django.urls import reverse

from programs.models import Aircraft, Program
from programs.test_home import PageLinks
from reference_data.models import FTHAHazard
from testing.models import EngineeringTestRequirement, Test, TestCard, TestPoint, TestSequence
from testing.test_support import PlanningDataMixin


class ProgramDashboardTests(PlanningDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.program_a.description = "Synthetic Alpha development program"
        cls.program_a.status = "Active"
        cls.program_a.save()
        cls.aircraft_a = Aircraft.objects.create(
            program=cls.program_a, aircraft_number="ALPHA-AC-02", aircraft_type="Synthetic jet",
            registration="SYN-ALPHA", serial_number="SERIAL-A", remarks="Alpha-only aircraft notes",
        )
        cls.aircraft_first = Aircraft.objects.create(
            program=cls.program_a, aircraft_number="ALPHA-AC-01", aircraft_type="Synthetic jet",
        )
        cls.aircraft_b = Aircraft.objects.create(
            program=cls.program_b, aircraft_number="BRAVO-AC", aircraft_type="Bravo-only type",
        )
        second_test = Test.objects.create(
            engineering_requirement=cls.requirement_a, test_number="TEST-02",
            test_title="Second Alpha test", objective="Synthetic objective",
        )
        second_requirement = EngineeringTestRequirement.objects.create(
            program=cls.program_a, document_number="SPEC-02", document_title="Second specification",
            purpose="Verify count across requirements",
        )
        third_test = Test.objects.create(
            engineering_requirement=second_requirement, test_number="TEST-03",
            test_title="Third Alpha test", objective="Synthetic objective",
        )
        for number in ["PT-02", "PT-03"]:
            TestPoint.objects.create(test=second_test, test_point_number=number)
        for revision in ["A", "B"]:
            TestCard.objects.create(
                test=second_test, card_number="CARD-02", revision=revision,
                title="Synthetic revision", procedure="Synthetic procedure",
            )
        TestCard.objects.create(
            test=third_test, card_number="CARD-03", title="Synthetic card",
            procedure="Synthetic procedure",
        )
        TestSequence.objects.create(program=cls.program_a, sequence_number="SEQ-02", title="Second")
        for program, test, number in [(cls.program_a, cls.test_a, "HAZ-01"),
                                      (cls.program_a, None, "HAZ-02"),
                                      (cls.program_b, cls.test_b, "HAZ-B")]:
            FTHAHazard.objects.create(
                program=program, test=test, hazard_id=number,
                description="Synthetic hazard", mitigation="Synthetic mitigation",
            )

    def detail(self, program=None):
        return self.client.get(reverse(
            "programs:program_detail", args=[(program or self.program_a).pk],
        ))

    def test_program_list_displays_available_identity_fields_and_detail_links(self):
        response = self.client.get(reverse("programs:program_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "programs/program_list.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Program ID")
        self.assertContains(response, "Synthetic Alpha development program")
        self.assertContains(response, "Active")
        for program in [self.program_a, self.program_b]:
            self.assertContains(response, f'<td>{program.pk}</td>', html=True)
            self.assertContains(response, f'<a href="{reverse("programs:program_detail", args=[program.pk])}">{program.name}</a>', html=True)

    def test_program_list_orders_by_name(self):
        first = Program.objects.create(name="Aardvark synthetic")
        response = self.client.get(reverse("programs:program_list"))
        self.assertQuerySetEqual(response.context["programs"],
                                 [first, self.program_a, self.program_b])

    def test_program_list_empty_state(self):
        Program.objects.all().delete()
        response = self.client.get(reverse("programs:program_list"))
        self.assertContains(response, "No programs yet.")
        self.assertContains(response, f'href="{reverse("admin:index")}"')
        self.assertQuerySetEqual(response.context["programs"], [])

    def test_detail_displays_program_and_aircraft_identity(self):
        response = self.detail()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "programs/program_detail.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertEqual(response.context["program"], self.program_a)
        for value in [self.program_a.name, self.program_a.description, self.program_a.status,
                      "Synthetic jet", "SYN-ALPHA", "SERIAL-A", "Alpha-only aircraft notes"]:
            self.assertContains(response, value)
        self.assertContains(response, f"Program ID {self.program_a.pk}")

    def test_counts_are_program_scoped_and_include_all_revisions(self):
        for program, expected in [
            (self.program_a, {"Tests": 3, "Test Points": 3, "Test Cards": 4,
                              "Test Sequences": 2, "Hazard Records": 2}),
            (self.program_b, {"Tests": 1, "Test Points": 1, "Test Cards": 1,
                              "Test Sequences": 1, "Hazard Records": 1}),
        ]:
            with self.subTest(program=program.name):
                response = self.detail(program)
                self.assertEqual(response.context["counts"], expected)
                for label, count in expected.items():
                    self.assertContains(response,
                        f'<div class="metric-card"><dt>{label}</dt><dd>{count}</dd></div>',
                        html=True)

    def test_aircraft_are_filtered_and_ordered_with_no_other_program_data(self):
        response = self.detail()
        self.assertQuerySetEqual(response.context["aircraft"], [self.aircraft_first, self.aircraft_a])
        self.assertNotContains(response, "BRAVO-AC")
        self.assertNotContains(response, "Bravo-only type")
        self.assertNotContains(response, "Synthetic Bravo")
        response_b = self.detail(self.program_b)
        self.assertQuerySetEqual(response_b.context["aircraft"], [self.aircraft_b])
        self.assertNotContains(response_b, "ALPHA-AC")

    def test_empty_program_has_zero_counts_and_helpful_aircraft_state(self):
        empty = Program.objects.create(name="Empty synthetic program")
        response = self.detail(empty)
        self.assertContains(response, "No aircraft assigned to this program yet.")
        self.assertContains(response, "No description provided.")
        self.assertEqual(response.context["counts"], {
            "Tests": 0, "Test Points": 0, "Test Cards": 0,
            "Test Sequences": 0, "Hazard Records": 0,
        })
        self.assertQuerySetEqual(response.context["aircraft"], [])

    def test_missing_program_returns_404(self):
        missing_id = max(self.program_a.pk, self.program_b.pk) + 1
        self.assertEqual(self.client.get(reverse(
            "programs:program_detail", args=[missing_id],
        )).status_code, 404)

    def test_navigation_preserves_requested_program_and_marks_programs_active(self):
        for program in [self.program_a, self.program_b]:
            with self.subTest(program=program.name):
                response = self.detail(program)
                self.assertContains(response,
                    f'<a href="{reverse("programs:program_list")}" aria-current="page">Programs</a>', html=True)
                self.assertContains(response,
                    f'<a href="{reverse("test_matrix", args=[program.pk])}">Test Matrix</a>', html=True)
                for name in ["home", "programs:program_list", "admin:index"]:
                    self.assertContains(response, f'href="{reverse(name)}"')

    def test_dashboard_links_resolve_without_broken_destinations(self):
        from urllib.parse import urlsplit

        for href in set(PageLinks(self.detail().content.decode()).links):
            with self.subTest(href=href):
                target = urlsplit(href)
                page = self.client.get(target.path or reverse(
                    "programs:program_detail", args=[self.program_a.pk],
                ), follow=True)
                self.assertEqual(page.status_code, 200)
                if target.fragment:
                    self.assertContains(page, f'id="{target.fragment}"')

    def test_dashboard_links_to_real_program_filtered_workspaces(self):
        response = self.detail()
        for key in ["requirements", "tests", "points", "cards", "sequences", "hazards"]:
            with self.subTest(key=key):
                url = reverse("record_list", args=[key]) + f"?program={self.program_a.pk}"
                self.assertContains(response, f'href="{url}"')
                page = self.client.get(url)
                self.assertEqual(page.status_code, 200)
                self.assertEqual(page.context["selected_program"], str(self.program_a.pk))

    def test_program_text_is_escaped_on_list_and_dashboard(self):
        self.program_a.name = '<script>alert("synthetic")</script>'
        self.program_a.description = "<b>Literal description</b>"
        self.program_a.save()
        for url in [reverse("programs:program_list"),
                    reverse("programs:program_detail", args=[self.program_a.pk])]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotContains(response, self.program_a.name)
                self.assertContains(response, "&lt;script&gt;")
                self.assertContains(response, "&lt;b&gt;Literal description&lt;/b&gt;")

    def test_homepage_links_to_program_list_and_each_dashboard(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("programs:program_list")}"')
        for program in [self.program_a, self.program_b]:
            self.assertContains(response,
                f'href="{reverse("programs:program_detail", args=[program.pk])}"')
