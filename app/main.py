"""Odometrics prototype API + web page.

Run:  python -m uvicorn app.main:app --reload --port 8000
Open: http://localhost:8000
"""
import calendar
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "pipeline"))
from brands import BRAND_PROFILE, brand_for  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import datasource  # noqa: E402

FUEL_LABELS = {"PET": "Petrol", "DSL": "Diesel", "CNG": "CNG", "EV": "EV",
               "HYB": "Hybrid", "PHEV": "Plug-in hybrid", "OTH": "Other"}

app = FastAPI(title="Odometrics")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


def data():
    """Registrations with clean brand names (Supabase, or local SQLite)."""
    return datasource.load(brand_for)


def as_of_for(segment):
    return date.fromisoformat(data()["as_of"][segment])


def prev_period(p):
    y, m = divmod(p, 100)
    return (y - 1) * 100 + 12 if m == 1 else p - 1


def label(p):
    y, m = divmod(p, 100)
    return f"{calendar.month_abbr[m]} {y}"


def filtered(segment, rtos, fuels):
    d = data()["reg"]
    d = d[d.segment == segment]
    if rtos:
        d = d[d.rto_code.isin(rtos)]
    if fuels:
        d = d[d.fuel_group.isin(fuels)]
    return d


def shares(df, brands):
    """count and share per brand from a slice; market = all brands in the slice."""
    total = int(df["count"].sum())
    by = df.groupby("brand")["count"].sum()
    out = {b: {"count": int(by.get(b, 0)), "share": (by.get(b, 0) / total * 100) if total else 0.0} for b in brands}
    return total, out, by.sort_values(ascending=False)


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/meta")
def meta(segment: str = "4W"):
    c = data()
    reg = c["reg"][c["reg"].segment == segment]
    vol = reg.groupby("brand")["count"].sum().sort_values(ascending=False)
    brands = []
    for b, n in vol.items():
        prof = BRAND_PROFILE.get(b)
        if prof and prof[0] != segment:
            continue
        brands.append({"brand": b, "volume": int(n),
                       "positioning": prof[1] if prof else None,
                       "ticket": prof[2] if prof else None,
                       "ev_only": prof[3] if prof else None})
    rto_vol = reg.groupby("rto_code")["count"].sum()
    rtos = sorted(({"code": k, "name": c["rtos"].get(k, k), "volume": int(v)} for k, v in rto_vol.items()),
                  key=lambda r: int("".join(ch for ch in r["code"] if ch.isdigit()) or 0))
    periods = sorted(reg["period"].unique().tolist())
    return {"as_of": as_of_for(segment).isoformat(), "brands": brands, "rtos": rtos,
            "periods": [{"value": p, "label": label(p)} for p in periods],
            "fuels": [{"value": k, "label": v} for k, v in FUEL_LABELS.items()]}


@app.get("/api/suggest")
def suggest(segment: str, brand: str, ev_only: bool = False, positioning: str = "", ticket: float = 0, limit: int = 5):
    """Suggest competitors: same segment, similar positioning/ticket, by volume."""
    vol = filtered(segment, None, ["EV"] if ev_only else None).groupby("brand")["count"].sum()
    scored = []
    for b, n in vol.items():
        if b == brand or n == 0:
            continue
        prof = BRAND_PROFILE.get(b)
        if not prof or prof[0] != segment:
            continue
        score = float(n)
        if positioning and prof[1] == positioning:
            score *= 3
        if ticket and prof[2][0] <= ticket <= prof[2][1]:
            score *= 3
        if ev_only and prof[3]:
            score *= 2
        scored.append((score, b))
    return {"competitors": [b for _, b in sorted(scored, reverse=True)[:limit]]}


