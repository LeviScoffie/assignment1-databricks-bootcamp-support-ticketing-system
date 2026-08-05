"""Apply schema.sql then seed.sql to the Lakebase database.

Run locally once you have a working `app.db.get_connection()`:

    python -m scripts.init_db
"""
import pathlib

from app import db

SQL_DIR = pathlib.Path(__file__).resolve().parent.parent / "sql"


def run_sql_file(conn, path: pathlib.Path) -> None:
    sql = path.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    print(f"applied {path.name}")


def main() -> None:
    with db.get_connection() as conn:
        run_sql_file(conn, SQL_DIR / "schema.sql")
        run_sql_file(conn, SQL_DIR / "seed.sql")
        conn.commit()
    print("done")


if __name__ == "__main__":
    main()
