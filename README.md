# Assignment 1 — Lakebase-Powered AI Ticket Support App

Day 1 boot camp homework: a small **Databricks App** (Flask) backed by
**Lakebase** (Databricks' Postgres-compatible OLTP database). Users create
support tickets and add messages to them. This becomes the foundation for the
context-engineering and AI-agent projects later in the boot camp.

## Architecture

```
Client (human UI / future AI agent)
        │  HTTP
        ▼
Flask app  (app.py)  ──►  Lakebase / Postgres  (sql/schema.sql)
        │                     tickets
   lakebase.py                ticket_messages  (FK → tickets)
 (reads LAKEBASE_URL from a Databricks secret, psycopg2 + RealDictCursor)
```

`lakebase.py` fetches the Postgres connection URL from a Databricks **secret**
(`database/lakebase-url`) at runtime and decodes it — the live credential never
lives in the app's environment. Helper API: `run_query` (read), `run_write`
(write), and `get_connection` (a psycopg2 connection for `INSERT ... RETURNING`).

## API

| Method & path | Purpose |
|---|---|
| `GET /healthz` | Liveness (no DB) |
| `GET /tickets` | List tickets, newest first |
| `POST /tickets` | Create a ticket — body `{title, status?, created_by?}` |
| `GET /tickets/<ticket_id>` | A ticket plus its message thread |
| `POST /tickets/<ticket_id>/messages` | Add a message — body `{message_text, author?}` |

`created_by` / `author` default to the logged-in user's email (from the
`X-Forwarded-Email` header Databricks Apps inject).

## Project structure

| Path | What it is | Status |
|---|---|---|
| `app.py` | Flask app + ticket routes | scaffolded |
| `lakebase.py` | Secret-backed connection helper (`run_query`/`run_write`/`get_connection`) | done |
| `sql/schema.sql` | DDL for `tickets` + `ticket_messages` (FK) | **to implement** |
| `sql/seed.sql` | Sample data (3+ tickets, 2+ msgs each, 2+ statuses) | **to implement** |
| `init_db.py` | Applies `schema.sql` then `seed.sql` | scaffolded |
| `setup_secrets.py` | One-time: store the Lakebase URL as `database/lakebase-url` | scaffolded |
| `app.yaml` | Databricks Apps deploy config (`python app.py` + secret pointers) | scaffolded |

## Local development

The app resolves its DB URL from a Databricks secret, so local runs need
Databricks auth **and** the secret to exist:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Authenticate to Databricks (CLI profile or DATABRICKS_HOST/DATABRICKS_TOKEN)
# 2. Create the secret once:
export LAKEBASE_URL='postgresql://app_user:...@HOST:5432/databricks_postgres?sslmode=require'
python setup_secrets.py

python init_db.py    # applies sql/schema.sql then sql/seed.sql
python app.py        # serves on http://0.0.0.0:8000
```

`GET /healthz` works without the database; the ticket routes need the schema +
seed applied.

## Deploy to Databricks Apps

Provision a Lakebase instance, run `setup_secrets.py`, then deploy this repo as
a Databricks App. `app.yaml` runs `python app.py` and passes
`LAKEBASE_SECRET_SCOPE`/`LAKEBASE_SECRET_KEY` so the app reads the URL from the
`database/lakebase-url` secret at runtime.
