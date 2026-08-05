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
FastAPI app  (app/main.py)  ──►  Lakebase / Postgres  (sql/schema.sql)
        │                            tickets
   app/db.py                         ticket_messages  (FK → tickets)
 (OAuth token → psycopg)
```

Design principle: **API-first**. The same endpoints serve the human UI now and
the AI agent later — business logic stays behind the API, not in templates.

## Project structure

| Path | What it is | Status |
|---|---|---|
| `app/main.py` | FastAPI app + routes | scaffolded |
| `app/db.py` | Lakebase connection (OAuth token as Postgres password) | **stub — to implement** |
| `sql/schema.sql` | DDL for `tickets` + `ticket_messages` (FK) | **stub — to implement** |
| `sql/seed.sql` | Sample data (3+ tickets, 2+ msgs each, 2+ statuses) | **stub — to implement** |
| `scripts/init_db.py` | Applies schema then seed | scaffolded |
| `app.yaml` | Databricks Apps run config | scaffolded |
| `requirements.txt` | Python dependencies | scaffolded |

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

`GET /health` works immediately. The database-backed routes work once
`app/db.py` and the schema are implemented.

## Database setup

Once `app/db.py` connects:

```bash
python -m scripts.init_db   # applies sql/schema.sql then sql/seed.sql
```

## Deploy to Databricks Apps

Provision a Lakebase database instance in the workspace, then deploy this repo
as a Databricks App (via the Databricks CLI / workspace Git integration).
Deployment steps to be filled in against current Databricks Apps docs.
