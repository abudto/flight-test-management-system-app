"""Read-only planning pages, separate from existing matrix and export views."""

from django.db.models import Count, Prefetch
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from programs.models import Program
from .models import Test, TestPointCondition


@login_required
@permission_required(("programs.view_program", "testing.view_test",
                      "testing.view_engineeringtestrequirement"), raise_exception=True)
@require_safe
def test_list(request, program_id):
    program = get_object_or_404(Program, pk=program_id)
    tests = (
        Test.objects.filter(engineering_requirement__program=program)
        .select_related("engineering_requirement")
        .order_by("test_number", "pk")
    )
    if request.user.has_perm("testing.view_testpoint"):
        tests = tests.annotate(point_count=Count("test_points"))
    return render(request, "testing/test_list.html", {"program": program, "tests": tests})


@login_required
@permission_required(("programs.view_program", "testing.view_test",
                      "testing.view_engineeringtestrequirement", "testing.view_testpoint",
                      "testing.view_testpointcondition"), raise_exception=True)
@require_safe
def test_detail(request, program_id, test_id):
    program = get_object_or_404(Program, pk=program_id)
    test = get_object_or_404(
        Test.objects.select_related("engineering_requirement"),
        pk=test_id, engineering_requirement__program=program,
    )
    points = test.test_points.order_by("test_point_number", "pk").prefetch_related(
        Prefetch("conditions", queryset=TestPointCondition.objects.order_by("pk")),
    )
    return render(request, "testing/test_detail.html", {
        "program": program, "test": test, "test_points": points,
    })
