import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=True)

with psycopg.connect(
    host=os.environ["PGHOST"],
    port=os.environ["PGPORT"],
    dbname=os.environ["PGDATABASE"],
    user=os.environ["PGUSER"],
    password=os.environ["PGPASSWORD"],
    sslmode="require",
    connect_timeout=10,
) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT product_id, product_name, category, price
            FROM public.products
            ORDER BY product_id;
        """)

        rows = cur.fetchall()
        print("database connection successful, query results:")
        for row in rows:
            print(row)

        cur.execute("SELECT COUNT(*) FROM public.orders;")
        print("order count:", cur.fetchone()[0])