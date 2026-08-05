"""
Databricks App: internal support ticketing.

- Serves a small Flask API.
- Reads/writes support tickets and their messages in Lakebase
  (Databricks-managed Postgres) via lakebase.py.

Run locally:
    python app.py
Deploy as a Databricks App using app.yaml.
"""

import logging
import os

from databricks.sdk import WorkspaceClient
from flask import Flask, jsonify, render_template, request

import lakebase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("support-app")

app = Flask(__name__)
_w = WorkspaceClient()

# Table names are overridable via env, mirroring the reference app's pattern.
TICKETS_TABLE = os.environ.get("TICKETS_TABLE_NAME", "tickets")
MESSAGES_TABLE = os.environ.get("MESSAGES_TABLE_NAME", "ticket_messages")

VALID_STATUSES = {"open", "in_progress", "resolved"}


def _current_user_email() -> str:
    """Resolve the logged-in user's email to attribute tickets/messages.

    Databricks Apps inject the identity via the X-Forwarded-Email header. Fall
    back to the SDK for local dev; if neither resolves, return "unknown" rather
    than failing the request (attribution is best-effort).
    """
    header_email = request.headers.get("X-Forwarded-Email")
    if header_email:
        return header_email
    try:
        return _w.current_user.me().user_name
    except Exception:  # noqa: BLE001 - identity lookup is best-effort
        return "unknown"


@app.errorhandler(Exception)
def handle_exception(err):
    """Return JSON for any unhandled error so clients never get an HTML page."""
    logger.exception("Unhandled exception while processing request")
    status_code = getattr(err, "code", 500)
    if not isinstance(status_code, int):
        status_code = 500
    return jsonify({"error": str(err)}), status_code


@app.route("/healthz")
def healthz():
    """Liveness probe — does not touch the database."""
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    """Serve the ticketing UI (templates/index.html)."""
    return render_template("index.html")


@app.route("/tickets", methods=["GET"])
def list_tickets():
    """List all tickets, newest first."""
    rows = lakebase.run_query(
        f"SELECT ticket_id, title, status, created_by, created_at "
        f"FROM {TICKETS_TABLE} ORDER BY created_at DESC"
    )
    return jsonify(rows)


@app.route("/tickets", methods=["POST"])
def create_ticket():
    """Create a ticket. Body: {title, status?, created_by?}."""
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    status = (body.get("status") or "open").strip()
    created_by = (body.get("created_by") or "").strip() or _current_user_email()

    if not title:
        return jsonify({"error": "title is required"}), 400
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400

    # INSERT ... RETURNING needs both a commit and the returned row, so we use
    # get_connection() directly rather than run_write (which returns rowcount).
    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {TICKETS_TABLE} (title, status, created_by) "
                f"VALUES (%s, %s, %s) "
                f"RETURNING ticket_id, title, status, created_by, created_at",
                (title, status, created_by),
            )
            row = cur.fetchone()
            conn.commit()
    return jsonify(row), 201


@app.route("/tickets/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    """Return a single ticket plus its message thread."""
    tickets = lakebase.run_query(
        f"SELECT ticket_id, title, status, created_by, created_at "
        f"FROM {TICKETS_TABLE} WHERE ticket_id = %s",
        (ticket_id,),
    )
    if not tickets:
        return jsonify({"error": f"ticket {ticket_id} not found"}), 404
    messages = lakebase.run_query(
        f"SELECT message_id, ticket_id, message_text, author, created_at "
        f"FROM {MESSAGES_TABLE} WHERE ticket_id = %s ORDER BY created_at ASC",
        (ticket_id,),
    )
    return jsonify({"ticket": tickets[0], "messages": messages})


@app.route("/tickets/<ticket_id>/status", methods=["PATCH"])
def update_ticket_status(ticket_id):
    """Update a ticket's status. Body: {status}.

    Returns the updated ticket row (200) or 404 if the ticket doesn't exist.
    Status must be one of VALID_STATUSES.
    """
    body = request.get_json(silent=True) or {}
    status = (body.get("status") or "").strip()

    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400

    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TICKETS_TABLE} SET status = %s WHERE ticket_id = %s "
                f"RETURNING ticket_id, title, status, created_by, created_at",
                (status, ticket_id),
            )
            row = cur.fetchone()
            conn.commit()
    if row is None:
        return jsonify({"error": f"ticket {ticket_id} not found"}), 404
    return jsonify(row)


@app.route("/tickets/<ticket_id>/messages", methods=["POST"])
def add_message(ticket_id):
    """Add a message to a ticket. Body: {message_text, author?}."""
    body = request.get_json(silent=True) or {}
    message_text = (body.get("message_text") or "").strip()
    author = (body.get("author") or "").strip() or _current_user_email()

    if not message_text:
        return jsonify({"error": "message_text is required"}), 400

    # Friendly 404 if the ticket is missing (the FK also guarantees integrity).
    exists = lakebase.run_query(
        f"SELECT 1 FROM {TICKETS_TABLE} WHERE ticket_id = %s", (ticket_id,)
    )
    if not exists:
        return jsonify({"error": f"ticket {ticket_id} not found"}), 404

    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {MESSAGES_TABLE} (ticket_id, message_text, author) "
                f"VALUES (%s, %s, %s) "
                f"RETURNING message_id, ticket_id, message_text, author, created_at",
                (ticket_id, message_text, author),
            )
            row = cur.fetchone()
            conn.commit()
    return jsonify(row), 201


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    # DATABRICKS_APP_PORT when deployed; fall back to 8000 for local dev.
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("FLASK_RUN_PORT", "8000")))
    logger.info(f"Starting Flask app on http://{host}:{port}")
    app.run(debug=True, host=host, port=port)
