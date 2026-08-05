"""Apply schema.sql then seed.sql to the Lakebase database.

Run locally once `lakebase.get_engine()` is implemented and LAKEBASE_URL is set:

    python init_db.py
"""
import pathlib

import lakebase

SQL_DIR = pathlib.Path(__file__).resolve().parent / "sql"


def main() -> None:
    # Use the raw DBAPI (psycopg2) connection so a whole multi-statement .sql
    # file runs in one execute() call.
    raw = lakebase.get_engine().raw_connection()
    try:
        cur = raw.cursor()
        for name in ("schema.sql", "seed.sql"):
            cur.execute((SQL_DIR / name).read_text())
            print(f"applied {name}")
        raw.commit()
    finally:
        raw.close()
    print("done")


if __name__ == "__main__":
    main()
