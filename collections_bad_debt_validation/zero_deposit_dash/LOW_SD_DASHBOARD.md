# Zero & Low Deposit (Low SD) Monitoring Dashboard — Full Documentation

_Last reviewed: 16-Nov-2026 (live sheet + SQL in this folder)_

| | |
|---|---|
| **Sheet** | Zero & Low Deposit Monitoring Dashboard — `1zsGMzqah8XCVfDM7f7R-BeNmK5DU5MxqTJ89xPJ25Sw` |
| **Purpose** | Track pilots holding a car with zero / low security deposit (SD), every day: how much they owe (Live OS), whether they pay, when they cross their deposit (surpass), whether calling and car recovery act in time, and how much turns into bad debt. Also gives the daily calling list (Agent_action) and agent-wise performance (Agent_DoD / Agent_WoW). |
| **Data** | Everest Reporting DB (Postgres / Timescale), loaded by the SQL Automation sheet `collections_queries` (`1uKeBnDSiKO1Lyei-vadU66P3nUFfCL_pUemyKq4r7QE`). |
| **Refresh** | Automation runs about every 3 hours. Every tab is formulas on top of `raw` (no manual paste), except `agent_weekly`, `dash_exclusions` and `actioning_type_list`. |
| **Week** | Hisaab week = Monday to Sunday. D1 = Monday … D7 = Sunday. |

---

## 1. Data flow

```
 DB tables ──► raw_pilot_week_v7.sql ──(automation row 71)──► raw!A1:DA   (105 SQL columns)
                                                               │
                         agent_weekly ─► raw!DC  (Weekly Agent, formula)
                      dash_exclusions ─► raw!DB  (Include / Exclude, formula)
                   Daily_Trend filters ─► raw!DD  (row passes Daily_Trend filters, formula)
                                                               │
                 ┌───────────────┬──────────────┬──────────────┴───────────┐
            Daily_Trend      City_View       Agent_DoD               Agent_WoW
          (1 city, 21 days) (city x day)  (agent x 8 days)        (agent x 4 weeks)

 DB tables ──► agent_action_masterlist.sql ──(automation row 75)──► Agent_action!A2:BQ (69 columns)
                     agent_weekly ─► Agent_action!BR (agent_username, formula)
              actioning_type_list ─► Agent_action!BS (actioning_type, formula)
```

---

## 2. Key definitions

