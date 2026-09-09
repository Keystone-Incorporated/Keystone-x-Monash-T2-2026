import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# =========================
# 1. Load environment
# =========================
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in .env")

# =========================
# 2. Find CSV
# =========================
current_dir = Path(__file__).resolve().parent

csv_files = [
    f for f in current_dir.glob("*.csv")
    if "200k" in f.name.lower()
]

if not csv_files:
    raise FileNotFoundError(
        "No CSV file containing '200k' in the filename was found."
    )

CSV_FILE = csv_files[0]

print(f"Using CSV: {CSV_FILE.name}")

# =========================
# 3. Read CSV
# =========================
encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]

df = None

for enc in encodings:
    try:
        print(f"Trying encoding: {enc}")
        df = pd.read_csv(
            CSV_FILE,
            encoding=enc,
            low_memory=False
        )
        print(f"Successfully read CSV using {enc}")
        break
    except UnicodeDecodeError:
        print(f"Failed: {enc}")

if df is None:
    raise RuntimeError("Could not decode CSV with common encodings.")
# =========================
# 4. Connect to PostgreSQL
# =========================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

TABLE_NAME = "businesses_200k"
CHUNK_SIZE = 5000

# =========================
# 5. Recreate table
# =========================
print(f"\nCreating table: {TABLE_NAME}")

# First chunk creates the table automatically
first_chunk = df.iloc[:CHUNK_SIZE]

first_chunk.to_sql(
    TABLE_NAME,
    engine,
    schema="public",
    if_exists="replace",
    index=False,
    method="multi"
)

print(f"Imported {len(first_chunk):,} / {len(df):,}")

# =========================
# 6. Import remaining chunks
# =========================
for start in range(CHUNK_SIZE, len(df), CHUNK_SIZE):
    end = min(start + CHUNK_SIZE, len(df))

    chunk = df.iloc[start:end]

    chunk.to_sql(
        TABLE_NAME,
        engine,
        schema="public",
        if_exists="append",
        index=False,
        method="multi"
    )

    print(f"Imported {end:,} / {len(df):,}")

# =========================
# 7. Verify row count
# =========================
with engine.connect() as conn:
    count = conn.execute(
        text(f'SELECT COUNT(*) FROM public."{TABLE_NAME}"')
    ).scalar()

print("\nImport complete.")
print(f"Rows in database: {count:,}")