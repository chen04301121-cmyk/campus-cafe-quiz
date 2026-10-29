"""RAG Text-to-SQL: question -> vector retrieval -> OpenAI -> SQL.

Workflow:
1. Retrieve the most relevant knowledge documents from ChromaDB.
2. Put the question and those documents into one prompt.
3. Ask the OpenAI model to write a single SELECT query.
4. Clean and check the answer before returning it.
"""

import os
import re

from openai import OpenAI

from rag_knowledge import KIND_EXAMPLE, KIND_SCHEMA, KIND_SEMANTICS
from rag_store import retrieve

MAX_QUESTION_LENGTH = 300

# The model name comes from the environment so it is easy to change
# without editing the code.
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are an expert PostgreSQL assistant for a small cafe database. "
    "Write one SQL query that answers the user's question. "
    "Use ONLY the tables and columns described in the context. "
    "Output a single SELECT query and nothing else: no explanation, "
    "no comments, no markdown."
)


def build_prompt(question, hits):
    """Combine the retrieved documents and the question into one prompt."""
    # Group the retrieved documents by kind so the model can read them easily.
    sections = [
        (KIND_SCHEMA, "Database schema"),
        (KIND_SEMANTICS, "Business rules"),
        (KIND_EXAMPLE, "Example questions and SQL"),
    ]
    parts = []
    for kind, title in sections:
        texts = [hit["text"] for hit in hits if hit["kind"] == kind]
        if texts:
            parts.append(f"## {title}\n" + "\n\n".join(texts))

    context = "\n\n".join(parts)
    return f"{context}\n\n## Question\n{question}\n\n## SQL"


def clean_sql(text):
    """Remove markdown fences and extra spaces from the model's answer."""
    text = text.strip()
    # Remove ```sql ... ``` wrappers if the model added them.
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_sql(question, n_results=4):
    """Return a dict with the generated SQL and the retrieved documents."""
    question = question.strip()
    if not question:
        raise ValueError("Enter a question first.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(
            f"Your question is too long (max {MAX_QUESTION_LENGTH} characters)."
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    # Step 1: retrieval from the vector database.
    hits = retrieve(question, n_results=n_results)

    # Step 2: build the prompt from the retrieved documents.
    prompt = build_prompt(question, hits)

    # Step 3: ask the model to generate the SQL.
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    sql = clean_sql(response.choices[0].message.content or "")

    # Step 4: only accept a read-only query.
    if not re.match(r"^(SELECT|WITH)\b", sql, re.IGNORECASE):
        raise ValueError("The model did not return a SELECT query.")

    return {"sql": sql, "hits": hits, "prompt": prompt}


if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    # Load OPENAI_API_KEY and OPENAI_MODEL from the local .env file.
    load_dotenv()

    user_question = (
        " ".join(sys.argv[1:])
        or "How many units of each product were sold?"
    )
    result = generate_sql(user_question)

    print("Retrieved context:")
    for hit in result["hits"]:
        print(f"  [{hit['distance']:.3f}] {hit['kind']:<9} {hit['id']}")
    print("\nGenerated SQL:")
    print(result["sql"])