| Term | Definition |
|---|---|
| **Live OS** | End-of-day outstanding from `hissab_driver_live_os.live_os` (after that day's payment). **Negative = pilot owes.** Only rows with `is_active = 1` (car with the pilot that day). |
| **Active pilot (that day)** | Pilot has a Live OS row that day (raw Live OS D*n* is a number). |
| **Current Deposit** | Sum of `mv_deposits_raw.amount` for the pilot, excluding deposit types `OWNNOW_TO_OWNNOW` and `SD_TO_OWNNOW`. |
| **Deposit as of a day** | Current Deposit minus deposits dated after that day (rebuilds the deposit the pilot had on that day). |
| **Deposit at Allocation** | `sd_amount` of the pilot's latest join event (New Join / Rejoin / Resurrection) up to the week end, from `analytics.ssot_alloc_dealloc_full`. |
| **SD Bucket (at allocation)** | From Deposit at Allocation: `0 Deposit` (≤ 0), `1-3K`, `3-5K`, `5-10K`, `10K+`, `Unknown` (no join event found). |
| **Surpass (Deposit used up)** | Live OS < 0 **and** amount owed ≥ deposit as of that day. A 0-deposit pilot surpasses as soon as he owes anything. |
| **New Surpass** | First surpass day of the week, blank if he was already surpassed on the previous Sunday. |
| **Weekly OS** | Monday opening OS of the pilot in the India Collections dashboard (`collections_bad_debt_mv.total_os`, `for_collections = 1`). |
| **Collection** | Money received that day from `mv_daily_recovery`: razorpay, other positive, phonepe, positive adjustment, deposit-to-OS. |
| **WOS Collected** | Part of the collection that clears Weekly OS first (capped at Weekly OS). Week sum = India Collections dashboard "collected". |
| **ELC / Non ELC** | ELC = tenure < 30 days (same as Calling Masterlist). Non_ELC = 30 days or more. |
| **Payment Habit** | `last_week_payment_habit` from the collections MV (Defaulter, Regular, etc.). |
| **Product (EIP split)** | Leasing is split into `Leasing - EIP` / `Leasing - Single`. Other values: D2O, EV_D2O, EV_Leasing, Revenue Share, Fixed Pay, Own Now. |
| **In Collections Dash (1/0)** | 1 = pilot is in the India Collections dashboard that week. 0 = only in Live OS (e.g. joined mid-week). |

### 2.1 Critical rule (same as Calling Masterlist MasterTab "Risk_Type")

OS = amount owed (positive number). Deposit = current deposit (min 0). Rent = daily rent.

| Product | Critical when |
|---|---|
| D2O | Deposit > 0 and OS ≥ 70% of deposit |
| Leasing - Single, EV | Deposit − OS ≤ 1 day rent |
| Revenue Share, Fixed Pay | Deposit > 0 and OS ≥ deposit |
| Leasing - EIP | OS ≥ 25,000 |
| Own Now | OS ≥ 30,000 |
| **Any product** | Also critical if surpassed that day. OS ≤ 0 is never critical. |

- **Critical – Morning (AM)**: rule on the OS at the **start** of the day (Live OS before that day's payment). This is the fixed morning calling list. Morning also counts OS ≥ deposit.
- **Critical – EOD**: same rule on the **end-of-day** Live OS (after payment).
- **Moved out of Critical** = Morning − EOD.

### 2.2 Bad debt

| Type | Meaning | Amount |
|---|---|---|
| **1 – Active bad debt** | Pilot is still active that day and surpassed (Live OS ≥ deposit) | Live OS above deposit = −Live OS − deposit |
| **2 – Non-active bad debt (left)** | Pilot had Live OS earlier in the week but none on this day (car gone), and his last Live OS was above deposit | Last Live OS of the week above deposit |

The type and amount are stored per day in raw `CM:CS` (Bad Debt Type D1-D7) and `CT:CZ` (Bad Debt Amt D1-D7). Monday can never be type 2, because there is no earlier day in that week.

### 2.3 Stage Today (raw `BS`, also in Agent_action)

| Stage | Condition (first match wins) |
|---|---|
| 6. Car Recovery Closed | Recovery case closed in the week |
| 5. In Car Recovery | Recovery case open |
| 0. Not Active | No Live OS today |
| 4. Owes >= Deposit - START RECOVERY | Surpassed today |
| 3. Critical (MasterTab rule) | Critical EOD today |
| 2. Owes - not critical yet | Live OS < 0 |
| 1. Paid Up | Otherwise |

### 2.4 Action Tag (raw `CL`, also in Agent_action)

| Tag | Condition |
|---|---|
| P0 - Critical (In car recovery) | Critical EOD and recovery case open |
| P0 - Critical (Not in car recovery) | Critical EOD, no open recovery case |
| P1 - Near surpass (<=1 day rent to deposit) | Owes, and deposit left ≤ 1 day rent |
| P2 - OS not collected | Owes today, or Weekly OS not fully collected |
| (blank) | Nothing to act on |

---

## 3. DB sources

| Table | Used for |
|---|---|
| `analytics.collections_bad_debt_mv` | Weekly rows (city, product, weekly OS, payment habit, tenure, EIP). `for_collections = 1`. |
| `hissab_driver_live_os` | Daily Live OS, rent, weekly OS (active rows). |
| `mv_daily_recovery` | Daily collection. |
| `mv_deposits_raw` | Deposit now and deposit as of each day. |
| `analytics.ssot_alloc_dealloc_full` / `_base` | Join events, deposit at allocation, city / product fallback, cars held. |
| `fleet_driver` | Driver id ↔ Employee ID (ETM). |
| `public.collections_calling_data_raw` | Attempts / connects per day, last disposition. |
| `car_dead_km` | GPS km on Mondays (Week Start GPS). |
| `recovery_cars` + `recovery_status_logs` | Car recovery cases (start, close; close = complete / failed / cancelled). |
| `car_allocation`, `crm.lead_driver`, trips / km tables | Agent_action only (open allocation, lead id, trips, km, ND days). |

Date filters are written with `current_date` directly (not a CTE value) so Timescale can skip old chunks. Without this the query times out.

---

## 4. Automation (`collections_queries` sheet)

| Row | Target tab | Start | Run | Clear range | SQL file |
|---|---|---|---|---|---|
| 71 | `raw` | A1 | TRUE | DA10000000 | `raw_pilot_week_v7.sql` |
| 72 | `dispo` | A1 | FALSE | C10000000 | `dispo_daily.sql` (tab deleted; row switched off) |
| 75 | `Agent_action` | A2 | TRUE | BQ15000 | `agent_action_masterlist.sql` |

Column meaning in `collections_queries`: B = query, C = clear, D = sheet id, E = tab, F = start cell, G = Run (TRUE / FALSE), H = clear range, I = last run, J = status.

**Manual run:** set G = TRUE on the row and trigger the automation. Check I / J for `SQL: SUCCESS | GSHEET: SUCCESS`.

> Do not run `raw` while `hissab_driver_live_os` is being refreshed (Monday hisaab). The output comes out half-empty (Live OS mostly NaN). Re-run after the refresh.

---

## 5. Tabs

| Tab | Type | What it is |
|---|---|---|
| **Daily_Trend** | Dashboard | One city, last 21 days, all metric sections (see §7). Filters in B1:B5. |
| **City_View** | Dashboard | City × day for key metrics, with product filter blocks (see §8). |
| **Agent_DoD** | Dashboard | Agent × last 8 days, 9 metrics (see §9). |
| **Agent_WoW** | Dashboard | Agent × last 4 weeks, 12 metrics (see §9). |
| **Agent_action** | Calling list | Today's calling list, MasterTab columns (see §10). |
| **raw** | Data | Pilot × week, 4 weeks (see §6). |
| **agent_weekly** | Input | Week, Employee ID, agent username (agent allocation). |
| **dash_exclusions** | Input | Date + Employee ID to exclude from the dashboards. |
| **actioning_type_list** | Input | D2O partner IDs with actioning type (all "Incentive" now). Anyone not listed = "Penalty". |
| **lists** | Hidden | Dropdown values and helper cells (e.g. `R10` = latest day number used by WoW). |
| **Read me!** | Help | Metric definitions for Daily_Trend. |
| **Sheet8** | Scratch | Not used by any dashboard. |

---

## 6. `raw` tab — column map (A:DD)

One row per **pilot per hisaab week**, last 4 weeks including the current one (~47.6K rows; ~10.2K per week). Population = collections MV rows of the week **plus** pilots with an active Live OS row that week.

| Col | Name | Notes |
|---|---|---|
| A | Week | Monday of the hisaab week |
| B | City | MV, else latest allocation |
| C | Product Type | |
| D | Employee ID | ETM |
| E | EIP / Single | |
| F | In Collections Dash (1/0) | |
| G | Deposit at Allocation | |
| H | SD Bucket (at allocation) | 0 Deposit / 1-3K / 3-5K / 5-10K / 10K+ / Unknown |
| I | Current Deposit | |
| J | Car Recovery Close Date | if closed this week |
| K | Week Start GPS | GPS Active / GPS Inactive / No Car (Monday) |
| L | Weekly OS (dash) | same as India Collections dash |
| M | Weekly OS (incl. live-only pilots) | |
| N | Collection Week Total | |
| O | Weekly OS Collected (capped, = dash) | |
| P | Total OS (latest live) | latest Live OS of the week |
| Q | Payment Habit | |
| R | ELC / Non ELC | tenure < 30 = ELC |
| S | Tenure Days | |
| T | Join Type (this week) | New Join / Rejoin / Existing |
| U | Last Join Type | |
| V | Last Join Date | |
| W | Daily Rent | |
| X | First Surpass Date | |
| Y | Car Recovery (week) | No / Open / Closed |
| Z | Car Recovery Start | |
| AA:AG | Live OS D1-D7 | blank = not active / future day |
| AH:AN | Collection D1-D7 | |
| AO:AU | WOS Collected D1-D7 | |
| AV:BB | Surpass D1-D7 | 1 / 0 |
| BC:BI | Attempts D1-D7 | |
| BJ:BP | Connects D1-D7 | |
| BQ | Product (EIP split) | |
| BR | Days Since Join | |
| BS | Stage Today | §2.3 |
| BT:BZ | MT Critical AM D1-D7 | morning critical 1/0 |
| CA:CG | MT Critical EOD D1-D7 | day-end critical 1/0 |
| CH | Surpassed after last join (4w, 1/0) | funnel |
| CI | Car recovery raised after last join (4w, 1/0) | funnel |
| CJ | Car recovered / case closed after last join (4w, 1/0) | funnel |
| CK | New Surpass Date (not surpassed day before) | |
| CL | Action Tag | §2.4 |
| CM:CS | Bad Debt Type D1-D7 | 1 / 2 / NaN |
| CT:CZ | Bad Debt Amt D1-D7 | |
| DA | Last Updated | IST time of the SQL run |
| **DB** | Dash Status (exception list) | **formula** — `Exclude` if (week date, ID) is in `dash_exclusions`, else `Include` |
| **DC** | Weekly Agent | **formula** — agent from `agent_weekly` for (week, ID), else `Unassigned` |
| **DD** | ok_2_Daily_Trend | **formula** — 1 if Include and passes Daily_Trend filters B2:B5 |

The SQL fills A:DA, and automation clears only up to DA, so the formula columns DB:DD survive every refresh.

---

## 7. Daily_Trend

- **Filters:** B1 City, B2 Product, B3 SD Bucket, B4 Payment Habit, B5 ELC (`All` = no filter). They apply through raw `DD`.
- **Layout:** row 7 = day number (1-7), row 8 = week Monday, row 9 = date, data from row 10, 21 day columns. A red date = Monday (Weekly OS resets).

| Section | Metrics |
|---|---|
| Pilots & Joins | Active pilots, of which 0 Deposit, New joins + rejoins, of which 0 Deposit |
| Rent vs Paid | Live OS that day, Paid towards rent that day (only money after Weekly OS is cleared), Rent paid % (day and week to date, max 100%), Rent generated WTD |
| Collection | Weekly OS, New OS this week, Total OS, Collected WTD, Collected %, Weekly OS collected that day, Weekly OS collected % WTD, Pending OS at day end |
| Critical & Calling | Critical Morning, Critical Day end, Moved out %, Critical Attempted / Connected, disposition split (7 buckets), Critical NOT called, All pilots called, Connect % |
| Car Recovery | Existing / New / Recovered, TAT, Pending (0-2, 3-5, 6-7, 8-14, 15+ days), Deposit used up, with recovery raised, Needed car recovery (no recovery), Recovery raised %, Newly crossed deposit, Newly crossed − new recovery |
| Join Funnel (All) | Joined → crossed deposit → recovery raised → recovered; Crossed deposit with NO recovery; NON-FUNNEL event-date counts |
| Bad Debt | Type 1 pilots / amount / % of total OS / per-day change / avg; Type 2 same; Total bad debt amount |

Example formula (Active pilots):
`=COUNTIFS(raw!$A$2:$A,C$8, raw!$B$2:$B,$Z$1, raw!$DD$2:$DD,1, INDEX(raw!$AA$2:$AG,0,C$7),">-1E+15")`
— `INDEX(…,0,day#)` picks the Live OS column of that weekday; `">-1E+15"` = "is a number".

Disposition buckets (from `dispo_daily.sql`, last call of the day): OS Recovery / Promise, Unclear, Busy / Hang up / No response, App / Payment / Hisaab issue, Car recovery, Other, No disposition.

---

## 8. City_View

- Row 1 = product block title, row 2 = product filter (`*` = all), row 3 = dates. Each product block (All, Leasing - Single, …) sits side by side.
- Every metric block: header row, `*` total row, then 7 cities (Mumbai, Kolkata, Bangalore, Delhi NCR, Hyderabad, Chennai, Pune).
- Metrics: Active pilots, Live OS pending at day end, Collection that day, Critical day end, Critical NOT called, New car recovery raised, Needed car recovery (no recovery), Active bad debt amount, Non-active bad debt amount.
- Uses raw `DB = "Include"` and `BQ` (product) directly, **not** the Daily_Trend filters.

Example: `=COUNTIFS(raw!$A$2:$A,B$3-WEEKDAY(B$3,3), raw!$B$2:$B,$A7, raw!$BQ$2:$BQ,B$2, raw!$DB$2:$DB,"Include", INDEX(raw!$AA$2:$AG,0,WEEKDAY(B$3,2)),">-1E+15")`

---

## 9. Agent_DoD and Agent_WoW

Both use only SUMIFS / COUNTIFS on `raw` (no helper tabs).

| | Agent_DoD | Agent_WoW |
|---|---|---|
| City filter | A2 (`*` = all India) | A2 |
| Row 3 | Metric name | Metric name |
| Row 4 | Dates (last 8 days, latest = TODAY()) + DoD | Week Mondays (last 4 weeks) + WoW |
| Row 5 | `*` = all agents total | `*` = all agents total |
| Row 6+ | Agents (auto list) | Agents (auto list) |
| Metrics | Active pilots, Collection, WOS collected, Attempts, Connects, Connect %, Critical EOD pilots, Surpass pilots, Bad debt amount | Pilots (in dash), Weekly OS, OS collected, Recovery %, Attempts, Connects, Connect %, Attempts per pilot, Critical EOD (week end), Surpass (week end), Bad debt amount (week end) |

**Agent list (A6), both tabs:**
`=IFERROR(SORT(UNIQUE(FILTER(raw!DC2:DC, raw!DC2:DC<>"", raw!DB2:DB="Include", raw!A2:A>=B4-WEEKDAY(B4,3), IF($A$2="*",raw!B2:B<>"",raw!B2:B=$A$2)))),"")`

**Active pilots (DoD):**
`=COUNTIFS(INDEX(raw!$AA$2:$AG,0,WEEKDAY(B$4,2)),">-1E+15", raw!$A$2:$A,B$4-WEEKDAY(B$4,3), raw!$DC$2:$DC,$A5, raw!$B$2:$B,$A$2, raw!$DB$2:$DB,"Include")`

**Pilots in dash (WoW):** `=COUNTIFS(raw!$A$2:$A,B$4, raw!$F$2:$F,1, raw!$DC$2:$DC,$A5, raw!$B$2:$B,$A$2, raw!$DB$2:$DB,"Include")`

"Week end" metrics in WoW take D7 for past weeks and today's day number (`lists!R10`) for the current week.

> With A2 = one city, row 5 shows only that city (e.g. Delhi NCR ≈ 2.2K active). Put `*` in A2 for all India (≈ 10.2K).

Number format: `[>=1000]+0.0,"K";[<=-1000]0.0,"K";0`.

---

## 10. Agent_action (daily calling list)

Same columns and order as **[Calculation Sheet] Collections: Calling Masterlist V2.0 → MasterTab**, current week only.

- **Population:** this hisaab week's collections list (`collections_bad_debt_mv`, `for_collections = 1`) + every partner with an open car allocation today.
- **Row 1:** group labels. **Row 2:** header. **Data from row 3.** SQL writes A2:BQ (69 columns).

| Group | Columns |
|---|---|
| Partner | week, date, partner_et_id |
| Partner Details | lead_id, partner_name, city |
| Product | product_type, elc_filter, car_numbers |
| Collections & Deposit | OS_Bucket, DP_Bucket, negative_os, total_recovery, net_os, recovery_pct, razorpay / other / phonepe recovery, adjustments, dp_to_os, current_deposit |
| Partner Status | active / inactive, last_payment_habit, Last Week OS, Car Count |
| Current Week Rentals | rented days, lease rent, fare_total, cash collected, subscription charges |
| Live OS | Total Current OS, Current OS Surpass SD |
| Partner Risk | Is_in Car Recovery, **Critical - Now (EOD)** |
| Uber ND Data | last / current week active and ND days, GPS / Uber / dead km, Uber trips |
| Last Payment & Jama Date | last_paid_date, last_jama_date |
| Call History | att_total, conn_total, last attempt / connect time, last_disposition, att_today, conn_today |
| Trips & Actioning | GPS_Tag, allocation_type, acceptance_rate, trip_tier, target_trips, min_remaining_trips |
| Partner Tag | Collections Tag, **Critical - Morning List (Still / Out)**, ND Tag, RANK, Yesterday Remarks, Car_Recovery Pending TAT, L2W tag, last_jama_date (1w), Last Week OS + Recovery, car_model |
| Today Action | **Stage Today**, **Action Tag** |
| Agent (formula) | **BR agent_username** (from agent_weekly; `Agent Missing` if none), **BS actioning_type** (D2O: from actioning_type_list, default Penalty) |

Bucket definitions:
- **OS_Bucket:** 0-500, 500-1K, 1-2K, 2-3K, 3-5K, 5-10K, 10-15K, 15-20K, 20-25K, 25-30K, 30K+
- **DP_Bucket:** 0-3K, 3-5K, 5-10K, 10-15K, 15-20K, 20-25K, 25-30K, 30-50K, 50K+
- **Collections Tag:** Full Paid (≥ 100% or < Rs 100 left) / Partial Paid / Not Paid
- **Critical - Now (EOD):** `Critical_Risk` on the latest Live OS.
- **Critical - Morning List (Still / Out):** pilot was critical on yesterday's EOD OS → `Critical_Risk` if still critical now, `Out of Critical` if he paid out.

Deliberate differences vs MasterTab:
1. Total Current OS = latest Live OS (not a sheet estimate).
2. Last week active / ND days = last week Mon–Sun (MasterTab formula had a date bug).
3. GPS_Tag also for Own Now (MasterTab checked "OWN", which never matched).
4. car_model keeps the year, so the Own Now 20K rule can match.
5. L2W tag computed from the collections MV (the MasterTab notpaid import is #REF!).

---

## 11. Repo files (`collections_bad_debt_validation/zero_deposit_dash/`)

| File | What |
|---|---|
| `raw_pilot_week_v7.sql` | `raw` tab query (automation row 71) — current |
| `raw_pilot_week.sql` | Old version (kept for history) |
| `agent_action_masterlist.sql` | `Agent_action` query (row 75) |
| `dispo_daily.sql` | Call disposition per pilot per day (row 72, off) |
| `sheet_builder/agent_wow_dod_sumifs.py` | Builds Agent_DoD / Agent_WoW formulas (current) |
| `sheet_builder/city_view.py` | Builds City_View |
| `sheet_builder/daily6.py` | Builds Daily_Trend (v6) |
| `sheet_builder/*.py` (others) | Older builders (eye, zero, journey, daily2-5, m4) |

---

## 12. Known issues / open items (16-Nov-2026)

| # | Issue | Impact | Fix |
|---|---|---|---|
| 1 | **`mv_daily_recovery` has no data after 08-Nov.** | Collection, WOS collected, Rent paid, Recovery % and "collected from bad debt" show **0 for 09-Nov onwards** in every tab, even though `hissab_driver_live_os.recovery` has ~Rs 5–11M per day. | Get the MV refresh fixed (data team), or switch the raw SQL collection to `hissab_driver_live_os.recovery` as a fallback. |
| 2 | Agent_action (row 75) last status `TIMEOUT (>15 min)` on 15-Nov 18:29. | Calling list not refreshed since then. | Re-run, or optimize the query (same approach as the sd_bucket fix). |
| 3 | `dispo` tab was deleted and row 72 is off. | Daily_Trend disposition rows show 0. | Restore the tab and set row 72 Run = TRUE, or remove those rows. |
| 4 | Bad debt "Joined this week & left" and "Weekly collection pilot left" are both coded as type 2. | Read me! lists 3 types; the dash shows 2 (Active / Non-active). | Fine as is; update Read me! wording if needed. |
| 5 | Read me! says raw refreshes from row 72. | Wrong reference. | Raw is row 71, dispo is row 72. |
| 6 | Raw run during the Monday hisaab refresh gives incomplete data. | Live OS NaN for many pilots. | Re-run row 71 after `hissab_driver_live_os` is updated. |
| 7 | Raw blanks are not empty: the automation writes nulls as `NaN`, a pgAdmin paste writes `NULL`. | A COUNTIFS with only `""` (or only one of them) never matches; "no Live OS yet" rows showed 0 (fixed 17-Nov). | Count blanks with `ARRAYFORMULA(SUM(COUNTIFS(..., {"NULL","NaN",""})))`; find numbers with `">-1E+15"`. |

---

### 17-Nov: Deposit at Allocation + SD buckets

- raw G "Deposit at Allocation" = deposit balance at the END of the allocation day (deposit already held from before + paid that day) = deposit now - deposits dated after the allocation day. Before it was only `sd_amount` paid on that allocation, so a rejoiner who paid 0 but already had a deposit showed 0.
  The higher of this balance and `sd_amount` is used (sd_amount is sometimes booked a day late).
- raw H "SD Bucket (at allocation)" = `0 Deposit` / `<3K` / `3-5K` (3,000-5,000) / `5K+` / `Unknown` (lists!C).
- City_View A2 = deposit bucket filter (All / 0 Deposit / <3K / 3-5K / 5K+ / Unknown); BP1 holds the COUNTIFS criterion (`*` or `=<bucket>`), added to every City_View formula.

### 17-Nov additions: joiners with no live OS yet

- Raw `pop` now also takes every New Join / Rejoin / Resurrection of the 4 weeks from `ssot_alloc_dealloc_full`, so a pilot allocated today shows up even before `hissab_driver_live_os` has a row (0-deposit tracking).
- Daily_Trend row 14 "of which allocated, no Live OS yet" = joins of that day whose Live OS for that day is blank (`NaN` / `NULL` / empty); row 15 = same and SD bucket `0 Deposit`.
- City_View rows 107-139: three blocks (New joins + rejoins, of which 0 Deposit, Allocated that day no Live OS yet), city x day.
- Cross-check 17-Nov vs DB (joiners with no live OS row on the join day): 10-Nov 65 / 11-Nov 28 / 12-Nov 23 / 13-Nov 42 / 14-Nov 33 / 15-Nov 6 / 16-Nov 0; City_View showed 64 / 28 / 23 / 42 / 33 / 6 / 0.

---

## 13. Quick checks (health)

| Check | Expected |
|---|---|
| `collections_queries!J71` | `SQL: SUCCESS … | GSHEET: SUCCESS` with ~45–50K rows |
| Active pilots, current week (City_View `*` row) | ~10–10.5K per day |
| raw `DA` (Last Updated) | Within the last 3–4 hours |
| raw `DC` | No `Unassigned` for pilots that are in `agent_weekly` |
| Collection D*n* for yesterday | Non-zero (if 0, see issue 1) |
