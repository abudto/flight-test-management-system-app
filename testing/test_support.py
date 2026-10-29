"""Small synthetic model fixtures; no demo fixture or production data needed."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from programs.models import Program
from testing.models import (
    EngineeringTestRequirement, Test, TestCard, TestPoint, TestPointCondition, TestSequence,
)


class PlanningDataMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.program_a = Program.objects.create(name="Synthetic Alpha")
        cls.program_b = Program.objects.create(name="Synthetic Bravo")
        for suffix, program in [("a", cls.program_a), ("b", cls.program_b)]:
            requirement = EngineeringTestRequirement.objects.create(
                program=program, document_number="SPEC-01",
                document_title="Synthetic specification", purpose="Model testing",
            )
            test = Test.objects.create(
                engineering_requirement=requirement, test_number="TEST-01",
                test_title="Synthetic test", objective="Verify relationships",
            )
            point = TestPoint.objects.create(test=test, test_point_number="PT-01")
            card = TestCard.objects.create(
                test=test, card_number="CARD-01", title="Synthetic card",
                procedure="Synthetic procedure",
            )
            sequence = TestSequence.objects.create(
                program=program, sequence_number="SEQ-01", title="Synthetic sequence",
            )
            for name, obj in [("requirement", requirement), ("test", test),
                              ("point", point), ("card", card), ("sequence", sequence)]:
                setattr(cls, f"{name}_{suffix}", obj)


class ConstraintAssertionsMixin:
    def assert_duplicate_rejected(self, duplicate):
        """Check validation AND a direct write that bypasses full_clean()."""
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        # Roll back the failed write to a savepoint before making more queries.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate.save(force_insert=True)
        self.assertIsNone(duplicate.pk)


class MatrixDataMixin(PlanningDataMixin):
    """Enrich existing planning fixtures for HTML and workbook assertions."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_a.test_title = "Alpha performance test"
        cls.test_a.save()
        cls.test_b.test_title = "Bravo private test"
        cls.test_b.save()
        cls.point_a.weight_category = "heavy"
        cls.point_a.cg_category = "Forward"
        cls.point_a.target_speed = 147.5
        cls.point_a.target_altitude = 6500.0
        cls.point_a.repetition_required = 3
        cls.point_a.pass_fail_criteria = "Speed remains within tolerance"
        cls.point_a.status = "PLANNED"
        cls.point_a.remarks = "Alpha engineering remarks"
        cls.point_a.save()
        cls.point_b.test_point_number = "BRAVO-ONLY"
        cls.point_b.save()
        TestPointCondition.objects.create(
            test_point=cls.point_a, name="Temperature", value="15", unit="degC",
            tolerance="2", remarks="Synthetic condition",
        )
        TestPointCondition.objects.create(
            test_point=cls.point_a, name="Configuration", value="Clean",
        )
        TestPointCondition.objects.create(
            test_point=cls.point_b, name="Bravo-only condition", value="Excluded",
        )

    def add_ordering_points(self):
        """Create out of order; identifiers intentionally test lexical ordering."""
        later_test = Test.objects.create(
            engineering_requirement=self.requirement_a, test_number="TEST-02",
            test_title="Later test", objective="Synthetic ordering check",
        )
        later_point = TestPoint.objects.create(test=later_test, test_point_number="PT-00")
        point_2 = TestPoint.objects.create(test=self.test_a, test_point_number="PT-2")
        point_10 = TestPoint.objects.create(test=self.test_a, test_point_number="PT-10")
        return [self.point_a, point_10, point_2, later_point]
