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