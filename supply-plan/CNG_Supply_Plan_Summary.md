# Weekly CNG Supply Plan: 28 Sep to 27 Dec 2026

*Summary for review. Actuals run to Sat 26 Sep 2026. All figures are India (7 cities: Mumbai, Delhi NCR, Bangalore, Hyderabad, Chennai, Kolkata, Pune) unless a city is named.*

## 1. The sheets

| Sheet | What it is | Link |
|---|---|---|
| **Lakshya-based plan** (main) | Matches Lakshya v4 month by month on attrition, recruitment, cars added and cars sold, and lands on Lakshya's util on 27 Dec. | [Open](https://docs.google.com/spreadsheets/d/1h314RtB8WjMOZEQTGEbR-Ly4iYUdXsnzWPUhGvpzvWI/edit) |
| **Actuals view** | What the business is likely to do: the last 8 weeks' run rate, last year's festival pattern, and Lakshya's month averages where agreed. | [Open](https://docs.google.com/spreadsheets/d/1qgLxZmiLOfBWFnmHzQrQZj10571ae8ln9Ao3q2991RI/edit) |
| **v2** | Every Own Now and L+DTO number taken from Lakshya v4 as given (reference). | [Open](https://docs.google.com/spreadsheets/d/1mYh3raKeU-taJxLsObbOfNbJpDx4wtx_2OPdJhQZjbY/edit) |
| Lakshya v4 model | The source target model. | [Open](https://docs.google.com/spreadsheets/d/1Bu8NkgNVcakYondqbyK_jW4nFuFDBqEk/edit) |

**Tabs to look at in each sheet**
- **Summary View:** weekly dashboard with a city picker. Each metric shows the plan, the actual and the same week last year.
- **Lakshya vs Plan vs LY:** the main comparison tab. For every week it shows Lakshya against Plan for:
  - attrition %
  - driver recruitment
  - util %
  - cars added
  - cars sold
  - EIP net add

  Next to that are the last 8 weeks' average, a month-by-month table, a seasonality check and the attrition working. Pick a city in cell B3.
- **Inputs:** every assumption, in cream cells.
- **City tabs:** the weekly working for each city.

Month rule: a week counts in the month of its Monday. October is w/c 28 Sep – 26 Oct, November is 2 – 30 Nov and December is 7 – 21 Dec.

## 2. Headline numbers (India)

### Lakshya-based plan: matches Lakshya every month

| Month | Attrition % a week (Lakshya / Plan) | Recruitment a week (Lakshya / Plan) | Recruitment total (Lakshya / Plan) | Util % (Lakshya / Plan) | Cars added | Cars sold | EIP net add |
|---|---|---|---|---|---|---|---|
| Oct | 9.8% / 9.8% | 1,118 / 1,118 | 5,591 / 5,591 | 65.2% / 62.6% | 1,382 / 1,382 | 290 / 290 | 235 / 235 |
| Nov | 8.5% / 8.5% | 1,082 / 1,082 | 5,408 / 5,408 | 64.1% / 64.3% | 918 / 918 | 253 / 253 | 235 / 235 |
| Dec | 8.8% / 8.8% | 1,272 / 1,272 | 3,816 / 3,816 | 71.8% / 70.6% | 0 / 0 | 178 / 178 | 141 / 141 |
| **13 weeks** | 9.1% / 9.1% | 1,140 / 1,140 | **14,815 / 14,815** | 66.3% / 65.1% | **2,300 / 2,300** | 721 / 721 | **612 / 612** |

**Util on 21 Dec: Plan 72.2% against Lakshya 72.1%.**

### Actuals view: what the run rate supports

| Month | Attrition % a week (Lakshya / Plan) | Recruitment a week (Lakshya / Plan) | Recruitment total (Lakshya / Plan) | Util % (Lakshya / Plan) | Cars added | Cars sold | EIP net add |
|---|---|---|---|---|---|---|---|
| Oct | 9.8% / 9.8% | 1,118 / 1,118 | 5,591 / 5,591 | 65.2% / 63.3% | 1,382 / 1,241 | 290 / 290 | 235 / 230 |
| Nov | 8.5% / 9.7% | 1,082 / 1,082 | 5,408 / 5,408 | 64.1% / 62.4% | 918 / 1,060 | 253 / 253 | 235 / 230 |
| Dec | 8.8% / 8.6% | 1,272 / 1,161 | 3,816 / 3,482 | 71.8% / 67.4% | 0 / 0 | 178 / 178 | 141 / 138 |
| **13 weeks** | 9.1% / 9.4% | 1,140 / 1,114 | **14,815 / 14,481** | 66.3% / 63.9% | 2,300 / 2,301 | 721 / 721 | 612 / 598 |

**Util on 21 Dec: Plan 69.4% against Lakshya 72.1%.**

The gap is December hiring, which is 334 hires short of Lakshya because each city's extra hiring is capped at its best week so far.

Where we start (last 8 weeks, actual):
- attrition 10.9% a week
- recruitment 979 a week
- util 62.7%

Last actual week (w/c 21 Sep): attrition 10.3%, recruitment 1,002, util 61.2%.

## 3. How the Actuals view is built

1. **Starting point.** It starts from the actual on 27 Sep and uses the last 8 weeks' run rate for each city.
2. **Recruitment:**
   - **October and November** use Lakshya's month average for each city.
   - **December** uses the 8-week run rate plus an extra hiring ramp towards Lakshya's 27 Dec util. The ramp is capped at each city's best week so far, so no city is asked to hire more than it ever has in a week.
3. **Attrition:**
   - **October** uses Lakshya's October average, easing down week by week.
   - **After October** it steps down from the 8-week rate to each city's best 4 weeks by 27 Dec.
4. **Seasonality.** Only two festivals are used: **Diwali** (all cities) and **Durga Puja** (Kolkata). Within a month the total stays the same; the festival only moves hires between weeks.
   - **Durga Puja / Dussehra (w/c 12 and 19 Oct) and the week before Diwali (w/c 26 Oct):** hiring dips by last year's drop for that week. The hires move into w/c 28 Sep and 5 Oct.
   - **Kolkata:** keeps its full Durga Puja pattern from last year.
   - **w/c 2 Nov:** Dhanteras to Diwali (Fri 6 – Sun 8 Nov) fall in this week this year, so it takes last year's Diwali-week hiring dip. India goes to 862, from 1,115.
   - **Attrition in w/c 2 Nov:** keeps 35% of last year's Diwali jump, which gives about 12% (the full jump would be 14.4%). The 35% is an input in Inputs A3b column P.
5. **EIP.** Uses the last 4 weeks' trend of +46 a week (598 over 13 weeks, against Lakshya's 612).
   - EIP cars fell 241 in August, mostly Mumbai drop-offs: from 2,483 on 2 Aug to 2,242 on 30 Aug.
   - They recovered 184 in September, to 2,426 on 26 Sep.
   - Using 8 weeks would have shown −94 over 13 weeks, which is August's fall rather than the current trend.
6. **Cars added and sold.** Same as Lakshya (2,300 added, 721 sold), taking bought cars by RTO status plus Lakshya's cars still to buy.

## 4. Changes made during this review

| # | Change | Why |
|---|---|---|
| 1 | The plan follows a steady line from the last 6–8 weeks' actuals; seasonality is shown only for Diwali and Durga Puja (Kolkata). | Avoid ups and downs that aren't real. |
| 2 | Hiring capped at each city's proven best week; no 300-a-week jumps. | Only plan what is achievable. |
| 3 | The Lakshya-based plan matches Lakshya month by month on attrition, recruitment, cars added and cars sold; 21 Dec util is 72.2% against Lakshya's 72.1%. | Month-on-month tracking against Lakshya. |
| 4 | Hiring cap setting (Inputs A8): each city at 200 a week in w/c 16 and 23 Nov, with the excess moved into early October. | Keep weekly hiring achievable. |
| 5 | Comparison tab built: Lakshya vs Plan, the last 3 actual weeks, the last 8 weeks' average, and a block for each city. | One place to compare week by week. |
| 6 | Attrition working shown in full with formulas (no typed numbers), tracing back to Lakshya's Churn tab. | Anyone can see how attrition is calculated. |
| 7 | Cars added and sold (and EIP) shown as month and 13-week **totals**, not averages. | Lakshya plans about 2,300 cars; the total must be visible. |
| 8 | Inputs tab cleaned up; reference tabs (Read Me, Monthly Dashboard, Seasonality Check) hidden; plain-text links added. | Readability. |
| 9 | Actuals view: w/c 2 Nov attrition brought down from 14.4% to about 12%. | The full jump was too high. |
| 10 | Actuals view: October and November recruitment set to Lakshya's month average, with no extra stretch. | Recruitment in those months was too low. |
| 11 | EIP net add added to the comparison; the Actuals view's EIP now uses the last 4 weeks' trend. | EIP showed −94 against Lakshya's +612. |
| 12 | New comparison layout: Lakshya and Plan for each measure, then an 8-week box, a month-by-month table (with recruitment totals), a seasonality comment and the attrition working. Text is centred with splitter lines. Applied to the Lakshya-based plan and the Actuals view. | Easier to read and compare. |
| 13 | Summary View (Actuals view): colour scale on every row; attrition is reversed so low shows green. | Quick visual check. |
| 14 | October weeks are no longer flat: festival-week hires moved to the earlier weeks. | Plan for the Durga Puja and Diwali impact. |
| 15 | w/c 2 Nov hiring dip for Diwali: India 862, from 1,115. | 1,115 isn't achievable in Diwali week. |

## 5. Open points for discussion

1. **Actuals view: December hiring is 334 short of Lakshya.** Util on 21 Dec is 69.4% against Lakshya's 72.1%. Closing the gap needs hiring above cities' best weeks, or better retention.
2. **Mumbai's December pattern** (Actuals view) follows last year's uneven December: 202 → 107 → 108 → 213. It could be smoothed to a steady line with the same December total.
3. **EIP in the Actuals view** is 598 against Lakshya's 612. It could be set exactly to Lakshya if preferred.
4. **Large first-week step in the Actuals view.** Moving festival-week hires earlier makes w/c 28 Sep recruitment 1,216, against 1,002 actual in the last week (+21%). Part of it could move to w/c 12 Oct if that is too steep.
5. **The v2 sheet** still uses the older comparison layout.
