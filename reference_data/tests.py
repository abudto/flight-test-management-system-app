from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from reference_data.models import (
    FTHAHazard, MeasurementDefinition, Regulation, RegulatoryRequirement, UnitDefinition,
)
from testing.test_support import ConstraintAssertionsMixin, PlanningDataMixin


class HazardModelTests(ConstraintAssertionsMixin, PlanningDataMixin, TestCase):
    def hazard(self, **overrides):
        values = dict(program=self.program_a, test=self.test_a, hazard_id="HAZ-01",
                      description="Synthetic hazard", mitigation="Synthetic mitigation")
        values.update(overrides)
        return FTHAHazard(**values)

    def test_matching_program_and_test_are_valid(self):
        hazard = self.hazard()
        hazard.full_clean()
        hazard.save()
        self.assertQuerySetEqual(self.program_a.hazards.all(), [hazard])
        self.assertFalse(self.program_b.hazards.exists())

    def test_foreign_program_test_is_rejected(self):
        with self.assertRaises(ValidationError) as error:
            self.hazard(test=self.test_b).full_clean()
        self.assertIn("test", error.exception.message_dict)

    def test_test_is_optional(self):
        hazard = self.hazard(test=None)
        hazard.full_clean()
        hazard.save()
        hazard.refresh_from_db()
        self.assertIsNone(hazard.test_id)

    def test_existing_hazard_cannot_be_validated_with_foreign_program(self):
        hazard = self.hazard()
        hazard.save()
        hazard.program = self.program_b
        with self.assertRaises(ValidationError) as error:
            hazard.full_clean()
        self.assertIn("test", error.exception.message_dict)

    def test_duplicate_hazard_identity_is_rejected(self):
        self.hazard().save()
        self.assert_duplicate_rejected(self.hazard())

    def test_same_hazard_identifier_is_allowed_in_another_program(self):
        for program, test in [(self.program_a, self.test_a),
                              (self.program_b, self.test_b)]:
            hazard = self.hazard(program=program, test=test)
            hazard.full_clean()
            hazard.save()
        self.assertEqual(FTHAHazard.objects.count(), 2)

    def test_deleting_test_keeps_program_hazard(self):
        hazard = self.hazard()
        hazard.save()
        self.test_a.delete()
        hazard.refresh_from_db()
        self.assertIsNone(hazard.test_id)
        self.assertEqual(hazard.program_id, self.program_a.pk)


class ReferenceConstraintTests(ConstraintAssertionsMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unit = UnitDefinition.objects.create(quantity="length", name="metre", symbol="m")
        cls.measurement = MeasurementDefinition.objects.create(
            name="Synthetic altitude", code="ALT", quantity="length", default_unit=cls.unit,
        )
        cls.regulation = Regulation.objects.create(
            code="SYNTH-REG", title="Synthetic regulation", authority="Synthetic authority",
        )
        cls.requirement = RegulatoryRequirement.objects.create(
            regulation=cls.regulation, section="1", description="Synthetic requirement",
        )

    def test_duplicate_unit_symbol_is_rejected(self):
        self.assert_duplicate_rejected(UnitDefinition(
            quantity="length", name="Another metre", symbol="m",
        ))

    def test_duplicate_measurement_code_is_rejected(self):
        self.assert_duplicate_rejected(MeasurementDefinition(
            name="Another altitude", code="ALT", quantity="length", default_unit=self.unit,
        ))

    def test_referenced_unit_is_protected(self):
        with self.assertRaises(ProtectedError) as error:
            self.unit.delete()
        self.assertIn(self.measurement, error.exception.protected_objects)
        self.measurement.refresh_from_db()
        self.assertEqual(self.measurement.default_unit_id, self.unit.pk)
        self.assertTrue(UnitDefinition.objects.filter(pk=self.unit.pk).exists())

    def test_referenced_regulation_is_protected(self):
        with self.assertRaises(ProtectedError) as error:
            self.regulation.delete()
        self.assertIn(self.requirement, error.exception.protected_objects)
        self.requirement.refresh_from_db()
        self.assertEqual(self.requirement.regulation_id, self.regulation.pk)
        self.assertTrue(Regulation.objects.filter(pk=self.regulation.pk).exists())
