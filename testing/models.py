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