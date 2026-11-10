"""Download RTO-wise Maker x Month tables from the old Vahan4 dashboard,
split by segment (2W/4W) and by fuel.

Several browser sessions (--workers, default 2) share one queue of RTO jobs.
It runs two passes:
  1. FUELMIX  - Y-Axis=Fuel, one file per RTO. Tells us which fuels are
                active in that RTO (and is itself the Fuel x Month table).
  2. Maker    - Y-Axis=Maker, one file per RTO per active fuel group
                (fuels of a group ticked together, see FUEL_GROUPS).

Files: data/raw/<YYYY-MM-DD>/KL_<rto>_<seg>_<fuelGroup|FUELMIX>_<year>.xlsx
Re-running on the same day skips files that already exist, so a crashed run
can simply be started again.

Usage:
  python collector/vahan_collector.py                       # all RTOs, 2W+4W, current year
  python collector/vahan_collector.py --years 2024 2025 2026
  python collector/vahan_collector.py --rtos KL7 --segments 4W --headed   # quick test
"""
import argparse
import asyncio
import logging
import random
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

log = logging.getLogger("vahan")
S = config.SELECTORS


def setup_logging():
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = config.LOGS_DIR / f"collector_{datetime.now():%Y-%m-%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )


# ---------- page helpers ----------

async def settle(page):
    try:
        await page.wait_for_load_state("networkidle", timeout=config.TIMEOUTS_MS["network_idle"])
    except Exception:
        pass
    try:
        await page.wait_for_selector(".ui-widget-overlay", state="hidden", timeout=5000)
    except Exception:
        pass
    await asyncio.sleep(0.5)


async def polite_pause():
    await asyncio.sleep(random.uniform(*config.DELAY_SECONDS))


async def open_dashboard(page):
    for attempt in range(1, 6):
        try:
            resp = await page.goto(config.TARGET_URL, wait_until="domcontentloaded",
                                   timeout=config.TIMEOUTS_MS["navigation"])
            if resp and not resp.ok:
                raise RuntimeError(f"HTTP {resp.status}")
            await settle(page)
            return
        except Exception as e:
            if attempt == 5:
                raise
            log.warning("Load attempt %s failed: %s", attempt, e)
            await asyncio.sleep(20 * attempt)


async def select_dropdown(page, label_sel, item_sel, value):
    await settle(page)
    try:
        if (await page.locator(label_sel).inner_text(timeout=2000)).strip() == value:
            return
    except Exception:
        pass
    for attempt in range(3):
        await page.locator(label_sel).click(force=True)
        await asyncio.sleep(0.8)
        item = page.locator(item_sel.format(value))
        # Items low in a long list are hidden until scrolled; a forced click
        # on a hidden item lands on whatever is visible there instead.
        try:
            await item.scroll_into_view_if_needed(timeout=5000)
            await item.click(timeout=5000)
        except Exception:
            try:
                await item.click(force=True, timeout=10000)
            except Exception as e:
                log.warning("could not click '%s' (attempt %d): %s", value, attempt + 1, str(e).splitlines()[0])
        await settle(page)
        shown = (await page.locator(label_sel).inner_text()).strip()
        if shown == value:
            return
        log.warning("dropdown shows '%s' after choosing '%s', retrying", shown, value)
        await page.keyboard.press("Escape")
    raise RuntimeError(f"Could not select '{value}' (dropdown shows '{shown}')")


async def open_sidebar(page):
    toggler = page.locator(S["sidebar_toggler"])
    if "ui-layout-toggler-closed" in (await toggler.get_attribute("class") or ""):
        await toggler.click(force=True)
        await asyncio.sleep(1)


async def set_group(page, group, wanted):
    """Make exactly the labels in `wanted` ticked within a checkbox group.
    Returns the wanted labels that do not exist on the page right now."""
    wanted = set(wanted)
    labels = page.locator(S["group_labels"].format(group=group))
    found = set()
    for i in range(await labels.count()):
        label = labels.nth(i)
        text = " ".join((await label.inner_text()).split())
        found.add(text)
        box_id = await label.get_attribute("for")
        checked = await page.locator(f'input[id="{box_id}"]').is_checked()
        if checked != (text in wanted):
            await label.click(force=True)
            await settle(page)
    if not found:
        raise RuntimeError(f"Checkbox group '{group}' not found in the side panel")
    return wanted - found


async def apply_side_filters(page, classes, fuel_labels):
    await open_sidebar(page)
    missing = await set_group(page, "VhClass", classes)
    if missing:
        log.debug("Vehicle classes not listed here: %s", sorted(missing))
    if len(missing) == len(classes):
        return False  # none of the segment's classes exist -> nothing to download
    missing_fuel = await set_group(page, "fuel", fuel_labels)
    if fuel_labels and len(missing_fuel) == len(fuel_labels):
        return False
    await page.locator(S["sidebar_refresh"]).last.click(force=True)
    await settle(page)
    return True


