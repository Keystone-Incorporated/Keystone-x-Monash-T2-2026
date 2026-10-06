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

Copy `.env.example` to `.env` and set the required password. The data source
defaults to the local CSV:

```dotenv
DATA_SOURCE=csv
DASH_ACCESS_PASSWORD=your-password
```

Set `DATA_SOURCE=supabase` and provide `DATABASE_URL` to use Supabase instead.
Supabase mode loads all rows from `public.businesses` into memory at startup;
it does not use pagination. Favourites and comments are read from and written
to their database tables. CSV mode keeps favourites and comments in the local
JSON files beside the CSV. Business detail edits are saved to the selected
source as well.

If the local Windows launcher is present, double-click `start_dashboard.bat`.

Alternatively, run:

```powershell
python app_map.py
```

Then open your browser and go to:

http://127.0.0.1:8055/

## Deployment

The dashboard is currently hosted on Render.

Production/testing URL:
https://keystone-employer-dashboard.onrender.com

Access is password protected.

Deployment from the `main` branch is currently manual to prevent
untested commits from automatically affecting the hosted dashboard.

For a Supabase deployment, set `DATA_SOURCE=supabase`, `DATABASE_URL`,
`DASH_ACCESS_PASSWORD`, and `DASH_SESSION_SECRET` in the Render environment,
and use `gunicorn app_map:server` as the start command.
