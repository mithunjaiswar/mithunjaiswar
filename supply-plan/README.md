# Lakshya 15,000 — weekly supply plan

`build_weekly_supply_plan.py` writes the workbook behind the Google Sheet
"Lakshya 15,000 - Weekly Supply Plan". The sheet's **Read Me** tab explains the plan with live numbers; this file
is the short version.

```
python3 build_weekly_supply_plan.py out.xlsx raw.json         # raw.json = {"hdr": [...], "data": [[...]]} from the SSOT query
python3 build_weekly_supply_plan.py out_v2.xlsx raw.json --v2  # v2: Lakshya as given
```

`plan_history.py` holds the history the plan is checked against (reporting DB, weekly by city, Jan 2024 – Sep 2026):
seasonal changes by season block in 2024 and 2025, the weekly series aligned on Diwali, each city's proven hiring
capacity and the 12-week attrition trend.

## The principle

A realistic path from the current run rate to the December target, with an operational basis for every week:

1. **Start** from the actual on the latest day loaded (Inputs A1); the current week (w/c 28 Sep) is plan week 1.
2. **Hiring** at the current run rate: driver acquisition (new joins + resurrections) over the last 4 weeks (Inputs A3).
3. **New cars**: all of Lakshya's 2,300. The 582 bought and at the stock yard are phased by RTO status over 8 weeks
   (ready: weeks 1–2, registration done: 2–3, under RTO: 3–6, RTO not started: 5–8); the cars still to buy land in
   Lakshya's months (Oct–Nov, Inputs A6). Each car gets a driver the week after it lands.
4. **Attrition** at the current rate (net attrition / drivers at week start, last 4 weeks). This year runs below last
   year, but has been flat for 12 weeks while last year rose; the plan keeps this year's level.
5. **Seasonality** only where 2024 and 2025 agree: each season block (Pre-Diwali, Diwali weeks, Recovery, December)
   is compared with the 4 weeks before it, aligned on Diwali; it changes hiring or attrition only if both years moved
   the same way by at least 5% (Seasonality Check tab).
6. **To Lakshya**: a steady extra hiring ramp on top of the run rate — the same extra each week, solved so 27 Dec
   lands on Lakshya — flagged wherever driver acquisition exceeds the city's proven capacity (best 4 weeks since
   Sep 2025). Inputs A1 picks the plan: `Lakshya`, `Capacity` (same ramp, never above capacity) or `Run rate`.
   All three paths are always shown, next to AOP and Lakshya.

## Tabs

| Tab | What it is |
|---|---|
| Read Me | The principle, the bridge by city (now → run rate → within capacity → plan → AOP → Lakshya), new cars, seasonality |
| Summary View | Weekly dashboard with a city picker: plan, actual and same week last year per metric |
| Monthly Dashboard | Month by month (India or a city): hiring, new-car drivers, extra ramp, attrition, run rate / capacity / plan vs AOP and Lakshya; why driver acquisition differs; insights |
| LY vs CY vs Plan | Last year, this year, run rate, within capacity, plan, AOP and Lakshya side by side, week on week |
| Inputs | A1 dates and the December-target switch, A2 city start and targets, A3 current run rate, A4 Lakshya month-ends, A5 AOP month-ends, A6 new cars (stock, delivery windows, pending, future orders), A7 cars sold, A8 calendar; C1 summary, C2 sources |
| Seasonality Check | Seasonal changes used, the 2024 vs 2025 check, attrition this year vs last, week-by-week 4-week averages aligned on Diwali |
| Mumbai … Pune | One tab per city: Weekly Supply Plan layout (A–AC), layers (AF–AW), last year (AY–BD), operational basis (BE–BT), Lakshya/AOP month-ends and paths (BU–CH) |
| Combined All | One QUERY stacking every city tab |
| raw_performance | Output of the SSOT query (`analytics.ssot_scorecard_agg`) |

**v2 – Lakshya as given** (separate Google Sheet): every Own Now and Leasing + DTO number is Lakshya v4's — weekly
driver acquisition as given, churn and rollover by month spread evenly, starting from Lakshya's own 27 Sep book and
fleet base, with Lakshya's 2,300 new cars (`LK_WEEKLY`, shown on the v2-only **Lakshya Weekly** tab).
