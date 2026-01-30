"""
URL patterns for the `core` app.

Right now we only expose a single endpoint for uploading equipment CSVs.
"""
from django.urls import path

from .views import EquipmentUploadView, HistoryListView

urlpatterns = [
    path("upload-equipment/", EquipmentUploadView.as_view(), name="upload-equipment"),
    path("history/", HistoryListView.as_view(), name="history"),
]

