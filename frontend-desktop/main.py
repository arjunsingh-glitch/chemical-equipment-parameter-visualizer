"""
Small PyQt5 desktop client that talks to the same Django API as the web app.

I reuse the same ideas from the browser version:
- Basic Auth credentials are typed once and reused for all requests.
- Matplotlib draws a tiny bar chart for the equipment type distribution.
- A worker thread handles HTTP so the window does not freeze during uploads.
"""

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import requests
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QFormLayout,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFrame,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

API_BASE_URL = "http://127.0.0.1:8000/api"
# Media URL for PDF reports – same host as API; backend returns paths like "media/reports/xxx.pdf"
MEDIA_BASE_URL = "http://127.0.0.1:8000"

# Global font sizes for FOSSEE readability on a standard monitor
FONT_SIZE_TITLE = 22
FONT_SIZE_SUBTITLE = 14
FONT_SIZE_LABEL = 14
FONT_SIZE_INPUT = 13
FONT_SIZE_BUTTON = 14
FONT_SIZE_TABLE = 14
FONT_SIZE_HISTORY_HEADER = 16
FONT_SIZE_HISTORY_ITEMS = 13


@dataclass
class UploadResult:
    ok: bool
    error_message: str | None
    stats: Dict[str, Any] | None
    pdf_report: str | None  # Relative path e.g. "media/reports/Equipment_Summary_Report_xxx.pdf"


@dataclass
class HistoryResult:
    ok: bool
    error_message: str | None
    history: list[Dict[str, Any]] | None


class UploadWorker(QThread):
    """Background job that uploads the CSV file to the Django API."""

    finished_with_result = pyqtSignal(object)

    def __init__(self, file_path: str, username: str, password: str):
        super().__init__()
        self.file_path = file_path
        self.username = username
        self.password = password

    def run(self) -> None:
        try:
            with open(self.file_path, "rb") as f:
                files = {"file": (self.file_path, f, "text/csv")}
                response = requests.post(
                    f"{API_BASE_URL}/upload-equipment/",
                    files=files,
                    auth=(self.username, self.password),
                    timeout=30,
                )

            if response.status_code != 200:
                try:
                    data = response.json()
                    msg = data.get("error", response.text)
                except Exception:  # noqa: BLE001
                    msg = response.text
                result = UploadResult(ok=False, error_message=msg, stats=None, pdf_report=None)
            else:
                data = response.json()
                result = UploadResult(
                    ok=True,
                    error_message=None,
                    stats=data.get("stats"),
                    pdf_report=data.get("pdf_report"),
                )
        except Exception as exc:  # noqa: BLE001
            result = UploadResult(ok=False, error_message=str(exc), stats=None, pdf_report=None)

        self.finished_with_result.emit(result)


class HistoryWorker(QThread):
    """Background job that fetches the last few uploads from the API."""

    finished_with_result = pyqtSignal(object)

    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password

    def run(self) -> None:
        try:
            response = requests.get(
                f"{API_BASE_URL}/history/",
                auth=(self.username, self.password),
                timeout=30,
            )

            if response.status_code != 200:
                try:
                    data = response.json()
                    msg = data.get("error", response.text)
                except Exception:  # noqa: BLE001
                    msg = response.text
                result = HistoryResult(ok=False, error_message=msg, history=None)
            else:
                data = response.json()
                result = HistoryResult(ok=True, error_message=None, history=data)
        except Exception as exc:  # noqa: BLE001
            result = HistoryResult(ok=False, error_message=str(exc), history=None)

        self.finished_with_result.emit(result)


