from django.shortcuts import render

# Create your views here.
from .models import TestPoint


def test_matrix(request):
    test_points = (
        TestPoint.objects.select_related(
            'test',
            'test__engineering_requirement',
            'test__engineering_requirement__program',
        )
        .order_by('test__test_number', 'test_point_number')
    )

    context = {
        'test_points': test_points,
    }

    return render(
        request,
        'testing/test_matrix.html',
        context,
    )