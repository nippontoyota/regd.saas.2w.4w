"""Settings for the Vahan collector.

Source: the old Vahan4 dashboard (no CAPTCHA). Its own banner says it is
discontinued after 15 Aug 2026, so expect this to stop working one day.
"""
from pathlib import Path

TARGET_URL = "https://vahan.parivahan.gov.in/vahan4dashboard/vahan/view/reportview.xhtml"

STATE_LABEL = "Kerala(87)"
STATE_CODE = "KL"
X_AXIS = "Month Wise"
YEAR_TYPE = "Calendar Year"
DEFAULT_YEARS = ["2026"]

# Segment = set of Vahan "Vehicle Class" checkboxes. Matches Vahan's own
# "Vehicle Category Group" for 2W/4W, minus ADAPTED VEHICLE (it sits in both).
SEGMENTS = {
    "2W": [
        "M-CYCLE/SCOOTER",
        "M-CYCLE/SCOOTER-WITH SIDE CAR",
        "MOPED",
        "MOTORISED CYCLE (CC > 25CC)",
        "MOTOR CYCLE/SCOOTER-SIDECAR(T)",
        "MOTOR CYCLE/SCOOTER-WITH TRAILER",
        "MOTOR CYCLE/SCOOTER-USED FOR HIRE",
    ],
    "4W": [
        "MOTOR CAR",
        "PRIVATE SERVICE VEHICLE (INDIVIDUAL USE)",
        "OMNI BUS (PRIVATE USE)",
        "QUADRICYCLE (PRIVATE)",
        "LUXURY CAB",
        "MAXI CAB",
        "MOTOR CAB",
        "QUADRICYCLE (COMMERCIAL)",
    ],
}

# Every fuel label Vahan lists, with its Vahan id.
FUELS = {
    "PETROL": "1", "DIESEL": "2", "PETROL/CNG": "3", "ELECTRIC(BOV)": "4",
    "PETROL/LPG": "5", "CNG ONLY": "6", "LPG ONLY": "8", "SOLAR": "10",
    "PETROL/HYBRID": "11", "DIESEL/HYBRID": "12", "ETHANOL(E100)": "13",
    "PETROL/METHANOL": "14", "METHANOL": "15", "PETROL(E20)": "16", "LNG": "17",
    "DUAL DIESEL/BIO CNG": "18", "DUAL DIESEL/CNG": "19", "DUAL DIESEL/LNG": "20",
    "DI-METHYL ETHER": "21", "FUEL CELL HYDROGEN": "22", "PURE EV": "23",
    "STRONG HYBRID EV": "25", "PLUG-IN HYBRID EV": "26", "PETROL(E20)/CNG": "29",
    "PETROL(E20)/LPG": "30", "PETROL(E20)/HYBRID": "31", "BIO-METHANE": "32",
    "BIO-CNG/BIO-GAS": "33", "HCNG": "34", "FLEX-FUEL(ETHANOL)": "35",
    "FLEX-FUEL(BIO-DIESEL)": "36", "HYDROGEN(ICE)": "37", "BIO-DIESEL(B100)": "38",
    "PETROL/HYBRID/CNG": "39", "PETROL(E20)/HYBRID/CNG": "40", "NOT APPLICABLE": "99",
}

# Fuel groups downloaded as one Maker x Month table each (all listed fuels
# ticked together). Fixed once downloaded; any fuel not listed falls into OTH.
FUEL_GROUPS = {
    "PET": ["PETROL", "PETROL(E20)", "PETROL/LPG", "PETROL(E20)/LPG", "PETROL/METHANOL"],
    "DSL": ["DIESEL"],
    "CNG": ["CNG ONLY", "PETROL/CNG", "PETROL(E20)/CNG"],
    "EV": ["PURE EV", "ELECTRIC(BOV)"],
    "HYB": ["STRONG HYBRID EV", "PETROL/HYBRID", "PETROL(E20)/HYBRID", "DIESEL/HYBRID",
            "PETROL/HYBRID/CNG", "PETROL(E20)/HYBRID/CNG"],
    "PHEV": ["PLUG-IN HYBRID EV"],
}
_grouped = {f for fuels in FUEL_GROUPS.values() for f in fuels}
FUEL_GROUPS["OTH"] = [f for f in FUELS if f not in _grouped]

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
LOGS_DIR = PROJECT_DIR / "logs"

# Be gentle with a government server: random pause between exports.
DELAY_SECONDS = (4, 8)

TIMEOUTS_MS = {
    "global": 90_000,
    "navigation": 60_000,
    "network_idle": 15_000,
    "table": 45_000,
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

SELECTORS = {
    "state_label": "xpath=//label[normalize-space()='State:']/following-sibling::div[contains(@class,'ui-selectonemenu')]//label",
    "state_item": "li[data-label='{}']",
    "rto_label": "label#selectedRto_label",
    "rto_items": "ul#selectedRto_items li",
    "rto_item": "ul#selectedRto_items li[data-label='{}']",
    "yaxis_label": "label#yaxisVar_label",
    "yaxis_item": "ul#yaxisVar_items li[data-label='{}']",
    "xaxis_label": "label#xaxisVar_label",
    "xaxis_item": "ul#xaxisVar_items li[data-label='{}']",
    "yeartype_label": "label#selectedYearType_label",
    "yeartype_item": "ul#selectedYearType_items li[data-label='{}']",
    "year_label": "label#selectedYear_label",
    "year_item": "ul#selectedYear_items li[data-label='{}']",
    "sidebar_toggler": "#filterLayout-toggler",
    # Checkbox groups in the left panel: table ids "VhClass" and "fuel".
    # Checkbox ids re-index when the RTO changes, so always go by label text.
    "group_labels": "xpath=//table[@id='{group}' or substring(@id, string-length(@id) - string-length(':{group}') + 1) = ':{group}']//label[@for]",
    # Top Refresh rebuilds the table but DROPS the side filters; the sidebar
    # Refresh applies the ticked side filters without resetting them.
    "top_refresh": "button:has-text('Refresh')",
    "sidebar_refresh": "xpath=//div[@id='filterLayout']//button[normalize-space()='Refresh']",
    "export_btn": "a:has(img[src*='csv.png'])",
    "table_row": "tbody.ui-datatable-data tr",
    # e.g. "Maker Month Wise Data of Kerala (2026)"; the RTO part is stale
    "table_heading": ".ui-datatable-header, .ui-panel-title",
}
