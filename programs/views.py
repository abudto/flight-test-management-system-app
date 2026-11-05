from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_safe

from .models import Program
from .workspace import RESOURCES, allowed


def home(request):
    return render(request, "programs/home.html", {
        "programs": Program.objects.order_by("name", "pk") if request.user.has_perm("programs.view_program") else Program.objects.none(),
    })


@login_required
@permission_required("programs.view_program", raise_exception=True)
@require_safe
def program_list(request):
    return render(request, "programs/program_list.html", {
        "programs": Program.objects.order_by("name", "pk"),
    })


@login_required
@permission_required("programs.view_program", raise_exception=True)
@require_safe
def program_detail(request, program_id):
    program = get_object_or_404(Program, pk=program_id)
    # Each query follows the same program path as the authenticated workspace.
    # Independent counts avoid multiplying records across unrelated joins.
    counts = {}
    workspaces = []
    labels = {"tests": "Tests", "points": "Test Points", "cards": "Test Cards",
              "sequences": "Test Sequences", "hazards": "Hazard Records"}
    for key in ["requirements", "tests", "points", "cards", "sequences", "hazards"]:
        resource = RESOURCES[key]
        if not allowed(request.user, resource, "view"):
            continue
        if key in labels:
            counts[labels[key]] = resource.model.objects.filter(
                **{resource.program_path: program.pk},
            ).count()
        workspaces.append({
            "title": resource.title,
            "url": reverse("record_list", args=[key]) + "?" + urlencode({"program": program.pk}),
        })
    can_view_aircraft = request.user.has_perm("programs.view_aircraft")
    return render(request, "programs/program_detail.html", {
        "program": program,
        "counts": counts,
        "workspaces": workspaces,
        "can_view_aircraft": can_view_aircraft,
        "aircraft": program.aircraft.order_by("aircraft_number", "pk") if can_view_aircraft else [],
    })
