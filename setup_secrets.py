"""One-time setup: create the Databricks secret scope and store LAKEBASE_URL.

The deployed Databricks App reads this secret at runtime (see app.yaml). Run
this once locally while authenticated to your Databricks workspace:

    export LAKEBASE_URL='postgresql://app_user:...@HOST:5432/databricks_postgres?sslmode=require'
    python setup_secrets.py

It is idempotent: re-running updates the stored value.
"""
import os

from databricks.sdk import WorkspaceClient

SCOPE = "database"
KEY = "lakebase-url"


def main() -> None:
    url = os.environ.get("LAKEBASE_URL")
    if not url:
        raise SystemExit("Set LAKEBASE_URL in your environment first.")

    w = WorkspaceClient()

    # create_scope fails if the scope already exists — that's fine on re-runs.
    try:
        w.secrets.create_scope(scope=SCOPE)
        print(f"created secret scope: {SCOPE}")
    except Exception as exc:  # noqa: BLE001 - scope likely already exists
        print(f"scope {SCOPE} not created (may already exist): {exc}")

    w.secrets.put_secret(scope=SCOPE, key=KEY, string_value=url)
    print(f"stored secret: {SCOPE}/{KEY}")


if __name__ == "__main__":
    main()
