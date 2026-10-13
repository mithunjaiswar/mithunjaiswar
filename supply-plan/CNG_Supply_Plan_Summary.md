# Weekly CNG Supply Plan: 28 Sep to 27 Dec 2026

*Summary for review. Actuals run to Sat 26 Sep 2026. All figures are India (7 cities: Mumbai, Delhi NCR, Bangalore, Hyderabad, Chennai, Kolkata, Pune) unless a city is named.*

## 1. The sheets

| Sheet | What it is | Link |
|---|---|---|
| **Lakshya-based plan** (main) | Each month's average util equals Lakshya's month average. Attrition, cars added, cars sold and EIP match Lakshya; recruitment carries the catch-up needed for util. | [Open](https://docs.google.com/spreadsheets/d/1h314RtB8WjMOZEQTGEbR-Ly4iYUdXsnzWPUhGvpzvWI/edit) |
| **Actuals view** | What the business is likely to do: the last 8 weeks' run rate, last year's festival pattern, and Lakshya's month averages where agreed. | [Open](https://docs.google.com/spreadsheets/d/1qgLxZmiLOfBWFnmHzQrQZj10571ae8ln9Ao3q2991RI/edit) |
| **v2** | Every Own Now and L+DTO number taken from Lakshya v4 as given (reference). | [Open](https://docs.google.com/spreadsheets/d/1mYh3raKeU-taJxLsObbOfNbJpDx4wtx_2OPdJhQZjbY/edit) |
| **Lakshya exact, week by week** | Every week equals Lakshya v4, in the new layout, with a **Monthly Summary** tab (Lakshya, plan, actual so far and last year by month). | [Open](https://docs.google.com/spreadsheets/d/15IhNdV4Vh_ieanqEDDLc5AOH0UMwk_5-aaI6h9T6ee0/edit) |

### Source data behind the sheets

| Source | What comes from it | Where |
|---|---|---|
| **Lakshya_15000_Model_v4** | Lakshya's targets:<br>• month-end on road, fleet, Own Now and L+DTO books<br>• weekly driver placements<br>• churn rates (Churn tab)<br>• cars to buy and sell | [Open](https://docs.google.com/spreadsheets/d/1Bu8NkgNVcakYondqbyK_jW4nFuFDBqEk/edit) |
| **SSOT query** (raw_performance) | Daily actuals by city and fuel type:<br>• drivers<br>• new joins, resurrections<br>• attrition, rejoins<br>• cars on road, fleet<br>• EIP add-ons and drop-offs<br><br>Covers this year and last year (last year gives the seasonality pattern). | [Query doc](https://docs.google.com/document/d/1UIKW0voWgrUu2HDonBR4GsWdFz8XLVgWq7r5UoaYMpc/edit). The output is pasted into the **raw_performance** tab of each sheet. |
| **Everest Reporting DB** (car books) | Actual cars added and sold each week, by city (car book start and end dates). | Read-only database. The figures are typed into the comparison tab as grey history. |
| **Lakshya Source** tab (in each sheet) | Lakshya v4 figures typed exactly as given: churn inputs and weekly placements. The attrition working traces back to this tab. | Inside each sheet |
| **Inputs** tab (in each sheet) | Every assumption the plan runs on:<br>• A1 switches<br>• A2 city start and targets<br>• A3 / A3b run rates and month rates<br>• A4 month-ends<br>• A6 cars<br>• A8 calendar | Inside each sheet |
| **Builder code** | The script that builds and publishes all three sheets. | GitHub repo `mithunjaiswar/mithunjaiswar`, branch `claude/pensive-mendel-s62wy1`, folder `supply-plan/` |

**Tabs to look at in each sheet**
- **Summary View:** weekly dashboard with a city picker. Each metric shows the plan, the actual and the same week last year.
- **Lakshya vs Plan vs LY:** the main comparison tab. For every week it shows Lakshya against Plan for:
  - attrition %
  - driver recruitment
  - util %
  - on-road cars
  - cars added
  - cars sold
  - EIP net add

  Next to that are the last 8 weeks' average, a month-by-month table, a seasonality check and the attrition working. Pick a city in cell B3.
- **Inputs:** every assumption, in cream cells.
- **City tabs:** the weekly working for each city.

Month rule: a week counts in the month of its Monday. October is w/c 28 Sep – 26 Oct, November is 2 – 30 Nov and December is w/c 7 – 21 Dec.

**Plan period:** 13 weeks, w/c 28 Sep to w/c 21 Dec (ending Sun 27 Dec), the same weeks as Lakshya v4. Lakshya's December weeks are used exactly as given (1,550 / 1,487 / 779 placements in w/c 7, 14 and 21 Dec).

## 2. Headline numbers (India)

### Lakshya-based plan: monthly average util matches Lakshya

| Month | Util % (Lakshya / Plan) | On-road cars, month avg (Lakshya / Plan) | Attrition % a week | Recruitment a week | Recruitment total | Cars added | Cars sold | EIP net add |
|---|---|---|---|---|---|---|---|---|
| Oct | **65.2% / 65.2%** | 13,038 / 12,946 | 9.8% / 9.8% | 1,118 / 1,314 | 5,591 / 6,572 | 1,382 / 1,382 | 290 / 290 | 235 / 235 |
| Nov | **64.1% / 64.1%** | 13,409 / 13,305 | 8.5% / 8.5% | 1,082 / 830 | 5,408 / 4,152 | 918 / 918 | 253 / 253 | 235 / 235 |
| Dec | **71.8% / 71.8%** | 15,066 / 14,955 | 8.8% / 8.8% | 1,272 / 1,659 | 3,816 / 4,977 | 0 / 0 | 178 / 178 | 141 / 141 |
| **13 weeks** | 66.3% / 66.3% | 13,649 / 13,548 | 9.1% / 9.1% | 1,140 / 1,208 | **14,815 / 15,701** | 2,300 / 2,300 | 721 / 721 | 612 / 612 |

On 27 Dec, the plan is at **15,621 cars on road and 75.2% util**, against Lakshya's 15,082 and 72.1%.

How the util match works:
- **Catch-up hiring.** On top of Lakshya's monthly recruitment, the plan adds a catch-up each month, sized so each city's average util for the month equals Lakshya's.
- **October:** we start below Lakshya (util 61.2% against 63.5%), so the plan hires **+196 a week**.
- **November:** hiring falls to **−252 a week** against Lakshya's 1,082.
- **December:** Lakshya's December averages 71.8% over only 3 weeks, so the plan hires **+387 a week**.
- **Overall:** recruitment over 13 weeks is 15,701, which is **886 above Lakshya**.
- **Capacity:** 33 city-weeks go above the city's best week (Bangalore, Hyderabad and Chennai 8 each; Mumbai, Delhi NCR and Pune 3 each). Every city ends above its maximum util.

On-road cars are about 100 below Lakshya each month even with util matched. Our fleet is slightly smaller than Lakshya's, so the same util gives fewer cars on road.

### Actuals view: what the run rate supports

| Month | Util % (Lakshya / Plan) | On-road cars, month avg (Lakshya / Plan) | Attrition % a week | Recruitment a week | Recruitment total | Cars added | Cars sold | EIP net add |
|---|---|---|---|---|---|---|---|---|
| Oct | 65.2% / 63.3% | 13,038 / 12,490 | 9.8% / 9.8% | 1,118 / 1,118 | 5,591 / 5,591 | 1,382 / 1,241 | 290 / 290 | 235 / 230 |
| Nov | 64.1% / 62.4% | 13,409 / 12,952 | 8.5% / 9.7% | 1,082 / 1,082 | 5,408 / 5,408 | 918 / 1,060 | 253 / 253 | 235 / 230 |
| Dec | 71.8% / 67.4% | 15,066 / 14,037 | 8.8% / 8.6% | 1,272 / 1,161 | 3,816 / 3,482 | 0 / 0 | 178 / 178 | 141 / 138 |
| **13 weeks** | 66.3% / 63.9% | 13,649 / 13,025 | 9.1% / 9.4% | 1,140 / 1,114 | 14,815 / 14,481 | 2,300 / 2,301 | 721 / 721 | 612 / 598 |

**On 27 Dec: util 69.4% and 14,416 cars on road, against Lakshya's 72.1% and 15,082.** December hiring is capped at each city's best week so far.

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
5. **EIP.** Uses the last 4 weeks' trend of +46 a week (598 over the plan, against Lakshya's 612).
   - EIP cars fell 241 in August, mostly Mumbai drop-offs: from 2,483 on 2 Aug to 2,242 on 30 Aug.
   - They recovered 184 in September, to 2,426 on 26 Sep.
   - Using 8 weeks would have shown −94 over 13 weeks, which is August's fall rather than the current trend.
6. **Cars added and sold.** Same as Lakshya (2,300 added, 721 sold), taking bought cars by RTO status plus Lakshya's cars still to buy.

## 4. Changes made during this review

| # | Change | Why |
|---|---|---|
| 1 | The plan follows a steady line from the last 6–8 weeks' actuals; seasonality is shown only for Diwali and Durga Puja (Kolkata). | Avoid ups and downs that aren't real. |
| 2 | Hiring capped at each city's proven best week; no 300-a-week jumps. | Only plan what is achievable. |
| 3 | The Lakshya-based plan matched Lakshya month by month on attrition, recruitment, cars added and cars sold (later changed by #17). | Month-on-month tracking against Lakshya. |
| 4 | Hiring cap setting (Inputs A8): each city at 200 a week in w/c 16 and 23 Nov, with the excess moved into early October. | Keep weekly hiring achievable. |
| 5 | Comparison tab built: Lakshya vs Plan, the last 3 actual weeks, the last 8 weeks' average, and a block for each city. | One place to compare week by week. |
| 6 | Attrition working shown in full with formulas (no typed numbers), tracing back to Lakshya's Churn tab. | Anyone can see how attrition is calculated. |
| 7 | Cars added and sold (and EIP) shown as month and plan-period **totals**, not averages. | Lakshya plans about 2,300 cars; the total must be visible. |
| 8 | Inputs tab cleaned up; reference tabs (Read Me, Monthly Dashboard, Seasonality Check) hidden; plain-text links added. | Readability. |
| 9 | Actuals view: w/c 2 Nov attrition brought down from 14.4% to about 12%. | The full jump was too high. |
| 10 | Actuals view: October and November recruitment set to Lakshya's month average, with no extra stretch. | Recruitment in those months was too low. |
| 11 | EIP net add added to the comparison; the Actuals view's EIP now uses the last 4 weeks' trend. | EIP showed −94 against Lakshya's +612. |
| 12 | New comparison layout: Lakshya and Plan for each measure, then an 8-week box, a month-by-month table (with recruitment totals), a seasonality comment and the attrition working. Text is centred with splitter lines. Applied to the Lakshya-based plan and the Actuals view. | Easier to read and compare. |
| 13 | Summary View (Actuals view): colour scale on every row; attrition is reversed so low shows green. | Quick visual check. |
| 14 | October weeks are no longer flat: festival-week hires moved to the earlier weeks. | Plan for the Durga Puja and Diwali impact. |
| 15 | w/c 2 Nov hiring dip for Diwali: India 862, from 1,115. | 1,115 isn't achievable in Diwali week. |
| 16 | Plan extended to w/c 28 Dec as a full 7-day week (to Sun 3 Jan); Lakshya's December after w/e 6 Dec re-split evenly over w/c 7, 14, 21 and 28 Dec (954 each). | Lakshya's last week was light, and every week should be a full week. |
| 16b | December brought back to end on w/c 21 Dec, with Lakshya's December weeks exactly as given. | The plan should match Lakshya's own weeks. |
| 17 | Lakshya-based plan: catch-up hiring each month so every city's **average util in each month equals Lakshya's month average** (Inputs A1 "Lakshya monthly util", targets in Inputs A3b Q–V). | Track util month by month, not only on the last day. |
| 18 | On-road cars added to the comparison tab: Lakshya vs Plan every week, in the 8-week box and by month (red when the plan is more than 3% off Lakshya). | See clearly whether we follow Lakshya. |

## 5. Open points for discussion

1. **Lakshya-based plan: December hiring jump.** Matching December's average util (71.8% over 3 weeks) needs 1,659 hires a week in December, against Lakshya's 1,272 average (and only 779 in Lakshya's w/c 21 Dec). Util goes up and down: about 67% at the end of October, 63% in Diwali week, 75.2% on 27 Dec. A smoother alternative is to match each month's closing util instead.
2. **Lakshya-based plan: above capacity and ceiling.** 33 city-weeks are above the city's best week, and every city ends above its maximum util.
3. **Actuals view: 667 cars short of Lakshya on 27 Dec** (util 69.4% against 72.1%), mostly Hyderabad (−452).
4. **Mumbai's December pattern** (Actuals view) follows last year's uneven December. It could be smoothed with the same December total.
5. **Large first-week step in the Actuals view.** w/c 28 Sep recruitment is 1,216 against 1,002 actual in the last week (+21%).
6. **The v2 sheet** still uses the older comparison layout.
