# Weekly CNG Supply Plan: Full Documentation

**Plan period:** 14 weeks, w/c 28 Sep 2026 to w/c 28 Dec 2026 (the last week ends Sun 3 Jan 2027).
**Actuals loaded up to:** Sat 26 Sep 2026. The opening position is Sun 27 Sep 2026.
**Cities:** Mumbai, Delhi NCR, Bangalore, Hyderabad, Chennai, Kolkata, Pune. India is the sum of these seven cities.
**Fuel:** CNG only.

This file records every rule, input, number and decision behind the three plan sheets. All figures were read from the live sheets after the last update.

---

## Contents

1. [Links](#1-links)
2. [Definitions](#2-definitions)
3. [Plan period and calendar](#3-plan-period-and-calendar)
4. [Source data](#4-source-data)
5. [The three sheets at a glance](#5-the-three-sheets-at-a-glance)
6. [Lakshya-based plan: how every number is built](#6-lakshya-based-plan-how-every-number-is-built)
7. [Actuals view: how every number is built](#7-actuals-view-how-every-number-is-built)
8. [v2 (everything = Lakshya)](#8-v2-everything--lakshya)
9. [Lakshya's December re-split](#9-lakshyas-december-re-split)
10. [Inputs tab, section by section (with the current values)](#10-inputs-tab-section-by-section-with-the-current-values)
11. [The comparison tab: Lakshya vs Plan vs LY](#11-the-comparison-tab-lakshya-vs-plan-vs-ly)
12. [Every other tab](#12-every-other-tab)
13. [Results: India and every city](#13-results-india-and-every-city)
14. [Key findings](#14-key-findings)
15. [Complete change log](#15-complete-change-log)
16. [Open points](#16-open-points)
17. [How the sheets are built and published](#17-how-the-sheets-are-built-and-published)

---

## 1. Links

| What | Link |
|---|---|
| **Lakshya-based plan** (main sheet) | https://docs.google.com/spreadsheets/d/1h314RtB8WjMOZEQTGEbR-Ly4iYUdXsnzWPUhGvpzvWI/edit |
| **Actuals view** | https://docs.google.com/spreadsheets/d/1qgLxZmiLOfBWFnmHzQrQZj10571ae8ln9Ao3q2991RI/edit |
| **v2 – everything = Lakshya** (reference) | https://docs.google.com/spreadsheets/d/1mYh3raKeU-taJxLsObbOfNbJpDx4wtx_2OPdJhQZjbY/edit |
| Lakshya_15000_Model_v4 (source of targets) | https://docs.google.com/spreadsheets/d/1Bu8NkgNVcakYondqbyK_jW4nFuFDBqEk/edit |
| SSOT query (raw data) | https://docs.google.com/document/d/1UIKW0voWgrUu2HDonBR4GsWdFz8XLVgWq7r5UoaYMpc/edit |
| Builder code | GitHub repo `mithunjaiswar/mithunjaiswar`, branch `claude/pensive-mendel-s62wy1`, folder `supply-plan/` |

The same links appear as plain text (no HYPERLINK formulas) in cells K1:P2 of each sheet's comparison tab.

---

## 2. Definitions

| Term | Meaning |
|---|---|
| **w/c** | "Week commencing": the Monday a week starts on. Every week runs Monday to Sunday. |
| **Attrition % (net attrition)** | Drivers leaving in the week (attrition + temp attrition − rejoins − temp rejoins) ÷ drivers at the start of the week (Monday). The same formula is used for Lakshya, the plan, actuals and last year. |
| **Recruitment (driver acquisition)** | New joins + resurrections in the week. Lakshya's figure is its weekly placements (L+DTO + Own Now). |
| **Util %** | Cars on road ÷ total cars (fleet) at the end of the week (Sunday). |
| **On-road cars** | Cars allotted to a driver at the end of the week. On road = EIP + Leasing/DTO + Own Now. |
| **Fleet** | Total CNG cars, including idle ones. Fleet changes only by cars added and cars sold. |
| **EIP** | Investor-owned cars. "EIP net add" = EIP cars joining minus EIP cars leaving in a week (raw field "Net EIP Add-ons"). These are cars, not drivers. |
| **Own Now** | Cars on the Own Now product. Own Now driver acquisition covers drivers for new cars plus drivers for existing cars. |
| **L+DTO** | Leasing + DTO cars on road. It is the remainder: on road − EIP − Own Now. |
| **Run rate** | The average of the last 8 actual weeks (w/c 3 Aug – w/c 21 Sep; the last week has 6 days loaded and is scaled to 7). |
| **Proven capacity** | A city's best 4-week average of driver acquisition since Sep 2025 (Inputs A3, column K). Weeks above it are flagged "Above capacity". |
| **Catch-up hiring** | Extra recruitment on top of Lakshya's base recruitment, so that each month's average util equals Lakshya's (Lakshya-based plan only). |
| **Month rule ("match month")** | A week counts in the month its Monday falls in, except w/c 28 Sep, which counts as October because the plan starts there. October = w/c 28 Sep – 26 Oct (5 weeks); November = w/c 2 – 30 Nov (5 weeks); December = w/c 7 – 28 Dec (4 weeks). This rule is used for all month averages and month totals. |
| **Lakshya month** | The month each week rolls up to in Lakshya's own model (by the Sunday it ends on). Oct = w/e 4 – 25 Oct (4 weeks); Nov = w/e 1 – 29 Nov (5 weeks); Dec = w/e 6 Dec – 3 Jan (5 weeks). It is used only to spread Lakshya's monthly churn, sales and new cars over weeks. |
| **LY** | Last year. "Same week last year" = 364 days earlier. The **Diwali-aligned** pattern uses 385 days earlier, which lines up Bhai Dooj week (w/c 9 Nov 2026 ↔ w/c 20 Oct 2025) and Durga Puja. |
| **Grey-blue cells** | Actual weeks. **Cream cells** are inputs you may change. **Grey cells** are history and reference. **Light-blue cells** are totals. |

---

## 3. Plan period and calendar

- **Opening date:** Sun 27 Sep 2026, the last actual Sunday. The plan starts from the actual position on this date.
- **First plan week:** w/c Mon 28 Sep (the current week).
- **Plan end:** Sun 3 Jan 2027 (the end of w/c 28 Dec). Every week has the full 7 days. There are 98 days in plan.
- **Lakshya's December targets** (its 31 Dec month-end) are compared with the plan at the end of w/c 28 Dec.

| # | Week (w/c) | Ends | Match month | Lakshya month | Share of Lakshya's month | Festival | Events |
|---|---|---|---|---|---|---|---|
| 1 | 28 Sep | 4 Oct | Oct | Oct | 25.0% | – | Gandhi Jayanti (Fri 2 Oct) |
| 2 | 5 Oct | 11 Oct | Oct | Oct | 25.0% | – | – |
| 3 | 12 Oct | 18 Oct | Oct | Oct | 25.0% | Durga Puja (Kolkata only) | – |
| 4 | 19 Oct | 25 Oct | Oct | Oct | 25.0% | Durga Puja (Kolkata only) | Dussehra (Tue 20 Oct) |
| 5 | 26 Oct | 1 Nov | Oct | Nov | 20.0% | – | Bangalore: Kannada Rajyotsava (Sun 1 Nov) |
| 6 | 2 Nov | 8 Nov | Nov | Nov | 20.0% | Diwali | Diwali (Sun 8 Nov) |
| 7 | 9 Nov | 15 Nov | Nov | Nov | 20.0% | Diwali | Bali Pratipada, Bhai Dooj; Hyderabad: GHMC election (Sun 15 Nov) |
| 8 | 16 Nov | 22 Nov | Nov | Nov | 20.0% | – | – |
| 9 | 23 Nov | 29 Nov | Nov | Nov | 20.0% | – | Guru Nanak Jayanti (Tue 24 Nov) |
| 10 | 30 Nov | 6 Dec | Nov | Dec | 25.0% | – | – |
| 11 | 7 Dec | 13 Dec | Dec | Dec | 18.75% | – | – |
| 12 | 14 Dec | 20 Dec | Dec | Dec | 18.75% | – | Kolkata: KMC election (Tue 15 Dec) |
| 13 | 21 Dec | 27 Dec | Dec | Dec | 18.75% | – | Christmas (Fri 25 Dec) |
| 14 | 28 Dec | 3 Jan | Dec | Dec | 18.75% | – | New Year (Fri 1 Jan); last plan week |

- **How the "share of Lakshya's month" is set:**
  - Lakshya spreads a month evenly over its weeks: October 1/4 each, November 1/5 each.
  - In December, w/e 6 Dec keeps Lakshya's quarter (25%). The remaining 75% is split by days over w/c 7, 14, 21 and 28 Dec, so 18.75% each.
  - These shares spread Lakshya's monthly churn, cars sold and cars still to buy over the weeks.
- **Hiring cap setting** (Inputs A8, columns O–P):
  - The cap column is blank, so no cap applies.
  - In the Lakshya-based plan, weeks 1–3 are marked "Yes". That means they would take any hires cut by a cap.
  - The cap only works with the "Lakshya" December-target option, which is not currently in use.

---

## 4. Source data

| Source | What comes from it | Where it lives |
|---|---|---|
| **Lakshya_15000_Model_v4** | Month-end targets (on road, fleet, Own Now and L+DTO books), weekly placements (Weekly L+DTO and Weekly Own Now tabs), churn rates (Churn tab / Inputs B73–B79), Own Now churn and rollover by month, new cars (2,300) and cars sold (721) | Typed as given on each sheet's **Lakshya Source** tab (grey) and Inputs A2/A4/A6/A7 |
| **SSOT query** (raw_performance) | Daily actuals by city and fuel type, this year and last year. Fields: fleet, on road (allotted cars), EIP vehicles, Own Now cars, new joins, resurrections, attrition, temp attrition, rejoins, temp rejoins, active partners (Monday), EIP add-ons and drop-offs, channel splits. | Pasted into the **raw_performance** tab of each sheet. Every actual and last-year figure is a SUMIFS on it. |
| **Everest Reporting DB** (read-only) | Weekly history Jan 2024 – Sep 2026 by city (`plan_history.py`): seasonal changes, Diwali-aligned series, proven capacity, 12-week attrition trend. Car books for actual cars added and sold (`car_flows.py`). Last year's Diwali-aligned weekly pattern (`ly_pattern.py`). | Typed as history (grey). The last-year cars for Aug 2025 could not be pulled (DB timeouts), so those are blank. |
| **New Car Stock Report, 27 Sep** | 582 cars bought and in the stock yard, by RTO status and city | Inputs A6 |
| **AOP FY27** | Month-end on road, EIP and driver recruitment, Sep–Dec | Inputs A5 (reference only) |

---

## 5. The three sheets at a glance

| | Lakshya-based plan | Actuals view | v2 |
|---|---|---|---|
| **Purpose** | Follow Lakshya month by month, with **each month's average util equal to Lakshya's** | What the business can realistically do from today's run rate | Lakshya's own numbers run through the same engine (reference) |
| **Inputs A1 "December target"** | `Lakshya monthly util` | `Capacity` | – (overridden) |
| **Starting point** | Actual on 27 Sep | Actual on 27 Sep | Lakshya's own 27 Sep book and fleet |
| **Base recruitment** | Lakshya's month average (per full week) × festival shape | Oct and Nov: Lakshya's month average × last year's shape; Dec: 8-week run rate × last year's shape | Lakshya's weekly placements as given (Dec re-split) |
| **Extra recruitment** | Monthly catch-up for util | December only: a ramp capped at each city's best week | None |
| **Attrition** | Lakshya's month average × festival shape | Oct: Lakshya's average × an easing line; Nov–Dec: 8-week rate stepping down to the best 4 weeks × last year's shape | Lakshya's monthly churn × weekly share |
| **EIP** | Straight line to Lakshya's December EIP | Last 4 weeks' trend | Straight line to Lakshya's December EIP |
| **Cars added / sold** | Lakshya (2,300 / 721) | Lakshya (2,300 / 721) | Lakshya |
| **Comparison tab layout** | New (Lakshya / Plan, 8-week box, month box, on-road cars) | New (same) | Older layout (with last year and month averages per measure) |
| **Summary View colour scale** | Util, Recruitment and Net Attrition % (plan and LY rows) | Every row of every block (attrition reversed: low = green) | As the Lakshya-based plan |

---

## 6. Lakshya-based plan: how every number is built

Steps 1–9 are calculated on each city tab, one row per week. India is the sum of the city tabs.

1. **Start.** The actual books on Sun 27 Sep are the opening position (A2): fleet, on road, EIP, Own Now and L+DTO.
2. **Base recruitment** (city tab BK):
   - Each week = Lakshya's month average for the match month (A3b K–M), per full 7-day week.
   - That is multiplied by the festival shape, normalised so the month still averages Lakshya: (1 + hiring festival change) ÷ the month's average of (1 + change).
   - The festival changes come from the Seasonality Check tab, section 1:

     | City | Diwali hiring | Diwali attrition | Durga Puja hiring | Durga Puja attrition |
     |---|---|---|---|---|
     | Mumbai | −20% | +20% | 0% | 0% |
     | Delhi NCR | −43% | +13% | 0% | 0% |
     | Bangalore | −22% | +11% | 0% | 0% |
     | Hyderabad | −7% | +18% | 0% | 0% |
     | Chennai | −11% | +64% | 0% | 0% |
     | Kolkata | −23% | −23% | −29% | +9% |
     | Pune | −19% | +41% | 0% | 0% |

   - **Which weeks the dips apply to:** Diwali applies to w/c 2 and 9 Nov in every city. Durga Puja applies to w/c 12 and 19 Oct in Kolkata only, with each week taking half of the one-week dip (Saptami Sat 17 Oct – Dashami Tue 20 Oct falls across both weeks).
   - **When a change is used:** only if it showed up in both 2024 and 2025 and is at least 5% (Inputs A1 "Seasonal change: minimum in both years").
   - **No other seasonality:** every other week has none.
3. **Net attrition rate** (BR):
   - Each week = Lakshya's month average for the match month (A3b E–G), per full week.
   - That is multiplied by the attrition festival shape, normalised the same way as recruitment.
   - Drivers leaving = (Own Now + L+DTO book at the start of the week) × rate × days ÷ 7.
4. **Catch-up hiring for util** (BL, used when A1 = "Lakshya monthly util"):
   - **The amount:** for each city and month there is one catch-up number a week (city tab, column BL, three rows under the totals: Oct, Nov, Dec). It is multiplied by the festival shape.
   - **How it's solved:** the number is chosen so that the **average of the month's weekly util = Lakshya's month-average util** (A3b T–V, default = Lakshya's own month average, A3b Q–S).
   - **The formula:** catch-up = (weeks in month × target util − Σ(util without this month's catch-up, including earlier months' catch-up still driving)) ÷ Σ(util added by one extra hire a week this month).
   - **Driver survival:** a hire made in week *k* is still driving in week *t* with the share CO(t) ÷ CO(k), where CO is the running product of (1 − weekly attrition rate).
   - **Order:** the months are solved in order, Oct → Nov → Dec, and each month allows for the earlier months' catch-up still on the road.
   - **Helper columns** on the city tab:
     - CO: share kept since 28 Sep
     - CP: shape
     - CQ: this month's catch-up so far ÷ share kept
     - CR: earlier months' catch-up ÷ share kept
     - CS: catch-up hires this week
     - CT: util target
     - CU: on road without catch-up = the run-rate path BS + the opening offset
   - **Current catch-up values, hires a week:**

     | City | Oct | Nov | Dec |
     |---|---|---|---|
     | Mumbai | +37.3 | −53.0 | +45.6 |
     | Delhi NCR | +14.6 | −30.8 | +18.9 |
     | Bangalore | +32.9 | −62.0 | +41.4 |
     | Hyderabad | +59.5 | −60.5 | +62.6 |
     | Chennai | +38.0 | −35.7 | +29.7 |
     | Kolkata | −2.5 | −8.6 | +10.9 |
     | Pune | +16.2 | −21.1 | +14.3 |
     | **India (net)** | **+197** | **−252** | **+223** |

   - **Why the catch-up goes up, down, up:** we start below Lakshya, at 61.2% util against 63.5%. To average 65.1% in October, util has to end October above Lakshya. November then needs fewer hires, and December more.
5. **Total recruitment** (AU) = base + catch-up. It is split into Own Now (drivers for new cars + existing-car trend) and L+DTO (the rest).
   - The channel mix (FSE, vendor, referrals, performance marketing) comes from the AOP mix in A2.
6. **New cars** (AD), all of Lakshya's 2,300:
   - **The 582 cars already bought** are phased by RTO status:

     | Status | Weeks | Cars |
     |---|---|---|
     | Ready for delivery | 1–2 | 209 |
     | Registration done | 2–3 | 12 |
     | Under RTO | 3–6 | 259 |
     | RTO not started | 5–8 | 102 |

   - **The 1,719 cars still to buy** land in Lakshya's months: 571 in Oct, 1,148 in Nov, 0 in Dec. They are spread by the week's share of Lakshya's month.
   - Weekly India arrivals are 288 a week in w/c 28 Sep – 19 Oct, 230 a week in w/c 26 Oct – 23 Nov, and 0 from w/c 30 Nov.
   - **Drivers for new cars:** each new car gets a driver the week after it lands. That driver comes out of the week's recruitment; it is not added on top.
   - **Flag:** a car ordered now reaches the road at least 5 weeks later. Inputs A6 shows the order-by dates for each city's cars that are not bought yet.
7. **Cars sold** (AE): Lakshya's 721 (Oct 242, Nov 242, Dec 237), spread by the week's share of Lakshya's month. Sold cars come out of idle cars, so they lower the fleet, not cars on road.
8. **EIP** (AG): a straight line from today's actual (2,426) to Lakshya's December EIP (3,038), spread by days. That is +43.7 a week for India and 612 over the plan.
9. **Own Now existing-car trend:** each city's 8-week Own Now change (A3 column J; India +43.5 a week).
10. **Checks shown on each city tab:**
    - **Capacity:** driver acquisition against proven capacity ("Above capacity" in red).
    - **Ceiling:** util against Lakshya's maximum utilisation ("Util headroom" below 0 in red).
    - **Gap:** the gap to Lakshya's month-end targets.
    - **Arithmetic check:** on road = EIP + L+DTO + Own Now. It must be 0; it shows red if not.
11. **Other December-target options** (Inputs A1 drop-down):
    - `Lakshya`: one steady ramp so util on the last day equals Lakshya's.
    - `Capacity`: the same ramp, but never above each city's best week.
    - `Run rate`: no extra hiring.

---

## 7. Actuals view: how every number is built

1. **Start:** the same actual position as the Lakshya-based plan on 27 Sep.
2. **Run rate:** the 8-week averages in A3. For India that is recruitment 979 a week, attrition 10.9% a week and EIP (last 4 weeks) +46 a week.
3. **Last year's pattern** (`ly_pattern.py`):
   - **How the index is built:** for each plan week, the same week 385 days earlier (Diwali-aligned) is divided by last year's average of the 8 weeks before the plan.
   - **Index columns:** recruitment index (city tab CL) and attrition index (CM).
   - **w/c 28 Dec** maps to w/c 8 Dec 2025.
4. **Before Diwali (w/c 28 Sep – 26 Oct):**
   - **Kolkata** keeps its full last-year pattern (Durga Puja).
   - **Other cities:** hiring is flat except in the Durga Puja / Dussehra weeks (w/c 12 and 19 Oct) and the week before Diwali (w/c 26 Oct). Those weeks dip by the city's or India's last-year dip, whichever is bigger (India: −2%, −13%, −6%). The hires lost move into the earlier weeks; the month stays on Lakshya's average.
   - **Attrition** keeps an easing line (no festival rise outside Kolkata).
5. **Recruitment:**
   - **October and November:** Lakshya's month average × last year's shape within the month.
   - **w/c 2 Nov:** Dhanteras – Diwali (Fri 6 – Sun 8 Nov) fall inside this week this year, so it takes last year's Diwali-week dip, the lower of last year's two Diwali weeks. India goes to 862 instead of 1,115.
   - **December:** the 8-week run rate × last year's shape, plus an extra ramp that is **December only** and **capped at each city's best week**. The ramp is solved toward Lakshya's last-day util but cannot go above capacity.
6. **Attrition:**
   - **October:** Lakshya's October average × an easing line × the festival pattern (Kolkata only).
   - **After October:** the 8-week rate steps down in a straight line to each city's best 4 weeks of the last 12 (A3b N–O) by the end of the plan. It never goes above that line, except in festival weeks.
   - **w/c 2 Nov:** keeps **35%** of last year's Diwali-week attrition jump (A3b column P). India comes out at about 12% instead of 14.4%.
7. **EIP:** the last 4 weeks' trend (30 Aug – 26 Sep), not the 8 weeks.
   - **Why:** August included Mumbai drop-offs. EIP cars fell from 2,483 (2 Aug) to 2,242 (30 Aug), then recovered to 2,426 (26 Sep).
   - **By city, a week:** Mumbai +26.0, Delhi −3.0, Bangalore +20.5, Hyderabad −2.8, Chennai +9.0, Kolkata −1.8, Pune −2.0. India +46.0.
8. **Cars:** the same 2,300 added and 721 sold as Lakshya, so util compares like for like.

---

## 8. v2 (everything = Lakshya)

- **What it takes from Lakshya v4:**
  - Every Own Now and L+DTO number: weekly placements as given, with December re-split.
  - Churn and rollover by Lakshya month × the week's share.
  - It starts from Lakshya's own 27 Sep book and fleet.
- **Lakshya Weekly tab:** shows the weekly placements, the churn by month and the start gap against actual.
- **Comparison tab:** keeps the older layout (Lakshya, plan, last year, last 8 weeks, month averages per measure).
- **Where the "Lakshya" figures come from:** the main and Actuals comparison tabs take their "Lakshya" weekly figures (`lakshya_cmp.py`) from v2's engine output. That is how Lakshya's weekly on road, fleet, book and util are produced.

---

## 9. Lakshya's December re-split

- **The problem:** Lakshya v4's weekly plan stops at w/e 27 Dec, and its last week is light. India has 779 placements that week against 1,487 the week before, because the week carries the tail of December.
- **What the plan does:** it runs to w/c 28 Dec. Lakshya's December placements after w/e 6 Dec (w/e 13, 20 and 27 Dec as given: 1,550 + 1,487 + 779 = 3,816) are split evenly over w/c 7, 14, 21 and 28 Dec: **954 each**.
- **December's total is unchanged.** Lakshya still lands on 15,082 cars on road and 72.1% util at the end.
- **Where to see it:** the Lakshya Source tab shows Lakshya's weeks as given (grey, on the right) and the split as formulas: given total × days in plan ÷ days in w/c 7–28 Dec.
- **Churn and cars sold** in December use the same weekly shares: w/e 6 Dec 25%, then 18.75% a week.
- **Week length:** every week, including w/c 28 Dec, is a full 7-day week.

---

## 10. Inputs tab, section by section (with the current values)

**Colour key:** cream = you can change; grey-blue = actual; white = formula; grey = history; light blue = total or output.

### A1 – Plan dates and switches

| Setting | Lakshya-based plan | Actuals view |
|---|---|---|
| Opening date (last actual Sunday) | 27 Sep | 27 Sep |
| First plan week starts (Monday) | 28 Sep | 28 Sep |
| Plan ends (Sunday) | 3 Jan | 3 Jan |
| Weeks per month | 4.33 (= 52 ÷ 12) | 4.33 |
| India CNG on-road goal, Dec | 15,000 (Lakshya's cities add to 15,082) | 15,000 |
| Actuals used up to | 26 Sep | 26 Sep |
| December target | **Lakshya monthly util** | **Capacity** |
| Seasonal change: minimum in both years | 5% | 5% |

### A2 – City start and December targets (start = actual, 27 Sep)

| City | Fleet | On road | EIP | Own Now | L+DTO | Lakshya Dec EIP | Lakshya Dec Own Now | Lakshya Dec L+DTO | **Lakshya Dec on road** | L+DTO churn / month | Own Now churn | Own Now rollover | New-car share | **Max util** | Lakshya fleet Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Mumbai | 4,171 | 2,649 | 1,021 | 510 | 1,118 | 1,150 | 1,006 | 1,225 | 3,381 | 58% | 7.1% | 3.1% | 51.1% | 75.0% | 4,508 |
| Delhi NCR | 4,179 | 2,231 | 63 | 710 | 1,458 | 83 | 850 | 1,535 | 2,468 | 49% | 9.4% | 0.0% | 10.1% | 62.0% | 3,981 |
| Bangalore | 2,879 | 1,929 | 352 | 674 | 903 | 493 | 1,075 | 1,201 | 2,769 | 54% | 9.9% | 0.0% | 59.8% | 79.5% | 3,599 |
| Hyderabad | 2,584 | 1,641 | 416 | 303 | 922 | 604 | 700 | 1,112 | 2,416 | 65% | 3.9% | 6.6% | 55.6% | 79.5% | 3,143 |
| Chennai | 2,556 | 1,752 | 467 | 421 | 864 | 577 | 725 | 1,004 | 2,306 | 56% | 10.1% | 0.0% | 68.2% | 79.5% | 2,972 |
| Kolkata | 1,085 | 546 | 47 | 210 | 289 | 61 | 305 | 233 | 599 | 73% | 9.4% | 0.0% | 0.0% | 60.0% | 1,046 |
| Pune | 1,730 | 985 | 60 | 278 | 647 | 70 | 442 | 631 | 1,143 | 68% | 9.8% | 0.0% | 28.6% | 70.0% | 1,664 |
| **India** | **19,184** | **11,733** | **2,426** | **3,106** | **6,201** | **3,038** | **5,103** | **6,941** | **15,082** | | | | | | **20,913** |

Recruitment channel mix (AOP), by share of recruitment:

| City | FSE | Vendor | Referrals | Performance marketing |
|---|---|---|---|---|
| Mumbai | 0.0% | 26.4% | 9.5% | 64.1% |
| Delhi NCR | 32.1% | 19.2% | 8.6% | 40.1% |
| Bangalore | 1.0% | 27.7% | 13.2% | 58.1% |
| Hyderabad | 3.5% | 37.0% | 9.0% | 50.5% |
| Chennai | 0.0% | 44.8% | 9.5% | 45.7% |
| Kolkata | 0.0% | 33.9% | 7.9% | 58.2% |
| Pune | 0.0% | 37.0% | 15.0% | 48.0% |

### A3 – Current run rate (last 8 weeks, w/c 3 Aug – Sat 26 Sep, against the same weeks last year)

| City | Recruitment a week | Same weeks LY | YoY | Drivers leaving a week | Attrition rate (this year) | Attrition rate (LY) | YoY | EIP change a week (8 wks) | Own Now change a week | **Proven capacity** (best 4 wks) | Since | EIP used: Lakshya plan / Actuals view |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Mumbai | 159 | 240 | −34% | 186 | 10.1% | 12.8% | −21% | −9.5 | +1.7 | 250 | 1 Jun 26 | +9.2 / +26.0 |
| Delhi NCR | 192 | 199 | −3% | 211 | 9.5% | 9.4% | +1% | −1.0 | +7.1 | 246 | 1 Jun 26 | +1.4 / −3.0 |
| Bangalore | 142 | 195 | −27% | 166 | 9.4% | 11.1% | −15% | +2.8 | +13.2 | 194 | 15 Jun 26 | +10.1 / +20.5 |
| Hyderabad | 158 | 193 | −18% | 187 | 13.4% | 14.2% | −5% | −0.4 | +7.6 | 213 | 4 May 26 | +13.4 / −2.8 |
| Chennai | 135 | 154 | −12% | 150 | 10.5% | 11.9% | −12% | +3.2 | +6.4 | 178 | 27 Oct 25 | +7.9 / +9.0 |
| Kolkata | 70 | 79 | −11% | 76 | 14.8% | 18.8% | −21% | −1.3 | +3.1 | 96 | 25 May 26 | +1.0 / −1.8 |
| Pune | 123 | 114 | +7% | 131 | 13.5% | 13.6% | −1% | −1.0 | +4.5 | 146 | 25 May 26 | +0.7 / −2.0 |
| **India** | **979** | 1,174 | −17% | 1,107 | **10.9%** | 12.2% | −11% | −7.3 | +43.5 | 1,323 | | +43.7 / +46.0 |

### A3b – Plan rates by month (a full 7-day week; match month)

| City | Lakshya attrition Oct / Nov / Dec | Lakshya recruitment Oct / Nov / Dec | Best 4 weeks attrition (Actuals end point) | **Lakshya util month avg Oct / Nov / Dec** (= plan target) |
|---|---|---|---|---|
| Mumbai | 9.8% / 8.4% / 6.5% | 208 / 201 / 176 | 9.6% | 67.4% / 67.0% / 73.3% |
| Delhi NCR | 8.5% / 7.7% / 6.3% | 195 / 186 / 170 | 9.2% | 55.8% / 55.8% / 60.8% |
| Bangalore | 8.5% / 7.4% / 5.9% | 187 / 187 / 165 | 8.3% | 70.6% / 68.1% / 74.9% |
| Hyderabad | 11.9% / 10.3% / 7.9% | 198 / 193 / 169 | 12.8% | 70.0% / 66.7% / 74.6% |
| Chennai | 9.5% / 8.3% / 6.6% | 156 / 155 / 136 | 9.2% | 72.2% / 69.3% / 75.7% |
| Kolkata | 10.7% / 9.0% / 7.0% | 56 / 49 / 42 | 14.3% | 51.5% / 51.5% / 56.2% |
| Pune | 11.8% / 10.3% / 8.1% | 119 / 110 / 96 | 12.8% | 61.3% / 60.3% / 67.1% |
| **India** | **9.8% / 8.5% / 6.8%** | **1,118 / 1,082 / 954** | 10.2% | **65.1% / 63.9% / 70.4%** |

- **Plan columns:** E–G (attrition used) and K–M (base recruitment used) are cream and equal Lakshya by default. T–V (util target) is cream and equals Q–S (Lakshya).
- **Actuals view, column P:** 35% of last year's Diwali attrition jump kept in w/c 2 Nov (every city).

### A4 – Lakshya month-end targets (27 Sep, 25 Oct, 29 Nov, Dec)

| City | EIP (straight line) Sep / Oct / Nov / Dec | Own Now Sep / Oct / Nov / Dec | L+DTO Sep / Oct / Nov / Dec | On road Sep / Oct / Nov / Dec |
|---|---|---|---|---|
| Mumbai | 1,021 / 1,058 / 1,104 / 1,150 | 549 / 711 / 869 / 1,006 | 1,179 / 1,183 / 1,152 / 1,225 | 2,749 / 2,952 / 3,125 / 3,381 |
| Delhi NCR | 63 / 69 / 76 / 83 | 688 / 757 / 804 / 850 | 1,488 / 1,489 / 1,446 / 1,535 | 2,239 / 2,315 / 2,326 / 2,468 |
| Bangalore | 352 / 392 / 443 / 493 | 687 / 824 / 961 / 1,075 | 1,080 / 1,110 / 1,109 / 1,201 | 2,119 / 2,326 / 2,513 / 2,769 |
| Hyderabad | 416 / 470 / 537 / 604 | 314 / 448 / 582 / 700 | 1,054 / 1,063 / 1,041 / 1,112 | 1,784 / 1,981 / 2,160 / 2,416 |
| Chennai | 467 / 498 / 538 / 577 | 438 / 537 / 641 / 725 | 925 / 943 / 933 / 1,004 | 1,830 / 1,978 / 2,112 / 2,306 |
| Kolkata | 47 / 51 / 56 / 61 | 205 / 245 / 274 / 305 | 283 / 264 / 235 / 233 | 535 / 560 / 565 / 599 |
| Pune | 60 / 63 / 66 / 70 | 287 / 345 / 395 / 442 | 678 / 656 / 612 / 631 | 1,025 / 1,064 / 1,073 / 1,143 |
| **India** | 2,426 / 2,601 / 2,819 / 3,038 | 3,168 / 3,867 / 4,526 / 5,103 | 6,687 / 6,708 / 6,528 / 6,941 | **12,281 / 13,176 / 13,873 / 15,082** |

Lakshya has no monthly EIP, so EIP is a straight line (by days) from the actual to its December target.

### A5 – AOP FY27 month-ends (reference)

| City | On road Sep / Oct / Nov / Dec | EIP Sep / Oct / Nov / Dec | Recruitment Sep / Oct / Nov / Dec |
|---|---|---|---|
| Mumbai | 2,935 / 2,628 / 2,785 / 3,116 | 1,029 / 929 / 1,029 / 1,099 | 1,212 / 772 / 681 / 1,015 |
| Delhi NCR | 2,584 / 2,417 / 2,572 / 2,845 | 82 / 65 / 64 / 82 | 831 / 676 / 807 / 1,021 |
| Bangalore | 2,231 / 2,112 / 2,105 / 2,468 | 391 / 341 / 291 / 321 | 803 / 763 / 716 / 868 |
| Hyderabad | 1,918 / 1,871 / 2,036 / 2,215 | 312 / 306 / 340 / 333 | 898 / 825 / 881 / 916 |
| Chennai | 2,065 / 2,112 / 2,112 / 2,163 | 446 / 420 / 457 / 458 | 687 / 841 / 689 / 698 |
| Kolkata | 793 / 711 / 770 / 815 | 81 / 71 / 78 / 88 | 320 / 264 / 297 / 313 |
| Pune | 1,069 / 1,002 / 1,066 / 1,196 | 60 / 64 / 64 / 72 | 535 / 453 / 506 / 598 |
| **India** | 13,595 / 12,853 / 13,446 / **14,818** | 2,401 / 2,196 / 2,323 / 2,453 | 5,286 / 4,594 / 4,577 / 5,429 |

### A6 – New cars

Bought and in stock (New Car Stock Report, 27 Sep):

| City | RTO not started | Under RTO | Registration done | Ready for delivery | **Total bought** | Lakshya Sep–Oct | Lakshya Nov | **Lakshya total** | Still to buy: Oct / Nov | Total still to buy |
|---|---|---|---|---|---|---|---|---|---|---|
| Mumbai | 0 | 0 | 0 | 8 | 8 | 234 | 233 | 467 | 226 / 233 | 459 |
| Delhi NCR | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 / 0 | 0 |
| Bangalore | 102 | 0 | 12 | 50 | 164 | 317 | 316 | 633 | 153 / 316 | 469 |
| Hyderabad | 0 | 56 | 0 | 125 | 181 | 317 | 316 | 633 | 136 / 316 | 452 |
| Chennai | 0 | 203 | 0 | 0 | 203 | 242 | 241 | 483 | 39 / 241 | 280 |
| Kolkata | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 |
| Pune | 0 | 0 | 0 | 25 | 25 | 42 | 42 | 84 | 17 / 42 | 59 |
| **India** | 102 | 259 | 12 | 209 | **582** | 1,152 | 1,148 | **2,300** | 571 / 1,148 | **1,719** |

Cars reaching the fleet each week (India): 288 a week in w/c 28 Sep – 19 Oct; 230 a week in w/c 26 Oct – 23 Nov; 0 from w/c 30 Nov. City split: Mumbai 59/47, Bangalore 79/63, Hyderabad 79/63, Chennai 61/48, Pune 11/8, Delhi and Kolkata 0.

### A7 – Cars sold (Lakshya: 721)

| City | Oct | Nov | Dec | Total |
|---|---|---|---|---|
| Mumbai | 50 | 50 | 51 | 151 |
| Delhi NCR | 70 | 70 | 69 | 209 |
| Bangalore / Hyderabad / Chennai / Kolkata | 17 | 17 | 16 | 50 each |
| Pune | 54 | 54 | 53 | 161 |
| **India** | 242 | 242 | 237 | **721** |

### A8 – Weekly calendar

See [section 3](#3-plan-period-and-calendar).

Columns:
- week #, start, end, month, days in plan
- festival
- events by city
- Lakshya month-end it counts to
- hiring cap and the weeks that take the hires cut
- match month
- share of Lakshya's month

### C1 – Plan summary by city (end of w/c 28 Dec)

**Lakshya-based plan:**

| City | On road at start | **On road (plan)** | Lakshya | Plan − Lakshya | AOP Dec | Fleet | **Util** | Max util | Headroom | Recruitment (14 wks) | Peak week | Capacity | Weeks above capacity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Mumbai | 2,649 | 3,433 | 3,381 | +52 | 3,116 | 4,487 | 76.5% | 75.0% | **−1.5%** | 2,875 | 245 | 250 | 0 |
| Delhi NCR | 2,231 | 2,489 | 2,468 | +21 | 2,845 | 3,970 | 62.7% | 62.0% | **−0.7%** | 2,609 | 210 | 246 | 0 |
| Bangalore | 1,929 | 2,735 | 2,769 | −34 | 2,468 | 3,462 | 79.0% | 79.5% | 0.5% | 2,579 | 220 | 194 | **9** |
| Hyderabad | 1,641 | 2,523 | 2,416 | +107 | 2,215 | 3,167 | 79.7% | 79.5% | **−0.2%** | 2,885 | 257 | 213 | **9** |
| Chennai | 1,752 | 2,360 | 2,306 | +54 | 2,163 | 2,989 | 79.0% | 79.5% | 0.5% | 2,233 | 194 | 178 | **5** |
| Kolkata | 546 | 610 | 599 | +11 | 815 | 1,035 | 58.9% | 60.0% | 1.1% | 682 | 60 | 96 | 0 |
| Pune | 985 | 1,157 | 1,143 | +14 | 1,196 | 1,653 | 70.0% | 70.0% | 0.0% | 1,571 | 135 | 146 | 0 |
| **India** | 11,733 | **15,307** | 15,082 | **+225** | 14,818 | 20,763 | **73.7%** | | | **15,434** | | 1,323 | 23 |

**Actuals view:**

| City | On road (plan) | Lakshya | Plan − Lakshya | Util | Max util | Recruitment (14 wks) | Weeks above capacity |
|---|---|---|---|---|---|---|---|
| Mumbai | 3,365 | 3,381 | −16 | 75.0% | 75.0% | 2,588 | 0 |
| Delhi NCR | 2,462 | 2,468 | −6 | 62.0% | 62.0% | 2,698 | 2 |
| Bangalore | 2,639 | 2,769 | −130 | 76.2% | 79.5% | 2,528 | 4 |
| Hyderabad | 1,970 | 2,416 | **−446** | 62.2% | 79.5% | 2,807 | 3 |
| Chennai | 2,290 | 2,306 | −16 | 76.6% | 79.5% | 2,244 | 0 |
| Kolkata | 593 | 599 | −6 | 57.3% | 60.0% | 854 | 0 |
| Pune | 1,159 | 1,143 | +16 | 70.1% | 70.0% | 1,676 | 1 |
| **India** | **14,478** | 15,082 | **−604** | **69.7%** | | **15,395** | 10 |

### C2 – Sources

The sources listed in [section 4](#4-source-data), with links.

---

## 11. The comparison tab: Lakshya vs Plan vs LY

**Pick:** cell B3 (India or a city). Cell E3 holds the city filter, a formula.

**Rows 1–2:** title and definitions. **K1:P2:** plain-text links to Lakshya v4, the Lakshya-based plan, the Actuals view, v2 and the SSOT query.

### Section 1 – Week by week, for the pick

| Rows | Content |
|---|---|
| 3 actual weeks (grey-blue) | w/c 7, 14, 21 Sep (21 Sep has 6 days loaded, scaled to a week) |
| "Last 3 weeks avg (actual)" | Average of the 3 actual weeks |
| "Last 8 weeks avg (actual)" | From section 3 |
| 14 plan weeks | w/c 28 Sep – 28 Dec |
| "Avg 28 Sep – 28 Dec (cars, EIP: total)" | Attrition and recruitment: per full week; util and on-road cars: average; cars added, cars sold and EIP: 14-week total |

Columns, left to right (Lakshya-based plan and Actuals view):

1. **Seven measures**, each with Lakshya and Plan (actual in grey-blue):
   - Attrition % a week
   - Driver recruitment a week
   - Util % (week end)
   - **On-road cars (week end)**
   - Cars added a week
   - Cars sold a week
   - EIP net add a week
2. **Last 8 weeks avg (actual):** one column per measure.
3. **Month by month:** Month, then Lakshya and Plan for each measure.
   - Attrition and recruitment are per full week; recruitment also has its month total.
   - Util and on-road cars are month averages.
   - Cars added, cars sold and EIP are month totals.
   - The "14 weeks" row gives the plan-period figures.
4. **Seasonality check:**
   - **"Seasonality not in plan":** weeks where last year (Diwali-aligned) hiring fell 15%+ or attrition rose 15%+ and the plan does not show it.
   - **"Action needed":** sourcing push / retention push, or the expected miss. In the Actuals view, weeks before Diwali outside Kolkata are not flagged.
5. **How attrition is calculated** (14 formula columns):
   - L+DTO opening book × Lakshya churn rate = the month's L+DTO churn.
   - That churn × the week's share of Lakshya's month, plus Own Now churn and rollover × the same share, gives Lakshya's drivers leaving.
   - Drivers leaving ÷ the book at week start = Lakshya attrition % (= column B).
   - Plan: book × this week's rate = drivers leaving; drivers leaving ÷ book = plan attrition % (= column C).

**Formatting:**
- **Red text:**
  - a plan week more than 10% off Lakshya (on-road cars: 3%);
  - a plan month more than 2% off Lakshya's month.
- **Lines:**
  - thick navy month lines;
  - a dashed line after w/c 28 Sep (it counts in October);
  - navy splitter lines before every measure, the 8-week box, the month box and each measure inside it, the seasonality columns and the working.
- **Text:** centred everywhere except the seasonality comments.

### Section 2 – By city, week by week

The same block for every city (navy city header), then India.

### Section 3 – The last 8 weeks, actual

Eight actual weeks (w/c 3 Aug – 21 Sep) for each city and India, plus their average, for each measure:
- attrition
- recruitment
- util
- on-road cars
- cars added
- cars sold
- EIP net add

Cars added and sold are reporting-DB history (grey).

---

## 12. Every other tab

| Tab | Visible? | What it shows |
|---|---|---|
| **Summary View** | Yes | City and fuel picker (B1). Weekly dashboard: 4 actual weeks + 14 plan weeks. Each block has a 2026 plan row, a 2026 actual row and a 2025 same-week row. Blocks: Util, On Road Cars, On road growth %, Recruitment, Net Attrition %, EIP Growth, FSE, Vendor, Referrals, Performance marketing, EIP %, Total car, Total buy, Total Sold, On Road Cars EIP / Own Now / L+DTO, Driver Acquisition. A "We are here" marker (yellow) and an Actual marker are shown. Colour scale: see section 5. |
| **Lakshya vs Plan vs LY** | Yes | See [section 11](#11-the-comparison-tab-lakshya-vs-plan-vs-ly). |
| **Inputs** | Yes | See [section 10](#10-inputs-tab-section-by-section-with-the-current-values). |
| **Lakshya Source** | Yes | Lakshya v4's own figures, typed as given. (1) Churn inputs: L+DTO book 31 Aug, churn rate a month, Own Now churn and rollover by month. (2) Weekly driver acquisition (L+DTO, Own Now, total) w/c 7 Sep – 28 Dec, with December re-split formulas and the "as given" weeks on the right. |
| **City tabs** (7) | Yes | The weekly engine, one row per week: 4 actual weeks (rows 2–5), 14 plan weeks, totals row, step rows. Columns: see below. |
| **Combined All** | Yes | All city tabs stacked (feeds Summary View). |
| **raw_performance** | Yes | The pasted SSOT output. |
| **Read Me** | Hidden | How the plan works. |
| **Monthly Dashboard** | Hidden | Month by month: plan against run rate, AOP and Lakshya; bridges and insights. |
| **Seasonality Check** | Hidden | (1) Festival dips used. (2) History of each season block in 2024 and 2025. (3) Attrition this year vs last year. (4) Week by week aligned on Diwali. |
| **Lakshya Weekly** | v2 only | Lakshya's weekly placements, churn by month, start gap. |

**City tab columns** (in sheet order):
- **Identity:** City, Fuel Type, Month, Week.
- **Fleet:** Total Cars, nULP, Total buy, Total sold.
- **Start of week:** cars on Road (WB), active partners (WB).
- **Recruitment:** Net Allocations, Total Allocations, Total Channel, FSE, Vendor, Referrals, Performance marketing.
- **EIP:** EIP Net add-on, seasonality, EIP cars.
- **Attrition:** Rejoin %, Attrition + Temp Attrition, Net Attrition (Abs), Net Attrition %.
- **End of week:** L+DTO cars on road (WE), Own Now cars on road (WE), Week-ending cars on Road, Week ending Util, Util ceiling.
- **Engine inputs:** Days in plan, Season block, EIP net add.
- **Own Now:** book WB, drivers for new cars, net add, churn, purchase rollover, driver acquisition (of which new cars / existing cars).
- **L+DTO:** book WB, net attrition (all drivers), net add, churn, driver acquisition.
- **Total and checks:** Total driver acquisition, Check (on road = EIP + L+DTO + Own Now), Util headroom.
- **Last year:** LY week, LY active partners, LY recruitment, LY net attrition (abs / %), LY attrition index, hiring and attrition seasonal change (validated).
- **Hiring path:** current hiring run rate, proven capacity, new cars going on road, run-rate hiring, extra hiring, planned on-road add, weekly growth %, organic growth %, acquisition vs capacity, gap to Lakshya.
- **Rate and paths:** net attrition rate, run-rate path (cars on road, drivers).
- **Month-end targets:** Lakshya month-end, EIP / Own Now / L+DTO / on-road month-end targets, AOP month-end, Plan − Lakshya, Plan − AOP.
- **Survival and capacity path:** share of hires still driving at the end, share kept this week, extra hiring within capacity, within-capacity path (drivers, cars on road), cars short above max util.
- **Hiring cap:** cap, hires cut, hires moved in.
- **Last year's pattern:** hiring index, attrition index.
- **Month:** match month.
- **Catch-up columns:** share kept since 28 Sep, shape, this month so far, earlier months, catch-up hires, util target, on road without catch-up.

---

## 13. Results: India and every city

L = Lakshya, P = plan. Attrition and recruitment "a week" are per full 7-day week. Util and on-road cars are month averages. Recruitment total, cars and EIP are totals.

### 13.1 Lakshya-based plan (main)

**Month by month, every city**

| City | Month | Util % L / P | On-road avg L / P | Attrition % a week L / P | Recruitment a week L / P | Recruitment total L / P | Cars added L / P | Cars sold L / P | EIP net add L / P |
|---|---|---|---|---|---|---|---|---|---|
| India | Oct | 65.1% / 65.1% | 13,028 / 12,936 | 9.8% / 9.8% | 1,118 / 1,315 | 5,591 / 6,573 | 1,382 / 1,382 | 290 / 290 | 219 / 219 |
|  | Nov | 63.9% / 63.9% | 13,382 / 13,278 | 8.5% / 8.5% | 1,082 / 830 | 5,408 / 4,152 | 918 / 918 | 253 / 253 | 219 / 219 |
|  | Dec | 70.4% / 70.4% | 14,762 / 14,654 | 6.8% / 6.8% | 954 / 1,177 | 3,816 / 4,710 | 0 / 0 | 178 / 178 | 175 / 175 |
|  | 14 weeks | 66.2% / 66.2% | 13,650 / 13,549 | 8.5% / 8.5% | 1,058 / 1,102 | 14,815 / 15,434 | 2,300 / 2,300 | 721 / 721 | 612 / 612 |
| Mumbai | Oct | 67.4% / 67.4% | 2,915 / 2,902 | 9.8% / 9.8% | 208 / 245 | 1,038 / 1,224 | 281 / 281 | 60 / 60 | 46 / 46 |
|  | Nov | 67.0% / 67.0% | 3,025 / 3,010 | 8.4% / 8.4% | 201 / 153 | 1,007 / 764 | 186 / 186 | 53 / 53 | 46 / 46 |
|  | Dec | 73.3% / 73.3% | 3,313 / 3,297 | 6.5% / 6.5% | 176 / 222 | 705 / 887 | 0 / 0 | 38 / 38 | 37 / 37 |
|  | 14 weeks | 68.9% / 68.9% | 3,068 / 3,054 | 8.3% / 8.3% | 196 / 205 | 2,750 / 2,875 | 467 / 467 | 151 / 151 | 129 / 129 |
| Delhi NCR | Oct | 55.8% / 55.8% | 2,309 / 2,302 | 8.5% / 8.5% | 195 / 210 | 976 / 1,049 | 0 / 0 | 84 / 84 | 7 / 7 |
|  | Nov | 55.8% / 55.8% | 2,265 / 2,259 | 7.7% / 7.7% | 186 / 161 | 932 / 804 | 0 / 0 | 73 / 73 | 7 / 7 |
|  | Dec | 60.8% / 60.8% | 2,432 / 2,425 | 6.3% / 6.3% | 170 / 189 | 681 / 756 | 0 / 0 | 52 / 52 | 6 / 6 |
|  | 14 weeks | 57.2% / 57.2% | 2,328 / 2,322 | 7.6% / 7.6% | 185 / 186 | 2,589 / 2,609 | 0 / 0 | 209 / 209 | 20 / 20 |
| Bangalore | Oct | 70.6% / 70.6% | 2,286 / 2,192 | 8.5% / 8.5% | 187 / 220 | 937 / 1,101 | 380 / 380 | 20 / 20 | 50 / 50 |
|  | Nov | 68.1% / 68.1% | 2,414 / 2,319 | 7.4% / 7.4% | 187 / 130 | 934 / 651 | 253 / 253 | 18 / 18 | 50 / 50 |
|  | Dec | 74.9% / 74.9% | 2,700 / 2,597 | 5.9% / 5.9% | 165 / 207 | 661 / 827 | 0 / 0 | 12 / 12 | 40 / 40 |
|  | 14 weeks | 71.0% / 71.0% | 2,450 / 2,353 | 7.3% / 7.3% | 181 / 184 | 2,532 / 2,579 | 633 / 633 | 50 / 50 | 141 / 141 |
| Hyderabad | Oct | 70.0% / 70.0% | 1,945 / 1,966 | 11.9% / 11.9% | 198 / 257 | 988 / 1,286 | 380 / 380 | 20 / 20 | 67 / 67 |
|  | Nov | 66.7% / 66.7% | 2,060 / 2,074 | 10.3% / 10.3% | 193 / 135 | 967 / 673 | 253 / 253 | 18 / 18 | 67 / 67 |
|  | Dec | 74.6% / 74.6% | 2,347 / 2,365 | 7.9% / 7.9% | 169 / 232 | 677 / 927 | 0 / 0 | 12 / 12 | 54 / 54 |
|  | 14 weeks | 70.1% / 70.1% | 2,101 / 2,118 | 10.2% / 10.2% | 188 / 206 | 2,632 / 2,885 | 633 / 633 | 50 / 50 | 188 / 188 |
| Chennai | Oct | 72.2% / 72.2% | 1,952 / 1,966 | 9.5% / 9.5% | 156 / 194 | 778 / 968 | 290 / 290 | 20 / 20 | 39 / 39 |
|  | Nov | 69.3% / 69.3% | 2,034 / 2,045 | 8.3% / 8.3% | 155 / 120 | 773 / 602 | 193 / 193 | 18 / 18 | 39 / 39 |
|  | Dec | 75.7% / 75.7% | 2,254 / 2,267 | 6.6% / 6.6% | 136 / 166 | 543 / 662 | 0 / 0 | 12 / 12 | 31 / 31 |
|  | 14 weeks | 72.2% / 72.2% | 2,068 / 2,080 | 8.2% / 8.2% | 150 / 159 | 2,094 / 2,233 | 483 / 483 | 50 / 50 | 110 / 110 |
| Kolkata | Oct | 51.5% / 51.5% | 558 / 552 | 10.7% / 10.7% | 56 / 53 | 278 / 267 | 0 / 0 | 20 / 20 | 5 / 5 |
|  | Nov | 51.5% / 51.5% | 549 / 543 | 9.0% / 9.0% | 49 / 41 | 244 / 205 | 0 / 0 | 18 / 18 | 5 / 5 |
|  | Dec | 56.2% / 56.2% | 591 / 584 | 7.0% / 7.0% | 42 / 52 | 166 / 210 | 0 / 0 | 12 / 12 | 4 / 4 |
|  | 14 weeks | 52.8% / 52.8% | 564 / 558 | 9.0% / 9.0% | 49 / 49 | 688 / 682 | 0 / 0 | 50 / 50 | 14 / 14 |
| Pune | Oct | 61.3% / 61.3% | 1,063 / 1,056 | 11.8% / 11.8% | 119 / 135 | 596 / 677 | 50 / 50 | 65 / 65 | 4 / 4 |
|  | Nov | 60.3% / 60.3% | 1,036 / 1,029 | 10.3% / 10.3% | 110 / 91 | 551 / 454 | 34 / 34 | 56 / 56 | 4 / 4 |
|  | Dec | 67.1% / 67.1% | 1,126 / 1,118 | 8.1% / 8.1% | 96 / 110 | 383 / 440 | 0 / 0 | 40 / 40 | 3 / 3 |
|  | 14 weeks | 62.6% / 62.6% | 1,071 / 1,064 | 10.2% / 10.2% | 109 / 112 | 1,530 / 1,571 | 84 / 84 | 161 / 161 | 10 / 10 |

**End of w/c 28 Dec, and where each city starts (last 8 weeks, actual)**

| City | End of w/c 28 Dec: util L / P | On-road L / P | Last 8 weeks: attrition | recruitment | util | on-road |
|---|---|---|---|---|---|---|
| India | 72.1% / 73.7% | 15,082 / 15,307 | 10.9% | 979 | 62.7% | 12,012 |
| Mumbai | 75.0% / 76.5% | 3,381 / 3,433 | 9.9% | 159 | 63.3% | 2,672 |
| Delhi NCR | 62.0% / 62.7% | 2,468 / 2,489 | 9.6% | 192 | 53.2% | 2,228 |
| Bangalore | 76.9% / 79.0% | 2,769 / 2,735 | 9.4% | 142 | 71.2% | 2,016 |
| Hyderabad | 76.9% / 79.7% | 2,416 / 2,523 | 13.4% | 158 | 68.8% | 1,752 |
| Chennai | 77.6% / 79.0% | 2,306 / 2,360 | 10.4% | 135 | 70.1% | 1,782 |
| Kolkata | 57.3% / 58.9% | 599 / 610 | 14.6% | 70 | 50.3% | 545 |
| Pune | 68.7% / 70.0% | 1,143 / 1,157 | 13.4% | 123 | 58.7% | 1,018 |

**Recruitment week by week (plan)**

| City | 28 Sep | 05 Oct | 12 Oct | 19 Oct | 26 Oct | 02 Nov | 09 Nov | 16 Nov | 23 Nov | 30 Nov | 07 Dec | 14 Dec | 21 Dec | 28 Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **India Lakshya** | 1,415 | 1,356 | 1,169 | 985 | 666 | 565 | 769 | 1,283 | 1,433 | 1,358 | 954 | 954 | 954 | 954 |
| **India plan** | 1,321 | 1,321 | 1,304 | 1,304 | 1,321 | 711 | 711 | 910 | 910 | 910 | 1,177 | 1,177 | 1,177 | 1,177 |
| Mumbai rec | 245 | 245 | 245 | 245 | 245 | 133 | 133 | 166 | 166 | 166 | 222 | 222 | 222 | 222 |
| Delhi NCR rec | 210 | 210 | 210 | 210 | 210 | 111 | 111 | 194 | 194 | 194 | 189 | 189 | 189 | 189 |
| Bangalore rec | 220 | 220 | 220 | 220 | 220 | 112 | 112 | 143 | 143 | 143 | 207 | 207 | 207 | 207 |
| Hyderabad rec | 257 | 257 | 257 | 257 | 257 | 129 | 129 | 138 | 138 | 138 | 232 | 232 | 232 | 232 |
| Chennai rec | 194 | 194 | 194 | 194 | 194 | 112 | 112 | 126 | 126 | 126 | 166 | 166 | 166 | 166 |
| Kolkata rec | 60 | 60 | 43 | 43 | 60 | 35 | 35 | 45 | 45 | 45 | 52 | 52 | 52 | 52 |
| Pune rec | 135 | 135 | 135 | 135 | 135 | 80 | 80 | 98 | 98 | 98 | 110 | 110 | 110 | 110 |

### 13.2 Actuals view

**Month by month, every city**

| City | Month | Util % L / P | On-road avg L / P | Attrition % a week L / P | Recruitment a week L / P | Recruitment total L / P | Cars added L / P | Cars sold L / P | EIP net add L / P |
|---|---|---|---|---|---|---|---|---|---|
| India | Oct | 65.1% / 63.3% | 13,028 / 12,491 | 9.8% / 9.8% | 1,118 / 1,118 | 5,591 / 5,591 | 1,382 / 1,241 | 290 / 290 | 219 / 230 |
|  | Nov | 63.9% / 62.4% | 13,382 / 12,944 | 8.5% / 9.7% | 1,082 / 1,082 | 5,408 / 5,408 | 918 / 1,060 | 253 / 253 | 219 / 230 |
|  | Dec | 70.4% / 67.3% | 14,762 / 14,021 | 6.8% / 8.5% | 954 / 1,099 | 3,816 / 4,396 | 0 / 0 | 178 / 178 | 175 / 184 |
|  | 14 weeks | 66.2% / 64.1% | 13,650 / 13,090 | 8.5% / 9.4% | 1,058 / 1,100 | 14,815 / 15,395 | 2,300 / 2,301 | 721 / 721 | 612 / 644 |
| Mumbai | Oct | 67.4% / 66.7% | 2,915 / 2,875 | 9.8% / 9.8% | 208 / 208 | 1,038 / 1,038 | 281 / 281 | 60 / 60 | 46 / 130 |
|  | Nov | 67.0% / 69.6% | 3,025 / 3,125 | 8.4% / 8.9% | 201 / 201 | 1,007 / 1,007 | 186 / 186 | 53 / 53 | 46 / 130 |
|  | Dec | 73.3% / 73.2% | 3,313 / 3,295 | 6.5% / 7.1% | 176 / 136 | 705 / 543 | 0 / 0 | 38 / 38 | 37 / 104 |
|  | 14 weeks | 68.9% / 69.6% | 3,068 / 3,084 | 8.3% / 8.7% | 196 / 185 | 2,750 / 2,588 | 467 / 467 | 151 / 151 | 129 / 364 |
| Delhi NCR | Oct | 55.8% / 54.9% | 2,309 / 2,268 | 8.5% / 8.5% | 195 / 195 | 976 / 976 | 0 / 1 | 84 / 84 | 7 / -15 |
|  | Nov | 55.8% / 52.9% | 2,265 / 2,146 | 7.7% / 8.3% | 186 / 186 | 932 / 932 | 0 / 0 | 73 / 73 | 7 / -15 |
|  | Dec | 60.8% / 59.1% | 2,432 / 2,359 | 6.3% / 6.7% | 170 / 197 | 681 / 790 | 0 / 0 | 52 / 52 | 6 / -12 |
|  | 14 weeks | 57.2% / 55.4% | 2,328 / 2,250 | 7.6% / 7.9% | 185 / 193 | 2,589 / 2,698 | 0 / 1 | 209 / 209 | 20 / -42 |
| Bangalore | Oct | 70.6% / 70.5% | 2,286 / 2,147 | 8.5% / 8.5% | 187 / 187 | 937 / 937 | 380 / 304 | 20 / 20 | 50 / 103 |
|  | Nov | 68.1% / 69.9% | 2,414 / 2,371 | 7.4% / 8.8% | 187 / 187 | 934 / 934 | 253 / 329 | 18 / 18 | 50 / 103 |
|  | Dec | 74.9% / 73.7% | 2,700 / 2,556 | 5.9% / 7.5% | 165 / 164 | 661 / 657 | 0 / 0 | 12 / 12 | 40 / 82 |
|  | 14 weeks | 71.0% / 71.2% | 2,450 / 2,344 | 7.3% / 8.3% | 181 / 181 | 2,532 / 2,528 | 633 / 633 | 50 / 50 | 141 / 287 |
| Hyderabad | Oct | 70.0% / 63.3% | 1,945 / 1,777 | 11.9% / 11.9% | 198 / 198 | 988 / 988 | 380 / 366 | 20 / 20 | 67 / -14 |
|  | Nov | 66.7% / 58.7% | 2,060 / 1,825 | 10.3% / 12.8% | 193 / 193 | 967 / 967 | 253 / 267 | 18 / 18 | 67 / -14 |
|  | Dec | 74.6% / 61.2% | 2,347 / 1,942 | 7.9% / 12.0% | 169 / 213 | 677 / 852 | 0 / 0 | 12 / 12 | 54 / -11 |
|  | 14 weeks | 70.1% / 61.1% | 2,101 / 1,841 | 10.2% / 12.3% | 188 / 201 | 2,632 / 2,807 | 633 / 633 | 50 / 50 | 188 / -39 |
| Chennai | Oct | 72.2% / 70.9% | 1,952 / 1,873 | 9.5% / 9.5% | 156 / 156 | 778 / 778 | 290 / 239 | 20 / 20 | 39 / 45 |
|  | Nov | 69.3% / 68.6% | 2,034 / 2,024 | 8.3% / 8.5% | 155 / 155 | 773 / 773 | 193 / 244 | 18 / 18 | 39 / 45 |
|  | Dec | 75.7% / 74.2% | 2,254 / 2,221 | 6.6% / 8.8% | 136 / 173 | 543 / 693 | 0 / 0 | 12 / 12 | 31 / 36 |
|  | 14 weeks | 72.2% / 71.0% | 2,068 / 2,026 | 8.2% / 9.0% | 150 / 160 | 2,094 / 2,244 | 483 / 483 | 50 / 50 | 110 / 126 |
| Kolkata | Oct | 51.5% / 50.4% | 558 / 541 | 10.7% / 10.7% | 56 / 56 | 278 / 278 | 0 / 0 | 20 / 20 | 5 / -9 |
|  | Nov | 51.5% / 46.2% | 549 / 487 | 9.0% / 12.9% | 49 / 49 | 244 / 244 | 0 / 0 | 18 / 18 | 5 / -9 |
|  | Dec | 56.2% / 53.0% | 591 / 551 | 7.0% / 10.8% | 42 / 83 | 166 / 332 | 0 / 0 | 12 / 12 | 4 / -7 |
|  | 14 weeks | 52.8% / 49.6% | 564 / 524 | 9.0% / 11.5% | 49 / 61 | 688 / 854 | 0 / 0 | 50 / 50 | 14 / -25 |
| Pune | Oct | 61.3% / 58.5% | 1,063 / 1,010 | 11.8% / 11.8% | 119 / 119 | 596 / 596 | 50 / 50 | 65 / 65 | 4 / -10 |
|  | Nov | 60.3% / 56.7% | 1,036 / 967 | 10.3% / 11.2% | 110 / 110 | 551 / 551 | 34 / 34 | 56 / 56 | 4 / -10 |
|  | Dec | 67.1% / 65.7% | 1,126 / 1,096 | 8.1% / 9.7% | 96 / 132 | 383 / 529 | 0 / 0 | 40 / 40 | 3 / -8 |
|  | 14 weeks | 62.6% / 59.9% | 1,071 / 1,019 | 10.2% / 11.0% | 109 / 120 | 1,530 / 1,676 | 84 / 84 | 161 / 161 | 10 / -28 |

**End of w/c 28 Dec, and where each city starts (last 8 weeks, actual)**

| City | End of w/c 28 Dec: util L / P | On-road L / P | Last 8 weeks: attrition | recruitment | util | on-road |
|---|---|---|---|---|---|---|
| India | 72.1% / 69.7% | 15,082 / 14,478 | 10.9% | 979 | 62.7% | 12,012 |
| Mumbai | 75.0% / 75.0% | 3,381 / 3,365 | 9.9% | 159 | 63.3% | 2,672 |
| Delhi NCR | 62.0% / 62.0% | 2,468 / 2,462 | 9.6% | 192 | 53.2% | 2,228 |
| Bangalore | 76.9% / 76.2% | 2,769 / 2,639 | 9.4% | 142 | 71.2% | 2,016 |
| Hyderabad | 76.9% / 62.2% | 2,416 / 1,970 | 13.4% | 158 | 68.8% | 1,752 |
| Chennai | 77.6% / 76.6% | 2,306 / 2,290 | 10.4% | 135 | 70.1% | 1,782 |
| Kolkata | 57.3% / 57.3% | 599 / 593 | 14.6% | 70 | 50.3% | 545 |
| Pune | 68.7% / 70.1% | 1,143 / 1,159 | 13.4% | 123 | 58.7% | 1,018 |

**Recruitment week by week (plan)**

| City | 28 Sep | 05 Oct | 12 Oct | 19 Oct | 26 Oct | 02 Nov | 09 Nov | 16 Nov | 23 Nov | 30 Nov | 07 Dec | 14 Dec | 21 Dec | 28 Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **India Lakshya** | 1,415 | 1,356 | 1,169 | 985 | 666 | 565 | 769 | 1,283 | 1,433 | 1,358 | 954 | 954 | 954 | 954 |
| **India plan** | 1,216 | 1,202 | 1,132 | 978 | 1,064 | 862 | 862 | 1,245 | 1,258 | 1,181 | 1,043 | 1,018 | 1,177 | 1,159 |
| Mumbai rec | 225 | 225 | 220 | 197 | 171 | 182 | 182 | 214 | 228 | 202 | 104 | 106 | 210 | 122 |
| Delhi NCR rec | 211 | 211 | 206 | 175 | 173 | 100 | 100 | 222 | 259 | 251 | 172 | 173 | 219 | 226 |
| Bangalore rec | 203 | 203 | 183 | 175 | 174 | 165 | 165 | 219 | 188 | 196 | 162 | 147 | 154 | 194 |
| Hyderabad rec | 220 | 220 | 187 | 154 | 206 | 173 | 173 | 212 | 224 | 186 | 213 | 213 | 213 | 213 |
| Chennai rec | 163 | 163 | 159 | 142 | 152 | 132 | 132 | 178 | 178 | 153 | 178 | 178 | 163 | 174 |
| Kolkata rec | 70 | 55 | 55 | 27 | 71 | 41 | 41 | 57 | 49 | 55 | 74 | 84 | 92 | 82 |
| Pune rec | 125 | 125 | 122 | 109 | 117 | 69 | 69 | 144 | 131 | 139 | 140 | 116 | 126 | 147 |

---

## 14. Key findings

1. **Start gap.**
   - We start below Lakshya: util 61.2% against 63.5%; on road 11,733 against Lakshya's 27 Sep book of 12,281.
   - Recruitment runs at 979 a week (last 8 weeks) against Lakshya's October 1,118.
   - Attrition runs at 10.9% against Lakshya's October 9.8%.
2. **This year against last year.** Recruitment is 17% lower than the same weeks last year (979 vs 1,174), and attrition is lower too (10.9% vs 12.2%).
3. **Matching monthly util needs front-loaded hiring.**
   - The Lakshya-based plan hires +197 a week above Lakshya in October, 252 below in November and +223 above in December.
   - That is 15,434 hires over 14 weeks against Lakshya's 14,815 (+619).
   - Util ends at 73.7% against 72.1%.
4. **Util ceiling breached in the Lakshya-based plan:** Mumbai ends at 76.5% (max 75.0%), Delhi NCR at 62.7% (max 62.0%) and Hyderabad at 79.7% (max 79.5%).
5. **Hiring above proven capacity in the Lakshya-based plan:** Bangalore (9 weeks), Hyderabad (9 weeks) and Chennai (5 weeks).
6. **On-road cars run about 100 below Lakshya each month even with util matched.** Our fleet is slightly smaller than Lakshya's, so the same util gives fewer cars on road.
7. **The Actuals view lands 604 cars short of Lakshya** (14,478 against 15,082, util 69.7%). Almost all of it is **Hyderabad (−446)**: attrition there runs 13.4% a week, and its December hiring is capped at its best week (213).
8. **EIP.**
   - EIP fell 241 cars in August (mostly Mumbai drop-offs) and recovered 184 in September.
   - The last 4 weeks run at +46 a week, close to Lakshya's +44–47.
9. **New cars.**
   - 582 of Lakshya's 2,300 are bought.
   - 571 more must be ordered for October and 1,148 for November.
   - A car ordered now reaches the road at least 5 weeks later, so October's cars not yet bought are already at risk.

---

## 15. Complete change log

| # | Request / issue | What was done |
|---|---|---|
| 1 | Base the plan on actuals up to 26 Sep | Opening position Sun 27 Sep; the current week is plan week 1 |
| 2 | "Is a jump from 190 to 257 a week possible?" | Flagged; capped hiring at each city's best week (no 300-a-week jumps) |
| 3 | Too much up and down; only Diwali and Durga Puja (Kolkata) seasonality; follow the last 6–8 weeks; standard line | The plan follows a steady line from the run rate; only those two festival dips |
| 4 | Comparison of attrition %, recruitment and util: Lakshya vs plan vs same week last year vs the last 8 weeks | Given in chat, then added to the sheet as the comparison tab |
| 5 | "Where is 21 Sep data?" | w/c 21 Sep shown as the last actual week (6 days, scaled) |
| 6 | "72.1% vs 63.2% – are we planning below Lakshya?" | Plan rebuilt on Lakshya; net attrition lowered further |
| 7 | Util is the priority; stretch to match Lakshya's util | Steady catch-up so the last-day util matched Lakshya (72.2% vs 72.1%) |
| 8 | No smoothing of 200 drivers in w/c 16 and 23 Nov; move them to w/c 28 Sep – 16 Oct | Hiring cap setting in Inputs A8 (cap 200, moved to weeks 1–3) |
| 9 | Add cars added and sold to the comparison | Added (actuals from the reporting DB) |
| 10 | City-wise blocks in the comparison | Section 2 (a block per city) |
| 11 | Add 3 weeks before 28 Sep to see the run rate | 3 actual weeks + the "Last 3 weeks avg" row |
| 12 | Lakshya's month average must match the plan month by month | Recruitment and attrition set to Lakshya's month averages (A3b) |
| 13 | Two plans on Lakshya and one view on last year + the 8-week average | Lakshya-based plan, v2 and the Actuals view |
| 14 | Actuals view too low; stretch it | Capacity ramp and attrition stepping down to the best 4 weeks |
| 15 | "Why no car additions in December?" | Explained: Lakshya assumes every car lands by 30 Nov |
| 16 | Fully match Lakshya | All months matched to Lakshya |
| 17 | Show where seasonality isn't taken and the action needed | Seasonality check columns ("not in plan" and "action needed") |
| 18 | Month-by-month split lines | Thick lines at month ends; the dashed line after 28 Sep |
| 19 | Explain how Lakshya's churn is split weekly; show the calculation | 14-column attrition working with formulas, traced to the Lakshya Source tab |
| 20 | No typed numbers like 3867 / 338 in formulas | Formulas reference the Lakshya Source tab and Inputs |
| 21 | Add the 8-week average; clean Inputs; hide Monthly Dashboard, Seasonality Check, Read Me; links in K–M without HYPERLINK | Done |
| 22 | Keep 28 Sep in October | Match-month rule |
| 23 | Lakshya buys 2,300 cars but the plan showed 460 | Cars shown as totals (month and plan period) |
| 24 | Actuals view: Durga Puja only for Kolkata; 2 Nov attrition 14% → 12%; November recruitment = Lakshya, no stretch; add EIP; new layout; colour scale in Summary View | All done (35% of the Diwali jump kept) |
| 25 | Show sums, not month averages, for cars | Done |
| 26 | Why EIP −94 against Lakshya +612 | Explained the August drop; Actuals view EIP on the last 4 weeks (+46 a week) |
| 27 | Add a monthly table after the 8-week box | Month-by-month box |
| 28 | October attrition too high and recruitment too low; centre the text; splitter lines | October = Lakshya's averages; December-only ramp; centring; splitters |
| 29 | Same format on the Lakshya-based plan | New layout applied to the main sheet |
| 30 | Not the same number every week in October; Diwali impact on 26 Oct; Durga Puja dips moved earlier | Festival-week dips moved to the earlier weeks |
| 31 | 02 Nov: 1,115 isn't achievable in Diwali week | w/c 2 Nov takes last year's Diwali-week dip (India 862) |
| 32 | Show recruitment month totals; better format | Recruitment month totals, month column, clearer headers |
| 33 | Manager summary MD; list every source | `CNG_Supply_Plan_Summary.md` with the sources table |
| 34 | Principles of the Lakshya-based plan | Given in chat (long and short versions) |
| 35 | Monthly average util should match Lakshya (not the December number); add On-Road Cars to the comparison | Monthly util catch-up ("Lakshya monthly util"); on-road cars measure |
| 36 | Lakshya has 21 Dec; add 28 Dec and split December's number | w/c 28 Dec added; Lakshya's December re-split (total unchanged) |
| 37 | Don't split the week; take all 7 days | w/c 28 Dec is a full week to Sun 3 Jan; December split evenly, 954 a week |
| 38 | Full documentation MD | This file |

---

## 16. Open points

1. **Lakshya-based plan, up-and-down pattern.**
   - Matching each month's average util means:
     - util goes 67.1% at the end of October → 63.3% in Diwali week → 73.7% at the end;
     - recruitment goes 1,315 → 830 → 1,177 a week.
   - A smoother alternative is to match each month's closing util instead. That gives steadier hiring, but the monthly averages would not match.
2. **Util ceiling breaches:** Mumbai (76.5% against 75%), Delhi NCR (62.7% against 62%) and Hyderabad (79.7% against 79.5%) in the Lakshya-based plan.
3. **Weeks above proven capacity:** Bangalore 9, Hyderabad 9 and Chennai 5 in the Lakshya-based plan.
4. **Actuals view, Hyderabad:** 446 cars short. This needs either lower attrition (13.4% now) or hiring above its best week.
5. **Actuals view, Mumbai's December:** follows last year's uneven December weeks. It can be smoothed with the same December total.
6. **Actuals view, first week:** recruitment steps from 1,002 (last actual week) to 1,216 in w/c 28 Sep (+21%), because festival-week hires were moved earlier.
7. **New cars:** 571 October cars and 1,148 November cars are still to be ordered. At 5 weeks from order to road, October's are already late.
8. **v2:** still on the older comparison layout.
9. **Last-year cars for Aug 2025:** missing from the reporting DB pull (left blank).

---

## 17. How the sheets are built and published

- **Builder:** `supply-plan/build_weekly_supply_plan.py`. It writes an .xlsx, which is uploaded over each live Google Sheet (Drive API), and the picks are restored afterwards.
  ```
  python3 build_weekly_supply_plan.py out.xlsx raw.json            # Lakshya-based plan
  python3 build_weekly_supply_plan.py out_act.xlsx raw.json --actual   # Actuals view
  python3 build_weekly_supply_plan.py out_v2.xlsx raw.json --v2        # v2
  ```
  `raw.json` = {"hdr": [...], "data": [[...]]}, the SSOT query output.
- **Data modules:**

  | Module | Holds |
  |---|---|
  | `lakshya_cmp.py` | Lakshya week by week, from the v2 engine |
  | `ly_pattern.py` | Last year's Diwali-aligned weekly pattern, 14 weeks |
  | `car_flows.py` | Actual cars added and sold by week |
  | `plan_history.py` | History, seasonality, capacity and the attrition trend |

- **Before every publish:**
  - The live sheet is compared formula by formula with the last published copy, to keep any manual edits and picks.
  - Every tab is scanned for errors (#REF!, #N/A and so on). Every publish so far had **0 errors**.
- **Repository:** `mithunjaiswar/mithunjaiswar`, branch `claude/pensive-mendel-s62wy1`. Docs:
  - `supply-plan/README.md`: technical description.
  - `supply-plan/CNG_Supply_Plan_Summary.md`: short manager summary.
  - `supply-plan/CNG_Supply_Plan_Full_Documentation.md`: this file.
