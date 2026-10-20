import pandas as pd
import psycopg

from quiz_db import run_query, save_answer, load_answer
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

from questions import QUESTIONS

load_dotenv(Path(__file__).with_name(".env"), override=True)

st.set_page_config(
    page_title="Campus Cafe SQL Quiz",
    page_icon="☕",
    layout="wide",
)

# Keep each browser session's auth client separate.
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_PUBLISHABLE_KEY"],
    )

supabase = st.session_state.supabase

st.title("Campus Cafe SQL Quiz")
st.write("5 questions | 4 points each | 20 points total")

user = None

try:
    session = supabase.auth.get_session()
    if session:
        user = supabase.auth.get_user(session.access_token).user
except Exception:
    st.warning("Your session could not be verified. Please sign in again.")

if user is None:
    st.info("Sign in to access the quiz. Running and saving require sign-in.")

    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input(
                "Password", type="password", key="login_password"
            )
            login_clicked = st.form_submit_button("Sign in")

        if login_clicked:
            if not email.strip() or not password:
                st.error("Enter your email and password.")
            else:
                try:
                    response = supabase.auth.sign_in_with_password(
                        {
                            "email": email.strip(),
                            "password": password,
                        }
                    )
                    if response.session:
                        st.rerun()
                    else:
                        st.error("Sign-in did not create a session.")
                except Exception as exc:
                    st.error(f"Sign-in failed: {exc}")

    with signup_tab:
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input(
                "Password", type="password", key="signup_password"
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
                key="signup_confirm_password",
            )
            signup_clicked = st.form_submit_button("Create account")

        if signup_clicked:
            if not new_email.strip():
                st.error("Enter your email.")
            elif len(new_password) < 8:
                st.error("Use a password with at least 8 characters.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    response = supabase.auth.sign_up(
                        {
                            "email": new_email.strip(),
                            "password": new_password,
                        }
                    )
                    if response.session:
                        st.rerun()
                    else:
                        st.success(
                            "Check your email for a confirmation link, "
                            "then return here and sign in."
                        )
                except Exception as exc:
                    st.error(f"Registration failed: {exc}")

    st.stop()

st.success(f"Signed in as {user.email}")

if st.button("Sign out"):
    try:
        supabase.auth.sign_out()
    except Exception:
        st.warning("Remote sign-out failed. The local session was cleared.")
    st.session_state.clear()
    st.rerun()

st.subheader("Choose a question")

question_id = st.selectbox(
    "Question",
    options=[question["id"] for question in QUESTIONS],
    format_func=lambda question_id: next(
        f"Q{question['id']}. {question['title']} "
        f"({question['points']} points)"
        for question in QUESTIONS
        if question["id"] == question_id
    ),
)

question = next(
    question for question in QUESTIONS
    if question["id"] == question_id
)

st.write(question["prompt"])

with st.expander("Database schema"):
    st.code(
        "products(product_id, product_name, category, price)\n"
        "orders(order_id, product_id, quantity, order_date)",
        language="text",
    )
    st.write("orders.product_id references products.product_id.")

with st.expander("Hint: expected SQL and result"):
    st.code(question["expected_sql"].strip(), language="sql")
    st.dataframe(
        pd.DataFrame(
            question["expected_rows"],
            columns=question["expected_columns"],
        ),
        hide_index=True,
    )
if st.button("Load saved answer"):
    try:
        saved_answer = load_answer(supabase, question_id)

        if saved_answer is None:
            st.info("No saved answer for this question.")
        else:
            st.session_state[f"sql_{question_id}"] = saved_answer
            st.success("Saved answer loaded.")
    except (PermissionError, ValueError) as exc:
        st.error(str(exc))
    except Exception:
        st.error("Could not load your answer. Please try again.")

query = st.text_area(
    "Your SQL",
    height=200,
    placeholder="SELECT ...",
    key=f"sql_{question_id}",
)

if st.button("Run SQL", type="primary"):
    try:
        with st.spinner("Running query..."):
            columns, rows, truncated = run_query(supabase, query)

        st.subheader("Query result")
        st.dataframe(
            pd.DataFrame(rows, columns=columns),
            hide_index=True,
        )

        if truncated:
            st.warning("Showing the first 500 rows.")
        else:
            st.success(f"Query completed. Rows returned: {len(rows)}")

    except (PermissionError, ValueError) as exc:
        st.error(str(exc))
    except psycopg.Error as exc:
        message = exc.diag.message_primary or "Database query failed."
        st.error(f"SQL error: {message}")
    except Exception:
        st.error("The query could not run. Please try again.")

if st.button("Save answer"):
    try:
        save_answer(supabase, question_id, query)
        st.success("Answer saved to the database.")
    except (PermissionError, ValueError) as exc:
        st.error(str(exc))
    except Exception:
        st.error("Could not save your answer. Please try again.")