"""Apply schema.sql then seed.sql to the Lakebase database.

Run locally once the `assignment1-support-tickets/lakebase-url` secret exists and you are
authenticated to Databricks:

    python init_db.py
"""
import pathlib

import lakebase

SQL_DIR = pathlib.Path(__file__).resolve().parent / "sql"


def main() -> None:
    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            for name in ("schema.sql", "seed.sql"):
                cur.execute((SQL_DIR / name).read_text())
                print(f"applied {name}")
        conn.commit()
    print("done")


if __name__ == "__main__":
    main()
