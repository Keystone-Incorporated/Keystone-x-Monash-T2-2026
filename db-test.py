from pathlib import Path
import os
import pandas as pd
from sqlalchemy import create_engine


def load_local_env():
    env_file = Path(__file__).with_name(".env")

    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key:
            os.environ.setdefault(key, value)


load_local_env()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is not set in .env")

engine = create_engine(database_url)

df = pd.read_sql(
    "SELECT * FROM public.businesses",
    engine
)

print("Shape:", df.shape)
print("Columns:", df.columns.tolist())
print(df.head())