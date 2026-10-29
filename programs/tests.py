from django.test import TestCase

from programs.models import Aircraft
from testing.test_support import PlanningDataMixin


class AircraftProgramTests(PlanningDataMixin, TestCase):
    def test_aircraft_belong_to_separate_programs(self):
        aircraft_a = Aircraft.objects.create(
            program=self.program_a, aircraft_number="AC-01", aircraft_type="Synthetic",
        )
        aircraft_b = Aircraft.objects.create(
            program=self.program_b, aircraft_number="AC-02", aircraft_type="Synthetic",
        )
        aircraft_a.full_clean()
        aircraft_b.full_clean()
        self.assertQuerySetEqual(self.program_a.aircraft.all(), [aircraft_a])
        self.assertQuerySetEqual(self.program_b.aircraft.all(), [aircraft_b])

    def test_requirement_and_test_relations_remain_program_scoped(self):
        self.assertQuerySetEqual(
            self.program_a.engineering_requirements.all(), [self.requirement_a],
        )
        self.assertQuerySetEqual(self.requirement_a.tests.all(), [self.test_a])
        self.assertQuerySetEqual(self.requirement_b.tests.all(), [self.test_b])
