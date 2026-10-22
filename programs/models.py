from django.db import models

# Create your models here.
class Program(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=30, default="Active")

    def __str__(self):
        return self.name