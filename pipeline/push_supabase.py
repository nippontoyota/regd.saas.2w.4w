"""Push the local database (data/odometrics.db) to the odm_ tables in Supabase.

Needs .env with NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY, and the
tables from supabase/001_odometrics_tables.sql created once in the SQL Editor.

For every segment + year in the local database, the matching rows in Supabase
are deleted and re-inserted, so Supabase ends up identical to the local copy.
Only odm_ tables are touched.

Usage:
  python pipeline/push_supabase.py
  python pipeline/push_supabase.py --segments=2W
"""
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brands import brand_for  # noqa: E402

DB_PATH = PROJECT_DIR / "data" / "odometrics.db"
BATCH = 1000


def load_env():
    env = {}
    for line in (PROJECT_DIR / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/"), env["SUPABASE_SERVICE_ROLE_KEY"]


URL, KEY = load_env()


def call(method, path, body=None, prefer=None):
    req = urllib.request.Request(f"{URL}/rest/v1/{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("apikey", KEY)
    req.add_header("Authorization", f"Bearer {KEY}")
    req.add_header("Content-Type", "application/json")
    if prefer:
        req.add_header("Prefer", prefer)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.headers, r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} failed: {e.code} {e.read().decode()[:500]}")


def remote_count(table, query):
    headers, _ = call("HEAD", f"{table}?{query}", prefer="count=exact")
    return int(headers["Content-Range"].split("/")[-1])


def replace(table, df, segments_years):
    for seg, year in segments_years:
        call("DELETE", f"{table}?state=eq.KL&segment=eq.{seg}&year=eq.{year}")
    rows = df.to_dict("records")
    for i in range(0, len(rows), BATCH):
        call("POST", table, rows[i:i + BATCH], prefer="return=minimal")
        print(f"  {table}: {min(i + BATCH, len(rows)):,}/{len(rows):,}", end="\r")
    print()


def main():
    seg_arg = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--segments=")), "")
    with sqlite3.connect(DB_PATH) as db:
        reg = pd.read_sql("select * from registrations", db)
        mix = pd.read_sql("select * from fuel_mix", db)
        rtos = pd.read_sql("select * from rtos", db)
    if seg_arg:
        keep = seg_arg.split(",")
        reg, mix = reg[reg.segment.isin(keep)], mix[mix.segment.isin(keep)]
    reg["brand"] = reg["maker"].map(brand_for)
    for df in (reg, mix):
        df["year"] = df["year"].astype(int)
        df["month"] = df["month"].astype(int)
        df["count"] = df["count"].astype(int)

    print(f"Supabase: {URL}")
    call("POST", "odm_rtos?on_conflict=rto_code", rtos.to_dict("records"),
         prefer="resolution=merge-duplicates,return=minimal")
    print(f"  odm_rtos: {len(rtos)} upserted")

    combos = sorted(set(map(tuple, reg[["segment", "year"]].drop_duplicates().values.tolist())))
    replace("odm_registrations", reg, combos)
    replace("odm_fuel_mix", mix, combos)

    print("Check (local rows vs Supabase rows):")
    ok = True
    for seg, year in combos:
        for table, df in [("odm_registrations", reg), ("odm_fuel_mix", mix)]:
            local = len(df[(df.segment == seg) & (df.year == year)])
            remote = remote_count(table, f"state=eq.KL&segment=eq.{seg}&year=eq.{year}")
            ok &= local == remote
            print(f"  {table} {seg} {year}: local {local:,}  supabase {remote:,}  {'OK' if local == remote else 'MISMATCH'}")
    print("All good." if ok else "Some counts differ — re-run the push.")


if __name__ == "__main__":
    main()
