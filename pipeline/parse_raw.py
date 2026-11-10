"""Turn one day's raw Vahan exports into clean tables in the local database.

Reads   data/raw/<run date>/KL_<rto>_<seg>_<group|FUELMIX>_<year>.xlsx
Writes  data/odometrics.db (SQLite):
  registrations  state, rto_code, segment, fuel_group, maker, year, month, count, as_of
  fuel_mix       state, rto_code, segment, fuel, year, month, count, as_of
  rtos           rto_code, rto_name, state

Checks that, for every RTO and segment, the fuel-group files add up to the
fuel-mix total month by month. Nothing is written if a check fails.

Usage:
  python pipeline/parse_raw.py                 # latest run folder
  python pipeline/parse_raw.py 2026-10-19
  python pipeline/parse_raw.py --partial       # load only pairs that pass the check
  python pipeline/parse_raw.py --segments=2W   # load only 2W; 4W in the DB is kept
"""
import re
import sqlite3
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
DB_PATH = PROJECT_DIR / "data" / "odometrics.db"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
NAME_RE = re.compile(r"^(?P<state>[A-Z]+)_(?P<rto>[A-Z0-9]+)_(?P<seg>2W|4W)_(?P<kind>[A-Z]+)_(?P<year>\d{4})\.xlsx$")
TITLE_RTO_RE = re.compile(r"of (?P<name>.+?) - (?P<code>[A-Z]+\d+) ,")


def to_int(value):
    text = str(value).replace(",", "").strip()
    return int(float(text)) if text and text.lower() != "nan" else 0


def read_table(path):
    """Return (title, [(row_label, {month: count})]) from a Vahan export."""
    df = pd.read_excel(path, header=None, dtype=str)
    title = str(df.iloc[0, 0])
    header = [str(x).strip().upper() for x in df.iloc[3]]
    month_cols = {header[i]: i for i in range(len(header)) if header[i] in MONTHS}
    rows = []
    for _, r in df.iloc[4:].iterrows():
        label = str(r.iloc[1]).strip()
        if not label or label.lower() == "nan":
            continue
        rows.append((label, {m: to_int(r.iloc[i]) for m, i in month_cols.items()}))
    return title, rows


def parse(run_dir):
    as_of = run_dir.name
    reg, mix, rto_names = [], [], {}
    for path in sorted(run_dir.glob("*.xlsx")):
        m = NAME_RE.match(path.name)
        if not m:
            print(f"skip {path.name}")
            continue
        state, rto, seg, kind, year = m["state"], m["rto"], m["seg"], m["kind"], int(m["year"])
        title, rows = read_table(path)
        t = TITLE_RTO_RE.search(title)
        if t and t["code"] == rto:  # title is only trustworthy when it names this RTO
            rto_names[rto] = t["name"].strip()
        for label, months in rows:
            for mon, count in months.items():
                if count:
                    rec = dict(state=state, rto_code=rto, segment=seg, year=year,
                               month=MONTHS.index(mon) + 1, count=count, as_of=as_of)
                    if kind == "FUELMIX":
                        mix.append({**rec, "fuel": label.upper()})
                    else:
                        reg.append({**rec, "fuel_group": kind, "maker": label.upper()})
    return pd.DataFrame(reg), pd.DataFrame(mix), rto_names


def validate(reg, mix):
    keys = ["rto_code", "segment", "year", "month"]
    a = reg.groupby(keys)["count"].sum()
    b = mix.groupby(keys)["count"].sum()
    both = pd.concat([a.rename("groups"), b.rename("fuel_mix")], axis=1).fillna(0)
    bad = both[both["groups"] != both["fuel_mix"]]
    return bad


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    partial = "--partial" in sys.argv
    if args:
        run_dir = RAW_DIR / args[0]
    else:
        run_dir = max(p for p in RAW_DIR.iterdir() if p.is_dir())
    print(f"Parsing {run_dir}")
    reg, mix, rto_names = parse(run_dir)
    seg_arg = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--segments=")), "")
    if seg_arg:  # load only these segments; other segments in the DB stay as they are
        keep = seg_arg.split(",")
        reg, mix = reg[reg.segment.isin(keep)], mix[mix.segment.isin(keep)]
        print(f"Loading segments: {keep}")
    print(f"registrations rows: {len(reg):,}  fuel-mix rows: {len(mix):,}  RTOs: {reg.rto_code.nunique()}")

    bad = validate(reg, mix)
    if len(bad):
        bad_pairs = sorted({(r, s) for r, s, *_ in bad.index})
        print(f"CHECK FAILED for {len(bad_pairs)} RTO/segment pairs (groups don't add up to fuel mix):")
        print(bad.head(20).to_string())
        if not partial:
            print("Re-run the collector to fill missing files, then parse again. Nothing written.")
            print("(Use --partial to load only the RTO/segment pairs that pass.)")
            sys.exit(1)
        drop = lambda df: df[~df.set_index(["rto_code", "segment"]).index.isin(bad_pairs)]
        reg, mix = drop(reg), drop(mix)
        print(f"--partial: left out {len(bad_pairs)} pairs, loading {reg.rto_code.nunique()} RTOs")
    else:
        print("Check passed: fuel groups add up to fuel mix for every RTO, segment and month.")

    rto_csv = run_dir / "rtos.csv"  # saved by the collector from the RTO dropdown
    if rto_csv.exists():
        for code, label in pd.read_csv(rto_csv).itertuples(index=False):
            # "ALUVA SRTO - KL41( 23-MAR-2019 )" -> "ALUVA SRTO"
            rto_names[code] = re.sub(r"\s*-\s*[A-Z]+\d+\s*\(.*$", "", label.strip()).title().replace("Rto", "RTO").replace("Srto", "SRTO")
    rtos = pd.DataFrame(
        [{"rto_code": c, "rto_name": rto_names.get(c, c), "state": "KL"} for c in sorted(set(reg.rto_code) | set(mix.rto_code))])

    with sqlite3.connect(DB_PATH) as db:
        for table, df in [("registrations", reg), ("fuel_mix", mix)]:
            exists = db.execute("select 1 from sqlite_master where name=?", (table,)).fetchone()
            if exists:
                # replace only the year + segment combinations in this run
                for y, seg in df[["year", "segment"]].drop_duplicates().itertuples(index=False):
                    db.execute(f"delete from {table} where year=? and segment=? and state=?", (int(y), seg, "KL"))
            df.to_sql(table, db, if_exists="append", index=False)
        if db.execute("select 1 from sqlite_master where name='rtos'").fetchone():
            rtos = pd.concat([pd.read_sql("select * from rtos", db), rtos]).drop_duplicates("rto_code", keep="last")
        rtos.to_sql("rtos", db, if_exists="replace", index=False)
        db.execute("create index if not exists ix_reg on registrations(segment, year, month, rto_code)")
    print(f"Written to {DB_PATH}")


if __name__ == "__main__":
    main()
