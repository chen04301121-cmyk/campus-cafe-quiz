# Campus Cafe SQL Quiz

A 20-point SQL quiz built with Python, Streamlit, Supabase PostgreSQL,
and Supabase Auth. Students sign in, write SQL, run it against live
data, view result tables, and save their answers.

## Links

- Quiz site: https://campus-cafe-quiz-b2ifkmvrgsbw4azmh6h22x.streamlit.app/
- Repository: https://github.com/chen04301121-cmyk/campus-cafe-quiz
- GitHub Actions: https://github.com/chen04301121-cmyk/campus-cafe-quiz/actions

## How to use the quiz

1. Open the quiz site.
2. Select **Create account** and register with an email and password.
3. If email confirmation is requested, confirm your email, return to
   the quiz site, and sign in.
4. Choose a question.
5. Enter a single SQL query starting with SELECT or WITH.
6. Click **Run SQL** to view results from the live database.
7. Expand **Hint: expected SQL and result** to compare your result
   with the reference answer.
8. Click **Save answer** to save the current question's SQL.
9. After signing in again, select the question and click
   **Load saved answer** to retrieve it.

Saving an answer does not execute it or require it to be correct.
Each student has one saved answer per question. Saving again updates
that answer.

Signed-out users cannot run queries or save answers. Authentication
is checked again inside the run, save, and load functions.

## Quiz questions

| Question | Topic | Points |
|---|---|---:|
| 1 | Filter coffee products | 4 |
| 2 | Sort and limit the most expensive products | 4 |
| 3 | Join orders with product names | 4 |
| 4 | Group and sum quantities sold | 4 |
| 5 | Find products without orders using a LEFT JOIN | 4 |
| **Total** | | **20** |

Every question includes reference SQL, expected column names, and
expected result rows.

The reference SQL is one possible solution. Students should compare
result sets rather than reproduce the reference SQL character for
character. The application does not automatically assign grades.

## AI SQL Assistant (RAG Text-to-SQL)

The app has a second, public page that turns a plain-English question into a
SQL query using Retrieval-Augmented Generation (RAG). No sign-in is required.

- AI SQL Assistant page: https://campus-cafe-quiz-b2ifkmvrgsbw4azmh6h22x.streamlit.app/AI_SQL_Assistant
- Quiz page (requires sign-in): https://campus-cafe-quiz-b2ifkmvrgsbw4azmh6h22x.streamlit.app/

If the app is asleep, click "Yes, get this app back up!" and wait about a minute. The first question is slower because the vector database is built on first use.

### RAG architecture

```
User question
   -> ChromaDB vector search (top 4 most similar knowledge documents)
   -> OpenAI model (question + retrieved documents in one prompt)
   -> Generated SQL
   -> Extra credit: run with the read-only database role, show the table,
      compare with the quiz's expected answer
```

**Vector database (ChromaDB).** 14 short documents are embedded with
ChromaDB's default embedding model and stored in a local collection:

