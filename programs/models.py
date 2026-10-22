from django.db import models

# Create your models here.
class Program(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=30, default="Active")

    def __str__(self):
        return self.name


class Aircraft(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='aircraft',
    )

    aircraft_number = models.CharField(max_length=50)
    registration = models.CharField(max_length=50, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    aircraft_type = models.CharField(max_length=100)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return self.aircraft_number