async def build_base_table(page, year, y_axis):
    """Set the top filters and press the top Refresh (this clears side filters)."""
    await select_dropdown(page, S["state_label"], S["state_item"], config.STATE_LABEL)
    await select_dropdown(page, S["yaxis_label"], S["yaxis_item"], y_axis)
    await select_dropdown(page, S["xaxis_label"], S["xaxis_item"], config.X_AXIS)
    await select_dropdown(page, S["yeartype_label"], S["yeartype_item"], config.YEAR_TYPE)
    await select_dropdown(page, S["year_label"], S["year_item"], year)
    await page.locator(S["top_refresh"]).first.click(force=True)
    await settle(page)
    await page.wait_for_selector(S["table_row"], timeout=config.TIMEOUTS_MS["table"])
    heading = await page.locator(S["table_heading"]).first.inner_text()
    expected = f"{y_axis} {config.X_AXIS} Data"
    state = config.STATE_LABEL.split("(")[0]
    if expected not in heading or state not in heading or f"({year})" not in heading:
        raise RuntimeError(f"Wrong table built: '{heading.splitlines()[0]}' (expected '{expected} of {state} ({year})')")


async def list_rtos(page):
    await page.wait_for_function(
        'document.querySelectorAll("ul#selectedRto_items li").length > 1')
    rtos = []
    for el in await page.locator(S["rto_items"]).all():
        label = await el.get_attribute("data-label")
        if label and not label.startswith("All Vahan4"):
            rtos.append(label)
    return rtos


def rto_code(label):
    m = re.search(rf"\b{config.STATE_CODE}\s*-?\s*0*(\d{{1,3}})\b", label.upper())
    if m:
        return f"{config.STATE_CODE}{int(m.group(1))}"
    return re.sub(r"[^A-Z0-9]+", "_", label.upper()).strip("_")


async def table_is_empty(page):
    rows = page.locator(S["table_row"])
    if await rows.count() == 0:
        return True
    return "no record" in (await rows.first.inner_text()).lower()


async def export(page, path):
    await asyncio.sleep(1.5)  # PrimeFaces rebinds the export link after refresh
    async with page.expect_download() as info:
        await page.locator(S["export_btn"]).click(force=True)
    download = await info.value
    tmp = path.with_suffix(".part")
    await download.save_as(tmp)
    tmp.replace(path)


async def download_table(page, rto, classes, fuel_labels, path):
    """Select the RTO, apply side filters and export. Returns False when the
    filtered table has no data."""
    await select_dropdown(page, S["rto_label"], S["rto_item"], rto)
    # The table title keeps the RTO from the last top Refresh, so it can't be
    # trusted; check the dropdown itself before exporting.
    shown = (await page.locator(S["rto_label"]).inner_text()).strip()
    if shown != rto:
        raise RuntimeError(f"RTO dropdown shows '{shown}', expected '{rto}'")
    # The RTO switch updates the table asynchronously; exporting too early
    # saves the previous RTO's numbers. Give it time to land.
    await asyncio.sleep(2)
    await settle(page)
    if not await apply_side_filters(page, classes, fuel_labels) or await table_is_empty(page):
        return False
    await export(page, path)
    log.info("saved %s", path.name)
    await polite_pause()
    return True


def active_fuels(fuelmix_file):
    """Fuel labels with a non-zero total in a FUELMIX export."""
    df = pd.read_excel(fuelmix_file, header=None, dtype=str)
    known = set(config.FUELS)
    active = []
    for _, row in df.iterrows():
        cells = [str(c).strip() for c in row if pd.notna(c)]
        label = next((c for c in cells if c.upper() in known), None)
        if not label:
            continue
        numbers = [float(c.replace(",", "")) for c in cells
                   if re.fullmatch(r"[\d,]+(\.\d+)?", c)]
        # first number is the serial no.; the rest are months + total
        if sum(numbers[1:]) > 0:
            active.append(label.upper())
    return active


# ---------- main loop ----------

class Worker:
    """One browser context = one Vahan session. Rebuilds the base table only
    when the year or Y-axis it needs changes (the top Refresh is slow)."""

    def __init__(self, name, page):
        self.name, self.page, self.base = name, page, None

    async def ensure_base(self, year, y_axis):
        if self.base != (year, y_axis):
            await build_base_table(self.page, year, y_axis)
            self.base = (year, y_axis)

    async def download(self, year, y_axis, rto, classes, fuel_labels, path, attempts=2):
        """Export one table. On error, reload the dashboard (a stuck PrimeFaces
        page never recovers by itself) and try again."""
        for attempt in range(1, attempts + 1):
            try:
                await self.ensure_base(year, y_axis)
                return await download_table(self.page, rto, classes, fuel_labels, path)
            except Exception as e:
                if attempt == attempts:
                    raise
                log.warning("[%s] retrying %s after reload: %s", self.name, path.name, str(e).splitlines()[0])
                self.base = None
                await asyncio.sleep(15)
                await open_dashboard(self.page)