- 3 database schema documents (tables, columns, the foreign key)
- 5 business semantics documents (what "units sold", "revenue" or "never
  ordered" mean in SQL, allowed category values, PostgreSQL rules)
- 6 few-shot examples (a question with its SQL; they are different from the
  quiz questions so the quiz answers are not leaked)

For every question the app retrieves the 4 most similar documents. The page
shows them in the "Retrieved context" section, so the retrieval is visible.

**AI API.** OpenAI Chat Completions API. The model name is read from the
`OPENAI_MODEL` environment variable. The prompt contains only the retrieved
documents and the question, and the model is told to return one SELECT query.
The answer is checked to start with `SELECT` or `WITH` before it is used.

**Safety.**

- Generated SQL runs only with the existing `quiz_reader` role (SELECT on
  `products` and `orders`), in a read-only transaction, with a 5 second
  timeout, and multiple statements are rejected.
- Because the page is public, the AI can be called at most 10 times per
  visitor session and 100 times per day for the whole site.
- The API key is stored only in `.env` (local) or Streamlit Secrets
  (deployed). It is never committed.

### New files

| File | Purpose |
|---|---|
| `rag_knowledge.py` | The 14 knowledge documents (schema, semantics, examples) |
| `rag_store.py` | Builds the ChromaDB collection and retrieves similar documents |
| `rag_sql.py` | Builds the prompt, calls OpenAI, cleans and checks the SQL |
| `sql_runner.py` | Read-only execution without sign-in and result comparison |
| `pages/1_AI_SQL_Assistant.py` | The public Streamlit page |

### Run locally

1. Install the dependencies: `python -m pip install -r requirements.txt`
2. Add these lines to the local `.env` file (do not commit it):

```
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
OPENAI_MODEL="YOUR_MODEL_NAME"
```

3. Start the app: `python -m streamlit run app.py`
4. Open **AI SQL Assistant** in the left sidebar.

The `chroma_db/` folder is created automatically on the first question and is
ignored by Git. The first question is slower because ChromaDB downloads its
default embedding model once.

When deploying to Streamlit Community Cloud, add `OPENAI_API_KEY` and
`OPENAI_MODEL` to the app's Secrets next to the existing database secrets.

### Screenshots

Basic: a question and its generated SQL.

![Question and generated SQL](docs/rag-basic.png)

Extra credit: executed SQL, result table, and validation outcome.

![Executed SQL, result table and validation](docs/rag-extra-credit.png)

## Architecture

- **Streamlit Community Cloud** hosts the Python web application.
- **Supabase Auth** handles email/password registration and sign-in.
- **Supabase PostgreSQL** stores products, orders, and saved answers.
- **Psycopg** runs student queries over the network through the
  Supabase Session pooler with `sslmode=require`.
- **Supabase Data API** saves and retrieves answers using the signed-in
  user's authentication session.
- **GitHub Actions** runs the reference queries against the live
  database using credentials stored in GitHub Secrets.

## Database and permissions

The database contains:

- `products`: 6 products with names, categories, and prices.
- `orders`: 10 orders with product references, quantities, and dates.
- `quiz_answers`: saved SQL identified by user ID and question ID.

The `quiz_reader` database role can select from `products` and
`orders`. Student queries do not use the administrator account.

Query execution uses read-only transactions, a five-second statement
timeout, and prepared execution that rejects multiple statements.
The UI displays at most 500 result rows.

The `quiz_answers` table uses Row Level Security. Authenticated users
can select, insert, and update only rows belonging to their own
`auth.uid()`. Anonymous users and `quiz_reader` cannot access it.

Saved SQL is transmitted as a data value through the Supabase client,
not interpolated into an SQL command.

## Repository files

| File | Purpose |
|---|---|
| `app.py` | Authentication and quiz interface |
| `questions.py` | Five questions, points, reference SQL, and expected results |
| `quiz_db.py` | Authentication checks, query execution, and answer storage |
| `database_setup.sql` | Initial tables, seed data, role, and RLS policies |
| `setup_reader.py` | Generates the reader password and saves it locally |
| `test_connection.py` | Checks the initial administrator connection |
| `verify_quiz.py` | Verifies all five reference queries against live data |
| `requirements.txt` | Python dependencies |
| `.github/workflows/verify.yml` | GitHub Actions workflow |
| `.gitignore` | Excludes local credentials and environment files |

## Set up a new Supabase project

These instructions are for a fresh project. Do not rerun the initial
database script against an already initialized database.

1. Create a Supabase project and securely retain its database password.
2. Enable the Data API. Disable automatic exposure of new tables.
3. In SQL Editor, run `database_setup.sql` once.
4. In the project's Connect panel, select **Session pooler** and copy
   the host, port, database, and complete administrator username.
5. Obtain the project's URL and Publishable key.
6. Enable email/password authentication.
7. In **Authentication > URL Configuration**, set **Site URL** to the
   deployed quiz URL. For local-only testing, use
   `http://localhost:8501`.

## Run locally

Use Python 3.14.

```bash
git clone https://github.com/chen04301121-cmyk/campus-cafe-quiz.git
cd campus-cafe-quiz
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a local `.env` file in the repository root:

```dotenv
PGHOST=YOUR_SESSION_POOLER_HOST
PGPORT=5432
PGDATABASE=postgres
PGUSER=postgres.YOUR_PROJECT_REF
PGPASSWORD="YOUR_ADMIN_DATABASE_PASSWORD"
PGSSLMODE=require
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
```

Replace the placeholders with your own project's values. Do not commit
this file.

For a newly initialized project, run:

```bash
python test_connection.py
python setup_reader.py
python verify_quiz.py
python -m streamlit run app.py
```

`setup_reader.py` generates a random reader password and adds
`QUIZ_PGUSER` and `QUIZ_PGPASSWORD` to `.env`. It also configures the
reader's default read-only transactions and statement timeout.

Running it again resets the reader password. If you reset it, update
the corresponding GitHub and Streamlit Secrets.

## GitHub Actions and Secrets

The **Verify SQL Quiz** workflow runs on pushes to `main` and can also
be started manually from the Actions page.

In the repository, open:

**Settings > Secrets and variables > Actions > New repository secret**

Add these repository secrets:

| Secret | Value |
|---|---|
| `PGHOST` | Session pooler hostname |
| `QUIZ_PGUSER` | Full pooler username, such as `quiz_reader.PROJECT_REF` |
| `QUIZ_PGPASSWORD` | Reader password generated by `setup_reader.py` |

Secret values must not include the variable name or surrounding quotes.

The workflow installs dependencies and runs `verify_quiz.py`. This
script checks the database role, the 20-point total, and the column
names, values, and row order returned by all five reference queries.

A successful run ends with:

```text
All 5 questions passed. Total points: 20
```

The workflow references `${{ secrets.QUIZ_PGPASSWORD }}`. No database
password is embedded in the workflow file. A successful live database
verification run is available in this repository's Actions history.

## Deploy to Streamlit Community Cloud

1. Connect Streamlit Community Cloud to GitHub.
2. Choose this repository, branch `main`, and entry point `app.py`.
3. Select Python 3.14 in Advanced settings.
4. Add the following root-level TOML secrets, replacing placeholders:

```toml
PGHOST = "YOUR_SESSION_POOLER_HOST"
PGPORT = "5432"
PGDATABASE = "postgres"
QUIZ_PGUSER = "quiz_reader.YOUR_PROJECT_REF"
QUIZ_PGPASSWORD = "YOUR_READER_PASSWORD"
SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "YOUR_PUBLISHABLE_KEY"
```

5. Deploy the app and set the Supabase Auth Site URL to its public URL.
6. Test sign-in, SQL execution, saving, and loading on the public site.

GitHub Actions Secrets and Streamlit Secrets are configured separately.
The deployed app does not need the administrator database credentials.

## Verification

The following checks were completed during setup:

- All five reference queries matched their expected results.
- The reader role could read products but could not update products
  or delete orders.
- The deployed site supported sign-in and live SQL execution.
- Saved answers could be loaded after signing out and signing in again.
- GitHub Actions completed a successful live database check using Secrets.

## Scope

This project implements the required quiz, hosted database,
authentication, answer saving, and GitHub Actions workflow.

An audit log and audit-log integrity checks are not implemented.