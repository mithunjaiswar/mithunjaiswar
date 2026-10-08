# Weekly CNG Supply Plan: 28 Sep to 31 Dec 2026

*Summary for review. Actuals run to Sat 26 Sep 2026. All figures are India (7 cities: Mumbai, Delhi NCR, Bangalore, Hyderabad, Chennai, Kolkata, Pune) unless a city is named.*

## 1. The sheets

| Sheet | What it is | Link |
|---|---|---|
| **Lakshya-based plan** (main) | Each month's average util equals Lakshya's month average. Attrition, cars added, cars sold and EIP match Lakshya; recruitment carries the catch-up needed for util. | [Open](https://docs.google.com/spreadsheets/d/1h314RtB8WjMOZEQTGEbR-Ly4iYUdXsnzWPUhGvpzvWI/edit) |
| **Actuals view** | What the business is likely to do: the last 8 weeks' run rate, last year's festival pattern, and Lakshya's month averages where agreed. | [Open](https://docs.google.com/spreadsheets/d/1qgLxZmiLOfBWFnmHzQrQZj10571ae8ln9Ao3q2991RI/edit) |
| **v2** | Every Own Now and L+DTO number taken from Lakshya v4 as given (reference). | [Open](https://docs.google.com/spreadsheets/d/1mYh3raKeU-taJxLsObbOfNbJpDx4wtx_2OPdJhQZjbY/edit) |

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

Month rule: a week counts in the month of its Monday. October is w/c 28 Sep – 26 Oct, November is 2 – 30 Nov and December is 7 – 31 Dec.

**Plan period:** 14 weeks, w/c 28 Sep to w/c 28 Dec. The last week has 4 days, 28 – 31 Dec, so the plan ends on Lakshya's December month-end. Monthly "a week" figures for attrition and recruitment are per full 7-day week.

**Lakshya's December, re-split.** Lakshya v4's weekly plan stops at w/e 27 Dec, and that last week is light (India 779 hires against about 1,500 the week before) because it carries the tail of December. December's placements after w/e 6 Dec are now split by days:
- w/c 7, 14 and 21 Dec: 1,068 each (7 days)
- w/c 28 Dec: 611 (4 days)

December's total is unchanged at 3,816. The split is shown as formulas on the Lakshya Source tab.

## 2. Headline numbers (India)

### Lakshya-based plan: monthly average util matches Lakshya

| Month | Util % (Lakshya / Plan) | On-road cars, month avg (Lakshya / Plan) | Attrition % a week | Recruitment a week | Recruitment total | Cars added | Cars sold | EIP net add |
|---|---|---|---|---|---|---|---|---|
| Oct | **65.1% / 65.1%** | 13,032 / 12,940 | 9.8% / 9.8% | 1,118 / 1,315 | 5,591 / 6,573 | 1,382 / 1,382 | 290 / 290 | 225 / 225 |
| Nov | **64.0% / 64.0%** | 13,393 / 13,289 | 8.5% / 8.5% | 1,082 / 830 | 5,408 / 4,152 | 918 / 918 | 253 / 253 | 225 / 225 |
| Dec | **70.6% / 70.6%** | 14,805 / 14,697 | 7.6% / 7.6% | 1,068 / 1,299 | 3,816 / 4,638 | 0 / 0 | 178 / 178 | 161 / 161 |
| **14 weeks** | 66.3% / 66.3% | 13,668 / 13,567 | 8.7% / 8.7% | 1,092 / 1,132 | **14,815 / 15,362** | 2,300 / 2,300 | 721 / 721 | 612 / 612 |

On 31 Dec, the plan is at **15,243 cars on road and 73.4% util**, against Lakshya's 15,082 and 72.1%.

How the util match works:
- **Catch-up hiring.** On top of Lakshya's monthly recruitment, the plan adds a catch-up each month, sized so each city's average util for the month equals Lakshya's.
- **October:** we start below Lakshya (util 61.2% against 63.5%). To average 65.1% over October, the plan must hire **+197 a week** and finish October above Lakshya, at 67.2%.
- **November:** that lead means hiring falls to **−252 a week**, against Lakshya's 1,082.
- **December:** hiring rises again, to **+231 a week**.
- **Overall:** recruitment over 14 weeks is 15,362, which is **547 above Lakshya**.
- **Capacity:** Bangalore, Hyderabad and Chennai go above their best week so far in 9 weeks each. These weeks are flagged on the city tabs.

On-road cars are about 100 below Lakshya each month even with util matched. Our fleet is slightly smaller than Lakshya's, so the same util gives fewer cars on road.

### Actuals view: what the run rate supports

| Month | Util % (Lakshya / Plan) | On-road cars, month avg (Lakshya / Plan) | Attrition % a week | Recruitment a week | Recruitment total | Cars added | Cars sold | EIP net add |
|---|---|---|---|---|---|---|---|---|
| Oct | 65.1% / 63.3% | 13,032 / 12,491 | 9.8% / 9.8% | 1,118 / 1,118 | 5,591 / 5,591 | 1,382 / 1,241 | 290 / 290 | 225 / 230 |
| Nov | 64.0% / 62.4% | 13,393 / 12,944 | 8.5% / 9.7% | 1,082 / 1,082 | 5,408 / 5,408 | 918 / 1,060 | 253 / 253 | 225 / 230 |
| Dec | 70.6% / 67.5% | 14,805 / 14,050 | 7.6% / 8.5% | 1,068 / 1,120 | 3,816 / 4,000 | 0 / 0 | 178 / 178 | 161 / 164 |
| **14 weeks** | 66.3% / 64.2% | 13,668 / 13,098 | 8.7% / 9.4% | 1,092 / 1,105 | 14,815 / 14,999 | 2,300 / 2,301 | 721 / 721 | 612 / 624 |

**On 31 Dec: util 69.5% and 14,436 cars on road, against Lakshya's 72.1% and 15,082.** December hiring is capped at each city's best week so far.

Where we start (last 8 weeks, actual):
- attrition 10.9% a week
- recruitment 979 a week
- util 62.7%

Last actual week (w/c 21 Sep): attrition 10.3%, recruitment 1,002, util 61.2%.

## 3. How the Actuals view is built

1. **Starting point.** It starts from the actual on 27 Sep and uses the last 8 weeks' run rate for each city.
2. **Recruitment:**
   - **October and November** use Lakshya's month average for each city.
   - **December** uses the 8-week run rate plus an extra hiring ramp towards Lakshya's 31 Dec util. The ramp is capped at each city's best week so far, so no city is asked to hire more than it ever has in a week.
3. **Attrition:**
   - **October** uses Lakshya's October average, easing down week by week.
   - **After October** it steps down from the 8-week rate to each city's best 4 weeks by 31 Dec.
4. **Seasonality.** Only two festivals are used: **Diwali** (all cities) and **Durga Puja** (Kolkata). Within a month the total stays the same; the festival only moves hires between weeks.
   - **Durga Puja / Dussehra (w/c 12 and 19 Oct) and the week before Diwali (w/c 26 Oct):** hiring dips by last year's drop for that week. The hires move into w/c 28 Sep and 5 Oct.
   - **Kolkata:** keeps its full Durga Puja pattern from last year.
   - **w/c 2 Nov:** Dhanteras to Diwali (Fri 6 – Sun 8 Nov) fall in this week this year, so it takes last year's Diwali-week hiring dip. India goes to 862, from 1,115.
   - **Attrition in w/c 2 Nov:** keeps 35% of last year's Diwali jump, which gives about 12% (the full jump would be 14.4%). The 35% is an input in Inputs A3b column P.
5. **EIP.** Uses the last 4 weeks' trend of +46 a week (624 over the plan, against Lakshya's 612).
   - EIP cars fell 241 in August, mostly Mumbai drop-offs: from 2,483 on 2 Aug to 2,242 on 30 Aug.
   - They recovered 184 in September, to 2,426 on 26 Sep.
   - Using 8 weeks would have shown −94 over 13 weeks, which is August's fall rather than the current trend.
6. **Cars added and sold.** Same as Lakshya (2,300 added, 721 sold), taking bought cars by RTO status plus Lakshya's cars still to buy.

## 4. Changes made during this review

| # | Change | Why |
|---|---|---|
| 1 | The plan follows a steady line from the last 6–8 weeks' actuals; seasonality is shown only for Diwali and Durga Puja (Kolkata). | Avoid ups and downs that aren't real. |
| 2 | Hiring capped at each city's proven best week; no 300-a-week jumps. | Only plan what is achievable. |
| 3 | The Lakshya-based plan matched Lakshya month by month on attrition, recruitment, cars added and cars sold (later changed by #18). | Month-on-month tracking against Lakshya. |
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
| 16 | Plan extended to w/c 28 Dec (4 days, to 31 Dec); Lakshya's December after w/e 6 Dec re-split by days over 7, 14, 21 and 28 Dec. | Lakshya's last week was light; the plan now ends on Lakshya's December month-end. |
| 17 | Monthly "a week" figures for attrition and recruitment are per full 7-day week. | The 4-day last week shouldn't drag December's weekly average down. |
| 18 | Lakshya-based plan: catch-up hiring each month so every city's **average util in each month equals Lakshya's month average** (Inputs A1 "Lakshya monthly util", targets in Inputs A3b Q–V). | Track util month by month, not only on the last day. |
| 19 | On-road cars added to the comparison tab: Lakshya vs Plan every week, in the 8-week box and by month (red when the plan is more than 3% off Lakshya). | See clearly whether we follow Lakshya. |

## 5. Open points for discussion

1. **Lakshya-based plan: util up and down.** Matching each month's average util means util rises to 67.2% at the end of October, dips to 63.3% in Diwali week, then climbs to 73.4% by 31 Dec. Recruitment follows the same pattern: 1,315 a week in October, 830 in November, 1,299 in December. A flatter alternative is to match each month's closing util instead, which hires more smoothly but doesn't hit the monthly averages.
2. **Lakshya-based plan: hiring above best weeks.** Bangalore, Hyderabad and Chennai must hire above their best week so far in October and December (flagged on the city tabs).
3. **Actuals view: December hiring short of Lakshya.** Util on 31 Dec is 69.5% against Lakshya's 72.1%. Closing the gap needs hiring above cities' best weeks, or better retention.
4. **Mumbai's December pattern** (Actuals view) follows last year's uneven December: 202 → 105 → 107 → 212 → 71 (the last is a 4-day week). It could be smoothed to a steady line with the same December total.
5. **Large first-week step in the Actuals view.** Moving festival-week hires earlier makes w/c 28 Sep recruitment 1,216, against 1,002 actual in the last week (+21%).
6. **The v2 sheet** still uses the older comparison layout.
