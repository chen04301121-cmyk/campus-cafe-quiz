"""AI SQL Assistant page (no login required).

Streamlit shows every file in the pages/ folder as its own page, and each
page runs independently of app.py. That is why this page is public even
though the quiz page requires a sign-in.

Flow: question -> vector retrieval -> OpenAI -> generated SQL
      -> (extra credit) read-only execution -> compare with quiz answer.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAIError

from questions import QUESTIONS
from rag_sql import generate_sql
from sql_runner import compare_with_expected, run_readonly_query

# Load local secrets from the project's .env file. On Streamlit Cloud there
# is no .env file; the secrets are provided as environment variables instead.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

st.set_page_config(page_title="AI SQL Assistant", page_icon="🤖", layout="wide")

# Because this page is public, limit how often the AI can be called so
# nobody can use up the API budget.
SESSION_LIMIT = 10  # questions per visitor session
DAILY_LIMIT = 100   # questions per day for the whole site

EXAMPLE_QUESTIONS = [
    "How many units of each product were sold?",
    "Which products have never been ordered?",
    "What is the total revenue for each category?",
    "Which date had the most orders?",
]


@st.cache_resource
def daily_counter():
    """Shared counter that lives as long as the server process."""
    return {"day": date.today(), "count": 0}


def check_limits():
    """Return an error message if a limit is reached, otherwise None."""
    counter = daily_counter()
    if counter["day"] != date.today():
        # A new day started: reset the shared counter.
        counter["day"] = date.today()
        counter["count"] = 0
    if st.session_state.get("ai_calls", 0) >= SESSION_LIMIT:
        return f"You reached the limit of {SESSION_LIMIT} questions per session."
    if counter["count"] >= DAILY_LIMIT:
        return "The daily question limit for this site has been reached. Try again tomorrow."
    return None


def record_call():
    """Count one AI call for this visitor and for the whole site."""
    st.session_state["ai_calls"] = st.session_state.get("ai_calls", 0) + 1
    daily_counter()["count"] += 1


def use_example(text):
    """Callback for the example buttons: fill the text box, clear the quiz pick."""
    st.session_state["ai_question"] = text
    st.session_state["ai_quiz_pick"] = 0


def use_quiz_question():
    """Callback for the quiz selector: copy the quiz prompt into the text box."""
    quiz_id = st.session_state["ai_quiz_pick"]
    if quiz_id:
        quiz = next(q for q in QUESTIONS if q["id"] == quiz_id)
        st.session_state["ai_question"] = quiz["prompt"]


def show_comparison(columns, rows, quiz):
    """Compare the executed result with the quiz's expected answer."""
    status, message = compare_with_expected(
        columns, rows, quiz["expected_columns"], quiz["expected_rows"]
    )
    if status == "correct":
        st.success(f"Correct. {message}")
    elif status in ("names", "order"):
        st.warning(f"Almost. {message}")
    else:
        st.error(f"Not correct. {message}")

    with st.expander("Expected answer"):
        st.dataframe(
            pd.DataFrame(quiz["expected_rows"], columns=quiz["expected_columns"]),
            hide_index=True,
        )


st.title("AI SQL Assistant")
st.write(
    "Ask a question about the cafe data in plain English. The app searches a "
    "vector database for the most relevant knowledge (RAG), then asks an AI "
    "model to write the SQL. The SQL is then run with a read-only database "
    "account so you can see the result."
)

with st.expander("Database schema"):
    st.code(
        "products(product_id, product_name, category, price)\n"
        "orders(order_id, product_id, quantity, order_date)",
        language="text",
    )

# Clicking an example button fills the text box below.
st.write("Try an example:")
columns = st.columns(len(EXAMPLE_QUESTIONS))
for column, example in zip(columns, EXAMPLE_QUESTIONS):
    column.button(
        example,
        use_container_width=True,
        on_click=use_example,
        args=(example,),
    )

# Optional: pick a quiz question to test the AI against the expected answer.
st.selectbox(
    "Or test with a quiz question (the result is compared with the expected answer)",
    options=[0] + [q["id"] for q in QUESTIONS],
    format_func=lambda quiz_id: (
        "None"
        if quiz_id == 0
        else f"Q{quiz_id}. "
        + next(q["title"] for q in QUESTIONS if q["id"] == quiz_id)
    ),
    key="ai_quiz_pick",
    on_change=use_quiz_question,
)

question = st.text_area(
    "Your question",
    key="ai_question",
    height=100,
    max_chars=300,
    placeholder="For example: Which products have never been ordered?",
)

if st.button("Generate SQL", type="primary"):
    limit_message = check_limits()
    if limit_message:
        st.warning(limit_message)
    else:
        record_call()
        result = None
        try:
            with st.spinner("Retrieving knowledge and generating SQL..."):
                result = generate_sql(question)
        except ValueError as exc:
            st.error(str(exc))
        except RuntimeError:
            st.error("The AI service is not configured correctly.")
        except OpenAIError:
            st.error("The AI service could not answer. Please try again.")
        except Exception:
            st.error("Something went wrong. Please try again.")

        if result:
            st.subheader("Generated SQL")
            st.code(result["sql"], language="sql")

            with st.expander("Retrieved context (from the vector database)"):
                for hit in result["hits"]:
                    st.markdown(
                        f"**{hit['id']}** · {hit['kind']} · "
                        f"distance {hit['distance']:.3f}"
                    )
                    st.text(hit["text"])

            # Extra credit: run the SQL with the read-only account.
            st.subheader("Query result")
            try:
                with st.spinner("Running the SQL..."):
                    result_columns, result_rows, truncated = run_readonly_query(
                        result["sql"]
                    )
                st.dataframe(
                    pd.DataFrame(result_rows, columns=result_columns),
                    hide_index=True,
                )
                if truncated:
                    st.warning("Showing the first 500 rows.")
                else:
                    st.caption(f"Rows returned: {len(result_rows)}")

                # Compare with the expected answer if a quiz question is chosen.
                quiz_id = st.session_state.get("ai_quiz_pick", 0)
                if quiz_id:
                    quiz = next(q for q in QUESTIONS if q["id"] == quiz_id)
                    show_comparison(result_columns, result_rows, quiz)
            except ValueError as exc:
                st.error(str(exc))
            except psycopg.Error as exc:
                message = exc.diag.message_primary or "Database query failed."
                st.error(f"The generated SQL could not run: {message}")
            except Exception:
                st.error("The SQL could not be run. Please try again.")

remaining = SESSION_LIMIT - st.session_state.get("ai_calls", 0)
st.caption(f"Questions left in this session: {max(remaining, 0)}")
