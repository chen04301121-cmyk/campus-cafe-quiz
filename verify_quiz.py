import os
from decimal import Decimal
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from questions import QUESTIONS


def normalize_rows(rows):
    return [
        tuple(
            Decimal(str(value))
            if isinstance(value, (int, float, Decimal))
            else value
            for value in row
        )
        for row in rows
    ]


def main():
    load_dotenv(Path(__file__).with_name(".env"))

    total_points = sum(question["points"] for question in QUESTIONS)

    if len(QUESTIONS) != 5 or total_points != 20:
        raise ValueError("The quiz must contain 5 questions totaling 20 points.")

    with psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["QUIZ_PGUSER"],
        password=os.environ["QUIZ_PGPASSWORD"],
        sslmode="require",
        connect_timeout=15,
    ) as conn:
        conn.read_only = True

        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '5s'")

            cur.execute("SELECT current_user;")
            if cur.fetchone()[0] != "quiz_reader":
                raise RuntimeError("Checks must run as quiz_reader.")

            for question in QUESTIONS:
                cur.execute(question["expected_sql"], prepare=True)

                columns = [column.name for column in cur.description]
                rows = cur.fetchmany(501)

                if columns != question["expected_columns"]:
                    raise AssertionError(
                        f"Q{question['id']}: column names do not match."
                    )

                if normalize_rows(rows) != normalize_rows(
                    question["expected_rows"]
                ):
                    raise AssertionError(
                        f"Q{question['id']}: result rows do not match."
                    )

                print(
                    f"PASS Q{question['id']}: "
                    f"{len(rows)} rows match the expected result."
                )

    print(f"All 5 questions passed. Total points: {total_points}")


if __name__ == "__main__":
    main()