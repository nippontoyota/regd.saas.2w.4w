"""Where the dashboard gets its data.

- Supabase (odm_ tables) when NEXT_PUBLIC_SUPABASE_URL and
  SUPABASE_SERVICE_ROLE_KEY are set — always the case on Vercel.
- Otherwise the local SQLite file data/odometrics.db.

The service-role key is only used here, on the server; it never reaches the
browser. Data is cached in memory and re-read at most every CACHE_SECONDS.
"""
import json
import os
import sqlite3
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "odometrics.db"
CACHE_SECONDS = 600
PAGE = 1000  # Supabase returns at most 1,000 rows per request
REG_COLUMNS = "rto_code,segment,fuel_group,maker,brand,year,month,count,as_of"


def _load_dotenv():
    """Read .env for local runs (Vercel provides real environment variables)."""
    env_file = PROJECT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY) and os.environ.get("ODOMETRICS_SOURCE") != "sqlite"


def _get(path, headers=None, body=None):
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}",
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.headers, json.loads(r.read() or b"[]")


def _fetch_all(table, select, order):
    """Fetch every row of a table, 1,000 at a time, in parallel."""
    headers, _ = _get(f"{table}?select=id&limit=1", {"Prefer": "count=exact"})
    total = int(headers["Content-Range"].split("/")[-1])

    def page(offset):
        return _get(f"{table}?select={select}&order={order}&limit={PAGE}&offset={offset}")[1]

    with ThreadPoolExecutor(max_workers=8) as pool:
        pages = pool.map(page, range(0, total, PAGE))
    return pd.DataFrame([row for p in pages for row in p])


def _from_supabase():
    try:
        # one request: all rows, column by column (see supabase/003_registrations_snapshot.sql)
        _, cols = _get("rpc/odm_registrations_snapshot", body={})
        reg = pd.DataFrame(cols)
    except Exception as e:
        print(f"snapshot call failed ({e}); falling back to paged reads")
        reg = _fetch_all("odm_registrations", REG_COLUMNS, "id")  # slower fallback
    _, rtos = _get("odm_rtos?select=rto_code,rto_name")
    return reg, pd.DataFrame(rtos)


def _from_sqlite(brand_for):
    with sqlite3.connect(DB_PATH) as db:
        reg = pd.read_sql("select * from registrations", db)
        rtos = pd.read_sql("select * from rtos", db)
    reg["brand"] = reg["maker"].map(brand_for)
    return reg, rtos


_cache = {"loaded_at": 0, "key": None}


def load(brand_for):
    """Registrations + RTO names + latest download date per segment."""
    key = "supabase" if USE_SUPABASE else (DB_PATH.stat().st_mtime if DB_PATH.exists() else None)
    fresh = time.time() - _cache["loaded_at"] < CACHE_SECONDS
    if _cache["key"] == key and (fresh or not USE_SUPABASE):
        return _cache
    reg, rtos = _from_supabase() if USE_SUPABASE else _from_sqlite(brand_for)
    for col in ("year", "month", "count"):
        reg[col] = reg[col].astype(int)
    reg["period"] = reg["year"] * 100 + reg["month"]
    as_of = reg.groupby("segment")["as_of"].max().map(lambda s: str(s)[:10]).to_dict()
    _cache.update(loaded_at=time.time(), key=key, reg=reg,
                  rtos=dict(zip(rtos.rto_code, rtos.rto_name)), as_of=as_of,
                  source="supabase" if USE_SUPABASE else "sqlite")
    return _cache