class EquipmentChartCanvas(FigureCanvas):
    """Tiny Matplotlib canvas that draws the bar chart used in the UI."""

    def __init__(self, parent: QWidget | None = None):
        self.fig = Figure(figsize=(5, 3), facecolor="#020617")
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.fig.tight_layout()
        self.plot_distribution({})

    def plot_distribution(self, type_distribution: Dict[str, int]) -> None:
        self.ax.clear()
        # Use dark background for both empty and data states so it matches the app theme
        self.ax.set_facecolor("#020617")
        self.fig.patch.set_facecolor("#020617")

        if not type_distribution:
            self.ax.text(
                0.5,
                0.5,
                "No data yet",
                ha="center",
                va="center",
                color="white",
                fontsize=14,
                transform=self.ax.transAxes,
            )
            self.ax.tick_params(axis="both", labelcolor="#64748b", colors="#475569")
            for spine in self.ax.spines.values():
                spine.set_visible(False)
        else:
            labels = list(type_distribution.keys())
            values = list(type_distribution.values())
            bar_colors = ["#0891b2"] * len(values)

            self.ax.bar(labels, values, color=bar_colors)
            # Larger font sizes for chart title and axes (FOSSEE readability)
            self.ax.set_title("Equipment type distribution", color="white", fontsize=16)
            self.ax.set_ylabel("Count", color="white", fontsize=14)
            self.ax.tick_params(axis="x", labelrotation=45, labelcolor="white", labelsize=12)
            self.ax.tick_params(axis="y", labelcolor="white", labelsize=12)

        self.draw()


