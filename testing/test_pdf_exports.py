"""Inspect real PDF responses; text inspection does not establish visual quality.

Known defect: a sequence table row taller than a page raises LayoutError.
The expected-failure test requires a successful export retaining all its text.
Remove its marker when row pagination is fixed; do not truncate the content.
"""

from datetime import date
from io import BytesIO
from unittest import expectedFailure

from django.test import TestCase
from django.urls import reverse
from pypdf import PdfReader

from testing.models import TestPoint, TestSequenceItem
from testing.test_support import MatrixDataMixin


class PDFDataMixin(MatrixDataMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_a.objective = "Verify synthetic performance"
        cls.test_a.pass_fail_criteria = "Maintain specified limits"
        cls.test_a.save()
        cls.card_a.title = "Alpha performance card"
        cls.card_a.revision = "C"
        cls.card_a.preparation = "Check synthetic instrumentation"
        cls.card_a.procedure = "Establish target condition\nRecord observations"
        cls.card_a.safety_notes = "Abort on synthetic limit exceedance"
        cls.card_a.remarks = "Card engineering notes"
        cls.card_a.save()
        cls.card_b.card_number = "BRAVO-CARD"
        cls.card_b.save()
        cls.sequence_a.title = "Alpha flight sequence"
        cls.sequence_a.revision = "D"
        cls.sequence_a.planned_date = date(2026, 11, 5)
        cls.sequence_a.objective = "Collect synthetic performance observations"
        cls.sequence_a.remarks = "Sequence engineering notes"
        cls.sequence_a.save()
        cls.point_second = TestPoint.objects.create(
            test=cls.test_a, test_point_number="PT-02",
        )
        cls.point_unassigned = TestPoint.objects.create(
            test=cls.test_a, test_point_number="UNASSIGNED-POINT",
        )
        # Insert in reverse execution order so an unsorted export fails.
        cls.second_item = TestSequenceItem.objects.create(
            sequence=cls.sequence_a, order=20, test_point=cls.point_second,
            test_card=cls.card_a, estimated_duration_min=7,
        )
        cls.first_item = TestSequenceItem.objects.create(
            sequence=cls.sequence_a, order=10, test_point=cls.point_a,
            test_card=cls.card_a, estimated_duration_min=11,
        )
        TestSequenceItem.objects.create(
            sequence=cls.sequence_b, order=1, test_point=cls.point_b, test_card=cls.card_b,
        )

    def read_pdf(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        reader = PdfReader(BytesIO(response.content), strict=True)
        self.assertGreaterEqual(len(reader.pages), 1)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertTrue(text.strip())
        return reader, text

    def pdf_text(self, response):
        return " ".join(self.read_pdf(response)[1].split())


class TestCardPDFTests(PDFDataMixin, TestCase):
    def export(self, card=None):
        return self.client.get(reverse("export_card_pdf", args=[(card or self.card_a).pk]))

    def test_response_and_revision_filename(self):
        response = self.export()
        self.read_pdf(response)
        self.assertEqual(response["Content-Disposition"],
                         f'attachment; filename="FTC_{self.card_a.pk}_Rev_C.pdf"')

    def test_program_test_and_card_identity(self):
        text = self.pdf_text(self.export())
        for expected in ["FLIGHT TEST CARD", "Synthetic Alpha", "CARD-01 | Rev C",
                         "Alpha performance card", "TEST-01", "Verify synthetic performance"]:
            self.assertIn(expected, text)
        self.assertNotIn("Synthetic Bravo", text)
        self.assertNotIn("BRAVO-CARD", text)

    def test_preparation_procedure_criteria_and_safety_notes(self):
        text = self.pdf_text(self.export())
        for expected in ["Check synthetic instrumentation", "Establish target condition",
                         "Record observations", "Maintain specified limits",
                         "Abort on synthetic limit exceedance", "Card engineering notes"]:
            self.assertIn(expected, text)

    def test_only_assigned_points_appear(self):
        text = self.pdf_text(self.export())
        self.assertIn("PT-01", text)
        self.assertIn("PT-02", text)
        self.assertNotIn("UNASSIGNED-POINT", text)
        self.assertNotIn("BRAVO-ONLY", text)

    def test_repeated_point_assignments_do_not_duplicate_rows(self):
        TestSequenceItem.objects.create(
            sequence=self.sequence_a, order=30, test_point=self.point_a,
            test_card=self.card_a,
        )
        _, raw_text = self.read_pdf(self.export())
        lines = [line.strip() for line in raw_text.splitlines()]
        self.assertEqual(lines.count("PT-01"), 1)
        self.assertEqual(lines.count("PT-02"), 1)

    def test_assigned_point_conditions_and_choice_labels(self):
        text = self.pdf_text(self.export())
        for expected in ["HEAVY", "FWD", "Temperature: 15 degC", "Configuration: Clean"]:
            self.assertIn(expected, text)
        self.assertNotIn("Bravo-only condition", text)

    def test_card_without_assigned_points_still_exports(self):
        self.card_a.sequence_items.all().delete()
        text = self.pdf_text(self.export())
        self.assertIn("Associated Test Points", text)
        self.assertIn("CARD-01 | Rev C", text)
        self.assertIn("Establish target condition", text)
        self.assertNotIn("PT-01", text)
        self.assertNotIn("PT-02", text)

    def test_special_characters_are_literal_and_multiline_content_is_retained(self):
        self.card_a.procedure = 'FIRST: A & B <limit> > 0 "quoted"\nSECOND: record <b>literal</b>'
        self.card_a.safety_notes = "Stay within limits & stop > threshold"
        self.card_a.save()
        text = self.pdf_text(self.export())
        first = 'FIRST: A & B <limit> > 0 "quoted"'
        second = "SECOND: record <b>literal</b>"
        self.assertIn(first, text)
        self.assertIn(second, text)
        self.assertLess(text.index(first), text.index(second))
        self.assertIn("Stay within limits & stop > threshold", text)

    def test_missing_card_returns_404(self):
        missing_id = max(self.card_a.pk, self.card_b.pk) + 1
        self.assertEqual(self.client.get(reverse("export_card_pdf", args=[missing_id])).status_code,
                         404)


class TestSequencePDFTests(PDFDataMixin, TestCase):
    def export(self, sequence=None):
        return self.client.get(reverse(
            "export_sequence_pdf", args=[(sequence or self.sequence_a).pk],
        ))

    def test_response_and_revision_filename(self):
        response = self.export()
        self.read_pdf(response)
        self.assertEqual(response["Content-Disposition"],
                         f'attachment; filename="FTS_{self.sequence_a.pk}_Rev_D.pdf"')

    def test_program_sequence_and_planning_identity(self):
        text = self.pdf_text(self.export())
        for expected in ["FLIGHT TEST SEQUENCE", "Synthetic Alpha", "SEQ-01 | Rev D",
                         "Alpha flight sequence", "2026-11-05",
                         "Collect synthetic performance observations", "Sequence engineering notes"]:
            self.assertIn(expected, text)
        self.assertNotIn("Synthetic Bravo", text)
        self.assertNotIn("BRAVO-ONLY", text)
        self.assertNotIn("BRAVO-CARD", text)
        self.assertNotIn("UNASSIGNED-POINT", text)

    def test_execution_order_follows_item_order(self):
        text = self.pdf_text(self.export())
        self.assertLess(text.index("PT-01"), text.index("PT-02"))
        self.assertIn("CARD-01", text)

    def test_total_planned_duration_is_sum_of_items(self):
        self.assertIn("Total estimated test duration: 18 minutes", self.pdf_text(self.export()))

    def test_optional_card_and_missing_duration_preserve_item(self):
        self.first_item.test_card = None
        self.first_item.estimated_duration_min = None
        self.first_item.save()
        text = self.pdf_text(self.export())
        self.assertIn("PT-01", text)
        self.assertIn("PT-02", text)
        self.assertIn("Total estimated test duration: 7 minutes", text)
        # The missing card/duration cells are rendered as dashes, not Python None.
        self.assertNotIn("None", text)
        _, raw_text = self.read_pdf(self.export())
        self.assertGreaterEqual([line.strip() for line in raw_text.splitlines()].count("-"), 2)

    def test_empty_sequence_still_exports_with_zero_duration(self):
        self.sequence_a.items.all().delete()
        text = self.pdf_text(self.export())
        self.assertIn("Execution Sequence", text)
        self.assertIn("SEQ-01 | Rev D", text)
        self.assertIn("Total estimated test duration: 0 minutes", text)
        self.assertNotIn("PT-01", text)
        self.assertNotIn("PT-02", text)

    def test_missing_planned_date_has_explicit_placeholder(self):
        self.sequence_a.planned_date = None
        self.sequence_a.save()
        self.assertIn("Planned date: Not scheduled", self.pdf_text(self.export()))

    def test_special_characters_and_multiline_notes_are_retained(self):
        self.sequence_a.remarks = "FIRST: A & B <limit>\nSECOND: keep <b>literal</b> > 0"
        self.sequence_a.save()
        self.first_item.remarks = "A & B < 5"
        self.first_item.save()
        text = self.pdf_text(self.export())
        for expected in ["FIRST: A & B <limit>", "SECOND: keep <b>literal</b> > 0", "A & B < 5"]:
            self.assertIn(expected, text)
        self.assertLess(text.index("FIRST:"), text.index("SECOND:"))

    def test_missing_sequence_returns_404(self):
        missing_id = max(self.sequence_a.pk, self.sequence_b.pk) + 1
        self.assertEqual(self.client.get(reverse(
            "export_sequence_pdf", args=[missing_id],
        )).status_code, 404)

    @expectedFailure
    def test_oversized_row_exports_without_losing_required_content(self):
        """Known defect: ReportLab cannot split this tall sequence table row."""
        self.first_item.remarks = "ROWSTART\n" + "overflow line\n" * 150 + "ROWEND"
        self.first_item.save()
        text = self.pdf_text(self.export())
        self.assertIn("ROWSTART", text)
        self.assertIn("ROWEND", text)
        self.assertEqual(text.count("overflow line"), 150)
        self.assertIn("PT-01", text)
        self.assertIn("PT-02", text)
        self.assertIn("Total estimated test duration: 18 minutes", text)
