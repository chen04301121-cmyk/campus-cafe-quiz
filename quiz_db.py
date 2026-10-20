import os
import re

import psycopg


def require_user(auth_client):
    try:
        session = auth_client.auth.get_session()
        if session is None:
            raise PermissionError("Please sign in first.")

        user = auth_client.auth.get_user(session.access_token).user
        if user is None:
            raise PermissionError("Please sign in first.")

        return user
    except Exception as exc:
        raise PermissionError(
            "Your session could not be verified. Please sign in again."
        ) from exc


def run_query(auth_client, query):
    require_user(auth_client)

    query = query.strip()

    if not query:
        raise ValueError("Enter a SQL query first.")

    if len(query) > 10000:
        raise ValueError("Your query is too long.")

    if not re.match(r"^(SELECT|WITH)\b", query, re.IGNORECASE):
        raise ValueError("Start your query with SELECT or WITH.")

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
                raise ValueError("Your query must return a result table.")

            columns = [column.name for column in cur.description]
            rows = cur.fetchmany(501)

    truncated = len(rows) > 500
    return columns, rows[:500], truncated

def save_answer(auth_client, question_id, answer_sql):
    user = require_user(auth_client)
    answer_sql = answer_sql.strip()

    if question_id not in range(1, 6):
        raise ValueError("Invalid question.")

    if not answer_sql:
        raise ValueError("Enter an answer before saving.")

    if len(answer_sql) > 10000:
        raise ValueError("Your answer is too long.")

    auth_client.table("quiz_answers").upsert(
        {
            "user_id": str(user.id),
            "question_id": question_id,
            "answer_sql": answer_sql,
        },
        on_conflict="user_id,question_id",
    ).execute()


def load_answer(auth_client, question_id):
    user = require_user(auth_client)

    response = (
        auth_client.table("quiz_answers")
        .select("answer_sql")
        .eq("user_id", str(user.id))
        .eq("question_id", question_id)
        .execute()
    )

    if response.data:
        return response.data[0]["answer_sql"]

    return None