"""
Databricks App: internal support ticketing.

- Serves a small Flask API plus the browser UI at /.
- Reads/writes support tickets and their messages in Lakebase
  (Databricks-managed Postgres) via lakebase.py.

Run locally:
    python app.py
Deploy as a Databricks App using app.yaml.
"""

import logging
import os
import uuid

from databricks.sdk import WorkspaceClient
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

import lakebase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("support-app")

app = Flask(__name__)
_w = WorkspaceClient()

# Table names are overridable via env, mirroring the reference app's pattern.
TICKETS_TABLE = os.environ.get("TICKETS_TABLE_NAME", "tickets")
MESSAGES_TABLE = os.environ.get("MESSAGES_TABLE_NAME", "ticket_messages")

VALID_STATUSES = ("open", "in_progress", "resolved")
VALID_PRIORITIES = ("low", "medium", "high", "urgent")

TITLE_MAX = 255
TITLE_MIN = 3
MESSAGE_MAX = 5000

# Columns every ticket response carries, so the shape never drifts between
# list / create / update / restore.
TICKET_COLS = (
    "ticket_id, title, status, priority, created_by, created_at, deleted_at"
)

# Aggregate counts behind GET /stats, returned as a single row.
#
# Every bucket is a FILTER clause over one scan of `tickets` rather than ten
# separate subqueries — the planner reads the table once and tallies each
# counter as rows stream past. `messages` lives in the other table, so it is
# the one value that needs a subquery.
#
# `live` is repeated in each FILTER because "open" means "open AND not
# archived" — an archived ticket keeps its old status, so without the
# deleted_at guard the status buckets would double-count the archive.
_STATS_SQL = f"""
SELECT
    count(*) FILTER (WHERE deleted_at IS NULL)                                AS total,
    count(*) FILTER (WHERE deleted_at IS NULL AND status   = 'open')          AS open,
    count(*) FILTER (WHERE deleted_at IS NULL AND status   = 'in_progress')   AS in_progress,
    count(*) FILTER (WHERE deleted_at IS NULL AND status   = 'resolved')      AS resolved,
    count(*) FILTER (WHERE deleted_at IS NULL AND priority = 'low')           AS low,
    count(*) FILTER (WHERE deleted_at IS NULL AND priority = 'medium')        AS medium,
    count(*) FILTER (WHERE deleted_at IS NULL AND priority = 'high')          AS high,
    count(*) FILTER (WHERE deleted_at IS NULL AND priority = 'urgent')        AS urgent,
    count(*) FILTER (WHERE deleted_at IS NOT NULL)                            AS archived,
    (SELECT count(*) FROM {MESSAGES_TABLE})                                   AS messages
FROM {TICKETS_TABLE}
"""


