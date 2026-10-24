from django.shortcuts import render, get_object_or_404

# Create your views here.
from programs.models import Program
from .models import TestPoint


def test_matrix(request, program_id):
    program = get_object_or_404(
        Program,
        pk=program_id,
    )

    test_points = (
        TestPoint.objects
        .filter(
            test__engineering_requiremene__program=program
        )
        .select_related(
            'test',
            'test__engineering_requirement',
            'test__engineering_requirement__program',
        )
        .order_by('test__test_number', 'test_point_number')
    )

    context = {
        'program': program,
        'test_points': test_points,
    }

    return render(
        request,
        'testing/test_matrix.html',
        context,
    )