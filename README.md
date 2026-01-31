## FOSSEE Chemical Equipment Parameter Visualizer

This repository contains my solution for the FOSSEE screening task **"Chemical Equipment Parameter Visualizer"**.
The goal of the project is to read chemical equipment data from CSV files, compute basic statistics using
Python, and present the results both on the web and in a desktop application.

### 📺 Project Demo Video

You can watch the full demonstration of this hybrid application on YouTube:
**[Watch the Demo Video Here](https://youtu.be/zTHJymRW_O8)**

### 🔑 Authentication Credentials

To test the Web and Desktop applications, use the following local credentials:

* **Username:** Arjun
* **Password:** Hello@1234

---

### Project Structure

* `backend/` – Django REST API backend (CSV processing, analytics, PDF generation).
* `frontend-web/` – React + Chart.js dashboard for uploading CSVs and viewing charts.
* `frontend-desktop/` – PyQt5 desktop client with an embedded Matplotlib chart.

---

### Installation & Setup

#### 1. Repository and backend setup

1. **Clone / create the repository** From the project root:
```bash
chmod +x setup.sh
./setup.sh

```


This initialises a git repository (if it does not exist yet) and creates a default `.gitignore`
plus an initial commit.
2. **Create a virtual environment (recommended)** ```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```


```


3. **Install backend dependencies**
```bash
pip install -r requirements.txt

```


4. **Apply migrations and create a user for Basic Auth**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

```


5. **Run the Django development server**
```bash
python manage.py runserver

```


By default the backend will be available at `http://127.0.0.1:8000/`.

#### 2. React web frontend (`frontend-web`)

1. **Install Node dependencies**
```bash
cd frontend-web
npm install

```


2. **Start the Vite dev server**
```bash
npm run dev

```


The web dashboard should be available at `http://127.0.0.1:5173/`.
Make sure the Django backend is running so the upload endpoint is reachable.

#### 3. PyQt5 desktop frontend (`frontend-desktop`)

1. **Create / activate a Python environment** (you can reuse the backend env or create a new one).
2. **Install desktop requirements**
```bash
cd frontend-desktop
pip install -r requirements.txt

```


3. **Run the desktop client**
```bash
python main.py

```


The desktop app expects the Django backend at `http://127.0.0.1:8000/` and uses the same API as the web app.

---

### Logic: How the backend works

* **CSV upload and validation** The `core` app exposes an endpoint `/api/upload-equipment/` that accepts a CSV file
with the following columns:
* `Name`
* `Type`
* `Flowrate`
* `Pressure`
* `Temperature`


Django REST Framework reads the uploaded file, and **Pandas** is used to parse it into a
DataFrame. Using Pandas makes the analytics more readable: with a few lines we can
compute means, counts, and group-by statistics instead of writing manual loops.
* **Analytics with Pandas** After reading the CSV, the backend:
* Counts the total number of equipment rows.
* Computes the average flowrate, pressure and temperature.
* Uses `value_counts()` on the `Type` column to get the distribution of equipment types.


The same data is saved to the `Equipment` model so it can be inspected later if needed.
* **PDF report generation and storage** The summary statistics are also written into a simple PDF report using **ReportLab**.
The report is stored under `MEDIA_ROOT/reports/` and the relative path (for example
`media/reports/equipment_report_YYYYMMDD_HHMMSS.pdf`) is stored in the `History` model.
* **History management (keep last 5 uploads)** Each successful upload creates a `History` entry containing:
* Original file name.
* A short text summary (total count and averages).
* The path to the generated PDF report.


After saving a new entry, the view trims the table so that only the **five most recent**
uploads are kept. Older `History` rows are deleted, which keeps the database small and
makes it easier to display recent activity to the user.

---

### API endpoints

* **`POST /api/upload-equipment/`**
* **Auth**: Basic Auth or Session Auth (Django user).
* **Body** (multipart form-data):
* `file`: CSV file with columns `Name`, `Type`, `Flowrate`, `Pressure`, `Temperature`.


* **Response (200)**:
```json
{
  "message": "CSV processed successfully.",
  "stats": {
    "total_count": 10,
    "average_flowrate": 123.45,
    "average_pressure": 2.34,
    "average_temperature": 56.78,
    "type_distribution": {
      "Pump": 4,
      "Valve": 6
    }
  },
  "pdf_report": "media/reports/equipment_report_20260127_120000.pdf"
}

```


* **Error cases**:
* Missing or invalid file.
* Missing required columns in the CSV (returns a helpful list of missing column names).
* Authentication failure.





---

### Tech stack at a glance

* **Backend**: Django + Django REST Framework, Pandas, ReportLab, SQLite.
* **Web frontend**: React, Chart.js (via `react-chartjs-2`), Tailwind CSS, Axios.
* **Desktop frontend**: PyQt5, Matplotlib, `requests`.

---

**Submitted by:** Arjun Singh

**Registration Number:** 24BSA10257

**Institution:** VIT Bhopal University