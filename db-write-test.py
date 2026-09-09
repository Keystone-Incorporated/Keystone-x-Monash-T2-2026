import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# 先找一条记录
with engine.connect() as conn:
    row = conn.execute(
        text("""
            SELECT id, "Business Name", "Phone"
            FROM public.businesses
            WHERE id IS NOT NULL
            LIMIT 1
        """)
    ).mappings().first()

print("Before:", row)

business_id = row["id"]
old_phone = row["Phone"]

# 写入一个测试值
test_phone = "TEST-12345"

with engine.begin() as conn:
    conn.execute(
        text("""
            UPDATE public.businesses
            SET "Phone" = :phone
            WHERE id = :id
        """),
        {
            "phone": test_phone,
            "id": business_id
        }
    )

# 再读回来确认
with engine.connect() as conn:
    updated = conn.execute(
        text("""
            SELECT id, "Business Name", "Phone"
            FROM public.businesses
            WHERE id = :id
        """),
        {"id": business_id}
    ).mappings().first()

print("After:", updated)

# 恢复原值
with engine.begin() as conn:
    conn.execute(
        text("""
            UPDATE public.businesses
            SET "Phone" = :phone
            WHERE id = :id
        """),
        {
            "phone": old_phone,
            "id": business_id
        }
    )

print("Restored original value.")