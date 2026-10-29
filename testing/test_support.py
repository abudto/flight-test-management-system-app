"""Small synthetic model fixtures; no demo fixture or production data needed."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from programs.models import Program
from testing.models import EngineeringTestRequirement, Test, TestCard, TestPoint, TestSequence


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
