"""
Small collection of API views for the `core` app.

The idea is:
- accept a CSV file from the frontends,
- let Pandas do the heavy lifting for statistics,
- write a short PDF summary so the user can download a report later.

Nothing here is very "enterprise" – it is just the amount of structure
I would normally use for a student side‑project.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from io import BytesIO
import pandas as pd
from django.conf import settings
from django.utils.timezone import now
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Equipment, History
from .serializers import EquipmentUploadSerializer, HistorySerializer


class EquipmentUploadView(APIView):
    """
    Upload endpoint used by both the web and desktop clients.

    I kept the logic in a single view instead of a ViewSet because there is
    only one operation here: "upload CSV and give me stats back".
    """

    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    # We hardcode the expected column names so the error messages can be clear.
    # NOTE: The official FOSSEE sample file uses "Equipment Name" as the first
    # column, so we align with that exact header here.
    REQUIRED_COLUMNS = {"Equipment Name", "Type", "Flowrate", "Pressure", "Temperature"}

    def post(self, request, *args, **kwargs):
        """
        Accept a CSV file, compute statistics, generate a PDF summary and
        return everything as JSON so the frontends stay very thin.
        """
        serializer = EquipmentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            # Typical student‑style validation: send back all serializer errors.
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        upload = serializer.validated_data["file"]

        try:
            # `upload` is a Django InMemoryUploadedFile / TemporaryUploadedFile.
            # Pandas can read straight from this file‑like object so we do not
            # need to write it to disk first.
            df = pd.read_csv(upload)

            # Many CSVs exported from Excel sneak in a BOM at the start of the
            # first column name (e.g. "\ufeffEquipment Name").  Normalising the
            # headers here keeps the later code a bit less fragile.
            cleaned_columns = [col.strip().lstrip("\ufeff") for col in df.columns]
            df.columns = cleaned_columns

            # If the sample file is edited, column names can easily drift.
            # It is nicer to fail fast here with a clear error than to crash
            # somewhere in the statistics code.
            missing_columns = self.REQUIRED_COLUMNS.difference(df.columns)
            if missing_columns:
                return Response(
                    {
                        "error": "CSV is missing required column(s).",
                        "missing_columns": sorted(list(missing_columns)),
                        "seen_columns": list(df.columns),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Basic statistics – written out in a very explicit way so it is
            # easy to follow without being a Pandas expert.
            total_count = int(len(df))
            avg_flowrate = float(df["Flowrate"].mean()) if total_count > 0 else 0.0
            avg_pressure = float(df["Pressure"].mean()) if total_count > 0 else 0.0
            avg_temperature = float(df["Temperature"].mean()) if total_count > 0 else 0.0

            # Distribution of equipment types (e.g. Pump, Valve, Reactor, etc.)
            type_distribution_series = df["Type"].value_counts()
            type_distribution = {
                str(equipment_type): int(count)
                for equipment_type, count in type_distribution_series.items()
            }

            stats_payload = {
                "total_count": total_count,
                "average_flowrate": avg_flowrate,
                "average_pressure": avg_pressure,
                "average_temperature": avg_temperature,
                "type_distribution": type_distribution,
            }

            # Store each row as an Equipment instance.
            # TODO: for a bigger dataset I would probably switch this to a
            # proper bulk insert or streaming approach.
            equipment_objects: list[Equipment] = []
            for _, row in df.iterrows():
                equipment_obj = Equipment(
                    # The CSV column is called "Equipment Name" in the FOSSEE sample,
                    # but our model field is simply `name`, so we map it here.
                    name=row["Equipment Name"],
                    equipment_type=row["Type"],
                    flowrate=row["Flowrate"],
                    pressure=row["Pressure"],
                    temperature=row["Temperature"],
                )
                equipment_objects.append(equipment_obj)

            # Persist to the database in one go.
            Equipment.objects.bulk_create(equipment_objects)

            # Generate a small PDF report that summarises the stats so the user
            # can save or share it.
            pdf_relative_path = self.create_summary_pdf(
                original_filename=upload.name,
                stats=stats_payload,
            )

            # Save a History entry so we can later show the last 5 uploads.
            history_summary = (
                f"Total: {total_count}, "
                f"Avg Flowrate: {avg_flowrate:.2f}, "
                f"Avg Pressure: {avg_pressure:.2f}, "
                f"Avg Temperature: {avg_temperature:.2f}"
            )

            History.objects.create(
                original_filename=upload.name,
                summary=history_summary,
                pdf_path=pdf_relative_path,
            )

            # Keep only the latest 5 History records – delete older ones so the
            # table does not grow forever for this small demo.
            self._trim_history()

            return Response(
                {
                    "message": "CSV processed successfully.",
                    "stats": stats_payload,
                    "pdf_report": pdf_relative_path,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:  # noqa: BLE001
            # I still keep a broad except here because this is a student demo
            # and I would rather return *some* information than a 500 HTML page.
            return Response(
                {
                    "error": "Unexpected error while processing CSV on the server.",
                    "details": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def create_summary_pdf(self, original_filename: str, stats: dict) -> str:
        """
        Build a short, text‑only PDF summary using ReportLab.

        I deliberately avoid any charts here – the charts live in the
        frontends – and keep this file as a printable summary instead.
        """
        # Store reports in MEDIA_ROOT/reports so they can be served via MEDIA_URL.
        reports_dir = settings.MEDIA_ROOT / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Natural‑looking name with a timestamp to avoid clashes.
        timestamp = now().strftime("%Y%m%d_%H%M%S")
        filename = f"Equipment_Summary_Report_{timestamp}.pdf"
        full_path = reports_dir / filename

        # Use an in‑memory buffer and then write once at the end so we only
        # touch the filesystem a single time.
        buffer = BytesIO()
        pdf_canvas = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4  # not used heavily, but here for clarity

        y = height - 50  # start a little below the top edge

        pdf_canvas.setFont("Helvetica-Bold", 14)
        pdf_canvas.drawString(40, y, "Chemical Equipment Summary Report")
        y -= 30

        pdf_canvas.setFont("Helvetica", 10)
        pdf_canvas.drawString(40, y, f"Source file: {original_filename}")
        y -= 20
        pdf_canvas.drawString(40, y, f"Generated at: {datetime.now():%Y-%m-%d %H:%M:%S}")
        y -= 30

        pdf_canvas.setFont("Helvetica-Bold", 12)
        pdf_canvas.drawString(40, y, "Summary Statistics")
        y -= 20

        pdf_canvas.setFont("Helvetica", 10)
        pdf_canvas.drawString(60, y, f"Total equipment count: {stats['total_count']}")
        y -= 15
        pdf_canvas.drawString(60, y, f"Average flowrate: {stats['average_flowrate']:.2f}")
        y -= 15
        pdf_canvas.drawString(60, y, f"Average pressure: {stats['average_pressure']:.2f}")
        y -= 15
        pdf_canvas.drawString(
            60,
            y,
            f"Average temperature: {stats['average_temperature']:.2f}",
        )
        y -= 25

        pdf_canvas.setFont("Helvetica-Bold", 12)
        pdf_canvas.drawString(40, y, "Equipment Type Distribution")
        y -= 20

        pdf_canvas.setFont("Helvetica", 10)
        for equipment_type, count in stats["type_distribution"].items():
            # If we reach the bottom of the page, start a new one (simple logic).
            if y < 60:
                pdf_canvas.showPage()
                y = height - 50
                pdf_canvas.setFont("Helvetica", 10)
            pdf_canvas.drawString(60, y, f"{equipment_type}: {count}")
            y -= 15

        pdf_canvas.showPage()
        pdf_canvas.save()

        # Finally write the buffer to the file system.
        with open(full_path, "wb") as f:
            f.write(buffer.getvalue())

        # Return the relative path so the frontend can combine it with MEDIA_URL.
        # Use forward slashes so URLs work on all platforms (Windows returns \ from os.path.join).
        relative_path = "media/reports/" + filename
        return relative_path

    def _trim_history(self) -> None:
        """
        Keep the History table small by retaining only the newest 5 entries.

        For a personal project it is totally fine to just delete the older
        rows instead of archiving them somewhere else.
        """
        qs = History.objects.order_by("-uploaded_at")
        # Skip the latest 5 uploads and delete everything older than that.
        for old_entry in qs[5:]:
            old_entry.delete()


class HistoryListView(APIView):
    """
    Simple read‑only view that feeds the small "Recent uploads" panels on the
    web and desktop frontends.
    """

    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Return the latest 5 history entries, newest first."""
        history_entries = History.objects.order_by("-uploaded_at")[:5]
        serializer = HistorySerializer(history_entries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

