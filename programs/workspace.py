"""Server-rendered planning workspace using an explicit model/field registry.

Permissions are Django model permissions, not program membership. Parent links
are immutable on edit so moving a parent cannot invalidate its descendants.
"""
from dataclasses import dataclass
from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction, models
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from programs.models import Program, Aircraft
from testing.models import (EngineeringTestRequirement, Test, TestPoint,
                            TestPointCondition, TestCard, TestSequence, TestSequenceItem)
from reference_data.models import (FTHAHazard, UnitDefinition, MeasurementDefinition,
                                   Regulation, RegulatoryRequirement, CrewMember)


@dataclass(frozen=True)
class Resource:
    model: type
    title: str
    fields: tuple
    columns: tuple
    program_path: str = ""
    parent: str = ""


RESOURCES = {
    "programs": Resource(Program, "Programs", ("name", "description", "status"), ("name", "status"), "pk"),
    "aircraft": Resource(Aircraft, "Aircraft", ("program", "aircraft_number", "registration", "serial_number", "aircraft_type", "remarks"), ("aircraft_number", "aircraft_type", "program"), "program", "program"),
    "requirements": Resource(EngineeringTestRequirement, "Engineering requirements", ("program", "document_number", "document_title", "purpose", "remarks"), ("document_number", "document_title", "program"), "program", "program"),
    "tests": Resource(Test, "Tests", ("engineering_requirement", "test_number", "test_title", "objective", "special_equipment", "special_test_requirement", "test_procedure", "pass_fail_criteria", "related_regulation", "remarks"), ("test_number", "test_title", "engineering_requirement"), "engineering_requirement__program", "engineering_requirement"),
    "points": Resource(TestPoint, "Test points", ("test", "test_point_number", "weight_category", "cg_category", "target_speed", "target_altitude", "repetition_required", "pass_fail_criteria", "status", "remarks"), ("test_point_number", "test", "status"), "test__engineering_requirement__program", "test"),
    "conditions": Resource(TestPointCondition, "Point conditions", ("test_point", "name", "value", "unit", "tolerance", "remarks"), ("name", "value", "unit", "test_point"), "test_point__test__engineering_requirement__program", "test_point"),
    "cards": Resource(TestCard, "Test cards", ("test", "card_number", "title", "revision", "preparation", "procedure", "safety_notes", "remarks"), ("card_number", "title", "revision", "test"), "test__engineering_requirement__program", "test"),
    "sequences": Resource(TestSequence, "Test sequences", ("program", "sequence_number", "title", "revision", "planned_date", "objective", "remarks"), ("sequence_number", "title", "revision", "planned_date"), "program", "program"),
    "items": Resource(TestSequenceItem, "Sequence items", ("sequence", "order", "test_point", "test_card", "estimated_duration_min", "remarks"), ("order", "test_point", "test_card", "estimated_duration_min"), "sequence__program", "sequence"),
    "hazards": Resource(FTHAHazard, "Hazard analysis", ("program", "test", "hazard_id", "description", "cause", "consequence", "mitigation", "severity", "probability", "remarks"), ("hazard_id", "description", "severity", "program"), "program", "program"),
    "units": Resource(UnitDefinition, "Units", ("quantity", "name", "symbol", "to_si_factor"), ("symbol", "name", "quantity")),
    "measurements": Resource(MeasurementDefinition, "Measurements", ("name", "code", "description", "quantity", "default_unit"), ("code", "name", "default_unit")),
    "regulations": Resource(Regulation, "Regulations", ("code", "title", "authority", "revision"), ("code", "title", "revision")),
    "regulatory-requirements": Resource(RegulatoryRequirement, "Regulatory requirements", ("regulation", "section", "description"), ("section", "regulation", "description"), parent="regulation"),
    "crew": Resource(CrewMember, "Crew directory", ("full_name", "nickname", "employee_id", "organization", "active"), ("full_name", "organization", "active")),
}
MODEL_KEYS = {resource.model: key for key, resource in RESOURCES.items()}


