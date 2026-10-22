from django.contrib import admin

# Register your models here.
from .models import EngineeringTestRequirement, Test, TestPoint, TestPointCondition


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


@admin.register(TestPoint)
class TestPointAdmin(admin.ModelAdmin):
    list_display = (
        'test_point_number',
        'test',
        'weight_category',
        'cg_category',
        'target_speed',
        'target_altitude',
        'status',
    )

    search_fields = ('test_point_number',)


@admin.register(TestPointCondition)
class TestPointConditionAdmin(admin.ModelAdmin):
    list_display = (
        'test_point',
        'name',
        'value',
        'unit',
    )