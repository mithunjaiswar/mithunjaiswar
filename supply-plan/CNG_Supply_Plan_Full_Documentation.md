# Weekly CNG Supply Plan: Full Documentation

**Plan period:** 13 weeks, w/c 28 Sep 2026 to w/c 21 Dec 2026 (the last week ends Sun 27 Dec 2026), the same weeks as Lakshya v4.
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
| **Lakshya exact, week by week** (with Monthly Summary) | https://docs.google.com/spreadsheets/d/15IhNdV4Vh_ieanqEDDLc5AOH0UMwk_5-aaI6h9T6ee0/edit |
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
| **Month rule ("match month")** | A week counts in the month its Monday falls in, except w/c 28 Sep, which counts as October because the plan starts there. October = w/c 28 Sep – 26 Oct (5 weeks); November = w/c 2 – 30 Nov (5 weeks); December = w/c 7 – 21 Dec (3 weeks). This rule is used for all month averages and month totals. |
| **Lakshya month** | The month each week rolls up to in Lakshya's own model (by the Sunday it ends on). Oct = w/e 4 – 25 Oct (4 weeks); Nov = w/e 1 – 29 Nov (5 weeks); Dec = w/e 6 – 27 Dec (4 weeks). It is used only to spread Lakshya's monthly churn, sales and new cars over weeks. |
| **LY** | Last year. "Same week last year" = 364 days earlier. The **Diwali-aligned** pattern uses 385 days earlier, which lines up Bhai Dooj week (w/c 9 Nov 2026 ↔ w/c 20 Oct 2025) and Durga Puja. |
| **Grey-blue cells** | Actual weeks. **Cream cells** are inputs you may change. **Grey cells** are history and reference. **Light-blue cells** are totals. |

---

## 3. Plan period and calendar

- **Opening date:** Sun 27 Sep 2026, the last actual Sunday. The plan starts from the actual position on this date.
- **First plan week:** w/c Mon 28 Sep (the current week).
- **Plan end:** Sun 27 Dec 2026 (the end of w/c 21 Dec), the same last week as Lakshya v4. Every week has the full 7 days. There are 91 days in plan.
- **December:** Lakshya's December weeks are used **exactly as given** (no re-split). Lakshya's own last week (w/c 21 Dec) is light: India 779 hires against 1,487 the week before.

| # | Week (w/c) | Ends | Match month | Lakshya month | Share of Lakshya's month | Festival | Events |
|---|---|---|---|---|---|---|---|
| 1 | 28 Sep | 4 Oct | Oct | Oct | 25% | – | Gandhi Jayanti (Fri 2 Oct) |
| 2 | 5 Oct | 11 Oct | Oct | Oct | 25% | – | – |
| 3 | 12 Oct | 18 Oct | Oct | Oct | 25% | Durga Puja (Kolkata only) | – |
| 4 | 19 Oct | 25 Oct | Oct | Oct | 25% | Durga Puja (Kolkata only) | Dussehra (Tue 20 Oct) |
| 5 | 26 Oct | 1 Nov | Oct | Nov | 20% | – | Bangalore: Kannada Rajyotsava (Sun 1 Nov) |
| 6 | 2 Nov | 8 Nov | Nov | Nov | 20% | Diwali | Diwali (Sun 8 Nov) |
| 7 | 9 Nov | 15 Nov | Nov | Nov | 20% | Diwali | Bali Pratipada, Bhai Dooj; Hyderabad: GHMC election (Sun 15 Nov) |
| 8 | 16 Nov | 22 Nov | Nov | Nov | 20% | – | – |
| 9 | 23 Nov | 29 Nov | Nov | Nov | 20% | – | Guru Nanak Jayanti (Tue 24 Nov) |
| 10 | 30 Nov | 6 Dec | Nov | Dec | 25% | – | – |
| 11 | 7 Dec | 13 Dec | Dec | Dec | 25% | – | – |
| 12 | 14 Dec | 20 Dec | Dec | Dec | 25% | – | Kolkata: KMC election (Tue 15 Dec) |
| 13 | 21 Dec | 27 Dec | Dec | Dec | 25% | – | Christmas (Fri 25 Dec); last plan week, ends Sun 27 Dec as in Lakshya |

- **Share of Lakshya's month:** Lakshya spreads a month evenly over its weeks: October 1/4, November 1/5, December 1/4. These shares spread Lakshya's monthly churn, cars sold and cars still to buy over the weeks.
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
| **Base recruitment** | Lakshya's month average × festival shape | Oct and Nov: Lakshya's month average × last year's shape; Dec: 8-week run rate × last year's shape | Lakshya's weekly placements as given |
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
     | Mumbai | +37.3 | −53.0 | +77.2 |
     | Delhi NCR | +14.6 | −30.8 | +43.3 |
     | Bangalore | +32.8 | −62.0 | +69.6 |
     | Hyderabad | +59.5 | −60.5 | +96.8 |
     | Chennai | +38.0 | −35.7 | +53.2 |
     | Kolkata | −2.5 | −8.6 | +18.5 |
     | Pune | +16.2 | −21.1 | +28.3 |
     | **India (net)** | **+196** | **−252** | **+387** |

   - **Why the catch-up goes up, down, up:** we start below Lakshya, at 61.2% util against 63.5%. To average 65.2% in October, util has to end October above Lakshya. November then needs fewer hires. December needs many more, because Lakshya's December averages 71.8% over only 3 weeks.
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
8. **EIP** (AG): a straight line from today's actual (2,426) to Lakshya's December EIP (3,038), spread by days. That is +47 a week for India and 612 over the plan.
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