def allowed(user, resource, action):
    meta = resource.model._meta
    return user.has_perm(f"{meta.app_label}.{action}_{meta.model_name}")


def resource_for(request, key, action="view"):
    if key not in RESOURCES:
        raise Http404("Unknown workspace page")
    resource = RESOURCES[key]
    if not allowed(request.user, resource, action):
        raise PermissionDenied
    return resource


def object_url(obj):
    return reverse("record_detail", args=[MODEL_KEYS[type(obj)], obj.pk])


def display(obj, field):
    value = getattr(obj, field)
    method = getattr(obj, f"get_{field}_display", None)
    if method:
        value = method()
    return "—" if value is None or value == "" else value


def context_for(request, key, resource):
    return {"resource": resource, "resource_key": key,
            "can_add": allowed(request.user, resource, "add"),
            "can_change": allowed(request.user, resource, "change"),
            "can_delete": allowed(request.user, resource, "delete")}


@login_required
def record_list(request, key):
    resource = resource_for(request, key)
    objects = resource.model.objects.all()
    foreign_keys = [f.name for f in resource.model._meta.fields if f.many_to_one]
    if foreign_keys:
        objects = objects.select_related(*foreign_keys)
    program = request.GET.get("program", "")
    if program and resource.program_path:
        selected = get_object_or_404(Program, pk=program) if program.isdecimal() else None
        if selected is None:
            raise Http404("Invalid program")
        objects = objects.filter(**{resource.program_path: selected.pk})
    query = request.GET.get("q", "").strip()
    if query:
        search = Q()
        for name in resource.fields:
            if isinstance(resource.model._meta.get_field(name), (models.CharField, models.TextField)):
                search |= Q(**{f"{name}__icontains": query})
        objects = objects.filter(search)
    ordering = ("order", "pk") if key == "items" else ("pk",)
    page = Paginator(objects.order_by(*ordering), 25).get_page(request.GET.get("page"))
    context = context_for(request, key, resource)
    context.update(page=page, q=query, selected_program=program,
                   programs=Program.objects.order_by("name") if resource.program_path else [],
                   headers=[resource.model._meta.get_field(f).verbose_name for f in resource.columns],
                   rows=[{"url": object_url(obj), "values": [display(obj, f) for f in resource.columns]} for obj in page],
                   pagination_query=urlencode({"q": query, "program": program}))
    return render(request, "workspace/list.html", context)


@login_required
def record_detail(request, key, pk):
    resource = resource_for(request, key)
    obj = get_object_or_404(resource.model, pk=pk)
    fields = []
    for name in resource.fields:
        field = resource.model._meta.get_field(name)
        value = display(obj, name)
        link = None
        if field.many_to_one and getattr(obj, name) is not None:
            related = getattr(obj, name)
            related_resource = RESOURCES[MODEL_KEYS[type(related)]]
            if allowed(request.user, related_resource, "view"):
                link = object_url(related)
        fields.append({"label": field.verbose_name, "value": value, "url": link})
    children = []
    for child_key, child in RESOURCES.items():
        if not child.parent or not allowed(request.user, child, "view"):
            continue
        fk = child.model._meta.get_field(child.parent)
        if fk.related_model is type(obj):
            records = child.model.objects.filter(**{child.parent: obj}).order_by("order" if child_key == "items" else "pk")
            children.append({"title": child.title, "key": child_key,
                             "records": [{"title": str(row), "url": object_url(row)} for row in records],
                             "add_url": reverse("record_create", args=[child_key]) + "?" + urlencode({"parent": obj.pk}),
                             "can_add": allowed(request.user, child, "add")})
    export = None
    if key in {"programs", "cards", "sequences"}:
        export = reverse({"programs": "export_test_matrix", "cards": "export_card_pdf", "sequences": "export_sequence_pdf"}[key], args=[obj.pk])
    context = context_for(request, key, resource)
    context.update(record=obj, fields=fields, children=children, export_url=export)
    return render(request, "workspace/detail.html", context)


