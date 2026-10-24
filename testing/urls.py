from django.urls import path
from . import views

urlpatterns = [
    path(
        'program/<int:program_id>/matrix/',
        views.test_matrix,
        name='test_matrix',
    ),
]