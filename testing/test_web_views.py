"""Read-only specification navigation and program-scoped lookups."""

from django.test import TestCase
from django.urls import reverse

from programs.models import Program
from testing.models import Test, TestPoint, TestPointCondition
from testing.test_support import MatrixDataMixin


class TestManagementTests(MatrixDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_a.objective = "Verify Alpha planned performance"
        cls.test_a.test_procedure = "Establish condition\nRecord observations"
        cls.test_a.special_equipment = "Synthetic sensor package"
        cls.test_a.special_test_requirement = "Synthetic ground check"
        cls.test_a.pass_fail_criteria = "Test-level acceptance criteria"
        cls.test_a.related_regulation = "SYNTH-REG section 1"
        cls.test_a.remarks = "Synthetic test remarks"
        cls.test_a.save()
        cls.requirement_a.purpose = "Synthetic specification purpose"
        cls.requirement_a.remarks = "Synthetic requirement remarks"
        cls.requirement_a.save()

    def list_url(self, program=None):
        return reverse("test_list", args=[(program or self.program_a).pk])

    def detail_url(self, program=None, test=None):
        return reverse("test_detail", args=[(program or self.program_a).pk,
                                            (test or self.test_a).pk])

    def test_list_filters_program_and_links_correct_detail(self):
        for program, test, excluded in [
            (self.program_a, self.test_a, self.test_b),
            (self.program_b, self.test_b, self.test_a),
        ]:
            with self.subTest(program=program.name):
                response = self.client.get(self.list_url(program))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "testing/test_list.html")
                self.assertTemplateUsed(response, "base.html")
                self.assertQuerySetEqual(response.context["tests"], [test])
                self.assertContains(response, test.test_title)
                self.assertContains(response, test.test_number)
                self.assertContains(response, test.objective)
                self.assertContains(response, test.engineering_requirement.document_number)
                self.assertContains(response, f'href="{self.detail_url(program, test)}"')
                self.assertNotContains(response, excluded.test_title)

    def test_list_orders_tests_and_displays_point_count(self):
        later = Test.objects.create(
            engineering_requirement=self.requirement_a, test_number="TEST-02",
            test_title="Later synthetic test", objective="Synthetic objective",
        )
        response = self.client.get(self.list_url())
        self.assertQuerySetEqual(response.context["tests"], [self.test_a, later])
        self.assertEqual([test.point_count for test in response.context["tests"]], [1, 0])

    def test_empty_program_list(self):
        empty = Program.objects.create(name="Empty synthetic program")
        response = self.client.get(self.list_url(empty))
        self.assertContains(response, "No tests recorded for this program yet.")
        self.assertContains(response, f'href="{reverse("programs:program_detail", args=[empty.pk])}"')
        self.assertQuerySetEqual(response.context["tests"], [])

    def test_invalid_program_returns_404_for_both_pages(self):
        missing = max(self.program_a.pk, self.program_b.pk) + 1
        for url in [reverse("test_list", args=[missing]),
                    reverse("test_detail", args=[missing, self.test_a.pk])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_invalid_test_returns_404(self):
        missing = max(self.test_a.pk, self.test_b.pk) + 1
        self.assertEqual(self.client.get(reverse(
            "test_detail", args=[self.program_a.pk, missing],
        )).status_code, 404)

    def test_cross_program_detail_lookup_returns_404_in_both_directions(self):
        for program, test in [(self.program_a, self.test_b), (self.program_b, self.test_a)]:
            with self.subTest(program=program.name):
                self.assertEqual(self.client.get(self.detail_url(program, test)).status_code, 404)

    def test_detail_renders_specification_requirement_and_criteria(self):
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "testing/test_detail.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertEqual(response.context["test"], self.test_a)
        for text in [self.program_a.name, self.test_a.test_number, self.test_a.test_title,
                     self.test_a.objective, "Establish condition", "Record observations",
                     self.test_a.special_equipment, self.test_a.special_test_requirement,
                     self.test_a.pass_fail_criteria, self.test_a.related_regulation,
                     self.test_a.remarks, self.requirement_a.document_number,
                     self.requirement_a.document_title, self.requirement_a.purpose,
                     self.requirement_a.remarks, self.point_a.pass_fail_criteria]:
            self.assertContains(response, text)

    def test_detail_contains_only_this_tests_points(self):
        other = Test.objects.create(
            engineering_requirement=self.requirement_a, test_number="OTHER",
            test_title="Other test", objective="Synthetic objective",
        )
        TestPoint.objects.create(test=other, test_point_number="OTHER-TEST-POINT")
        response = self.client.get(self.detail_url())
        self.assertQuerySetEqual(response.context["test_points"], [self.point_a])
        self.assertContains(response, self.point_a.test_point_number)
        self.assertNotContains(response, "OTHER-TEST-POINT")
        self.assertNotContains(response, "BRAVO-ONLY")
        self.assertNotContains(response, "Bravo-only condition")

    def test_detail_orders_points_and_renders_all_of_them(self):
        point_2 = TestPoint.objects.create(test=self.test_a, test_point_number="PT-2")
        point_10 = TestPoint.objects.create(test=self.test_a, test_point_number="PT-10")
        response = self.client.get(self.detail_url())
        self.assertQuerySetEqual(response.context["test_points"],
                                 [self.point_a, point_10, point_2])
        for point in [self.point_a, point_10, point_2]:
            self.assertContains(response, f'<h3 id="point-{point.pk}">{point.test_point_number}</h3>',
                                html=True)

    def test_conditions_render_recorded_units_tolerances_and_remarks(self):
        response = self.client.get(self.detail_url())
        self.assertContains(response, """
            <tr><td>Temperature</td><td>15</td><td>degC</td><td>2</td>
            <td class="text-content">Synthetic condition</td></tr>
        """, html=True)
        self.assertContains(response, """
            <tr><td>Configuration</td><td>Clean</td><td>Not specified</td>
            <td>Not specified</td><td class="text-content">Not specified</td></tr>
        """, html=True)

    def test_numeric_and_condition_zero_remain_visible(self):
        self.point_a.target_speed = 0
        self.point_a.target_altitude = 0
        self.point_a.repetition_required = 0  # Existing model permits this; do not reinterpret it.
        self.point_a.save()
        TestPointCondition.objects.create(
            test_point=self.point_a, name="Zero condition", value="0", unit="kt", tolerance="0",
        )
        response = self.client.get(self.detail_url())
        for label in ["Target speed (kt)", "Target altitude (ft)"]:
            self.assertContains(response, f'<div><dt>{label}</dt><dd>0.0</dd></div>', html=True)
        self.assertContains(response,
            '<div><dt>Repetitions required</dt><dd>0</dd></div>', html=True)
        self.assertContains(response, """
            <tr><td>Zero condition</td><td>0</td><td>kt</td><td>0</td>
            <td class="text-content">Not specified</td></tr>
        """, html=True)

    def test_null_targets_and_blank_specification_are_explicit(self):
        self.point_a.target_speed = None
        self.point_a.target_altitude = None
        self.point_a.save()
        self.test_a.test_procedure = ""
        self.test_a.save()
        response = self.client.get(self.detail_url())
        for label in ["Target speed (kt)", "Target altitude (ft)", "Test procedure"]:
            self.assertContains(response,
                f'<div><dt>{label}</dt><dd>Not specified</dd></div>', html=True)

    def test_test_without_points_and_point_without_conditions(self):
        self.point_a.conditions.all().delete()
        self.assertContains(self.client.get(self.detail_url()),
                            "No conditions recorded for this test point.")
        self.point_a.delete()
        response = self.client.get(self.detail_url())
        self.assertContains(response, "No test points recorded for this test yet.")
        self.assertQuerySetEqual(response.context["test_points"], [])

    def test_navigation_dashboard_to_list_to_detail_and_back(self):
        dashboard_url = reverse("programs:program_detail", args=[self.program_a.pk])
        dashboard = self.client.get(dashboard_url)
        self.assertContains(dashboard, f'href="{self.list_url()}"')
        listing = self.client.get(self.list_url())
        self.assertContains(listing, f'href="{self.detail_url()}"')
        detail = self.client.get(self.detail_url())
        for url in [dashboard_url, self.list_url(),
                    reverse("test_matrix", args=[self.program_a.pk])]:
            self.assertContains(detail, f'href="{url}"')
        self.assertContains(detail,
            f'<a href="{self.list_url()}" aria-current="page">Tests</a>', html=True)

    def test_escaping_and_multiline_text(self):
        self.test_a.test_title = '<script>alert("synthetic")</script>'
        self.test_a.test_procedure = "First & <limit>\nSecond line"
        self.test_a.save()
        for url in [self.list_url(), self.detail_url()]:
            response = self.client.get(url)
            self.assertNotContains(response, self.test_a.test_title)
            self.assertContains(response, "&lt;script&gt;")
        self.assertContains(self.client.get(self.detail_url()),
                            "First &amp; &lt;limit&gt;<br>Second line", html=True)

    def test_pages_are_read_only(self):
        before = (Test.objects.count(), TestPoint.objects.count(), TestPointCondition.objects.count())
        for url in [self.list_url(), self.detail_url()]:
            response = self.client.get(url)
            # The shared header has a legitimate POST logout form; these pages
            # must not contain any engineering edit controls.
            self.assertNotContains(response, 'name="test_title"')
            self.assertNotContains(response, 'name="test_procedure"')
            self.assertEqual(self.client.post(url, {"test_title": "Unwanted change"}).status_code,
                             405)
        self.test_a.refresh_from_db()
        self.assertEqual(self.test_a.test_title, "Alpha performance test")
        self.assertEqual(before,
                         (Test.objects.count(), TestPoint.objects.count(), TestPointCondition.objects.count()))
