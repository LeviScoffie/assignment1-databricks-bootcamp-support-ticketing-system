"""One-time setup: create the Databricks secret scope and store LAKEBASE_URL.

The deployed Databricks App reads this secret at runtime (see app.yaml). Run
this once locally while authenticated to your Databricks workspace:

    python setup_secrets.py

It will prompt you (with masked input) for the Lakebase connection URL. You
can also pre-set LAKEBASE_URL in the environment to skip the prompt. Idempotent:
re-running updates the stored value.
"""
import getpass
import os

from databricks.sdk import WorkspaceClient

SCOPE = "database"
KEY = "lakebase-url"


def _read_url() -> str:
    url = os.environ.get("LAKEBASE_URL")
    if url:
        return url.strip()
    print("Paste the Lakebase connection URL (input hidden):")
    print("  format: postgresql://<role>:<password>@<host>:5432/databricks_postgres?sslmode=require")
    url = getpass.getpass("LAKEBASE_URL: ").strip()
    if not url:
        raise SystemExit("no URL provided")
    if not url.startswith(("postgresql://", "postgres://")):
        raise SystemExit("URL must start with postgresql:// or postgres://")
    return url


def main() -> None:
    url = _read_url()
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
