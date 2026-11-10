"""Vahan maker name -> clean brand, plus a brand profile used to suggest
competitors (positioning, typical ticket size, EV-only).

Unknown makers fall back to a cleaned-up name and show up in
`python pipeline/brands.py` so they can be added here.

Ticket sizes are rough ex-showroom ranges in lakh rupees, for suggesting
competitors only. Edit freely.
"""
import re

MAKER_TO_BRAND = {
    # 4W
    "MARUTI SUZUKI INDIA LTD": "Maruti Suzuki",
    "MARUTI UDYOG LTD": "Maruti Suzuki",
    "TOYOTA KIRLOSKAR MOTOR PVT LTD": "Toyota",
    "HYUNDAI MOTOR INDIA LTD": "Hyundai",
    "MAHINDRA & MAHINDRA LIMITED": "Mahindra",
    "MAHINDRA ELECTRIC AUTOMOBILE LTD": "Mahindra",
    "TATA MOTORS PASSENGER VEHICLES LTD": "Tata",
    "TATA PASSENGER ELECTRIC MOBILITY LTD": "Tata",
    "TATA MOTORS LTD": "Tata",
    "KIA INDIA PRIVATE LIMITED": "Kia",
    # Skoda and Volkswagen are one maker in Vahan; can't be split.
    "SKODA AUTO VOLKSWAGEN INDIA PVT LTD": "Skoda-VW",
    "SKODA AUTO AS": "Skoda-VW",
    "VOLKSWAGEN AG": "Skoda-VW",
    "HONDA CARS INDIA LTD": "Honda Cars",
    "JSW MG MOTOR INDIA PVT LTD": "MG",
    "NISSAN MOTOR INDIA PVT LTD": "Nissan",
    "RENAULT INDIA PVT LTD": "Renault",
    # Stellantis = Citroen + Jeep in India
    "STELLANTIS AUTOMOBILES INDIA PVT LTD": "Citroen-Jeep",
    "STELLANTIS INDIA PVT LTD": "Citroen-Jeep",
    "BMW INDIA PVT LTD": "BMW",
    "MERCEDES-BENZ INDIA PVT LTD": "Mercedes-Benz",
    "MERCEDES -BENZ AG": "Mercedes-Benz",
    "BYD INDIA PRIVATE LIMITED": "BYD",
    "VINFAST AUTO INDIA PVT LTD": "VinFast",
    "JAGUAR LAND ROVER INDIA LIMITED": "JLR",
    "FORCE MOTORS LIMITED": "Force",
    "VOLVO AUTO INDIA PVT LTD": "Volvo",
    "PORSCHE AG GERMANY": "Porsche",
    "AUDI AG": "Audi",
    "TESLA INDIA MOTORS AND ENERGY PVT LTD": "Tesla",
    "ISUZU MOTORS INDIA PVT LTD": "Isuzu",
    # 2W
    "HONDA MOTORCYCLE AND SCOOTER INDIA (P) LTD": "Honda 2W",
    "TVS MOTOR COMPANY LTD": "TVS",
    "HERO MOTOCORP LTD": "Hero",
    "SUZUKI MOTORCYCLE INDIA PVT LTD": "Suzuki 2W",
    "INDIA YAMAHA MOTOR PVT LTD": "Yamaha",
    "ROYAL-ENFIELD (UNIT OF EICHER LTD)": "Royal Enfield",
    "BAJAJ AUTO LTD": "Bajaj",
    "ATHER ENERGY LTD": "Ather",
    "RIVER MOBILITY PVT LTD": "River",
    "SIMPLEENERGY PVT LTD": "Simple Energy",
    "PIAGGIO VEHICLES PVT LTD": "Piaggio (Vespa/Aprilia)",
    "OLA ELECTRIC TECHNOLOGIES PVT LTD": "Ola Electric",
    "GREAVES ELECTRIC MOBILITY LTD": "Ampere",
    "CLASSIC LEGENDS PVT LTD": "Jawa-Yezdi-BSA",
    "OBEN ELECTRIC VEHICLES PVT LTD": "Oben",
    "ULTRAVIOLETTE AUTOMOTIVE PVT LTD": "Ultraviolette",
    "INDIA KAWASAKI MOTORS PVT LTD": "Kawasaki",
    "REVOLT INTELLICORP PVT LTD": "Revolt",
    "BGAUSS AUTO PRIVATE LIMITED": "BGauss",
    "KLB KOMAKI PVT LTD": "Komaki",
    "TRIUMPH MOTORCYCLES (INDIA) PVT LTD": "Triumph",
    "DUCATI INDIA PVT LTD": "Ducati",
    "HERO ELECTRIC VEHICLES PVT. LTD": "Hero Electric",
    "HARLEY DAVIDSON (IMPORTER: HERO MOTOCORP)": "Harley-Davidson",
    "KINETIC GREEN ENERGY & POWER SOLUTIONS LTD": "Kinetic Green",
}

