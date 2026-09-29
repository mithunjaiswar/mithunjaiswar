# Lakshya 15,000 — weekly supply plan

`build_weekly_supply_plan.py` writes the workbook behind the Google Sheet
"Lakshya 15,000 - Weekly Supply Plan". The sheet's **Read Me** tab explains the plan with live numbers; this file
is the short version.

```
python3 build_weekly_supply_plan.py out.xlsx raw.json         # raw.json = {"hdr": [...], "data": [[...]]} from the SSOT query
python3 build_weekly_supply_plan.py out_v2.xlsx raw.json --v2  # v2: Lakshya as given
python3 build_weekly_supply_plan.py out_act.xlsx raw.json --actual  # actuals-based view
```

Three sheets come out of it:

- **Lakshya-based plan** (default): base recruitment and net attrition follow Lakshya month by month (each month's weeks
  average to Lakshya's month average; a week counts in the month of its Monday, w/c 28 Sep in Oct), with a steady
  catch-up so 27 Dec util equals Lakshya's; EIP on Lakshya's line.
- **Actuals-based view** (`--actual`, sheet "Weekly CNG Supply Plan - Actuals view"): hiring and attrition = the last
  8 weeks' average x last year's week-by-week pattern, Diwali-aligned (`ly_pattern.py`); EIP on its last 4 weeks (the 8 weeks include August's Mumbai drop-offs); no
  catch-up. Before Diwali (w/c 28 Sep - 26 Oct) Kolkata keeps last year's shape (Durga Puja); elsewhere hiring
  dips only in w/c 12, 19 Oct (Durga Puja / Dussehra) and 26 Oct (pre-Diwali), the hires moving to the earlier weeks; November
  recruitment = Lakshya's month average (no stretch), October recruitment and
  attrition too; the capacity ramp is December's only; w/c 2 Nov attrition keeps 35% of last year's jump (Inputs A3b P).
  Its comparison tab shows Lakshya and plan per measure (+ EIP net add), then a last-8-weeks box, the seasonality check
  and the attrition working; its Summary View has a colour scale on every row.
  Same cars as the Lakshya-based plan, so util compares like for like.
- **v2** (`--v2`): every Own Now and L+DTO number is Lakshya v4's.

`plan_history.py` holds the history the plan is checked against (reporting DB, weekly by city, Jan 2024 – Sep 2026):
seasonal changes by season block in 2024 and 2025, the weekly series aligned on Diwali, each city's proven hiring
capacity and the 12-week attrition trend.

## The principle

A realistic path from the current run rate to the December target, with an operational basis for every week:

1. **Start** from the actual on the latest day loaded (Inputs A1); the current week (w/c 28 Sep) is plan week 1.
2. **Hiring** at the current run rate: driver acquisition (new joins + resurrections) over the last 8 weeks (Inputs A3), held flat.
3. **New cars**: all of Lakshya's 2,300. The 582 bought and at the stock yard are phased by RTO status over 8 weeks
   (ready: weeks 1–2, registration done: 2–3, under RTO: 3–6, RTO not started: 5–8); the cars still to buy land in
   Lakshya's months (Oct–Nov, Inputs A6). Each car gets a driver the week after it lands, taken out of that week's
   hiring (not added on top, so hiring doesn't jump). These are **flagged**: a car
   ordered now reaches the road 5 weeks later at the earliest, so Inputs A6 shows the order-by dates by city.
4. **Attrition** matches Lakshya month by month: each month's weeks average to Lakshya's month average (Inputs A3b), keeping the Diwali / Durga Puja shape within the month. The last 8 weeks' rate is the reference. **EIP** grows on a straight line to Lakshya's December EIP.
   This year's attrition runs below last year's.
5. **Seasonality**: only two festival dips — Diwali (w/c 2 and 9 Nov, every city) and Durga Puja (w/c 12 and 19 Oct,
   Kolkata only), each the average of 2024 and 2025 vs the 4 weeks before (Seasonality Check, section 1). Every other
   week is flat.
6. **To Lakshya**: a steady extra hiring ramp on top of the run rate (hiring starts at today's level and rises in a
   straight line, never up and down) — the same extra each week, solved so 27 Dec
   lands on Lakshya — flagged wherever driver acquisition exceeds the city's proven capacity (best 4 weeks since
   Sep 2025). Inputs A1 picks the plan: `Lakshya` (the default: the ramp that makes every city's util on 27 Dec equal
   Lakshya's util — Lakshya on road / Lakshya fleet × our fleet), `Capacity` (same ramp, never above the city's best
   week, lands lower) or `Run rate`.
   **Hiring cap by week** (Inputs A8, columns O-P): w/c 16 and 23 Nov are capped at 200 drivers a city; the hires cut
   move to w/c 28 Sep - 12 Oct, split evenly and grossed up for attrition so 27 Dec (and util) is unchanged.
   All three paths are always shown, next to AOP and Lakshya.

## Tabs

Read Me, Monthly Dashboard and Seasonality Check are built but hidden in the sheet.

| Tab | What it is |
|---|---|
| Read Me | The principle, the bridge by city (now → run rate → within capacity → plan → AOP → Lakshya), new cars, seasonality |
| Summary View | Weekly dashboard with a city picker: plan, actual and same week last year per metric |
| Monthly Dashboard | Month by month (India or a city): hiring, new-car drivers, extra ramp, attrition, run rate / capacity / plan vs AOP and Lakshya; why driver acquisition differs; insights |
| Lakshya vs Plan vs LY | Attrition %, driver recruitment, util, cars added and cars sold (actuals: reporting DB, `car_flows.py`): Lakshya vs plan vs the same week last year vs the last 8 weeks' average — week by week (pick a city), by city, and the 8 actual weeks behind the average |
| Lakshya Source | Lakshya v4's own figures, typed as given: L+DTO book on 31 Aug, churn rate by city, Own Now churn and rollover, weekly placements (the comparison tab's working reads these) |
| Inputs | A1 dates and the December-target switch, A2 city start and targets, A3 current run rate, A4 Lakshya month-ends, A5 AOP month-ends, A6 new cars (stock, delivery windows, pending, future orders), A7 cars sold, A8 calendar; C1 summary, C2 sources |
| Seasonality Check | The two festival dips used (Diwali, Durga Puja in Kolkata), the 2024 vs 2025 history by season, attrition this year vs last, week-by-week 4-week averages aligned on Diwali |
| Mumbai … Pune | One tab per city: Weekly Supply Plan layout (A–AC), layers (AF–AW), last year (AY–BD), operational basis (BE–BT), Lakshya/AOP month-ends and paths (BU–CH) |
| Combined All | One QUERY stacking every city tab |
| raw_performance | Output of the SSOT query (`analytics.ssot_scorecard_agg`) |

**v2 – Lakshya as given** (separate Google Sheet): every Own Now and Leasing + DTO number is Lakshya v4's — weekly
driver acquisition as given, churn and rollover by month spread evenly, starting from Lakshya's own 27 Sep book and
fleet base, with Lakshya's 2,300 new cars (`LK_WEEKLY`, shown on the v2-only **Lakshya Weekly** tab).