### 8.1 Lakshya exact, week by week (new sheet)

- **What it is:** the v2 engine, so every week equals Lakshya v4. That covers recruitment, attrition, util, on-road cars, fleet, cars added and sold, and EIP. It starts from Lakshya's own 27 Sep book.
- **Comparison tab:** the new layout.
- **Monthly Summary tab:**
  - Its own city picker (B1).
  - For each month (Oct, Nov, Dec) and the 13 weeks, every Summary View metric shows: Lakshya v4 (where Lakshya has the figure), Plan, **Plan − Lakshya** (0 everywhere, red if not), Actual so far (fully loaded weeks only), and Last year (same weeks, 364 days earlier).
  - Flows are month totals; util and attrition are month averages; stock figures are at the month's last week.
  - The title and the footnote were removed on the live sheet by the user and are kept removed.
- **India results:** util 65.2% / 64.1% / 71.8%; on road at month-end 13,055 / 14,263 / 15,082; recruitment 5,591 / 5,408 / 3,816 (14,815); attrition 9.8% / 8.5% / 8.8%; cars added 2,300 and sold 721; EIP +612.

---

## 9. Lakshya's December

- **Lakshya's own weeks are used as given.** Lakshya's December weeks are w/e 6, 13, 20 and 27 Dec: India 1,358, 1,550, 1,487 and 779 placements. The plan ends with w/c 21 Dec (w/e 27 Dec), the same as Lakshya, so every weekly Lakshya figure matches its model exactly.
- **History of this rule:**
  - On 8 Oct the plan was extended to w/c 28 Dec, with December re-split by days (later as 4 equal weeks of 954).
  - On 13 Oct it was changed back to end on w/c 21 Dec to match Lakshya. The re-split is switched off (`DEC_RESPLIT = False` in the builder).
- **Churn and cars sold** in December are spread evenly over Lakshya's 4 December weeks (25% each).

---

## 10. Inputs tab, section by section (with the current values)

**Colour key:** cream = you can change; grey-blue = actual; white = formula; grey = history; light blue = total or output.

### A1 – Plan dates and switches

| Setting | Lakshya-based plan | Actuals view |
|---|---|---|
| Opening date (last actual Sunday) | 27 Sep | 27 Sep |
| First plan week starts (Monday) | 28 Sep | 28 Sep |
| Plan ends (Sunday) | 27 Dec | 27 Dec |
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
| Mumbai | 9.8% / 8.4% / 8.6% | 208 / 201 / 235 | 9.6% | 67.4% / 67.1% / 74.6% |
| Delhi NCR | 8.5% / 7.7% / 8.3% | 195 / 186 / 227 | 9.2% | 55.8% / 55.8% / 62.1% |
| Bangalore | 8.5% / 7.4% / 7.8% | 187 / 187 / 220 | 8.3% | 70.7% / 68.3% / 76.4% |
| Hyderabad | 11.9% / 10.3% / 10.3% | 198 / 193 / 226 | 12.8% | 70.1% / 67.0% / 76.4% |
| Chennai | 9.5% / 8.3% / 8.6% | 156 / 155 / 181 | 9.2% | 72.2% / 69.5% / 77.2% |
| Kolkata | 10.7% / 9.0% / 9.2% | 56 / 49 / 55 | 14.3% | 51.5% / 51.6% / 57.5% |
| Pune | 11.8% / 10.3% / 10.6% | 119 / 110 / 128 | 12.8% | 61.4% / 60.3% / 68.8% |
| **India** | **9.8% / 8.5% / 8.8%** | **1,118 / 1,082 / 1,272** | 10.2% | **65.2% / 64.1% / 71.8%** |

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

Cars reaching the fleet each week (India): 288 a week in w/c 28 Sep – 19 Oct; 230 a week in w/c 26 Oct – 23 Nov; 0 from w/c 30 Nov to w/c 21 Dec. City split: Mumbai 59/47, Bangalore 79/63, Hyderabad 79/63, Chennai 61/48, Pune 11/8, Delhi and Kolkata 0.

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

### C1 – Plan summary by city (end of w/c 21 Dec, Sun 27 Dec)

**Lakshya-based plan:**

