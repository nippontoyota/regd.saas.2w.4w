# Vahan data sources — site map (checked 2026-10-19)

## 1. Old Vahan4 Dashboard (reportview.xhtml)
URL: https://vahan.parivahan.gov.in/vahan4dashboard/vahan/view/reportview.xhtml
- Banner: "Vahan4Dashboard will be discontinued after 15 August 2026." Still live on 2026-10-19, but can be switched off any day.
- No CAPTCHA. JSF/PrimeFaces page (ViewState, AJAX postbacks). Excel export icon on the result table.

### Top filters
- Type: T=Thousand, L=Lakh, C=Crore, A=Actual Value
- State: codes e.g. KL=Kerala(87); 36 states, 1468/1469 RTOs nationally
- RTO: depends on State
- Y-Axis: Vehicle Category | Vehicle Class | Norms | Fuel | Maker | State
- X-Axis: Vehicle Category | Norms | Fuel | Vehicle Category Group | Financial Year | Calendar Year | Month Wise
- Year Type: F=Financial, C=Calendar
- Year: "Till Today", 2003..2026

### Vehicle Category Group (built-in grouping; value = group|class ids|category codes)
- 2W: classes 1,2,3,4,5,51,52,53 — categories 2WIC,2WN,2WT
- 3W: classes 6,54,55,57,58 — 3WN,3WT
- 4W: classes 5,7,15,23,31,56,70,71,93 — 4WIC,LMV,MMV,HMV
  (Adapted vehicle, Motor Car, Private Service Vehicle, Omni Bus (private), Quadricycle (private), Luxury Cab, Maxi Cab, Motor Cab, Quadricycle (commercial))
- Also: AH ambulance/hearses, CE construction eqpt, GV goods, PS public service, SC special, TL trailer, TR tractor

### Side-panel filters (left panel has its own Refresh)
- Fuel (id=name): 1 PETROL, 2 DIESEL, 3 PETROL/CNG, 4 ELECTRIC(BOV), 5 PETROL/LPG, 6 CNG ONLY, 8 LPG ONLY,
  10 SOLAR, 11 PETROL/HYBRID, 12 DIESEL/HYBRID, 13 ETHANOL(E100), 14 PETROL/METHANOL, 15 METHANOL, 16 PETROL(E20),
  17 LNG, 18 DUAL DIESEL/BIO CNG, 19 DUAL DIESEL/CNG, 20 DUAL DIESEL/LNG, 21 DI-METHYL ETHER, 22 FUEL CELL HYDROGEN,
  23 PURE EV, 25 STRONG HYBRID EV, 26 PLUG-IN HYBRID EV, 29 PETROL(E20)/CNG, 30 PETROL(E20)/LPG, 31 PETROL(E20)/HYBRID,
  32 BIO-METHANE, 33 BIO-CNG/BIO-GAS, 34 HCNG, 35 FLEX-FUEL(ETHANOL), 36 FLEX-FUEL(BIO-DIESEL), 37 HYDROGEN(ICE),
  38 BIO-DIESEL(B100), 39 PETROL/HYBRID/CNG, 40 PETROL(E20)/HYBRID/CNG, 99 NOT APPLICABLE
- Proposed fuel groups: EV = {4, 23}; Strong hybrid = {11, 25, 31, 39, 40, 12}; PHEV = {26};
  CNG = {3, 6, 29}; Petrol = {1, 16, 5, 30, 14}; Diesel = {2}; Other = rest
- Vehicle Category, Vehicle Class (full id list captured), Norms

## 2. New Parivahan Analytics — Public Report
URL: https://analytics.parivahan.gov.in/analytics/vahanpublicreport?lang=en
- Tabular Y-axis × X-axis report (the replacement for the old table) — **protected by CAPTCHA on every request.**

## 3. New Parivahan Analytics — Public Dashboard
URL: https://analytics.parivahan.gov.in/analytics/publicdashboard/vahan?lang=en
- Charts only. Filters: state, RTO, maker, category group, sub-category, class, fuel, EV type, owner type, transport/non-transport.
- Backed by JSON GET endpoints, no CAPTCHA, e.g. /publicdashboard/vahandashboard/top5Makerchart?...
- Gives top-5 makers and totals, **not** a full maker × month table.
