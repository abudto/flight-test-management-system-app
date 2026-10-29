from django.contrib import admin

# Register your models here.
from .models import EngineeringTestRequirement, Test, TestPoint, TestPointCondition
from .models import TestCard, TestSequence, TestSequenceItem

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


@admin.register(TestCard)
class TestCardAdmin(admin.ModelAdmin):
    list_display = (
        "card_number",
        "title",
        "test",
        "revision",
    )
    search_fields = (
        "card_number",
        "title",
    )


class TestSequenceItemInline(admin.TabularInline):
    model = TestSequenceItem
    extra = 1


@admin.register(TestSequence)
class TestSequenceAdmin(admin.ModelAdmin):
    list_display = (
        "sequence_number",
        "title",
        "program",
        "revision",
        "planned_date",
    )

    search_fields = (
        "sequence_number",
        "title",
    )

    inlines = [TestSequenceItemInline]


@admin.register(TestSequenceItem)
class TestSequenceItemAdmin(admin.ModelAdmin):
    list_display = (
        "sequence",
        "order",
        "test_point",
        "test_card",
        "estimated_duration_min",
    )