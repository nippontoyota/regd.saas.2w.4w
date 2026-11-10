"""Run .sql files against the Supabase Postgres database.

Needs SUPABASE_DB_PASSWORD in .env (host comes from NEXT_PUBLIC_SUPABASE_URL).

Usage:
  python pipeline/run_sql.py supabase/001_odometrics_tables.sql supabase/002_check_and_grant.sql
"""
import sys
from pathlib import Path

import psycopg

PROJECT_DIR = Path(__file__).resolve().parent.parent


def env():
    out = {}
    for line in (PROJECT_DIR / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def connect():
    e = env()
    ref = e["NEXT_PUBLIC_SUPABASE_URL"].split("//")[1].split(".")[0]
    password = e["SUPABASE_DB_PASSWORD"]
    # The direct host (db.<ref>.supabase.co) is IPv6-only; the pooler works on IPv4.
    attempts = [(e.get("SUPABASE_DB_HOST", "aws-1-ap-south-1.pooler.supabase.com"), 5432, f"postgres.{ref}"),
                (f"db.{ref}.supabase.co", 5432, "postgres")]
    errors = []
    for host, port, user in attempts:
        try:
            conn = psycopg.connect(host=host, port=port, dbname="postgres", user=user,
                                   password=password, connect_timeout=20, sslmode="require")
            print(f"Connected to {host}:{port}")
            return conn
        except Exception as ex:
            errors.append(f"{host}:{port} -> {str(ex).splitlines()[0]}")
    raise SystemExit("Could not connect:\n  " + "\n  ".join(errors))


def main():
    with connect() as conn:
        conn.autocommit = True
        for f in sys.argv[1:]:
            print(f"Running {f}")
            with conn.cursor() as cur:
                cur.execute(Path(f).read_text(encoding="utf-8"))
                while True:
                    if cur.description:
                        for row in cur.fetchall():
                            print("  ", row)
                    if not cur.nextset():
                        break


if __name__ == "__main__":
    main()
