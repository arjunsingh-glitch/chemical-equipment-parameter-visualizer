"""Small set of models used for the CSV upload demo."""
from __future__ import annotations

from django.db import models


class Equipment(models.Model):
    """
    One row per line in the uploaded CSV file.

    Keeping this model close to the CSV layout makes the Pandas-to-ORM
    mapping code in the view very straightforward.
    """

    name = models.CharField(max_length=255)
    equipment_type = models.CharField(max_length=100)  # "Type" column in CSV
    flowrate = models.FloatField()
    pressure = models.FloatField()
    temperature = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # type: ignore[override]
        return f"{self.name} ({self.equipment_type})"


class History(models.Model):
    """
    Light‑weight log of each CSV upload.

    I only keep a short text summary and a pointer to the PDF file – storing
    the whole DataFrame again here would just duplicate data from `Equipment`.
    """

    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255)
    summary = models.TextField(help_text="Short description of statistics from this upload.")
    pdf_path = models.CharField(
        max_length=500,
        help_text="Relative path to the generated PDF report for this upload.",
    )

    def __str__(self) -> str:  # type: ignore[override]
        return f"Upload on {self.uploaded_at:%Y-%m-%d %H:%M} - {self.original_filename}"

