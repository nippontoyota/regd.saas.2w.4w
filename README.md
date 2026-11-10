# Odometrics — Vahan market-share data

## Collector

Downloads RTO-wise **Maker × Month** tables from the old Vahan4 dashboard, split by
segment (2W / 4W) and by fuel, for Kerala.

```bash
pip install -r requirements.txt
python -m playwright install chromium

python collector/vahan_collector.py                          # all 87 RTOs, 2W + 4W, 2026
python collector/vahan_collector.py --years 2023 2024 2025   # backfill
python collector/vahan_collector.py --rtos KL7 --segments 4W --headed   # quick test, visible browser
```

For each year and segment it does two passes:

1. **FUELMIX**: Fuel × Month per RTO. This tells us which fuels are active there.
2. **Maker**: Maker × Month per RTO, one file per active fuel group (PET, DSL, CNG, EV, HYB, PHEV, OTH).
   All fuels in a group are ticked together; groups are in `FUEL_GROUPS`.

Files go to `data/raw/<run date>/KL_<rto>_<2W|4W>_<fuelGroup|FUELMIX>_<year>.xlsx`.
Groups are fixed once downloaded.
already exist, so after a crash you just run the same command again.

Segments are defined by Vahan *Vehicle Class* (see `SEGMENTS` in `collector/config.py`).
Taxis and bike taxis are included.

**Caveat:** the old dashboard says it is discontinued after 15 Aug 2026. It still works,
but expect it to stop one day.