| City | On road at start | **On road (plan)** | Lakshya | Plan − Lakshya | AOP Dec | Fleet | **Util** | Max util | Headroom | Recruitment (13 wks) | Peak week | Capacity | Weeks above capacity |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Mumbai | 2,649 | 3,491 | 3,381 | +110 | 3,116 | 4,487 | 77.8% | 75.0% | **−2.8%** | 2,925 | 312 | 250 | **3** |
| Delhi NCR | 2,231 | 2,550 | 2,468 | +82 | 2,845 | 3,970 | 64.2% | 62.0% | **−2.2%** | 2,664 | 270 | 246 | **3** |
| Bangalore | 1,929 | 2,785 | 2,769 | +16 | 2,468 | 3,462 | 80.5% | 79.5% | **−1.0%** | 2,622 | 290 | 194 | **8** |
| Hyderabad | 1,641 | 2,575 | 2,416 | +159 | 2,215 | 3,167 | 81.3% | 79.5% | **−1.8%** | 2,926 | 323 | 213 | **8** |
| Chennai | 1,752 | 2,407 | 2,306 | +101 | 2,163 | 2,989 | 80.5% | 79.5% | **−1.0%** | 2,273 | 234 | 178 | **8** |
| Kolkata | 546 | 623 | 599 | +24 | 815 | 1,035 | 60.2% | 60.0% | **−0.2%** | 693 | 74 | 96 | 0 |
| Pune | 985 | 1,190 | 1,143 | +47 | 1,196 | 1,653 | 72.0% | 70.0% | **−2.0%** | 1,599 | 156 | 146 | **3** |
| **India** | 11,733 | **15,621** | 15,082 | **+539** | 14,818 | 20,763 | **75.2%** | | | **15,701** | | 1,323 | 33 |

**Actuals view:**

