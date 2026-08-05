"""Lakebase (Postgres-compatible) connection layer.

This is YOUR core task. Everything else in the app assumes there is a working
`get_connection()` that returns a live psycopg connection to the Lakebase
database instance.

Key idea — you do NOT hardcode a password. For a Databricks App, the app's
service principal gets a short-lived OAuth token from the Databricks SDK, and
that token is used as the Postgres password. The username is the app/service
identity; host/port/dbname come from the Lakebase database instance.

Implementation notes to research when you fill this in:
  - `databricks.sdk.WorkspaceClient` can mint a database credential / token.
  - psycopg connects with host, port (5432), dbname, user, password(=token),
    sslmode="require".
  - Locally you may instead read a connection string from an env var so you can
    develop before deploying. Keep secrets in a `.env` (already gitignored),
    never committed.
"""


def get_connection():
    """Return a live psycopg connection to the Lakebase database instance.

    Returns:
        psycopg.Connection

    Raises:
        NotImplementedError: until you implement it.
    """
    raise NotImplementedError(
        "Implement Lakebase connection: build credentials (Databricks OAuth "
        "token as the Postgres password) and return a psycopg connection."
    )
