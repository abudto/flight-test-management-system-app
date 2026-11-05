from django.urls import path
from . import views
from . import web_views

urlpatterns = [
    path("program/<int:program_id>/tests/", web_views.test_list, name="test_list"),
    path("program/<int:program_id>/tests/<int:test_id>/", web_views.test_detail, name="test_detail"),
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
    path(
        "sequence/<int:sequence_id>/export/pdf/",
        views.export_sequence_pdf,
        name="export_sequence_pdf",
    ),
    path(
        "card/<int:card_id>/export/pdf/",
        views.export_card_pdf,
        name="export_card_pdf",
    ),
]
