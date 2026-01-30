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
    QScrollArea,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


API_BASE_URL = "http://127.0.0.1:8000/api"


@dataclass
class UploadResult:
    ok: bool
    error_message: str | None
    stats: Dict[str, Any] | None


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
                result = UploadResult(ok=False, error_message=msg, stats=None)
            else:
                data = response.json()
                result = UploadResult(ok=True, error_message=None, stats=data.get("stats"))
        except Exception as exc:  # noqa: BLE001
            result = UploadResult(ok=False, error_message=str(exc), stats=None)

        # Emit result back to the main (GUI) thread.
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

        # Emit result back to the main (GUI) thread.
        self.finished_with_result.emit(result)


class EquipmentChartCanvas(FigureCanvas):
    """Tiny Matplotlib canvas that draws the bar chart used in the UI."""

    def __init__(self, parent: QWidget | None = None):
        self.fig = Figure(figsize=(5, 3), facecolor="#020617")  # slate‑900
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.fig.tight_layout()

    def plot_distribution(self, type_distribution: Dict[str, int]) -> None:
        self.ax.clear()

        if not type_distribution:
            self.ax.text(
                0.5,
                0.5,
                "No data yet",
                ha="center",
                va="center",
                color="white",
                fontsize=10,
                transform=self.ax.transAxes,
            )
        else:
            labels = list(type_distribution.keys())
            values = list(type_distribution.values())
            bar_colors = ["#0891b2"] * len(values)  # teal accent

            self.ax.bar(labels, values, color=bar_colors)
            self.ax.set_title("Equipment type distribution", color="white")
            self.ax.set_ylabel("Count", color="white")
            self.ax.tick_params(axis="x", labelrotation=30, labelcolor="white")
            self.ax.tick_params(axis="y", labelcolor="white")
            self.ax.set_facecolor("#020617")  # slate‑900

        self.fig.patch.set_facecolor("#020617")
        self.draw()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chemical Equipment Parameter Visualizer - Desktop")
        self.setMinimumSize(900, 500)

        self.selected_file: str | None = None
        self.current_worker: UploadWorker | None = None
        self.current_history_worker: HistoryWorker | None = None
        self.history_data: list[Dict[str, Any]] = []

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        title = QLabel("Chemical Equipment Parameter Visualizer")
        title.setStyleSheet("color: #0f766e; font-size: 20px; font-weight: 600;")
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Upload an equipment CSV file, then view summary statistics and type distribution."
        )
        subtitle.setStyleSheet("color: #cbd5f5; font-size: 11px;")
        main_layout.addWidget(subtitle)

        # Top row: file picker + auth form + upload button.
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # File selection side
        file_column = QVBoxLayout()
        file_label = QLabel("Select equipment CSV")
        file_label.setStyleSheet("color: #e5e7eb; font-size: 11px;")

        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet("color: #9ca3af; font-size: 10px;")

        select_button = QPushButton("Browse...")
        select_button.setStyleSheet(
            "background-color: #0891b2; color: #020617; padding: 6px 12px; border-radius: 4px;"
        )
        select_button.clicked.connect(self.on_select_file)

        file_column.addWidget(file_label)
        file_column.addWidget(select_button)
        file_column.addWidget(self.file_path_label)

        # Auth form
        auth_column = QFormLayout()
        auth_label = QLabel("Basic Auth (Django user)")
        auth_label.setStyleSheet("color: #e5e7eb; font-size: 11px;")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet(
            "background-color: #020617; color: white; border: 1px solid #374151; padding: 4px;"
        )

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(
            "background-color: #020617; color: white; border: 1px solid #374151; padding: 4px;"
        )

        auth_column.addRow(auth_label)
        auth_column.addRow("Username:", self.username_input)
        auth_column.addRow("Password:", self.password_input)

        # Upload button
        self.upload_button = QPushButton("Upload CSV")
        self.upload_button.setStyleSheet(
            "background-color: #0f766e; color: #e5e7eb; padding: 8px 18px; border-radius: 4px;"
        )
        self.upload_button.clicked.connect(self.on_upload_clicked)

        top_row.addLayout(file_column, stretch=2)
        top_row.addLayout(auth_column, stretch=2)
        top_row.addWidget(self.upload_button, stretch=1)

        main_layout.addLayout(top_row)

        # Info label for errors / status
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #fecaca; font-size: 11px;")
        main_layout.addWidget(self.info_label)

        # Bottom section: stats + chart
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        # Summary stats text so the user can quickly scan the averages.
        self.stats_label = QLabel("No statistics yet.\nUpload a CSV to see results.")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("color: #e5e7eb; font-size: 11px;")
        bottom_row.addWidget(self.stats_label, stretch=1)

        # Matplotlib canvas showing the same distribution chart as the web app.
        self.chart_canvas = EquipmentChartCanvas(self)
        bottom_row.addWidget(self.chart_canvas, stretch=2)

        main_layout.addLayout(bottom_row)

        # Simple history panel – mirrors the small list on the React side.
        history_label = QLabel("Upload History (Last 5)")
        history_label.setStyleSheet("color: #e5e7eb; font-size: 14px; font-weight: 600; margin-top: 10px;")
        main_layout.addWidget(history_label)

        history_header = QHBoxLayout()
        refresh_history_button = QPushButton("Refresh History")
        refresh_history_button.setStyleSheet(
            "background-color: #0891b2; color: #020617; padding: 4px 8px; border-radius: 4px; font-size: 10px;"
        )
        refresh_history_button.clicked.connect(self.on_refresh_history)
        history_header.addWidget(refresh_history_button)
        history_header.addStretch()
        main_layout.addLayout(history_header)

        # List widget is enough here; no need for a full table.
        self.history_list = QListWidget()
        self.history_list.setStyleSheet(
            "background-color: #1e293b; color: #e5e7eb; border: 1px solid #374151; border-radius: 4px; font-size: 10px;"
        )
        self.history_list.setMaximumHeight(150)
        main_layout.addWidget(self.history_list)

        self.setLayout(main_layout)
        self.setStyleSheet("background-color: #020617;")  # slate‑900

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

        # Disable the button during the upload so it's harder to spam the API.
        self.upload_button.setEnabled(False)
        self.upload_button.setText("Uploading...")
        self.info_label.setText("")

        # Kick off the upload in the background; results are handled in
        # `on_upload_finished`.
        self.current_worker = UploadWorker(self.selected_file, username, password)
        self.current_worker.finished_with_result.connect(self.on_upload_finished)
        self.current_worker.start()

    def on_upload_finished(self, result: UploadResult) -> None:
        # Re‑enable the button once the thread has finished.
        self.upload_button.setEnabled(True)
        self.upload_button.setText("Upload CSV")

        if not result.ok:
            self._show_error(result.error_message or "Upload failed.")
            return

        if not result.stats:
            self._show_error("Upload succeeded but no stats were returned.")
            return

        stats = result.stats
        # Update the text summary so it roughly matches the web dashboard.
        summary_lines = [
            f"Total equipment count: {stats.get('total_count', 0)}",
            f"Average flowrate: {stats.get('average_flowrate', 0):.2f}",
            f"Average pressure: {stats.get('average_pressure', 0):.2f}",
            f"Average temperature: {stats.get('average_temperature', 0):.2f}",
        ]
        self.stats_label.setText("\n".join(summary_lines))

        # Update the chart by passing the type_distribution dict directly.
        type_distribution = stats.get("type_distribution", {})
        self.chart_canvas.plot_distribution(type_distribution)
        self.info_label.setText("Upload complete.")
        
        # Refresh history after successful upload
        self.on_refresh_history()

    def on_refresh_history(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            return

        # Start history worker thread
        self.current_history_worker = HistoryWorker(username, password)
        self.current_history_worker.finished_with_result.connect(self.on_history_finished)
        self.current_history_worker.start()

    def on_history_finished(self, result: HistoryResult) -> None:
        if not result.ok:
            # Silently fail - history is not critical
            return

        if not result.history:
            self.history_list.clear()
            return

        self.history_data = result.history
        self.history_list.clear()

        for entry in result.history:
            # Format: "filename - summary - date"
            try:
                uploaded_at = datetime.fromisoformat(entry["uploaded_at"].replace("Z", "+00:00"))
                date_str = uploaded_at.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = entry["uploaded_at"]

            item_text = f"{entry['original_filename']} - {entry['summary']} ({date_str})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, entry["pdf_path"])  # Store PDF path for potential download
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

