# EV Supply Plan: RTA Availability View (Chat Record)

**Sheet:** [EV Oct - Dec Plan](https://docs.google.com/spreadsheets/d/1mObpq-fUYLUyS9JiWS3-WzdskIeNRNN0xbUCFU3TrII/edit) (original draft tab: Sheet71, gid 622828070)
**Data source used:** Everest Reporting DB (PostgreSQL, read-only), EV cars only (Xpres-T and Comet EV)
**History window:** 8 weeks, 3 Aug – 21 Sep 2026
**Forecast window:** 14 weeks, from 28 Sep 2026
**Status as of 29 Sep 2026:** the level-model rebuild was designed and the inputs are in the sheet, but the new city blocks have **not yet been written** (the last write was stopped by the user).

---

## 1. What was asked

Original request, in the user's words:

> This is the EV supply plan, I want to make now RTA Availability visibility …
> 1. Show how many cars will be visible in RTA, based on how many cars go out in the last 8-week average, and make a tab where I can put input. I will enter an input if any specific week goodness will come.
> 2. If the net allocation is happening in minus, the RTA will increase, but all the cars will not come direct to RTA; they will go to the garage.
> 3. Every day swaps will happen … the returned cars will go directly to the garage.
> 4. Now make the RTA availability view.

Links shared for the drop-off sheet (`1wyQi1znwifTQHkQv9P2v1m1UR6vqKmRWY2ATDl6H_mo`) and the repair sheet (`1xhjlTUk2B41nlr-HrQ5P4uGPWxSmTUFBJUn8A8ZQ6tE`). **Neither could be opened** (403 / not found through the Google connectors), so all history was pulled from the Everest DB instead.

Follow-up questions, in order:
1. What does "RTA to garage / other" mean?
2. What is "Other movement (balancing)"?
3. Why is Kolkata showing such high RTA?
4. RTA goes beyond total cars. How is this possible?
5. Add an explanation column (G) to the averages table: what it shows and where each number comes from.
6. Where does "Total RTA inflow" come from?
7. Add the source tab and column to the explanations.
8. Visible RTA looks unrealistically high. In Mumbai we usually have 5–10 RTA cars. Cross-check the last few months and find which metric adds the extra.
9. The 5–10 count is early morning; in the evening it is just 3 or 4.
10. "Go ahead and make the changes you suggested. Also look at last year's data around this time to see the RTA history around seasonality, where drop-offs were high, which might lead to a spike in RTA count."

---

## 2. Tabs built in the sheet

### 2.1 RTA Flow Data (sheetId 700001)
8-week history per city (5 cities × 8 weeks = rows 5–44, header in row 4).

| Col | Field | Source (Everest DB) |
|---|---|---|
| A | Week start | – |
| B | City | fleet_city via fleet_car.city_id |
| C | RTA at week start | car_status_log (last status before Monday = Ready To Allot) |
| D | RTA at week end | car_status_log |
| E | Driver drop-offs | car_deallocation + car_allocation (driver took no other car) |
| F | Drop-offs direct to RTA | car_deallocation + car_status_log (next status = Ready To Allot) |
| G | Drop-offs to garage | = E − F |
| H | Swaps (car returned) | car_deallocation + car_allocation (same driver, different car, from 12 h before to 24 h after) |
| I | Swap cars direct to RTA | car_deallocation + car_status_log |
| J | Garage to RTA | car_status_log (garage/repair status → Ready To Allot) |
| K | New allocations | car_allocation (not swaps) |
| L | Swap allocations | car_allocation (swaps) |
| M | RTA to garage / other | car_status_log (Ready To Allot → anything other than Alloted / On Road) |
| N | Other movement (balancing) | = D − (C + F + I + J − K − L − M) |

Status IDs used: 7 = Ready To Allot, 19 = Alloted, 11 = On Road, 24 = Garage Visit, 9 = Repair, 18 = Audit Failed, 21 = Hub Visit.

### 2.2 RTA Inputs (sheetId 700002): yellow cells are inputs

| Rows | Content |
|---|---|
| 4–7 | Setting per city (Mumbai, Delhi NCR, Bangalore, Hyderabad, Kolkata) |
| 5 | Current RTA (from Sheet71): 1, 17, 10, 5, 27 |
| 6 | DB RTA reference only: 20, 26, 195, 8, 92 |
| 7 | Swaps-per-day override (blank = use 8-week average) |
| 9 | First plan week = 2026-09-28 |
| 10 | History weeks = 8 |
| 11 | History start = B9 − 7×B10 |
| 12 | History end = B9 − 7 |
| 15–29 | **Goodness % grid**, 14 weeks × 5 cities (all 0% now; type 10% or 20% for a week) |
| 31–35 | **New (level model):** |
| 33 | Normal RTA level, morning: Mumbai **8**, Delhi 17, Bangalore 10, Hyderabad 5, Kolkata 27 |
| 34 | Evening RTA as % of morning: **50%** all cities |
| 35 | Share of extra RTA cars still not allocated next week (carry-over): **50%** all cities |

Only Mumbai's 8 comes from you (5–10 in the morning). The other cities' normal levels are **placeholders taken from the current RTA inputs and need confirming**.

### 2.3 RTA Availability (sheetId 700003): the view
- **Rows 4–19:** summary, 14 weeks × 5 cities plus total, for visible RTA (B–G) and shortfall (I–N).
- **Rows 22–36:** 8-week averages table (AVERAGEIFS over RTA Flow Data).
  - G–K (merged): "What this row means (Mumbai as example)"
  - L–O (merged): "Source: tab, column and system table"
- **Rows 40 / 61 / 82 / 103 / 124:** weekly city blocks for Mumbai / Delhi NCR / Bangalore / Hyderabad / Kolkata (weeks across B:O). Helper columns: O = "City column", P = city index.
- The chart originally added here was deleted by someone and has not been re-added.

---

## 3. The 8-week averages (Mumbai example, cars per week)

| Row | Meaning | Mumbai | Comes from |
|---|---|---|---|
| RTA at week start | Cars in Ready To Allot on Monday morning | 29 | Flow Data col C |
| Driver drop-offs | Drivers who returned the car and left | 46 | col E |
| Drop-offs direct to RTA | Returned cars going straight to RTA | 19 | col F |
| % drop-offs direct to RTA | 19 ÷ 46 | **42%** | calculated |
| Swaps (car returned) | Driver returns one car and takes another within 24 h | 71 | col H |
| Swap cars direct to RTA | Returned swap cars straight back to RTA | 11 | col I |
| % swap cars direct to RTA | 11 ÷ 94 (row 28 ÷ row 32) | **11%** | calculated |
| Garage to RTA | Repaired or checked cars that became ready; **the biggest RTA source** | 129 | col J |
| New allocations | RTA → new or rejoining drivers | 52 | col K |
| Swap allocations | RTA → drivers who came to swap | 94 | col L |
| Swaps per day | 94 ÷ 7 (matches the user's "about 10 a day") | 13.5 | calculated |
| RTA to garage / other | Left RTA without going to a driver | 27 | col M |
| Other movement | Unexplained gap | +16 | col N |
| **Net change / week** | In − out | **+1.6** | calculated |

Other cities:
- **% drop-offs direct to RTA:** Delhi 28%, Kolkata 34%.
- **RTA to garage / other:** Delhi 34, Bangalore 67, Kolkata 78, Hyderabad 0.
- **Other movement:** Delhi +3.9, Bangalore −6.0, Kolkata +4.6, Hyderabad +0.6.

---

## 4. Answers to the explanation questions

### 4.1 "RTA to garage / other"
These are cars that sat in RTA but **left RTA without going to a driver**. A car goes from Ready To Allot to:
- Garage Visit / Repair (damage, battery or charging, service due)
- Audit Failed (the pre-allocation check)
- Hub Visit / Complex Transfer
- Insurance, Fitness Parking, Police Custody, Key Issue, For Sale, and so on

The Kolkata and Bangalore values (78, 67) look inflated because many cars go RTA → garage → RTA within days, for daily hub checks or charging. Those cars are also counted in "Garage to RTA", so the two lines largely cancel out.

### 4.2 "Other movement (balancing)"
This is the plug that makes each history week add up: **actual RTA at week end − (start + tracked in − tracked out)**.

Mumbai, week of 3 Aug:
- Start: 20
- In: 7 + 4 + 128 = 139
- Out: 59 + 89 + 26 = 174
- By the flows, RTA should be −15. The actual count was 13, so the gap is **+28**.

Likely causes:
- New cars added to the fleet
- Inter-city or hub transfers
- Status changes that were never logged
- Timing differences between the allocation tables and the status log

Bank analogy: you start with ₹20, trace ₹139 in and ₹174 out, but the bank shows ₹13. The ₹28 gap is money you didn't track.

### 4.3 Why Kolkata showed high RTA
Kolkata's own plan has net allocation of **−21 and −20** in the weeks of 5 and 12 Oct. That pushed drop-offs from about 86 to about 110 a week. With 34% of drop-offs going straight to RTA, that is about 8 extra RTA cars a week, so RTA peaked at 44 around 12 Oct. It then fell to 0 by December as net allocation turned positive (+25, +44).

The DB figure of 92 RTA today (vs your 27) is probably inflated by fleet growth (259 → 332 cars) and the ETS handover cars ("Kol handover" tab, 113 cars) being marked Ready To Allot early. The sheet uses your 27.

**To confirm:** is the negative October net allocation in the Kolkata plan correct?

### 4.4 RTA going beyond total cars
Cause: **someone typed a fixed 2 over the row 34 formulas** ("RTA to garage / other") for Mumbai, Delhi, Bangalore and Kolkata. Garage → RTA stayed at 129 while RTA → garage dropped to 2, which added about 25 phantom cars a week.

| City | Total cars | RTA 28 Dec with the typed 2 | RTA 28 Dec with the formula |
|---|---|---|---|
| Mumbai | 784 | 403 | 56 |
| Delhi NCR | 381 | 327 | 0 |
| Bangalore | 265 | 988 | 80 |
| Kolkata | 332 | 1,064 | 0 |
| Hyderabad | 30 | 1 | 1 |

The formulas were later restored.

Other issues found in the plan (Combined All tab):
- **Delhi NCR:** plan on-road goes from 419 (16 Nov) to 639 (28 Dec) against 381 total cars; utilisation reaches 168%.
- **Hyderabad:** plan on-road goes from 31 to 43 against 30 total cars from 16 Nov.
- **Bangalore:** tight at 157 on road + 80 RTA = 237 of 265 cars. The DB also shows 447 Bangalore EVs vs 268 in the plan.
- The model has **no cap at total cars**.

Suggested fixes (not yet done):
- Move the override for RTA to garage to the Inputs tab.
- Cap visible RTA at total cars − on road − minimum garage stock.
- Add a check row for weeks where plan on-road exceeds the fleet.

### 4.5 "Total RTA inflow" (old model)
Total RTA inflow = Garage to RTA + drop-offs direct to RTA + swap cars back to RTA + goodness uplift.

Mumbai, 28 Sep:
- Inflow: 129 + (56 × 42% = 23) + (94 × 11% = 11) + 0 = **163**
- Drop-offs 56 = usual new allocations 52 − plan net (−3)
- Visible RTA = 1 + 163 − 55 − 94 − 27 + 16 ≈ **7**

---

## 5. Why the forecast was too high (reality check)

**Actual Mumbai RTA from the DB** (EVs in Ready To Allot, 10 AM daily):

| Month | Avg | Median | Min | Max |
|---|---|---|---|---|
| Jun | 14 | 13 | 1 | 40 |
| Jul | 6 | 5 | 1 | 19 |
| Aug | 23 | 16 | 2 | 55 |
| Sep | 18 | 17 | 1 | 40 |

- The September 7 AM and 8 PM counts are both about 19–20.
- The hub reality is 5–10 in the morning and 3–4 in the evening.
- So the **Everest status count overstates real RTA by about 10–15 cars**. Some cars are marked RTA but are not physically ready.
- There is **no build-up** over the months, yet the old forecast climbed from 7 to 59 by mid-November.

**What added the extra +58 cars by 16 Nov (Mumbai):**

| Cause | Extra cars | Problem |
|---|---|---|
| 1. Carrying the 8-week trend forward | +13 | The +1.6/week trend comes mostly from the +16 "Other movement" line. That was a swing, not a trend. |
| 2. Mixed net allocation definitions | +19 | Drop-offs = DB new allocations (52) − plan net. The plan's history averaged +1.25 but the DB's averaged +6.9, so even a normal week created about 6 phantom drop-offs. |
| 3. Negative plan net in Oct–early Nov | +26 | This is real, but the old model kept those cars in RTA forever instead of letting them be allocated. |

Core problem: the old model was a **running total**. In reality, extra RTA cars get allocated or held in the garage within 1–2 weeks.

---

## 6. New design: level-based RTA model (approved, partly applied)

**Principle:** visible RTA = the city's normal level (an input) × (1 + goodness) + extra cars from abnormal weeks only, and those extra cars fade out.

Per city block (rows b+1 … b+17, weeks across B:O):

| Row | Label | Formula logic (column B = first week) |
|---|---|---|
| b+1 | Week | = RTA Inputs B9, then +7 |
| b+2 | Plan net allocation | SUMIFS Combined All col J (city, "EV", week) |
| b+3 | Plan net allocation, normal (8-week avg) | AVERAGEIFS Combined All col J over the history window |
| b+4 | Difference vs normal | b+2 − b+3 |
| b+5 | Extra drop-offs | MAX(0, −diff) |
| b+6 | of which straight to RTA | extra drop-offs × % direct (row 26) |
| b+7 | of which to garage first | b+5 − b+6 |
| b+8 | Extra allocations out of RTA | MAX(0, diff) |
| b+9 | Extra swap drain (only if swap override is set) | (override − avg swaps/7) × 7 × (1 − swap % direct) |
| b+10 | Extra RTA cars carried from last week | Week 1: MAX(0, current RTA − normal) × carry %; later: MAX(0, previous week's extra) × carry % |
| b+11 | Extra RTA cars this week | carried + straight to RTA − extra allocations − swap drain |
| b+12 | Normal RTA level, morning | RTA Inputs row 33 |
| b+13 | Goodness % | RTA Inputs goodness grid |
| b+14 | RTA balance, morning | normal × (1 + goodness) + extra |
| b+15 | **Visible RTA, morning** | MAX(0, balance) |
| b+16 | **Visible RTA, evening** | morning × evening % (row 34) |
| b+17 | **Shortfall** | MIN(0, balance) |

Summary top table:
- Visible = row b+15 of each block (INDEX/MATCH on week).
- Shortfall = row b+17.

Planned text updates:
- **A2:** subtitle explaining the level model.
- **A4:** "Visible RTA cars, morning".
- **A37:** note that rows 23–36 are reference history. Only rows 26, 29, 32 and 33 feed the forecast; Other movement and the Everest RTA count are not used.

Expected result: Mumbai sits around 8, with a small bump in October (negative plan net), and a shortfall shows in weeks where net allocation is well above normal.

### Progress
- ✅ RTA Inputs rows 31–35 written and formatted, with notes.
- ✅ Formulas for all five blocks generated (scratchpad script `gen4.py` → `req2.json`).
- ⛔ **Not applied:** clearing A40:O145, writing the new blocks, copying column C → D:O, the summary formulas, the text and the formatting. The write was stopped by the user.

---

## 7. Still pending
1. Apply the level-model rebuild to the RTA Availability tab (see section 6), then read back and verify.
2. Update the explanation and source cells (G/L, rows 35–36) to say "Other movement" is now reference only.
3. **Seasonality check:** query the Everest DB for Oct–Dec 2025 weekly RTA snapshots and drop-offs by city around Dussehra, Diwali, Chhath and Christmas. The aim is to see whether high drop-off weeks caused RTA spikes, keeping in mind EV fleets were smaller last year. Then suggest goodness % or seasonality inputs.
4. Confirm the normal RTA levels for Delhi NCR, Bangalore, Hyderabad and Kolkata (currently placeholders).
5. Confirm the negative October net allocation in the Kolkata plan.
6. Fix the Delhi NCR and Hyderabad plans, where on-road exceeds total cars from mid-November.
7. Optional: re-add the chart; add a total-cars cap and a check row.
8. Optional: switch the sources to your Drop-off and Repair sheets once they are shared with the connector account.

---

## 8. Technical notes
- The DB table `car_status_daily` is stale (it ends Oct 2025), so `car_status_log` was used.
- Drop-offs are counted from `car_deallocation` joined to `car_allocation` on deallocation_id. The status log was too noisy because EVs check in daily.
- Swap definition: the same driver is allocated a different car from 12 h before to 24 h after a drop-off.
- Large window queries time out on the DB. A per-car lateral lookup (`ORDER BY created_at DESC LIMIT 1`) works.
- Swap % denominator fixed from I/H to I/L (row 29 = IF(B32=0,0,B28/B32)).