# brand -> (segment, positioning, ticket range in lakh, ev_only)
BRAND_PROFILE = {
    "Maruti Suzuki": ("4W", "mass", (4, 20), False),
    "Hyundai": ("4W", "mass", (6, 25), False),
    "Tata": ("4W", "mass", (5, 25), False),
    "Mahindra": ("4W", "mid", (8, 30), False),
    "Kia": ("4W", "mid", (8, 25), False),
    "Toyota": ("4W", "mid", (7, 50), False),
    "Honda Cars": ("4W", "mid", (7, 18), False),
    "Skoda-VW": ("4W", "mid", (8, 40), False),
    "MG": ("4W", "mid", (7, 40), False),
    "Nissan": ("4W", "mass", (6, 12), False),
    "Renault": ("4W", "mass", (5, 12), False),
    "Citroen-Jeep": ("4W", "mid", (6, 35), False),
    "BYD": ("4W", "premium", (25, 60), True),
    "VinFast": ("4W", "mid", (16, 30), True),
    "Force": ("4W", "mid", (15, 30), False),
    "Isuzu": ("4W", "mid", (20, 30), False),
    "BMW": ("4W", "luxury", (45, 250), False),
    "Mercedes-Benz": ("4W", "luxury", (45, 300), False),
    "Audi": ("4W", "luxury", (45, 150), False),
    "JLR": ("4W", "luxury", (70, 300), False),
    "Volvo": ("4W", "luxury", (45, 100), False),
    "Porsche": ("4W", "luxury", (90, 300), False),
    "Tesla": ("4W", "luxury", (60, 80), True),
    "Honda 2W": ("2W", "mass", (0.7, 2), False),
    "TVS": ("2W", "mass", (0.6, 3), False),
    "Hero": ("2W", "mass", (0.6, 2.5), False),
    "Bajaj": ("2W", "mass", (0.7, 3.5), False),
    "Suzuki 2W": ("2W", "mass", (0.8, 2), False),
    "Yamaha": ("2W", "mid", (0.8, 2.5), False),
    "Royal Enfield": ("2W", "mid", (1.5, 4), False),
    "Jawa-Yezdi-BSA": ("2W", "mid", (1.5, 3), False),
    "Piaggio (Vespa/Aprilia)": ("2W", "mid", (1, 2), False),
    "Ather": ("2W", "mid", (1, 2), True),
    "Ola Electric": ("2W", "mass", (0.8, 1.6), True),
    "River": ("2W", "mid", (1.4, 1.6), True),
    "Simple Energy": ("2W", "mid", (1.2, 1.7), True),
    "Ampere": ("2W", "mass", (0.6, 1.2), True),
    "Oben": ("2W", "mid", (1.2, 1.6), True),
    "Revolt": ("2W", "mass", (0.9, 1.3), True),
    "BGauss": ("2W", "mass", (0.8, 1.3), True),
    "Komaki": ("2W", "mass", (0.6, 1.5), True),
    "Ultraviolette": ("2W", "premium", (2, 4), True),
    "Kawasaki": ("2W", "premium", (3, 30), False),
    "Triumph": ("2W", "premium", (2, 20), False),
    "Ducati": ("2W", "premium", (10, 40), False),
    "Harley-Davidson": ("2W", "premium", (2.5, 40), False),
}

_SUFFIX = re.compile(r"\b(PVT\.?|PRIVATE|LTD\.?|LIMITED|INDIA|CO\.?|COMPANY|\(P\)|AG|AS)\b|\(IMPORTER:.*?\)")


def brand_for(maker):
    maker = maker.strip().upper()
    if maker in MAKER_TO_BRAND:
        return MAKER_TO_BRAND[maker]
    cleaned = " ".join(_SUFFIX.sub(" ", maker).split())
    return cleaned.title() or maker.title()


if __name__ == "__main__":
    import sqlite3
    from pathlib import Path
    db = Path(__file__).resolve().parent.parent / "data" / "odometrics.db"
    rows = sqlite3.connect(db).execute(
        "select maker, segment, sum(count) from registrations group by 1, 2 order by 3 desc").fetchall()
    unknown = [(m, s, n) for m, s, n in rows if m not in MAKER_TO_BRAND]
    print(f"{len(rows)} maker/segment pairs, {len(unknown)} not mapped (fallback name used):")
    for m, s, n in unknown:
        print(f"  {n:>7}  {s}  {m}  ->  {brand_for(m)}")
