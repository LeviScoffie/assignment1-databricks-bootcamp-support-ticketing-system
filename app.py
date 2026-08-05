"""FastAPI entrypoint for the Lakebase support-ticketing app.

API-first: these endpoints are the surface that BOTH the human UI and (later in
the boot camp) the AI agent will call. All operational data lives in Lakebase.
Deployed via Databricks Apps (see app.yaml -> `uvicorn app:app`).
"""
from fastapi import FastAPI
from sqlalchemy import text

import lakebase

app = FastAPI(title="Lakebase Support Ticketing")


@app.get("/health")
def health():
    """Liveness probe — intentionally does NOT touch the database, so the app
    reports healthy even before Lakebase is wired up or has woken from idle."""
    return {"status": "ok"}


@app.get("/tickets")
def list_tickets():
    """Return all tickets, newest first.

    Works once `lakebase.get_engine()` is implemented and the schema exists.
    """
    with lakebase.get_engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT ticket_id, title, status, created_by, created_at "
                "FROM tickets ORDER BY created_at DESC"
            )
        ).mappings().all()
    return {"tickets": [dict(r) for r in rows]}


# --- Endpoints to build together next -----------------------------------
# POST /tickets                       -> create a ticket
# GET  /tickets/{ticket_id}           -> a ticket plus its message thread
# POST /tickets/{ticket_id}/messages  -> add a message to a ticket
# ------------------------------------------------------------------------
