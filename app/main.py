"""FastAPI entrypoint for the Lakebase support-ticketing app.

API-first design: these endpoints are the surface that BOTH the human UI and
(later in the boot camp) the AI agent will call. All operational data lives in
Lakebase. Keep business logic here/behind the API, never in a template.
"""
from fastapi import FastAPI

from app import db

app = FastAPI(title="Lakebase Support Ticketing")


@app.get("/health")
def health():
    """Liveness probe — intentionally does NOT touch the database, so the app
    reports healthy even before the Lakebase connection is wired up."""
    return {"status": "ok"}


@app.get("/tickets")
def list_tickets():
    """Return all tickets, newest first.

    Works once `db.get_connection()` is implemented and the schema exists.
    """
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ticket_id, title, status, created_by, created_at "
                "FROM tickets ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
    return {"tickets": rows}


# --- Endpoints to build together next -----------------------------------
# POST /tickets                       -> create a ticket
# GET  /tickets/{ticket_id}           -> a ticket plus its message thread
# POST /tickets/{ticket_id}/messages  -> add a message to a ticket
# ------------------------------------------------------------------------
