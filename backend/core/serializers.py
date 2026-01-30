"""Serializers used by the API views."""
from rest_framework import serializers
from .models import History


class EquipmentUploadSerializer(serializers.Serializer):
    """
    Minimal serializer that just checks we actually received a file.

    It feels a bit overkill for a single field, but it keeps the view
    code honest and is closer to how I would structure a real project.
    """

    file = serializers.FileField()


class HistorySerializer(serializers.ModelSerializer):
    """Expose a compact representation of an upload history entry."""

    class Meta:
        model = History
        fields = ["id", "uploaded_at", "original_filename", "summary", "pdf_path"]

