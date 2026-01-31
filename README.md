## FOSSEE Chemical Equipment Parameter Visualizer

This repository contains my solution for the FOSSEE screening task **"Chemical Equipment Parameter Visualizer"**.
The goal of the project is to read chemical equipment data from CSV files, compute basic statistics using
Python, and present the results both on the web and in a desktop application.

### 📺 Project Demo Video

You can watch the full demonstration of this hybrid application here:
**[Watch the Demo Video (Google Drive)](https://drive.google.com/file/d/1tHvIXom8lqjGFrRgC48riTj4AunWd7a4/view?usp=sharing)**

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

#### 1. Repository and Backend Setup

1. **Initialize the project environment:**
From the project root, run the setup script:
```bash
chmod +x setup.sh
./setup.sh

```


2. **Create and activate a virtual environment:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

```


3. **Install backend dependencies:**
```bash
pip install -r requirements.txt

```


4. **Prepare the database and Admin user:**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

```


*(Note: Create the user 'Arjun' to match the demo credentials)*
5. **Run the Django server:**
```bash
python manage.py runserver

```


The API will be available at `http://127.0.0.1:8000/`.

#### 2. React Web Frontend (`frontend-web`)

1. **Install Node dependencies:**
```bash
cd frontend-web
npm install

```


2. **Start the development server:**
```bash
npm run dev

```


The dashboard will be available at `http://127.0.0.1:5173/`.

#### 3. PyQt5 Desktop Frontend (`frontend-desktop`)

1. **Install desktop requirements:**
```bash
cd frontend-desktop
pip install -r requirements.txt

```


2. **Run the desktop client:**
```bash
python main.py

```



---

### Logic: How the Backend Works

* **CSV Upload and Validation:**
The backend uses **Pandas** to parse uploaded CSV files. It validates required columns (Name, Type, Flowrate, Pressure, Temperature) and handles data cleaning before processing.
* **Analytics:**
Using Pandas, the system calculates the total equipment count, average physical parameters, and the distribution of equipment types.
* **PDF Report Generation:**
Summary statistics are written into a PDF report using **ReportLab**. These reports are stored in the media directory and linked to the user's history.
* **History Management:**
The system automatically maintains only the **five most recent** uploads in the database. This is handled by a post-save logic in the Django views to ensure efficient storage management.

---

### Tech Stack at a Glance

* **Backend:** Django, Django REST Framework, Pandas, ReportLab, SQLite.
* **Web:** React, Chart.js, Tailwind CSS, Axios.
* **Desktop:** PyQt5, Matplotlib, Requests.

---

**Submitted by:** Arjun Singh

**Registration Number:** 24BSA10257

**Institution:** VIT Bhopal University
