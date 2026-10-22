from django.urls import path
from . import views

urlpatterns = [
    path(
        'matrix/',
        views.test_matrix,
        name='test_matrix',
    ),
]