class ValidationError(Exception):
    """A client-side input problem. Carries a field name so the UI can point at it."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


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


def _require_uuid(value: str, field: str = "ticket_id") -> str:
    """Validate a path parameter is a UUID before it reaches Postgres.

    Without this, a malformed id reaches the driver and Postgres raises
    'invalid input syntax for type uuid', which surfaces as an opaque 500.
    """
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        raise ValidationError(f"'{value}' is not a valid ticket id.", field) from None


def _require_text(body: dict, field: str, *, min_len: int, max_len: int, label: str) -> str:
    """Pull a required string from the JSON body with a message a human can act on."""
    raw = body.get(field)
    if raw is None:
        raise ValidationError(f"{label} is required.", field)
    if not isinstance(raw, str):
        raise ValidationError(f"{label} must be text.", field)
    value = raw.strip()
    if not value:
        raise ValidationError(f"{label} cannot be blank.", field)
    if len(value) < min_len:
        raise ValidationError(
            f"{label} is too short — it needs at least {min_len} characters "
            f"(you gave {len(value)}).",
            field,
        )
    if len(value) > max_len:
        raise ValidationError(
            f"{label} is too long — the limit is {max_len} characters "
            f"(you gave {len(value)}).",
            field,
        )
    return value


def _require_choice(value: str | None, allowed: tuple[str, ...], field: str, default: str | None = None) -> str:
    """Validate an enum-backed field, naming the valid options in the error."""
    if value is None or value == "":
        if default is not None:
            return default
        raise ValidationError(f"{field} is required.", field)
    value = str(value).strip()
    if value not in allowed:
        raise ValidationError(
            f"'{value}' is not a valid {field}. Choose one of: {', '.join(allowed)}.",
            field,
        )
    return value


@app.errorhandler(ValidationError)
def handle_validation_error(err: ValidationError):
    """Return a 400 that tells the client exactly what to fix, and where."""
    logger.info(f"400 {request.method} {request.path} — {err.message}")
    payload = {"error": err.message}
    if err.field:
        payload["field"] = err.field
    return jsonify(payload), 400


@app.errorhandler(Exception)
def handle_exception(err):
    """Return JSON for any unhandled error so clients never get an HTML page."""
    # HTTP errors (404, 405, ...) are routine — log a one-liner, not a stack
    # trace. Only genuine unhandled exceptions warrant the full traceback.
    if isinstance(err, HTTPException):
        logger.info(f"{err.code} {request.method} {request.path}")
        return jsonify({"error": err.description}), err.code

    logger.exception("Unhandled exception while processing request")
    return jsonify({"error": str(err)}), 500


@app.route("/healthz")
def healthz():
    """Liveness probe — does not touch the database."""
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    """Serve the ticketing UI (templates/index.html)."""
    return render_template("index.html")


@app.route("/meta")
def meta():
    """Vocabulary the UI renders its selectors and filters from.

    Serving this from the backend keeps the UI in step with the database enums
    instead of hard-coding a second copy of them in JavaScript.
    """
    return jsonify({"statuses": list(VALID_STATUSES), "priorities": list(VALID_PRIORITIES)})


@app.route("/tickets", methods=["GET"])
def list_tickets():
    """List tickets, newest first.

    Query params (all optional):
        status=open|in_progress|resolved   filter by status
        priority=low|medium|high|urgent    filter by priority
        archived=true                      show archived instead of live tickets
        q=<text>                           case-insensitive title search
    """
    archived = request.args.get("archived", "").lower() in ("1", "true", "yes")

    where = ["deleted_at IS NOT NULL" if archived else "deleted_at IS NULL"]
    params: list = []

    if status := request.args.get("status"):
        where.append("status = %s")
        params.append(_require_choice(status, VALID_STATUSES, "status"))

    if priority := request.args.get("priority"):
        where.append("priority = %s")
        params.append(_require_choice(priority, VALID_PRIORITIES, "priority"))

    if search := (request.args.get("q") or "").strip():
        where.append("title ILIKE %s")
        params.append(f"%{search}%")

    rows = lakebase.run_query(
        f"SELECT {TICKET_COLS} FROM {TICKETS_TABLE} "
        f"WHERE {' AND '.join(where)} ORDER BY created_at DESC",
        tuple(params),
    )
    return jsonify(rows)


@app.route("/stats", methods=["GET"])
def stats():
    """Aggregate counts for the dashboard strip: totals, by status, by priority."""
    rows = lakebase.run_query(_STATS_SQL)
    return jsonify(rows[0])


@app.route("/tickets", methods=["POST"])
def create_ticket():
    """Create a ticket. Body: {title, status?, priority?, created_by?}."""
    body = request.get_json(silent=True) or {}
    title = _require_text(body, "title", min_len=TITLE_MIN, max_len=TITLE_MAX, label="Title")
    status = _require_choice(body.get("status"), VALID_STATUSES, "status", default="open")
    priority = _require_choice(body.get("priority"), VALID_PRIORITIES, "priority", default="medium")
    created_by = (body.get("created_by") or "").strip() or _current_user_email()

    # INSERT ... RETURNING needs both a commit and the returned row, so we use
    # get_connection() directly rather than run_write (which returns rowcount).
    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {TICKETS_TABLE} (title, status, priority, created_by) "
                f"VALUES (%s, %s, %s, %s) RETURNING {TICKET_COLS}",
                (title, status, priority, created_by),
            )
            row = cur.fetchone()
            conn.commit()
    return jsonify(row), 201


@app.route("/tickets/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    """Return a single ticket plus its message thread (archived ones included)."""
    ticket_id = _require_uuid(ticket_id)
    tickets = lakebase.run_query(
        f"SELECT {TICKET_COLS} FROM {TICKETS_TABLE} WHERE ticket_id = %s",
        (ticket_id,),
    )
    if not tickets:
        return jsonify({"error": f"No ticket found with id {ticket_id}."}), 404
    messages = lakebase.run_query(
        f"SELECT message_id, ticket_id, message_text, author, created_at "
        f"FROM {MESSAGES_TABLE} WHERE ticket_id = %s ORDER BY created_at ASC",
        (ticket_id,),
    )
    return jsonify({"ticket": tickets[0], "messages": messages})


def _update_ticket_field(ticket_id: str, column: str, value: str):
    """Shared UPDATE ... RETURNING for the single-field patch routes."""
    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TICKETS_TABLE} SET {column} = %s "
                f"WHERE ticket_id = %s AND deleted_at IS NULL "
                f"RETURNING {TICKET_COLS}",
                (value, ticket_id),
            )
            row = cur.fetchone()
            conn.commit()
    if row is None:
        return jsonify({"error": f"No live ticket found with id {ticket_id}."}), 404
    return jsonify(row)


@app.route("/tickets/<ticket_id>/status", methods=["PATCH"])
def update_ticket_status(ticket_id):
    """Update a ticket's status. Body: {status}."""
    ticket_id = _require_uuid(ticket_id)
    body = request.get_json(silent=True) or {}
    status = _require_choice(body.get("status"), VALID_STATUSES, "status")
    return _update_ticket_field(ticket_id, "status", status)


