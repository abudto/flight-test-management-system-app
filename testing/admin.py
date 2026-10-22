from django.contrib import admin

# Register your models here.
from .models import EngineeringTestRequirement


@admin.register(EngineeringTestRequirement)
class EngineeringTestRequirementAdmin(admin.ModelAdmin):
    list_display = (
        'document_number',
        'document_title',
        'program',
    )
    search_fields = (
        'document_number',
        'document_title',
    )