def _summary_table_style() -> str:
    """Styles for the Summary table to match the React app (slate-800, borders)."""
    return """
        QTableWidget {
            background-color: #1e293b;
            color: #e2e8f0;
            gridline-color: #334155;
            border: 1px solid #475569;
            border-radius: 6px;
            font-size: %dpx;
        }
        QTableWidget::item {
            padding: 6px;
        }
        QHeaderView::section {
            background-color: #0f172a;
            color: #94a3b8;
            padding: 8px;
            border: none;
            border-bottom: 2px solid #475569;
            font-weight: 600;
        }
    """ % (
        FONT_SIZE_TABLE,
    )


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chemical Equipment Parameter Visualizer - Desktop")
        self.setMinimumSize(960, 620)

        self.selected_file: str | None = None
        self.current_worker: UploadWorker | None = None
        self.current_history_worker: HistoryWorker | None = None
        self.history_data: list[Dict[str, Any]] = []
        self.current_pdf_path: str | None = None  # Set after upload; used for Download PDF

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        title = QLabel("Chemical Equipment Parameter Visualizer")
        title.setStyleSheet(
            f"color: #0f766e; font-size: {FONT_SIZE_TITLE}px; font-weight: 600;"
        )
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Upload an equipment CSV file, then view summary statistics and type distribution."
        )
        subtitle.setStyleSheet(f"color: #cbd5e1; font-size: {FONT_SIZE_SUBTITLE}px;")
        main_layout.addWidget(subtitle)

        # ---- Top row: file picker, auth, upload ----
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        file_column = QVBoxLayout()
        file_label = QLabel("Select equipment CSV")
        file_label.setStyleSheet(f"color: #e2e8f0; font-size: {FONT_SIZE_LABEL}px;")

        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet(f"color: #94a3b8; font-size: {FONT_SIZE_INPUT}px;")

        select_button = QPushButton("Browse...")
        select_button.setStyleSheet(
            f"background-color: #0891b2; color: #020617; padding: 8px 14px; border-radius: 4px; font-size: {FONT_SIZE_BUTTON}px;"
        )
        select_button.clicked.connect(self.on_select_file)

        file_column.addWidget(file_label)
        file_column.addWidget(select_button)
        file_column.addWidget(self.file_path_label)

        auth_column = QFormLayout()
        auth_label = QLabel("Basic Auth (Django user)")
        auth_label.setStyleSheet(f"color: #e2e8f0; font-size: {FONT_SIZE_LABEL}px;")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet(
            f"background-color: #0f172a; color: white; border: 1px solid #475569; padding: 6px; font-size: {FONT_SIZE_INPUT}px;"
        )

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(
            f"background-color: #0f172a; color: white; border: 1px solid #475569; padding: 6px; font-size: {FONT_SIZE_INPUT}px;"
        )

        auth_column.addRow(auth_label)
        auth_column.addRow("Username:", self.username_input)
        auth_column.addRow("Password:", self.password_input)

        self.upload_button = QPushButton("Upload CSV")
        self.upload_button.setStyleSheet(
            f"background-color: #0f766e; color: #e2e8f0; padding: 10px 20px; border-radius: 4px; font-size: {FONT_SIZE_BUTTON}px;"
        )
        self.upload_button.clicked.connect(self.on_upload_clicked)

        top_row.addLayout(file_column, stretch=2)
        top_row.addLayout(auth_column, stretch=2)
        top_row.addWidget(self.upload_button, stretch=1)

        main_layout.addLayout(top_row)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet(f"color: #fecaca; font-size: {FONT_SIZE_LABEL}px;")
        main_layout.addWidget(self.info_label)

        # ---- Summary + Chart row: table (left) and chart (right), like React Summary Statistics ----
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        # Summary as a table (QTableWidget) consistent with React "Summary statistics" table
        summary_group = QFrame()
        summary_group.setStyleSheet(
            "QFrame { background-color: #1e293b; border: 1px solid #475569; border-radius: 8px; }"
        )
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setContentsMargins(12, 12, 12, 12)

        summary_title_row = QHBoxLayout()
        summary_title = QLabel("Summary statistics")
        summary_title.setStyleSheet(
            f"color: #f1f5f9; font-size: {FONT_SIZE_TABLE}px; font-weight: 600;"
        )
        summary_title_row.addWidget(summary_title)

        self.download_pdf_button = QPushButton("Download PDF Report")
        self.download_pdf_button.setEnabled(False)
        self.download_pdf_button.setStyleSheet(
            "background-color: transparent; color: #22d3ee; border: 1px solid #22d3ee; "
            f"padding: 6px 12px; border-radius: 4px; font-size: {FONT_SIZE_BUTTON - 1}px;"
        )
        self.download_pdf_button.clicked.connect(self.on_download_pdf)
        summary_title_row.addWidget(self.download_pdf_button)

        summary_layout.addLayout(summary_title_row)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.stats_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.stats_table.setShowGrid(True)
        self.stats_table.setStyleSheet(_summary_table_style())
        self._fill_stats_placeholder()
        summary_layout.addWidget(self.stats_table)

        bottom_row.addWidget(summary_group, stretch=1)

        self.chart_canvas = EquipmentChartCanvas(self)
        bottom_row.addWidget(self.chart_canvas, stretch=2)

        main_layout.addLayout(bottom_row)

        # ---- Upload History: larger header and monospaced list for alignment ----
        history_label = QLabel("Upload History (Last 5)")
        history_label.setStyleSheet(
            f"color: #e2e8f0; font-size: {FONT_SIZE_HISTORY_HEADER}px; font-weight: 600; margin-top: 8px;"
        )
        main_layout.addWidget(history_label)

        history_header = QHBoxLayout()
        refresh_history_button = QPushButton("Refresh History")
        refresh_history_button.setStyleSheet(
            f"background-color: #0891b2; color: #020617; padding: 6px 12px; border-radius: 4px; font-size: {FONT_SIZE_BUTTON - 1}px;"
        )
        refresh_history_button.clicked.connect(self.on_refresh_history)
        history_header.addWidget(refresh_history_button)
        history_header.addStretch()
        main_layout.addLayout(history_header)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet(
            "background-color: #1e293b; color: #e2e8f0; border: 1px solid #475569; "
            f"border-radius: 6px; font-size: {FONT_SIZE_HISTORY_ITEMS}px; font-family: 'Consolas', 'Monaco', monospace;"
        )
        self.history_list.setMaximumHeight(180)
        main_layout.addWidget(self.history_list)

        self.setLayout(main_layout)
        self.setStyleSheet("background-color: #020617;")

    def _fill_stats_placeholder(self) -> None:
        """Show placeholder row when no stats are available."""
        self.stats_table.setRowCount(1)
        self.stats_table.setItem(0, 0, QTableWidgetItem("—"))
        self.stats_table.setItem(0, 1, QTableWidgetItem("Upload a CSV to see results."))

    def _update_summary_table(self, stats: Dict[str, Any]) -> None:
        """Populate the summary table with the same metrics as the React app."""
        rows = [
            ("Total equipment count", str(stats.get("total_count", 0))),
            ("Average flowrate", f"{stats.get('average_flowrate', 0):.2f}"),
            ("Average pressure", f"{stats.get('average_pressure', 0):.2f}"),
            ("Average temperature", f"{stats.get('average_temperature', 0):.2f}"),
        ]
        self.stats_table.setRowCount(len(rows))
        for i, (metric, value) in enumerate(rows):
            self.stats_table.setItem(i, 0, QTableWidgetItem(metric))
            self.stats_table.setItem(i, 1, QTableWidgetItem(value))

    def on_download_pdf(self) -> None:
        """Download the PDF report from the Django backend media URL using requests."""
        if not self.current_pdf_path:
            return
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            self._show_error("Please enter username and password to download the report.")
            return

        # Normalize path to forward slashes for URL (backend may return Windows \ on Windows)
        path_for_url = self.current_pdf_path.replace("\\", "/")
        url = f"{MEDIA_BASE_URL}/{path_for_url}"
        default_name = Path(self.current_pdf_path).name

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF Report",
            default_name,
            "PDF files (*.pdf);;All files (*.*)",
        )
        if not save_path:
            return

        try:
            resp = requests.get(
                url,
                auth=(username, password),
                timeout=30,
                stream=True,
            )
            resp.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(resp.content)
            self.info_label.setText("PDF saved successfully.")
        except requests.RequestException as e:
            self._show_error(f"Failed to download PDF: {e}")
        except OSError as e:
            self._show_error(f"Failed to save file: {e}")

    def on_select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select equipment CSV", "", "CSV files (*.csv);;All files (*.*)"
        )
        if file_path:
            self.selected_file = file_path
            self.file_path_label.setText(file_path)
            self.info_label.setText("")

    def on_upload_clicked(self) -> None:
        if not self.selected_file:
            self._show_error("Please select a CSV file first.")
            return

        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            self._show_error("Please enter username and password.")
            return

        self.upload_button.setEnabled(False)
        self.upload_button.setText("Uploading...")
        self.info_label.setText("")

        self.current_worker = UploadWorker(self.selected_file, username, password)
        self.current_worker.finished_with_result.connect(self.on_upload_finished)
        self.current_worker.start()

    def on_upload_finished(self, result: UploadResult) -> None:
        self.upload_button.setEnabled(True)
        self.upload_button.setText("Upload CSV")

        if not result.ok:
            self._show_error(result.error_message or "Upload failed.")
            return

        if not result.stats:
            self._show_error("Upload succeeded but no stats were returned.")
            return

        stats = result.stats
        self._update_summary_table(stats)
        type_distribution = stats.get("type_distribution", {})
        self.chart_canvas.plot_distribution(type_distribution)

        self.current_pdf_path = result.pdf_report
        self.download_pdf_button.setEnabled(bool(self.current_pdf_path))

        self.info_label.setText("Upload complete.")
        self.on_refresh_history()

    def on_refresh_history(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            return

        self.current_history_worker = HistoryWorker(username, password)
        self.current_history_worker.finished_with_result.connect(self.on_history_finished)
        self.current_history_worker.start()

    def on_history_finished(self, result: HistoryResult) -> None:
        if not result.ok:
            return
        if not result.history:
            self.history_list.clear()
            return

        self.history_data = result.history
        self.history_list.clear()

        for entry in result.history:
            try:
                uploaded_at = datetime.fromisoformat(
                    entry["uploaded_at"].replace("Z", "+00:00")
                )
                date_str = uploaded_at.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = entry["uploaded_at"]

            item_text = f"{entry['original_filename']} — {entry['summary']} ({date_str})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, entry.get("pdf_path"))
            self.history_list.addItem(item)

    def _show_error(self, message: str) -> None:
        self.info_label.setText(message)
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.exec_()


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
