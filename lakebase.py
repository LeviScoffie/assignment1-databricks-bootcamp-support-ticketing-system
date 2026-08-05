"""Lakebase connection helper.

Single source of truth for talking to Lakebase (Databricks-managed Postgres).
Everything flows through ONE secret: `LAKEBASE_URL` — a standard Postgres URL
for a native role with a static password, e.g.

    postgresql://app_user:PASSWORD@HOST:5432/databricks_postgres?sslmode=require

Locally, `LAKEBASE_URL` comes from a gitignored `.env` (see `.env.example`).
In the deployed Databricks App it is injected from a Databricks secret
(see `setup_secrets.py` + `app.yaml`). SQLAlchemy is the engine; psycopg2 is
the underlying driver.
"""
import functools
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# Load .env in local dev. In the deployed app LAKEBASE_URL is already in the
# environment, so this is effectively a no-op there.
load_dotenv()


@functools.lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Build (once) and return a SQLAlchemy Engine from LAKEBASE_URL.

    Callers (app.py, init_db.py) use this engine to talk to Lakebase.
    """
    # TODO(human): implement engine construction.
    # 1. Read LAKEBASE_URL from the environment; fail loudly if it is missing.
    # 2. Return create_engine(url, ...). SQLAlchemy's default postgresql driver
    #    IS psycopg2, so a "postgresql://" URL already uses it (writing
    #    "postgresql+psycopg2://" is the explicit form).
    # 3. Choose pool settings. Hint: Lakebase Autoscaling scales to zero after
    #    idle, so a stale pooled connection can be dead on the next request —
    #    which SQLAlchemy option makes it test-and-reconnect transparently?
    raise NotImplementedError("Implement get_engine() — see TODO(human).")
