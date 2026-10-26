from django.urls import path
from . import views

urlpatterns = [
    path(
        'program/<int:program_id>/matrix/',
        views.test_matrix,
        name='test_matrix',
    ),
    path(
        'program/<int:program_id>/matrix/export/',
        views.export_test_matrix,
        name='export_test_matrix',
    ),
]