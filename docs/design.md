# Odometrics — product design decisions

## Platform
- Web app (mobile-friendly first; dealers check it on their phones)
- English only
- One brand per account (one dealership = one brand)
- Login and sign-up: later

## Brand palette — "Road navy"
| Role | Colour |
|---|---|
| Primary (header, text accents) | `#0F2A4A` navy |
| "You" — the customer's own brand in every chart | `#14A39A` teal |
| Alerts, "needs attention" | `#F2A93B` amber |
| Page background | `#F5F7FA` |
| Cards | `#FFFFFF` |

Rules:
- Only the customer's brand is coloured (teal); competitors are greys. A selected competitor gets a highlight colour on hover or tap.
- Green ▲ / red ▼ only for changes, never as decoration.
- Fonts: **Playfair Display Bold** for the logo, page titles and headline numbers;
  Inter for body text, tables, labels and chart axes (a serif at small sizes hurts readability of dense numbers).
- Large numbers, answer first, detail on tap.
- "Data as of <date>" always visible.
- Comparisons are always like-for-like (MTD vs the same days of last month or year).
- No Vahan jargon: show "Petrol / EV / Hybrid" and clean brand names.
- Don't use "Vahan" or "Parivahan" in the product name, so it can't be mistaken for a government product.

## Screens
1. Onboarding wizard: brand + segment → pure EV or mixed → positioning + ticket size → territory (RTOs) → competitors (pre-filled, editable)
2. Home dashboard: filter bar, 4 KPI tiles (registrations, share, rank, market size), share trend, competitor table, share by RTO, AI question box
3. RTO detail
4. Competitor view
5. Alerts (weekly WhatsApp/email digest + triggers)
6. Settings
7. Admin: customers, data freshness, collector status, maker-name review queue
