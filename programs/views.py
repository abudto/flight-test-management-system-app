from django.shortcuts import render

from .models import Program


def home(request):
    return render(request, "programs/home.html", {
        "programs": Program.objects.order_by("name", "pk"),
    })
