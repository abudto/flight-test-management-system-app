from django.db import models

# Create your models here.
from programs.models import Program


class EngineeringTestRequirement(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='engineering_requirements',
    )

    document_number = models.CharField(max_length=100)
    document_title = models.CharField(max_length=200)
    purpose = models.TextField()
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f'{self.document_number} - {self.document_title}'


class Test(models.Model):
    engineering_requirement = models.ForeignKey(
        EngineeringTestRequirement,
        on_delete=models.CASCADE,
        related_name='tests',
    )

    test_number = models.CharField(max_length=50)
    test_title = models.CharField(max_length=200)
    objective = models.TextField()

    special_equipment = models.TextField(blank=True)
    special_test_requirement = models.TextField(blank=True)
    test_procedure = models.TextField(blank=True)
    pass_fail_criteria = models.TextField(blank=True)
    related_regulation = models.CharField(
        max_length=200,
        blank=True
    )
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f'{self.test_number} - {self.test_title}'


class TestPoint(models.Model):
    class WeightCategory(models.TextChoices):
        light = 'light', 'LIGHT'
        medium = 'medium', 'MEDIUM'
        heavy = 'heavy', 'HEAVY'

    class CgCategory(models.TextChoices):
        forward = 'Forward', 'FWD'
        mid = 'Mid', 'MID'
        aft = 'Aft', 'AFT'


    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name='test_points',
    )

    test_point_number = models.CharField(max_length=50)
    weight_category = models.CharField(max_length=30, blank=True, choices=WeightCategory.choices)
    cg_category = models.CharField(max_length=30, blank=True, choices=CgCategory.choices)
    target_speed = models.FloatField(null=True, blank=True)
    target_altitude = models.FloatField(null=True, blank=True)
    repetition_required = models.PositiveBigIntegerField(default=1,)
    pass_fail_criteria = models.TextField(blank=True)
    status = models.CharField(max_length=30, default='PLANNED',)

    remarks = models.TextField(blank=True)

    def __str__(self):
        return self.test_point_number

class TestPointCondition(models.Model):
    test_point = models.ForeignKey(
        TestPoint,
        on_delete=models.CASCADE,
        related_name='conditions',
    )

    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    unit = models.CharField(max_length=30, blank=True)
    tolerance = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f'{self.name}: {self.value} {self.unit}'.strip()