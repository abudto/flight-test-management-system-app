from django.contrib import admin

# Register your models here.
from .models import (
    UnitDefinition,
    MeasurementDefinition,
    Regulation,
    RegulatoryRequirement,
    CrewMember,
    FTHAHazard
)

@admin.register(UnitDefinition)
class UnitDefinitionAdmin(admin.ModelAdmin):
    list_display = ("quantity", "name", "symbol", "to_si_factor")
    search_fields = ("name", "symbol")


@admin.register(MeasurementDefinition)
class MeasurementDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "quantity", "default_unit")
    search_fields = ("code", "name")


@admin.register(Regulation)
class RegulationAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "authority", "revision")
    search_fields = ("code", "title", "authority")


@admin.register(RegulatoryRequirement)
class RegulatoryRequirementAdmin(admin.ModelAdmin):
    list_display = ("regulation", "section")
    search_fields = ("section",)


@admin.register(CrewMember)
class CrewMemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "nickname", "employee_id", "organization", "active")
    search_fields = ("full_name", "employee_id")


@admin.register(FTHAHazard)
class FTHAHazardAdmin(admin.ModelAdmin):
    list_display = ("hazard_id", "program", "test", "severity", "probability")
    list_filter = ("program", "severity", "probability")
    search_fields = ("hazard_id", "description")
