from django.contrib import admin

# Register your models here.
from .models import EngineeringTestRequirement, Test


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

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = (
        'test_number',
        'test_title',
        'engineering_requirement',
    )
    search_fields = (
        'test_number',
        'test_title',
    )