# Requirements

- Python 3.13+

# Installation

Create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

# Run

For a quick start on Windows, double-click `start_dashboard.bat`.

Alternatively, run:

```powershell
python app_final.py
```

Then open your browser and go to:

http://127.0.0.1:8050/

## Deployment

The dashboard is currently hosted on Render.

Production/testing URL:
https://keystone-employer-dashboard.onrender.com

Access is password protected.

Deployment from the `main` branch is currently manual to prevent
untested commits from automatically affecting the hosted dashboard.