| City | On road (plan) | Lakshya | Plan − Lakshya | Util | Max util | Recruitment (13 wks) | Weeks above capacity |
|---|---|---|---|---|---|---|---|
| Mumbai | 3,365 | 3,381 | −16 | 75.0% | 75.0% | 2,473 | 0 |
| Delhi NCR | 2,460 | 2,468 | −8 | 61.9% | 62.0% | 2,551 | 2 |
| Bangalore | 2,664 | 2,769 | −105 | 76.9% | 79.5% | 2,422 | 4 |
| Hyderabad | 1,964 | 2,416 | **−452** | 62.0% | 79.5% | 2,594 | 3 |
| Chennai | 2,246 | 2,306 | −60 | 75.1% | 79.5% | 2,085 | 0 |
| Kolkata | 584 | 599 | −15 | 56.5% | 60.0% | 798 | 0 |
| Pune | 1,132 | 1,143 | −11 | 68.5% | 70.0% | 1,559 | 0 |
| **India** | **14,416** | 15,082 | **−667** | **69.4%** | | **14,481** | 9 |

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
| 13 plan weeks | w/c 28 Sep – 21 Dec |
| "Avg 28 Sep – 21 Dec (cars, EIP: total)" | Attrition and recruitment: a week; util and on-road cars: average; cars added, cars sold and EIP: 13-week total |

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
   - The "13 weeks" row gives the plan-period figures.
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
| **Summary View** | Yes | City and fuel picker (B1). Weekly dashboard: 4 actual weeks + 13 plan weeks. Each block has a 2026 plan row, a 2026 actual row and a 2025 same-week row. Blocks: Util, On Road Cars, On road growth %, Recruitment, Net Attrition %, EIP Growth, FSE, Vendor, Referrals, Performance marketing, EIP %, Total car, Total buy, Total Sold, On Road Cars EIP / Own Now / L+DTO, Driver Acquisition. A "We are here" marker (yellow) and an Actual marker are shown. Colour scale: see section 5. |
| **Lakshya vs Plan vs LY** | Yes | See [section 11](#11-the-comparison-tab-lakshya-vs-plan-vs-ly). |
| **Inputs** | Yes | See [section 10](#10-inputs-tab-section-by-section-with-the-current-values). |
| **Lakshya Source** | Yes | Lakshya v4's own figures, typed as given. (1) Churn inputs: L+DTO book 31 Aug, churn rate a month, Own Now churn and rollover by month. (2) Weekly driver acquisition (L+DTO, Own Now, total) w/c 7 Sep – 28 Dec, with December re-split formulas and the "as given" weeks on the right. |
| **City tabs** (7) | Yes | The weekly engine, one row per week: 4 actual weeks (rows 2–5), 13 plan weeks, totals row, step rows. Columns: see below. |
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
| India | Oct | 65.2% / 65.2% | 13,038 / 12,946 | 9.8% / 9.8% | 1,118 / 1,314 | 5,591 / 6,572 | 1,382 / 1,382 | 290 / 290 | 235 / 235 |
|  | Nov | 64.1% / 64.1% | 13,409 / 13,305 | 8.5% / 8.5% | 1,082 / 830 | 5,408 / 4,152 | 918 / 918 | 253 / 253 | 235 / 235 |
|  | Dec | 71.8% / 71.8% | 15,066 / 14,955 | 8.8% / 8.8% | 1,272 / 1,659 | 3,816 / 4,977 | 0 / 0 | 178 / 178 | 141 / 141 |
|  | 13 weeks | 66.3% / 66.3% | 13,649 / 13,548 | 9.1% / 9.1% | 1,140 / 1,208 | 14,815 / 15,701 | 2,300 / 2,300 | 721 / 721 | 612 / 612 |
| Mumbai | Oct | 67.4% / 67.4% | 2,917 / 2,904 | 9.8% / 9.8% | 208 / 245 | 1,038 / 1,224 | 281 / 281 | 60 / 60 | 50 / 50 |
|  | Nov | 67.1% / 67.1% | 3,031 / 3,016 | 8.4% / 8.4% | 201 / 153 | 1,007 / 764 | 186 / 186 | 53 / 53 | 50 / 50 |
|  | Dec | 74.6% / 74.6% | 3,371 / 3,355 | 8.6% / 8.6% | 235 / 312 | 705 / 937 | 0 / 0 | 38 / 38 | 30 / 30 |
|  | 13 weeks | 69.0% / 69.0% | 3,066 / 3,051 | 9.0% / 9.0% | 212 / 225 | 2,750 / 2,925 | 467 / 467 | 151 / 151 | 129 / 129 |
| Delhi NCR | Oct | 55.8% / 55.8% | 2,309 / 2,303 | 8.5% / 8.5% | 195 / 210 | 976 / 1,049 | 0 / 0 | 84 / 84 | 8 / 8 |
|  | Nov | 55.8% / 55.8% | 2,266 / 2,260 | 7.7% / 7.7% | 186 / 161 | 932 / 804 | 0 / 0 | 73 / 73 | 8 / 8 |
|  | Dec | 62.1% / 62.1% | 2,482 / 2,475 | 8.3% / 8.3% | 227 / 270 | 681 / 811 | 0 / 0 | 52 / 52 | 5 / 5 |
|  | 13 weeks | 57.2% / 57.2% | 2,332 / 2,326 | 8.2% / 8.2% | 199 / 205 | 2,589 / 2,664 | 0 / 0 | 209 / 209 | 20 / 20 |
| Bangalore | Oct | 70.7% / 70.7% | 2,289 / 2,194 | 8.5% / 8.5% | 187 / 220 | 937 / 1,101 | 380 / 380 | 20 / 20 | 54 / 54 |
|  | Nov | 68.3% / 68.3% | 2,420 / 2,325 | 7.4% / 7.4% | 187 / 130 | 934 / 651 | 253 / 253 | 18 / 18 | 54 / 54 |
|  | Dec | 76.4% / 76.4% | 2,754 / 2,650 | 7.8% / 7.8% | 220 / 290 | 661 / 870 | 0 / 0 | 12 / 12 | 33 / 33 |
|  | 13 weeks | 71.1% / 71.1% | 2,447 / 2,349 | 7.9% / 7.9% | 195 / 202 | 2,532 / 2,622 | 633 / 633 | 50 / 50 | 141 / 141 |
| Hyderabad | Oct | 70.1% / 70.1% | 1,948 / 1,969 | 11.9% / 11.9% | 198 / 257 | 988 / 1,286 | 380 / 380 | 20 / 20 | 72 / 72 |
|  | Nov | 67.0% / 67.0% | 2,068 / 2,082 | 10.3% / 10.3% | 193 / 135 | 967 / 673 | 253 / 253 | 18 / 18 | 72 / 72 |
|  | Dec | 76.4% / 76.4% | 2,404 / 2,422 | 10.3% / 10.3% | 226 / 323 | 677 / 968 | 0 / 0 | 12 / 12 | 43 / 43 |
|  | 13 weeks | 70.3% / 70.3% | 2,100 / 2,117 | 10.9% / 10.9% | 202 / 225 | 2,632 / 2,926 | 633 / 633 | 50 / 50 | 188 / 188 |
| Chennai | Oct | 72.2% / 72.2% | 1,953 / 1,967 | 9.5% / 9.5% | 156 / 194 | 778 / 968 | 290 / 290 | 20 / 20 | 42 / 42 |
|  | Nov | 69.5% / 69.5% | 2,039 / 2,050 | 8.3% / 8.3% | 155 / 120 | 773 / 602 | 193 / 193 | 18 / 18 | 42 / 42 |
|  | Dec | 77.2% / 77.2% | 2,299 / 2,312 | 8.6% / 8.6% | 181 / 234 | 543 / 703 | 0 / 0 | 12 / 12 | 25 / 25 |
|  | 13 weeks | 72.3% / 72.3% | 2,066 / 2,079 | 8.8% / 8.8% | 161 / 175 | 2,094 / 2,273 | 483 / 483 | 50 / 50 | 110 / 110 |
| Kolkata | Oct | 51.5% / 51.5% | 558 / 552 | 10.7% / 10.7% | 56 / 53 | 278 / 267 | 0 / 0 | 20 / 20 | 5 / 5 |
|  | Nov | 51.6% / 51.6% | 549 / 544 | 9.0% / 9.0% | 49 / 41 | 244 / 205 | 0 / 0 | 18 / 18 | 5 / 5 |
|  | Dec | 57.5% / 57.5% | 604 / 597 | 9.2% / 9.2% | 55 / 74 | 166 / 221 | 0 / 0 | 12 / 12 | 3 / 3 |
|  | 13 weeks | 52.9% / 52.9% | 565 / 559 | 9.7% / 9.7% | 53 / 53 | 688 / 693 | 0 / 0 | 50 / 50 | 14 / 14 |
| Pune | Oct | 61.4% / 61.4% | 1,063 / 1,056 | 11.8% / 11.8% | 119 / 135 | 596 / 677 | 50 / 50 | 65 / 65 | 4 / 4 |
|  | Nov | 60.3% / 60.3% | 1,036 / 1,030 | 10.3% / 10.3% | 110 / 91 | 551 / 453 | 34 / 34 | 56 / 56 | 4 / 4 |
|  | Dec | 68.8% / 68.8% | 1,153 / 1,145 | 10.6% / 10.6% | 128 / 156 | 383 / 468 | 0 / 0 | 40 / 40 | 2 / 2 |
|  | 13 weeks | 62.7% / 62.7% | 1,073 / 1,066 | 10.9% / 10.9% | 118 / 123 | 1,530 / 1,599 | 84 / 84 | 161 / 161 | 10 / 10 |

**End of w/c 21 Dec (27 Dec), and where each city starts (last 8 weeks, actual)**

| City | End of w/c 21 Dec (27 Dec): util L / P | On-road L / P | Last 8 weeks: attrition | recruitment | util | on-road |
|---|---|---|---|---|---|---|
| India | 72.1% / 75.2% | 15,082 / 15,621 | 10.9% | 979 | 62.7% | 12,012 |
| Mumbai | 75.0% / 77.8% | 3,381 / 3,491 | 9.9% | 159 | 63.3% | 2,672 |
| Delhi NCR | 62.0% / 64.2% | 2,468 / 2,550 | 9.6% | 192 | 53.2% | 2,228 |
| Bangalore | 76.9% / 80.5% | 2,769 / 2,785 | 9.4% | 142 | 71.2% | 2,016 |
| Hyderabad | 76.9% / 81.3% | 2,416 / 2,575 | 13.4% | 158 | 68.8% | 1,752 |
| Chennai | 77.6% / 80.5% | 2,306 / 2,407 | 10.4% | 135 | 70.1% | 1,782 |
| Kolkata | 57.3% / 60.2% | 599 / 623 | 14.6% | 70 | 50.3% | 545 |
| Pune | 68.7% / 72.0% | 1,143 / 1,190 | 13.4% | 123 | 58.7% | 1,018 |

**Recruitment week by week**

| City | 28 Sep | 05 Oct | 12 Oct | 19 Oct | 26 Oct | 02 Nov | 09 Nov | 16 Nov | 23 Nov | 30 Nov | 07 Dec | 14 Dec | 21 Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **India Lakshya** | 1,415 | 1,356 | 1,169 | 985 | 666 | 565 | 769 | 1,283 | 1,433 | 1,358 | 1,550 | 1,487 | 779 |
| **India plan** | 1,321 | 1,321 | 1,304 | 1,304 | 1,321 | 711 | 711 | 910 | 910 | 910 | 1,659 | 1,659 | 1,659 |
| Mumbai plan | 245 | 245 | 245 | 245 | 245 | 133 | 133 | 166 | 166 | 166 | 312 | 312 | 312 |
| Delhi NCR plan | 210 | 210 | 210 | 210 | 210 | 111 | 111 | 194 | 194 | 194 | 270 | 270 | 270 |
| Bangalore plan | 220 | 220 | 220 | 220 | 220 | 112 | 112 | 143 | 143 | 143 | 290 | 290 | 290 |
| Hyderabad plan | 257 | 257 | 257 | 257 | 257 | 129 | 129 | 138 | 138 | 138 | 323 | 323 | 323 |
| Chennai plan | 194 | 194 | 194 | 194 | 194 | 112 | 112 | 126 | 126 | 126 | 234 | 234 | 234 |
| Kolkata plan | 60 | 60 | 43 | 43 | 60 | 35 | 35 | 45 | 45 | 45 | 74 | 74 | 74 |
| Pune plan | 135 | 135 | 135 | 135 | 135 | 80 | 80 | 98 | 98 | 98 | 156 | 156 | 156 |

### 13.2 Actuals view

**Month by month, every city**

| City | Month | Util % L / P | On-road avg L / P | Attrition % a week L / P | Recruitment a week L / P | Recruitment total L / P | Cars added L / P | Cars sold L / P | EIP net add L / P |
|---|---|---|---|---|---|---|---|---|---|
| India | Oct | 65.2% / 63.3% | 13,038 / 12,490 | 9.8% / 9.8% | 1,118 / 1,118 | 5,591 / 5,591 | 1,382 / 1,241 | 290 / 290 | 235 / 230 |
|  | Nov | 64.1% / 62.4% | 13,409 / 12,952 | 8.5% / 9.7% | 1,082 / 1,082 | 5,408 / 5,408 | 918 / 1,060 | 253 / 253 | 235 / 230 |
|  | Dec | 71.8% / 67.4% | 15,066 / 14,037 | 8.8% / 8.6% | 1,272 / 1,161 | 3,816 / 3,482 | 0 / 0 | 178 / 178 | 141 / 138 |
|  | 13 weeks | 66.3% / 63.9% | 13,649 / 13,025 | 9.1% / 9.4% | 1,140 / 1,114 | 14,815 / 14,481 | 2,300 / 2,301 | 721 / 721 | 612 / 598 |
| Mumbai | Oct | 67.4% / 66.7% | 2,917 / 2,875 | 9.8% / 9.8% | 208 / 208 | 1,038 / 1,038 | 281 / 281 | 60 / 60 | 50 / 130 |
|  | Nov | 67.1% / 69.6% | 3,031 / 3,126 | 8.4% / 8.9% | 201 / 201 | 1,007 / 1,007 | 186 / 186 | 53 / 53 | 50 / 130 |
|  | Dec | 74.6% / 72.9% | 3,371 / 3,279 | 8.6% / 7.1% | 235 / 143 | 705 / 428 | 0 / 0 | 38 / 38 | 30 / 78 |
|  | 13 weeks | 69.0% / 69.2% | 3,066 / 3,065 | 9.0% / 8.8% | 212 / 190 | 2,750 / 2,473 | 467 / 467 | 151 / 151 | 129 / 338 |
| Delhi NCR | Oct | 55.8% / 54.9% | 2,309 / 2,267 | 8.5% / 8.5% | 195 / 195 | 976 / 976 | 0 / 1 | 84 / 84 | 8 / -15 |
|  | Nov | 55.8% / 53.0% | 2,266 / 2,146 | 7.7% / 8.3% | 186 / 186 | 932 / 932 | 0 / 0 | 73 / 73 | 8 / -15 |
|  | Dec | 62.1% / 59.6% | 2,482 / 2,376 | 8.3% / 6.8% | 227 / 214 | 681 / 643 | 0 / 0 | 52 / 52 | 5 / -9 |
|  | 13 weeks | 57.2% / 55.2% | 2,332 / 2,246 | 8.2% / 8.1% | 199 / 196 | 2,589 / 2,551 | 0 / 1 | 209 / 209 | 20 / -39 |
| Bangalore | Oct | 70.7% / 70.5% | 2,289 / 2,147 | 8.5% / 8.5% | 187 / 187 | 937 / 937 | 380 / 304 | 20 / 20 | 54 / 103 |
|  | Nov | 68.3% / 70.0% | 2,420 / 2,374 | 7.4% / 8.8% | 187 / 187 | 934 / 934 | 253 / 329 | 18 / 18 | 54 / 103 |
|  | Dec | 76.4% / 74.7% | 2,754 / 2,588 | 7.8% / 7.4% | 220 / 184 | 661 / 551 | 0 / 0 | 12 / 12 | 33 / 62 |
|  | 13 weeks | 71.1% / 71.3% | 2,447 / 2,336 | 7.9% / 8.4% | 195 / 186 | 2,532 / 2,422 | 633 / 633 | 50 / 50 | 141 / 267 |
| Hyderabad | Oct | 70.1% / 63.3% | 1,948 / 1,777 | 11.9% / 11.9% | 198 / 198 | 988 / 988 | 380 / 366 | 20 / 20 | 72 / -14 |
|  | Nov | 67.0% / 58.7% | 2,068 / 1,826 | 10.3% / 12.8% | 193 / 193 | 967 / 967 | 253 / 267 | 18 / 18 | 72 / -14 |
|  | Dec | 76.4% / 61.0% | 2,404 / 1,936 | 10.3% / 11.8% | 226 / 213 | 677 / 639 | 0 / 0 | 12 / 12 | 43 / -8 |
|  | 13 weeks | 70.3% / 61.0% | 2,100 / 1,832 | 10.9% / 12.2% | 202 / 200 | 2,632 / 2,594 | 633 / 633 | 50 / 50 | 188 / -36 |
| Chennai | Oct | 72.2% / 70.9% | 1,953 / 1,873 | 9.5% / 9.5% | 156 / 156 | 778 / 778 | 290 / 239 | 20 / 20 | 42 / 45 |
|  | Nov | 69.5% / 68.6% | 2,039 / 2,026 | 8.3% / 8.5% | 155 / 155 | 773 / 773 | 193 / 244 | 18 / 18 | 42 / 45 |
|  | Dec | 77.2% / 73.8% | 2,299 / 2,209 | 8.6% / 9.3% | 181 / 178 | 543 / 534 | 0 / 0 | 12 / 12 | 25 / 27 |
|  | 13 weeks | 72.3% / 70.7% | 2,066 / 2,009 | 8.8% / 9.0% | 161 / 160 | 2,094 / 2,085 | 483 / 483 | 50 / 50 | 110 / 117 |
| Kolkata | Oct | 51.5% / 50.4% | 558 / 541 | 10.7% / 10.7% | 56 / 56 | 278 / 278 | 0 / 0 | 20 / 20 | 5 / -9 |
|  | Nov | 51.6% / 46.2% | 549 / 487 | 9.0% / 12.9% | 49 / 49 | 244 / 244 | 0 / 0 | 18 / 18 | 5 / -9 |
|  | Dec | 57.5% / 53.5% | 604 / 555 | 9.2% / 11.3% | 55 / 92 | 166 / 276 | 0 / 0 | 12 / 12 | 3 / -5 |
|  | 13 weeks | 52.9% / 49.5% | 565 / 523 | 9.7% / 11.7% | 53 / 61 | 688 / 798 | 0 / 0 | 50 / 50 | 14 / -23 |
| Pune | Oct | 61.4% / 58.5% | 1,063 / 1,010 | 11.8% / 11.8% | 119 / 119 | 596 / 596 | 50 / 50 | 65 / 65 | 4 / -10 |
|  | Nov | 60.3% / 56.7% | 1,036 / 968 | 10.3% / 11.2% | 110 / 110 | 551 / 551 | 34 / 34 | 56 / 56 | 4 / -10 |
|  | Dec | 68.8% / 65.6% | 1,153 / 1,094 | 10.6% / 10.1% | 128 / 137 | 383 / 412 | 0 / 0 | 40 / 40 | 2 / -6 |
|  | 13 weeks | 62.7% / 59.5% | 1,073 / 1,013 | 10.9% / 11.2% | 118 / 120 | 1,530 / 1,559 | 84 / 84 | 161 / 161 | 10 / -26 |

**End of w/c 21 Dec (27 Dec), and where each city starts (last 8 weeks, actual)**

| City | End of w/c 21 Dec (27 Dec): util L / P | On-road L / P | Last 8 weeks: attrition | recruitment | util | on-road |
|---|---|---|---|---|---|---|
| India | 72.1% / 69.4% | 15,082 / 14,416 | 10.9% | 979 | 62.7% | 12,012 |
| Mumbai | 75.0% / 75.0% | 3,381 / 3,365 | 9.9% | 159 | 63.3% | 2,672 |
| Delhi NCR | 62.0% / 61.9% | 2,468 / 2,460 | 9.6% | 192 | 53.2% | 2,228 |
| Bangalore | 76.9% / 76.9% | 2,769 / 2,664 | 9.4% | 142 | 71.2% | 2,016 |
| Hyderabad | 76.9% / 62.0% | 2,416 / 1,964 | 13.4% | 158 | 68.8% | 1,752 |
| Chennai | 77.6% / 75.1% | 2,306 / 2,246 | 10.4% | 135 | 70.1% | 1,782 |
| Kolkata | 57.3% / 56.5% | 599 / 584 | 14.6% | 70 | 50.3% | 545 |
| Pune | 68.7% / 68.5% | 1,143 / 1,132 | 13.4% | 123 | 58.7% | 1,018 |

**Recruitment week by week**

| City | 28 Sep | 05 Oct | 12 Oct | 19 Oct | 26 Oct | 02 Nov | 09 Nov | 16 Nov | 23 Nov | 30 Nov | 07 Dec | 14 Dec | 21 Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **India Lakshya** | 1,415 | 1,356 | 1,169 | 985 | 666 | 565 | 769 | 1,283 | 1,433 | 1,358 | 1,550 | 1,487 | 779 |
| **India plan** | 1,216 | 1,202 | 1,132 | 978 | 1,064 | 862 | 862 | 1,245 | 1,258 | 1,181 | 1,113 | 1,099 | 1,270 |
| Mumbai plan | 225 | 225 | 220 | 197 | 171 | 182 | 182 | 214 | 228 | 202 | 107 | 108 | 213 |
| Delhi NCR plan | 211 | 211 | 206 | 175 | 173 | 100 | 100 | 222 | 259 | 251 | 197 | 200 | 246 |
| Bangalore plan | 203 | 203 | 183 | 175 | 174 | 165 | 165 | 219 | 188 | 196 | 189 | 177 | 185 |
| Hyderabad plan | 220 | 220 | 187 | 154 | 206 | 173 | 173 | 212 | 224 | 186 | 213 | 213 | 213 |
| Chennai plan | 163 | 163 | 159 | 142 | 152 | 132 | 132 | 178 | 178 | 153 | 178 | 178 | 178 |
| Kolkata plan | 70 | 55 | 55 | 27 | 71 | 41 | 41 | 57 | 49 | 55 | 84 | 96 | 96 |
| Pune plan | 125 | 125 | 122 | 109 | 117 | 69 | 69 | 144 | 131 | 139 | 146 | 128 | 138 |

---

## 14. Key findings

1. **Start gap.**
   - We start below Lakshya: util 61.2% against 63.5%; on road 11,733 against Lakshya's 27 Sep book of 12,281.
   - Recruitment runs at 979 a week (last 8 weeks) against Lakshya's October 1,118.
   - Attrition runs at 10.9% against Lakshya's October 9.8%.
2. **This year against last year.** Recruitment is 17% lower than the same weeks last year (979 vs 1,174), and attrition is lower too (10.9% vs 12.2%).
3. **Matching monthly util needs front-loaded hiring.**
   - The Lakshya-based plan hires +196 a week above Lakshya in October, 252 below in November and +387 above in December.
   - That is 15,701 hires over 13 weeks against Lakshya's 14,815 (+886).
   - Util ends at 75.2% against 72.1%, with 15,621 cars on road against 15,082.
4. **Util ceiling breached in the Lakshya-based plan.** Every city ends above its maximum utilisation: Mumbai 77.8% (max 75.0%), Delhi NCR 64.2% (62.0%), Bangalore 80.5% (79.5%), Hyderabad 81.3% (79.5%), Chennai 80.5% (79.5%), Kolkata 60.2% (60.0%) and Pune 72.0% (70.0%).
5. **Hiring above proven capacity in the Lakshya-based plan:** 33 city-weeks in total. Bangalore, Hyderabad and Chennai have 8 weeks each; Mumbai, Delhi NCR and Pune have 3 each.
6. **On-road cars run about 100 below Lakshya each month even with util matched.** Our fleet is slightly smaller than Lakshya's, so the same util gives fewer cars on road.
7. **The Actuals view lands 667 cars short of Lakshya** (14,416 against 15,082, util 69.4%). Most of it is **Hyderabad (−452)**: attrition there runs 13.4% a week, and its December hiring is capped at its best week (213).
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
| 39 | One more sheet with the weekly plan exactly equal to Lakshya, plus a monthly summary tab | New sheet "Lakshya exact, week by week" (v2 engine, new comparison layout incl. on-road cars) with a Monthly Summary tab: Lakshya / Plan / Plan − Lakshya / Actual so far / Last year for Oct, Nov, Dec and the plan total |
| 40 | December should end at w/c 21 Dec, to match Lakshya | Plan back to 13 weeks ending Sun 27 Dec; Lakshya's December weeks as given (no re-split); all four sheets rebuilt |

---

## 16. Open points

1. **Lakshya-based plan, December hiring jump.**
   - Lakshya's December averages 71.8% util over only 3 weeks. To match that average, the plan hires 1,659 a week in December, which is 387 above Lakshya's December average.
   - In w/c 21 Dec Lakshya itself has only 779.
   - Over the plan that is 15,701 hires against Lakshya's 14,815.
   - **The up-and-down pattern:** util goes about 67% at the end of October → 63% in Diwali week → 75.2% on 27 Dec, and recruitment goes 1,314 → 830 → 1,659 a week.
   - A smoother alternative is to match each month's closing util instead of the average.
2. **Util ceiling breaches:** every city ends above its maximum utilisation in the Lakshya-based plan (see finding 4).
3. **Weeks above proven capacity:** 33 city-weeks in the Lakshya-based plan.
4. **Actuals view, Hyderabad:** 452 cars short. This needs either lower attrition (13.4% now) or hiring above its best week.
5. **Actuals view, Mumbai's December:** follows last year's uneven December weeks. It can be smoothed with the same December total.
6. **Actuals view, first week:** recruitment steps from 1,002 (last actual week) to 1,216 in w/c 28 Sep (+21%), because festival-week hires were moved earlier.
7. **New cars:** 571 October cars and 1,148 November cars are still to be ordered. At 5 weeks from order to road, October's are already late.
8. **v2:** still on the older comparison layout.
9. **Last-year cars for Aug 2025:** missing from the reporting DB pull (left blank).
10. **The new "Lakshya exact" sheet** is shared only with its owner so far.

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
  | `ly_pattern.py` | Last year's Diwali-aligned weekly pattern (14 weeks kept; the plan uses 13) |
  | `car_flows.py` | Actual cars added and sold by week |
  | `plan_history.py` | History, seasonality, capacity and the attrition trend |

- **Before every publish:**
  - The live sheet is compared formula by formula with the last published copy, to keep any manual edits and picks.
  - Every tab is scanned for errors (#REF!, #N/A and so on). Every publish so far had **0 errors**.
- **Repository:** `mithunjaiswar/mithunjaiswar`, branch `claude/pensive-mendel-s62wy1`. Docs:
  - `supply-plan/README.md`: technical description.
  - `supply-plan/CNG_Supply_Plan_Summary.md`: short manager summary.
  - `supply-plan/CNG_Supply_Plan_Full_Documentation.md`: this file.