async def new_worker(browser, name):
    context = await browser.new_context(
        user_agent=config.USER_AGENT, accept_downloads=True,
        timezone_id="Asia/Kolkata", locale="en-IN")
    page = await context.new_page()
    page.set_default_timeout(config.TIMEOUTS_MS["global"])
    await open_dashboard(page)
    return Worker(name, page)


async def drain(workers, tasks, handle):
    """Workers pull tasks from one shared queue until it is empty."""
    queue = asyncio.Queue()
    for t in tasks:
        queue.put_nowait(t)

    async def loop(worker):
        while not queue.empty():
            await handle(worker, queue.get_nowait())

    await asyncio.gather(*(loop(w) for w in workers))


async def drain_with_retry(workers, tasks, handle, failed, failures):
    """Run all tasks; give the ones that failed one more round at the end."""
    failed.clear()
    await drain(workers, tasks, handle)
    if failed:
        retry = list(failed)
        log.info("second round for %d failed downloads", len(retry))
        failed.clear()
        await asyncio.sleep(30)
        await drain(workers, retry, handle)
        failures.extend(str(t[-1].name) if hasattr(t[-1], "name") else str(t) for t in failed)
        failed.clear()


async def run(args):
    out_dir = config.RAW_DIR / datetime.now().strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    failures = []
    failed = []  # tasks that failed in the current round

    def file_for(code, seg, kind, year):
        return out_dir / f"{config.STATE_CODE}_{code}_{seg}_{kind}_{year}.xlsx"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.headed)
        workers = list(await asyncio.gather(
            *(new_worker(browser, f"w{i + 1}") for i in range(args.workers))))

        await workers[0].ensure_base(args.years[0], "Fuel")
        rtos = await list_rtos(workers[0].page)
        pd.DataFrame({"rto_code": [rto_code(r) for r in rtos], "label": rtos}).to_csv(
            out_dir / "rtos.csv", index=False)
        if args.rtos:
            rtos = [r for r in rtos if rto_code(r) in args.rtos]
        log.info("RTOs: %d, segments: %s, years: %s, workers: %d",
                 len(rtos), args.segments, args.years, len(workers))

        # Pass 1: Fuel x Month per RTO x segment -> which fuels are active
        active = {}

        async def fuelmix(worker, task):
            year, seg, rto = task
            code = rto_code(rto)
            path = file_for(code, seg, "FUELMIX", year)
            try:
                if not path.exists():
                    if not await worker.download(year, "Fuel", rto, config.SEGMENTS[seg], [], path):
                        log.info("%s %s: no %s registrations", code, year, seg)
                        return
                active[task] = active_fuels(path)
            except Exception as e:
                log.error("[%s] FUELMIX failed %s %s %s: %s", worker.name, code, seg, year, str(e).splitlines()[0])
                failed.append(task)

        log.info("pass 1: fuel mix")
        await drain_with_retry(workers, [(y, s, r) for y in args.years for r in rtos for s in args.segments],
                               fuelmix, failed, failures)

        # Pass 2: Maker x Month per RTO x segment x active fuel group
        maker_tasks = []
        for (year, seg, rto), fuels in active.items():
            for group, group_fuels in config.FUEL_GROUPS.items():
                # tick only the group's fuels that are active in this RTO
                tick = [f for f in group_fuels if f in fuels]
                path = file_for(rto_code(rto), seg, group, year)
                if tick and not path.exists():
                    maker_tasks.append((year, seg, rto, group, tick, path))

        async def maker(worker, task):
            year, seg, rto, group, tick, path = task
            try:
                if not await worker.download(year, "Maker", rto, config.SEGMENTS[seg], tick, path):
                    log.warning("%s %s %s: group listed active but table empty", rto_code(rto), seg, group)
            except Exception as e:
                log.error("[%s] Maker failed %s: %s", worker.name, path.name, str(e).splitlines()[0])
                failed.append(task)

        log.info("pass 2: maker by fuel group, %d files to download", len(maker_tasks))
        await drain_with_retry(workers, maker_tasks, maker, failed, failures)
        await browser.close()

    if failures:
        log.error("%d downloads failed. Re-run the same command to retry them: %s",
                  len(failures), failures)
        return 1
    log.info("Done. Files in %s", out_dir)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--years", nargs="+", default=config.DEFAULT_YEARS)
    ap.add_argument("--segments", nargs="+", default=list(config.SEGMENTS), choices=list(config.SEGMENTS))
    ap.add_argument("--rtos", nargs="+", help="Limit to RTO codes, e.g. KL7 KL8")
    ap.add_argument("--workers", type=int, default=2, help="Parallel browser sessions (keep it small)")
    ap.add_argument("--headed", action="store_true", help="Show the browser window")
    args = ap.parse_args()
    if args.rtos:
        args.rtos = {r.upper().replace("-", "") for r in args.rtos}
    setup_logging()
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
