from django.urls import path
from . import workspace

urlpatterns = [
    path("<slug:key>/", workspace.record_list, name="record_list"),
    path("<slug:key>/new/", workspace.record_form, name="record_create"),
    path("<slug:key>/<int:pk>/", workspace.record_detail, name="record_detail"),
    path("<slug:key>/<int:pk>/edit/", workspace.record_form, name="record_edit"),
    path("<slug:key>/<int:pk>/delete/", workspace.record_delete, name="record_delete"),
]
