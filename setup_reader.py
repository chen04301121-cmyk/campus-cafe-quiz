import os
import secrets
from pathlib import Path

import psycopg
from psycopg import sql
from dotenv import load_dotenv, set_key

env_path = Path(__file__).with_name(".env")
load_dotenv(env_path, override=True)

admin_user = os.environ["PGUSER"]
if not admin_user.startswith("postgres."):
    raise ValueError("PGUSER must be the admin Session pooler username.")

project_ref = admin_user.split(".", 1)[1]
reader_user = f"quiz_reader.{project_ref}"
reader_password = secrets.token_urlsafe(32)

connection_settings = {
    "host": os.environ["PGHOST"],
    "port": os.environ["PGPORT"],
    "dbname": os.environ["PGDATABASE"],
    "sslmode": "require",
    "connect_timeout": 15,
}

with psycopg.connect(
    **connection_settings,
    user=admin_user,
    password=os.environ["PGPASSWORD"],
) as conn:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("ALTER ROLE quiz_reader LOGIN PASSWORD {}").format(
                sql.Literal(reader_password)
            )
        )
        cur.execute(
            "ALTER ROLE quiz_reader SET statement_timeout = '5s'"
        )
        cur.execute(
            "ALTER ROLE quiz_reader SET default_transaction_read_only = on"
        )

set_key(str(env_path), "QUIZ_PGUSER", reader_user)
set_key(str(env_path), "QUIZ_PGPASSWORD", reader_password)

print("Reader credentials saved to .env.")

with psycopg.connect(
    **connection_settings,
    user=reader_user,
    password=reader_password,
) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT current_user;")
        print("Connected as:", cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM public.products;")
        print("Product count:", cur.fetchone()[0])

        cur.execute("""
            SELECT
                has_table_privilege(
                    current_user, 'public.products', 'UPDATE'
                ),
                has_table_privilege(
                    current_user, 'public.orders', 'DELETE'
                );
        """)
        can_update, can_delete = cur.fetchone()
        print("Can update products:", can_update)
        print("Can delete orders:", can_delete)