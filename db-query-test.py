import os
import time

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in .env")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# 1. 测 COUNT(*)
start = time.time()

with engine.connect() as conn:
    count = conn.execute(
        text("SELECT COUNT(*) FROM public.businesses_200k")
    ).scalar()

elapsed = time.time() - start

print(f"Row count: {count:,}")
print(f"COUNT query time: {elapsed:.3f} seconds")


# 2. 测一个小的 filter query，只返回 100 行
start = time.time()

df = pd.read_sql(
    '''
    SELECT *
    FROM public.businesses_200k
    WHERE "Industry" = 'Hospitality'
    LIMIT 100
    ''',
    engine
)

elapsed = time.time() - start

print()
print("Filtered shape:", df.shape)
print(f"Filtered query time: {elapsed:.3f} seconds")

print()
print(df[["Business Name", "Industry", "Category"]].head())