@app.route("/tickets/<ticket_id>/priority", methods=["PATCH"])
def update_ticket_priority(ticket_id):
    """Update a ticket's priority. Body: {priority}."""
    ticket_id = _require_uuid(ticket_id)
    body = request.get_json(silent=True) or {}
    priority = _require_choice(body.get("priority"), VALID_PRIORITIES, "priority")
    return _update_ticket_field(ticket_id, "priority", priority)


@app.route("/tickets/<ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):
    """Archive a ticket (soft delete) — the row and its thread are preserved."""
    ticket_id = _require_uuid(ticket_id)
    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TICKETS_TABLE} SET deleted_at = CURRENT_TIMESTAMP "
                f"WHERE ticket_id = %s AND deleted_at IS NULL "
                f"RETURNING {TICKET_COLS}",
                (ticket_id,),
            )
            row = cur.fetchone()
            conn.commit()
    if row is None:
        return jsonify({"error": f"No live ticket found with id {ticket_id}."}), 404
    return jsonify(row)


@app.route("/tickets/<ticket_id>/restore", methods=["POST"])
def restore_ticket(ticket_id):
    """Bring an archived ticket back — the payoff of soft delete over hard delete."""
    ticket_id = _require_uuid(ticket_id)
    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TICKETS_TABLE} SET deleted_at = NULL "
                f"WHERE ticket_id = %s AND deleted_at IS NOT NULL "
                f"RETURNING {TICKET_COLS}",
                (ticket_id,),
            )
            row = cur.fetchone()
            conn.commit()
    if row is None:
        return jsonify({"error": f"No archived ticket found with id {ticket_id}."}), 404
    return jsonify(row)


@app.route("/tickets/<ticket_id>/messages", methods=["POST"])
def add_message(ticket_id):
    """Add a message to a ticket. Body: {message_text, author?}."""
    ticket_id = _require_uuid(ticket_id)
    body = request.get_json(silent=True) or {}
    message_text = _require_text(
        body, "message_text", min_len=1, max_len=MESSAGE_MAX, label="Message"
    )
    author = (body.get("author") or "").strip() or _current_user_email()

    # Friendly 404 if the ticket is missing or archived (the FK also guarantees
    # referential integrity, but its error message is not user-facing).
    exists = lakebase.run_query(
        f"SELECT 1 FROM {TICKETS_TABLE} WHERE ticket_id = %s AND deleted_at IS NULL",
        (ticket_id,),
    )
    if not exists:
        return jsonify({"error": f"No live ticket found with id {ticket_id}."}), 404

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
