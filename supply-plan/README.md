# Lakshya 15,000 — weekly supply plan

`build_weekly_supply_plan.py` writes the workbook behind the Google Sheet
"Lakshya 15,000 - Weekly Supply Plan (21 Sep - 27 Dec 2026)". The sheet's **Read Me** tab explains the
plan with live numbers; this file is the short version.

```
python3 build_weekly_supply_plan.py out.xlsx raw.json   # raw.json = {"hdr": [...], "data": [[...]]} from the SSOT query
```

## Tabs

| Tab | What it is |
|---|---|
| Read Me | How the plan bridges 20 Sep to 27 Dec: the rule, the bridge by season, India week by week vs last year |
| Lakshya vs Plan | Lakshya v4 as given next to this plan, for sharing |
| Summary View | Dashboard with a city picker: plan, actual and same week last year per metric |
| Monthly Dashboard | Month by month (Lakshya months) for India or a picked city, Lakshya plan vs our plan (books, on road, driver acquisition), why driver acquisition differs (India), and live insights |
| Inputs | Everything the plan is built from, in three parts: **A** what you set (A1 dates and switches, A2 city start / Dec targets / rates, A3 Lakshya month-end targets, A4 new cars, A5 cars sold, A6 weekly calendar), **B** learnt from last year (B1 festival impact), **C** output and sources |
| Diwali_Dip Analysis | Last year's proven weekly pace (section 1), the Diwali dip (section 2) and the Sunday cars-on-road history it is worked out from (section 3) |
| Mumbai … Pune | One tab per city, Weekly Supply Plan layout (A–AC), Lakshya build-up (AF–AW), last year and seasonality (AY–BF), realism check (BH–BQ) |
| Combined All | One QUERY stacking every city tab (same columns as the Weekly Supply Plan's Combined All) |
| raw_performance | Output of the SSOT query (`analytics.ssot_scorecard_agg`) |

## How a week is planned

1. **New cars** go on road the week after they arrive (2,300 cars, Oct–Nov).
2. **Organic growth** (recruitment net of churn) is asked for its share of the gap to **Lakshya's next
   month-end** (Own Now and Leasing+DTO books on 27 Sep, 25 Oct, 29 Nov, 27 Dec; EIP on a straight line —
   Inputs A3), after the new cars due that month: gap ÷ weeks left in the month, less in festival weeks (festival impact on recruitment from the
   Weekly Supply Plan's `seasonality_Impect` tab). Weeks with no festival get a factor of 1.
3. That organic growth is **compared with the city's proven pace**: its best 4-week average weekly growth in
   cars on road in the same season of 2024 or 2025 (Pre-Diwali, Diwali, Post-Diwali), floored at 0%.
   With the Inputs A1 switch on Yes a capped week rolls the rest into the next month. The default is No: every week takes what Lakshya's month-end needs, so the plan matches Lakshya at every month-end, and weeks above last year's pace are flagged red in city tab column BP.
   Nothing forces a spike in the last weeks.
4. **Diwali weeks (w/c 2 and 9 Nov)** do not grow: cars on road follow each city's average dip of 2024 and
   2025 in the same festival weeks (India −3.3% then −5.9%, −9.1% over the two weeks; Diwali_Dip Analysis tab).
   The dip comes out of the Leasing+DTO book, and new cars that land in those weeks wait and go on road
   from the recovery week at up to 1.5× the normal weekly rate. The weeks before and after make up the dip.
5. Each layer (EIP / Own Now / Leasing+DTO) is planned to its own month-end target; when the pace cap moves the
   total away from the sum, the difference is shared over the layers with a positive need. Leasing+DTO takes
   the Diwali dip and wins it back afterwards.
   Churn = last week's book × Lakshya monthly rate ÷ 4.33 × last year's attrition index for that week.
   Driver acquisition = net add + churn; recruitment by channel = driver acquisition × AOP channel mix.

## Seasons (2026)

| Season | Weeks | What last year showed | What the plan does |
|---|---|---|---|
| Pre-Diwali | w/c 21 Sep – 26 Oct | India flat to falling in 2025 (−2.6% to −5.4% weeks); best 4 weeks +1.5%/wk in 2024 | Organic ≤ each city's better year; October new cars on road |
| Diwali | w/c 2 & 9 Nov | Cars on road fell: India −9.8% (2024), −8.5% (2025) over the two weeks | Falls by each city's two-year average dip; new cars held back |
| Post-Diwali | w/c 16 Nov – 21 Dec | Real recovery: India +2.7–2.9%/wk best, Mumbai/Pune > 5% | Most of the remaining organic gap, within each city's pace |
