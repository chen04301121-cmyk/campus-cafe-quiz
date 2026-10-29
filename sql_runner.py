"""Run generated SQL safely and compare the result with a quiz answer.

This file has two jobs:
1. run_readonly_query: execute a SELECT query with the read-only database
   role. It does not require a sign-in, so the public AI page can use it.
2. compare_with_expected: check a query result against the expected rows
   stored in questions.py.
"""

import os
import re
from collections import Counter
from decimal import Decimal

import psycopg

MAX_ROWS = 500


def run_readonly_query(query):
    """Execute one SELECT/WITH query and return (columns, rows, truncated).

    Safety: the quiz_reader role can only read products and orders, the
    transaction is read-only, there is a 5 second timeout, and prepared
    execution rejects multiple statements.
    """
    query = query.strip()
    if not query:
        raise ValueError("There is no SQL to run.")
    if len(query) > 10000:
        raise ValueError("The SQL is too long.")
    if not re.match(r"^(SELECT|WITH)\b", query, re.IGNORECASE):
        raise ValueError("Only SELECT or WITH queries can be run.")

    with psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["QUIZ_PGUSER"],
        password=os.environ["QUIZ_PGPASSWORD"],
        sslmode="require",
        connect_timeout=10,
    ) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute("SET LOCAL lock_timeout = '2s'")
            # Prepared execution rejects multiple SQL statements.
            cur.execute(query, prepare=True)
            if cur.description is None:
                raise ValueError("The query did not return a result table.")
            columns = [column.name for column in cur.description]
            rows = cur.fetchmany(MAX_ROWS + 1)
            truncated = len(rows) > MAX_ROWS
            return columns, rows[:MAX_ROWS], truncated


def _normalize(value):
    """Make values comparable.

    The database returns Decimal('3.00') while questions.py stores 3.00,
    so every number is rounded to 2 decimals as a float. Other values
    (text, dates) are compared as strings.
    """
    if isinstance(value, (int, float, Decimal)):
        return round(float(value), 2)
    return str(value)


def compare_with_expected(columns, rows, expected_columns, expected_rows):
    """Compare a query result with the expected answer.

    Returns (status, message). Status is one of:
    "correct", "names", "order", "wrong".
    """
    actual = [tuple(_normalize(v) for v in row) for row in rows]
    expected = [tuple(_normalize(v) for v in row) for row in expected_rows]

    if actual == expected:
        same_names = [c.lower() for c in columns] == [
            c.lower() for c in expected_columns
        ]
        if same_names:
            return "correct", "The rows and column names match the expected answer."
        return (
            "names",
            "The rows match, but the column names differ. "
            f"Expected: {', '.join(expected_columns)}. "
            f"Got: {', '.join(columns)}.",
        )

    # Same rows in a different order.
    if Counter(actual) == Counter(expected):
        return "order", "The rows match, but they are in a different order."

    return (
        "wrong",
        f"The result does not match. Expected {len(expected)} row(s), "
        f"got {len(actual)} row(s).",
    )