@app.get("/api/dashboard")
def dashboard(segment: str, brand: str, competitors: str = "", rtos: str = "", fuel: str = "",
              period: int = Query(0, description="yyyymm; 0 = latest month")):
    c = data()
    comp = [b for b in competitors.split(",") if b]
    rto_list = [r for r in rtos.split(",") if r]
    fuels = [f for f in fuel.split(",") if f]
    d = filtered(segment, rto_list, fuels)
    if d.empty:
        raise HTTPException(404, "No registrations for this selection")
    periods = sorted(d["period"].unique())
    cur = int(period or periods[-1])
    prev = prev_period(cur)
    tracked = [brand] + comp

    cur_df, prev_df = d[d.period == cur], d[d.period == prev]
    total, cur_s, ranking = shares(cur_df, tracked)
    ptotal, prev_s, _ = shares(prev_df, tracked)

    # Current month is partial: compare volumes on a projected full-month basis.
    as_of = as_of_for(segment)
    is_partial = cur == as_of.year * 100 + as_of.month
    days_in = calendar.monthrange(cur // 100, cur % 100)[1]
    days_done = max(as_of.day - 1, 1) if is_partial else days_in
    projection = days_in / days_done

    def growth(now, before):
        return ((now * projection) / before - 1) * 100 if before else None

    rank_list = sorted(tracked, key=lambda b: -cur_s[b]["count"])
    table = [{"brand": b, "you": b == brand, "count": cur_s[b]["count"],
              "share": round(cur_s[b]["share"], 1),
              "share_change": round(cur_s[b]["share"] - prev_s[b]["share"], 1),
              "growth": None if growth(cur_s[b]["count"], prev_s[b]["count"]) is None
              else round(growth(cur_s[b]["count"], prev_s[b]["count"]))}
             for b in rank_list]
    others = total - sum(cur_s[b]["count"] for b in tracked)
    table.append({"brand": "Others", "you": False, "count": others,
                  "share": round(others / total * 100, 1) if total else 0, "share_change": None, "growth": None})

    # 12-month share trend
    trend_periods = [p for p in periods if p <= cur][-12:]
    trend = {"labels": [label(p) for p in trend_periods], "series": {}}
    for b in tracked:
        series = []
        for p in trend_periods:
            t, s, _ = shares(d[d.period == p], [b])
            series.append(round(s[b]["share"], 1))
        trend["series"][b] = series

    # By RTO
    by_rto = []
    for code, g in cur_df.groupby("rto_code"):
        t, s, rk = shares(g, [brand])
        pg = prev_df[prev_df.rto_code == code]
        _, ps, _ = shares(pg, [brand])
        leader = rk.index[0] if len(rk) else None
        by_rto.append({"code": code, "name": c["rtos"].get(code, code), "market": t,
                       "count": s[brand]["count"], "share": round(s[brand]["share"], 1),
                       "share_change": round(s[brand]["share"] - ps[brand]["share"], 1),
                       "leader": leader, "leader_share": round(rk.iloc[0] / t * 100, 1) if t else 0})
    by_rto.sort(key=lambda r: -r["market"])

    # Fuel mix: you vs market
    fuel_mix = []
    you_df = cur_df[cur_df.brand == brand]
    for f, name in FUEL_LABELS.items():
        m = int(cur_df[cur_df.fuel_group == f]["count"].sum())
        y = int(you_df[you_df.fuel_group == f]["count"].sum())
        if m:
            fuel_mix.append({"fuel": name, "market": round(m / total * 100, 1),
                             "you": round(y / max(int(you_df["count"].sum()), 1) * 100, 1)})

    you_now, you_prev = cur_s[brand], prev_s[brand]
    return {
        "as_of": as_of.isoformat(), "period": cur, "period_label": label(cur),
        "prev_label": label(prev), "partial": is_partial, "days_done": days_done, "days_in": days_in,
        "kpis": {
            "count": you_now["count"],
            "growth": None if growth(you_now["count"], you_prev["count"]) is None
            else round(growth(you_now["count"], you_prev["count"])),
            "share": round(you_now["share"], 1),
            "share_change": round(you_now["share"] - you_prev["share"], 1),
            "rank": rank_list.index(brand) + 1, "rank_of": len(rank_list),
            "market_rank": list(ranking.index).index(brand) + 1 if brand in ranking.index else None,
            "market": total,
            "market_growth": None if growth(total, ptotal) is None else round(growth(total, ptotal)),
        },
        "table": table, "trend": trend, "by_rto": by_rto, "fuel_mix": fuel_mix,
    }


@app.get("/api/rto")
def rto_detail(segment: str, code: str, brand: str, fuel: str = "", period: int = 0):
    """All brands in one RTO for one month, plus your monthly trend there."""
    c = data()
    fuels = [f for f in fuel.split(",") if f]
    d = filtered(segment, [code], fuels)
    if d.empty:
        raise HTTPException(404, "No registrations for this RTO")
    cur = int(period or d["period"].max())
    total, _, ranking = shares(d[d.period == cur], [])
    brands = [{"brand": b, "count": int(n), "share": round(n / total * 100, 1), "you": b == brand}
              for b, n in ranking.items()]
    months = sorted(d["period"].unique())[-12:]
    trend = []
    for p in months:
        t, s, _ = shares(d[d.period == p], [brand])
        trend.append({"label": label(p), "count": s[brand]["count"], "share": round(s[brand]["share"], 1)})
    return {"code": code, "name": c["rtos"].get(code, code), "period_label": label(cur),
            "market": total, "brands": brands, "trend": trend}