def make_form(resource, data=None, instance=None, parent=None):
    form_class = forms.modelform_factory(resource.model, fields=resource.fields,
                                         widgets={"planned_date": forms.DateInput(attrs={"type": "date"})})
    form = form_class(data=data, instance=instance)
    if resource.parent:
        field = form.fields[resource.parent]
        if instance:
            field.disabled = True
        elif parent:
            field.initial = parent.pk
            field.disabled = True
    for name, field in form.fields.items():
        field.widget.attrs.setdefault("class", "form-control")
        if isinstance(field.widget, forms.Textarea):
            field.widget.attrs["rows"] = 4
    if "target_speed" in form.fields:
        form.fields["target_speed"].label = "Target speed (kt)"
        form.fields["target_altitude"].label = "Target altitude (ft)"
    # Scope sequence choices to the owning program; model.clean checks card/test compatibility.
    sequence = None
    if resource.model is TestSequenceItem:
        sequence_id = instance.sequence_id if instance else (parent.pk if parent else (data or {}).get("sequence"))
        if str(sequence_id).isdecimal():
            sequence = TestSequence.objects.filter(pk=sequence_id).first()
        if sequence:
            form.fields["test_point"].queryset = TestPoint.objects.filter(test__engineering_requirement__program=sequence.program)
            form.fields["test_card"].queryset = TestCard.objects.filter(test__engineering_requirement__program=sequence.program)
    if resource.model is FTHAHazard:
        program_id = instance.program_id if instance else (parent.pk if parent else (data or {}).get("program"))
        if str(program_id).isdecimal():
            form.fields["test"].queryset = Test.objects.filter(engineering_requirement__program_id=program_id)
    return form


@login_required
@require_http_methods(["GET", "POST"])
def record_form(request, key, pk=None):
    resource = resource_for(request, key, "change" if pk else "add")
    # Editing redirects to a readable detail page; users need view permission too.
    resource_for(request, key)
    obj = get_object_or_404(resource.model, pk=pk) if pk else None
    parent = None
    if not obj and resource.parent and request.GET.get("parent"):
        parent_id = request.GET["parent"]
        if not parent_id.isdecimal():
            raise Http404("Invalid parent")
        parent = get_object_or_404(resource.model._meta.get_field(resource.parent).related_model, pk=parent_id)
    form = make_form(resource, request.POST if request.method == "POST" else None, obj, parent)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                saved = form.save()
        except IntegrityError:
            form.add_error(None, "This record conflicts with an existing record. Review the identifiers and try again.")
        else:
            messages.success(request, "Planning record saved.")
            return redirect(object_url(saved))
    context = context_for(request, key, resource)
    context.update(form=form, record=obj, cancel_url=object_url(obj) if obj else reverse("record_list", args=[key]))
    return render(request, "workspace/form.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def record_delete(request, key, pk):
    resource = resource_for(request, key, "delete")
    resource_for(request, key)
    obj = get_object_or_404(resource.model, pk=pk)
    # Refuse cascading and SET_NULL deletions: dependent engineering records must survive.
    blocked = any(getattr(obj, relation.get_accessor_name()).exists()
                  for relation in obj._meta.related_objects)
    if request.method == "POST" and not blocked:
        with transaction.atomic():
            obj.delete()
        messages.success(request, "Record deleted.")
        return redirect("record_list", key=key)
    context = context_for(request, key, resource)
    context.update(record=obj, blocked=blocked)
    return render(request, "workspace/delete.html", context, status=409 if blocked and request.method == "POST" else 200)


def workspace_navigation(request):
    if not request.user.is_authenticated:
        return {}
    return {"workspace_navigation": [{"key": key, "title": resource.title}
                                     for key, resource in RESOURCES.items()
                                     if allowed(request.user, resource, "view")]}
