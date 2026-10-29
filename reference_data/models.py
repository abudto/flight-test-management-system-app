from django.db import models

# Create your models here.
from programs.models import Program
from testing.models import Test


class UnitDefinition(models.Model):
    quantity = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20, unique=True)
    to_si_factor = models.DecimalField(
        max_digits=18,
        decimal_places=10,
        default=1,
    )

    def __str__(self):
        return self.symbol


class MeasurementDefinition(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    quantity = models.CharField(max_length=50)
    default_unit = models.ForeignKey(
        UnitDefinition,
        on_delete=models.PROTECT,
        related_name="measurements",
    )

    def __str__(self):
        return self.code


class Regulation(models.Model):
    code = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    authority = models.CharField(max_length=100)
    revision = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.code} - {self.title}"


class RegulatoryRequirement(models.Model):
    regulation = models.ForeignKey(
        Regulation,
        on_delete=models.PROTECT,
        related_name="requirements"
    )
    section = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return f"{self.regulation.code} {self.section}"


class CrewMember(models.Model):
    full_name = models.CharField(max_length=150)
    nickname = models.CharField(max_length=20)
    employee_id = models.CharField(
        max_length=50,
        blank=True
    )
    organization = models.CharField(
        max_length=150,
        blank=True,
    )
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name


class FTHAHazard(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="hazards",
    )
    test = models.ForeignKey(
        Test,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazards",
    )

    hazard_id = models.CharField(max_length=50)
    description = models.TextField()
    cause = models.TextField(blank=True)
    consequence = models.TextField(blank=True)
    mitigation = models.TextField()
    severity = models.CharField(
        max_length=30,
        blank=True
    )
    probability = models.CharField(
        max_length=30,
        blank=True,
    )
    remarks = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["program", "hazard_id"],
                name="unique_hazard_per_program",
            )
        ]

    def __str__(self):
        return self.hazard_id