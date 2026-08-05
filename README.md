# Assignment 1 — Lakebase-Powered AI Support App

Day 1 boot camp homework: a small **Databricks App** (FastAPI) backed by
**Lakebase** (Databricks' Postgres-compatible OLTP database). Users create
support tickets and add messages to them. This becomes the foundation for the
context-engineering and AI-agent projects later in the boot camp.

## Architecture

```
Client (human UI / future AI agent)
        │  HTTP
        ▼
FastAPI app  (app.py)  ──►  Lakebase / Postgres  (sql/schema.sql)
        │                       tickets
   lakebase.py                  ticket_messages  (FK → tickets)
 (LAKEBASE_URL → SQLAlchemy engine, psycopg2 driver)
```

Connection design: a **single secret**, `LAKEBASE_URL` — a native Postgres role
with a static password. Same variable locally (from `.env`) and in production
(injected from a Databricks secret). API-first: business logic lives behind the
API so the human UI and the future agent share one surface.

## Project structure

| Path | What it is | Status |
|---|---|---|
| `app.py` | FastAPI app + routes | scaffolded |
| `lakebase.py` | Connection helper (`LAKEBASE_URL`, SQLAlchemy + psycopg2) | **stub — to implement** |
| `sql/schema.sql` | DDL for `tickets` + `ticket_messages` (FK) | **stub — to implement** |
| `sql/seed.sql` | Sample data (3+ tickets, 2+ msgs each, 2+ statuses) | **stub — to implement** |
| `init_db.py` | Applies `schema.sql` then `seed.sql` | scaffolded |
| `setup_secrets.py` | One-time: create Databricks secret scope + store `LAKEBASE_URL` | scaffolded |
| `app.yaml` | Databricks Apps deploy config (command + env) | scaffolded |
| `requirements.txt` · `.env.example` · `.gitignore` | supporting files | scaffolded |

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set LAKEBASE_URL to your Lakebase connection URL
uvicorn app:app --reload
```

`GET /health` works immediately. The database-backed routes work once
`lakebase.py` and the schema are implemented.

## Database setup

```bash
python init_db.py             # applies sql/schema.sql then sql/seed.sql
```

## Secrets (for deployment)

```bash
export LAKEBASE_URL='postgresql://app_user:...@HOST:5432/databricks_postgres?sslmode=require'
python setup_secrets.py       # stores it as Databricks secret support-ticketing/lakebase-url
```

## Deploy to Databricks Apps

Provision a Lakebase database instance, run `setup_secrets.py`, then deploy this
repo as a Databricks App (via the Databricks CLI / workspace Git integration).
The app reads `LAKEBASE_URL` from the secret per `app.yaml`.
```
