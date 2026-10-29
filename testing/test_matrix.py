"""HTTP and rendered matrix behavior; no authorization policy is implied."""

from django.test import TestCase
from django.urls import reverse

from programs.models import Program
from testing.test_support import MatrixDataMixin


class TestMatrixTests(MatrixDataMixin, TestCase):
    def matrix(self, program=None):
        return self.client.get(reverse(
            "test_matrix", args=[(program or self.program_a).pk],
        ))

    def test_matrix_filters_requested_program(self):
        response = self.matrix()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "testing/test_matrix.html")
        self.assertEqual(response.context["program"], self.program_a)
        self.assertQuerySetEqual(response.context["test_points"], [self.point_a])
        self.assertContains(response, "Alpha performance test")
        self.assertNotContains(response, "BRAVO-ONLY")
        self.assertNotContains(response, "Bravo private test")
        response_b = self.matrix(self.program_b)
        self.assertQuerySetEqual(response_b.context["test_points"], [self.point_b])
        self.assertContains(response_b, "BRAVO-ONLY")
        self.assertNotContains(response_b, "Alpha performance test")

    def test_matrix_orders_by_test_then_point_identifier(self):
        expected = self.add_ordering_points()
        response = self.matrix()
        self.assertQuerySetEqual(response.context["test_points"], expected)
        body = response.content.decode()
        positions = [body.index(f"<td>{point.test_point_number}</td>") for point in expected]
        self.assertEqual(positions, sorted(positions))

    def test_empty_program_has_empty_state(self):
        empty = Program.objects.create(name="Empty synthetic program")
        response = self.matrix(empty)
        self.assertContains(response, "No test points found for this program.")
        self.assertQuerySetEqual(response.context["test_points"], [])
        self.assertNotContains(response, "Alpha performance test")

    def test_missing_program_returns_404(self):
        missing_id = max(self.program_a.pk, self.program_b.pk) + 1
        self.assertEqual(self.client.get(reverse("test_matrix", args=[missing_id])).status_code,
                         404)

    def test_matrix_displays_engineering_values_and_choice_labels(self):
        response = self.matrix()
        self.assertContains(response, "Program: Synthetic Alpha")
        self.assertContains(response, "<th>Speed (kt)</th>", html=True)
        self.assertContains(response, "<th>Altitude (ft)</th>", html=True)
        self.assertContains(response, """
            <tr><td>PT-01</td><td>Alpha performance test</td>
            <td>HEAVY</td><td>FWD</td><td>147.5</td><td>6500.0</td>
            <td>3</td><td>PLANNED</td></tr>
        """, html=True)

    def test_zero_targets_are_displayed_as_numbers(self):
        self.point_a.target_speed = 0
        self.point_a.target_altitude = 0
        self.point_a.save()
        self.assertContains(self.matrix(), """
            <tr><td>PT-01</td><td>Alpha performance test</td>
            <td>HEAVY</td><td>FWD</td><td>0.0</td><td>0.0</td>
            <td>3</td><td>PLANNED</td></tr>
        """, html=True)

    def test_missing_targets_are_displayed_as_dashes(self):
        self.point_a.target_speed = None
        self.point_a.target_altitude = None
        self.point_a.save()
        self.assertContains(self.matrix(), """
            <tr><td>PT-01</td><td>Alpha performance test</td>
            <td>HEAVY</td><td>FWD</td><td>-</td><td>-</td>
            <td>3</td><td>PLANNED</td></tr>
        """, html=True)

    def test_excel_link_targets_requested_program(self):
        url = reverse("export_test_matrix", args=[self.program_a.pk])
        self.assertContains(self.matrix(), f'<a href="{url}">Export Excel</a>', html=True)
