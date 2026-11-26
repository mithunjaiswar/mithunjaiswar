# `collections_calling_masterlist_collate` has loaded no data since 20 Nov 2026

**Reported:** 26 Nov 2026, Mithun (Collections)
**DAG:** `collections_calling_masterlist_collate`, owner Raja. Runs daily at 23:00 IST and writes to `public.mv_collections_calling_masterlist`.
**Status:** Every run shows **success**, but no rows have been inserted since 21 Nov.

---

## 1. What is broken

| Table | Latest `snapshot_date` | Latest `loaded_at` |
|---|---|---|
| `mv_collections_calling_masterlist` | **2026-11-20** | 2026-11-20 23:01 |
| `collections_calling_data_raw` (calls, separate DAG) | 2026-11-26 | 2026-11-26 13:33 (working) |

Check query:

```sql
select max(snapshot_date), max(loaded_at) from mv_collections_calling_masterlist;
```

## 2. Why: the header check fails for every city

`pull_and_clear` checks row 2 of each city's `Calling_Masterlist` tab against `COLUMNS`, **by position and exact name**.
On a mismatch, the `try/except` prints `ERROR, moving to next city` and skips that city.
When every city is skipped, the task prints `No data pushed.` and returns normally, so Airflow marks the run **success**.

Log from the run `scheduled__2026-11-25T17:30:00+00:00`, shortened:

```
[Bangalore] ERROR, moving to next city: [Bangalore] header mismatch -> col 1: expected 'week' but found 'Week (Mon)'; col 2: expected 'date' but found 'Data Date'; col 3: expected 'agent_username' but found 'Agent'; col 4: expected 'partner_et_id' but found 'Employee ID'; ...
[Chennai]   ERROR ... same
[Delhi NCR] ERROR ... col 5: expected 'lead_id' but found 'partner_et_id'; col 6: expected 'partner_name' but found 'partner_et_id'; ... col 13 ...
[Hyderabad] ERROR ... same as Bangalore
[Kolkata]   ERROR ... same
[Mumbai]    ERROR ... same
[Pune]      ERROR ... same
Skipped cities: ['Bangalore', 'Chennai', 'Delhi NCR', 'Hyderabad', 'Kolkata', 'Mumbai', 'Pune']
No data pushed.
```

Run history:

| Run (IST night) | Result in DB |
|---|---|
| 19 Nov | 11,494 rows, all 7 cities ✅ |
| 20 Nov | 6,234 rows: Chennai, Hyderabad, Mumbai, Pune. **Bangalore, Delhi NCR, Kolkata skipped** |
| 21 – 25 Nov | **0 rows**, all 7 cities skipped |

## 3. Why the headers changed

There are two separate causes.

### 3a. Six cities: the sheet layout changed (Bangalore, Chennai, Hyderabad, Kolkata, Mumbai, Pune)

From 19 Nov the city `Calling_Masterlist` tabs are filled by the Apps Script `sync_calling_masterlist.gs`. It copies the current week from the zero sheet `raw_v2` tab. The tab layout is now:

| | Old layout (what the DAG expects) | New layout (in the sheets now) |
|---|---|---|
| Row 1 | title | section names |
| Row 2 | header, snake_case (`week`, `date`, `agent_username`, ...) | header, readable names (`Week (Mon)`, `Data Date`, `Agent`, `Employee ID`, ...) |
| Row 3 | **first data row** | meaning of each column |
| Row 4 | data | **first data row** |
| Columns | 76 columns, `Yesterday Remarks` at BL, agent input BM:BX | A:BU pilot data printed by the script (new columns such as `Stage Today`, `Action To Take`, `Joined at 0 Deposit`), **BV:CH agent input** (`Call Status` ... `Remarks`), CI `Actioning Tag` (formula) |

Mumbai sheet `1sGaKUCpf1JCqgvoBulZ21oZ8mKWnKbHpJwRGvyfeQGw`, row 2 now:

```
A Week (Mon) | B Data Date | C Agent | D Employee ID | E Lead ID | F Pilot Name | G City | H Product | I ELC / Non-ELC |
J Car Numbers (now) | K OS Bucket | L Deposit Bucket Now | M Weekly OS to Collect (Rs) | N Collected This Week (Rs) |
O Weekly OS Left (Rs) | P Collection % | Q Razorpay (Rs) | R Other Payment (Rs) | S PhonePe (Rs) | T Positive Adjustment (Rs) |
U Deposit to OS (Rs) | V Deposit Now (Rs) | W Active / Inactive (now) | X Payment Habit | Y Last Week Closing OS (Rs) |
Z Cars Held This Week | AA Days Rented This Week | AB Rent This Week (Rs) | AC Uber Earnings (Rs) | AD Cash Collected (Rs) |
AE Uber Subscription (Rs) | AF Live OS Now (Rs) | AG Live OS + Deposit (Rs) | AH In Car Recovery | AI Critical Now (EOD) |
AJ Days With Car (last week) | AK Not-Driven Days (last week) | AL Days With Car | AM Not-Driven Days | AN GPS km (week) |
AO Uber km (week) | AP Dead km (week) | AQ Uber Trips (week) | AR Last Paid Date | AS Last Jama Date (4 weeks) |
AT Calls Attempted (week) | AU Calls Connected (week) | AV Last Attempt Time | AW Last Connect Time | AX Last Disposition |
AY Calls Attempted Today | AZ Calls Connected Today | BA GPS Yesterday | BB Allocation Type (D2O) | BC Actioning Type |
BD Acceptance Rate | BE Trip Tier | BF Target Trips | BG Min Remaining Trips | BH Collection Status | BI Morning List Status |
BJ ND Yesterday | BK Rank in City | BL Recovery Pending Days | BM L2W Payment Tag | BN Last Jama Date (this + last week) |
BO Last Week OS + Recovery (Rs) | BP Car Model (now) | BQ Stage Today | BR Action To Take | BS Joined at 0 Deposit |
BT Last Join Date | BU Yesterday Remarks | BV Call Status | BW Collections Disposition | BX 0 DP Pitch Disposition |
BY ND Disposition | BZ Critical Risk Disposition | CA Minimum Uber Trips Pitch | CB Current Driving Status | CC Other Platform |
CD Daily Earning w/o Uber | CE Driver Confirmation | CF Follow-up Date | CG Remarks | CH Actioning Tag
```

### 3b. Delhi NCR: header row 2 was damaged

Delhi sheet `1EgvSmWCBriuIhZWg3XNI5_Smz-U3YwIS4xZ5ohtZIDc` still has the **old** layout, but cells **E2:M2 all say `partner_et_id`**. This looks like an accidental drag-fill.
The sheet also shows "Updated: 6 Days Ago": the data in it is still for the 16 Nov week (date 20 Nov), so its own refresh has stopped too.

## 4. Impact

- **Missing snapshots:** no daily snapshot for **21–25 Nov** for any city. Bangalore, Delhi NCR and Kolkata are also missing **20 Nov**.
- **Downstream data stale after 20 Nov:** everything that reads this table, including:
  - Critical days (`risk_type` / `critical_risk_tag`)
  - Live OS last week (`total_current_os`) and paid status (`collections_tag`)
  - Yesterday remarks
  - The Own Now churn / recovery validity view (Central Car Recovery Dash)
  - raw_v2 "Yesterday Remarks", calling dashboards
- **Agent input not lost:** the skipped tabs were **not cleared**, so the agent input currently in the sheets is still there. The missing past days cannot be rebuilt.

## 5. Fix

### 5a. DAG: read the new layout by header **name**, and stop hiding failures

1. `DATA_START_ROW = 4`. Row 3 is now the column-meaning row.
2. Look up each column by its row 2 name instead of by position. Suggested mapping (new sheet header → DB column):

```python
COLUMNS = [
    ("Week (Mon)", "week", "date"),
    ("Data Date", "date", "date"),
    ("Agent", "agent_username", "text"),
    ("Employee ID", "partner_et_id", "text"),
    ("Lead ID", "lead_id", "int"),
    ("Pilot Name", "partner_name", "text"),
    ("City", "city", "text"),
    ("Product", "product_type", "text"),
    ("ELC / Non-ELC", "elc_filter", "text"),
    ("Car Numbers (now)", "car_numbers", "text"),
    ("OS Bucket", "os_bucket", "text"),
    ("Deposit Bucket Now", "dp_bucket", "text"),
    ("Weekly OS to Collect (Rs)", "negative_os", "num"),
    ("Collected This Week (Rs)", "total_recovery", "num"),
    ("Weekly OS Left (Rs)", "net_os", "num"),
    ("Collection %", "recovery_pct", "pct"),
    ("Razorpay (Rs)", "razorpay_recovery", "num"),
    ("Other Payment (Rs)", "other_recovery", "num"),
    ("PhonePe (Rs)", "phonepe_recovery", "num"),
    ("Positive Adjustment (Rs)", "adjustments", "num"),
    ("Deposit to OS (Rs)", "dp_to_os", "num"),
    ("Deposit Now (Rs)", "current_deposit", "num"),
    ("Active / Inactive (now)", "active_inactive", "text"),
    ("Payment Habit", "last_payment_habit", "text"),
    ("Last Week Closing OS (Rs)", "last_week_os", "num"),
    ("Cars Held This Week", "car_count", "int"),
    ("Days Rented This Week", "current_week_rented_days", "int"),
    ("Rent This Week (Rs)", "current_week_lease_rent", "num"),
    ("Uber Earnings (Rs)", "current_week_fare_total", "num"),
    ("Cash Collected (Rs)", "current_week_cash_collected", "num"),
    ("Uber Subscription (Rs)", "current_week_subscription_charges", "num"),
    ("Live OS Now (Rs)", "total_current_os", "num"),
    ("Live OS + Deposit (Rs)", "current_os_surpass_sd", "text"),   # was a Yes/No flag, now a number (see note)
    ("In Car Recovery", "is_in_car_recovery", "text"),
    ("Critical Now (EOD)", "risk_type", "text"),                  # 'Critical_Risk' as before
    ("Days With Car (last week)", "last_week_active_days", "int"),
    ("Not-Driven Days (last week)", "last_week_nd_days", "int"),
    ("Days With Car", "current_week_active_days", "int"),
    ("Not-Driven Days", "current_week_nd_days", "int"),
    ("GPS km (week)", "current_week_gps_kms", "num"),
    ("Uber km (week)", "current_week_uber_kms", "num"),
    ("Dead km (week)", "current_week_dead_kms", "num"),
    ("Uber Trips (week)", "current_week_uber_trips", "int"),
    ("Last Paid Date", "last_paid_date", "date"),
    ("Last Jama Date (4 weeks)", "last_jama_date", "date"),
    ("Calls Attempted (week)", "att_total", "int"),
    ("Calls Connected (week)", "conn_total", "int"),
    ("Last Attempt Time", "last_attempt_time", "time"),
    ("Last Connect Time", "last_connect_time", "time"),
    ("Last Disposition", "last_disposition", "text"),
    ("Calls Attempted Today", "att_today", "int"),
    ("Calls Connected Today", "conn_today", "int"),
    ("GPS Yesterday", "gps_tag", "text"),
    ("Allocation Type (D2O)", "allocation_type", "text"),
    ("Actioning Type", "actioning_type", "text"),
    ("Acceptance Rate", "acceptance_rate", "pct"),
    ("Trip Tier", "trip_tier", "text"),
    ("Target Trips", "target_trips", "int"),
    ("Min Remaining Trips", "min_remaining_trips", "int"),
    ("Collection Status", "collections_tag", "text"),            # Full Paid / Partial Paid / Not Paid
    ("Morning List Status", "critical_risk_tag", "text"),        # DECIDE: meaning changed (see note)
    ("ND Yesterday", "nd_tag", "text"),
    ("Rank in City", "rank", "int"),
    ("Yesterday Remarks", "yesterday_remarks", "text"),
    ("Call Status", "call_status", "text"),
    ("Collections Disposition", "collections_disposition", "text"),
    ("ND Disposition", "nd_disposition", "text"),
    ("Critical Risk Disposition", "critical_risk_disposition", "text"),
    ("Minimum Uber Trips Pitch", "minimum_uber_trips_pitch", "text"),
    ("Current Driving Status", "current_driving_status", "text"),
    ("Other Platform", "other_platform", "text"),
    ("Daily Earning w/o Uber", "daily_earning_wo_uber", "num"),
    ("Driver Confirmation", "driver_confirmation", "text"),
    ("Follow-up Date", "follow_up_date", "date"),
    ("Remarks", "remarks", "text"),
    # Optional new columns (need ALTER TABLE ADD COLUMN in _ensure_table):
    # ("0 DP Pitch Disposition", "zero_dp_pitch_disposition", "text"),
    # ("Stage Today", "stage_today", "text"),
    # ("Action To Take", "action_to_take", "text"),
    # ("Joined at 0 Deposit", "joined_at_0_deposit", "text"),
    # ("Actioning Tag", "actioning_tag", "text"),
]
```

3. Read each column by name, not by position:

```python
header = [_norm(h) for h in values[HEADER_ROW - 1]]
index_of = {}
missing = []
for sheet_header, db_column, _ in COLUMNS:
    try:
        index_of[db_column] = header.index(_norm(sheet_header))
    except ValueError:
        missing.append(sheet_header)
if missing:
    raise ValueError(f"[{city}] missing headers: {missing}")

rows = [
    [(row[index_of[c]] if index_of[c] < len(row) else "") for c in DB_COLS]
    for row in values[DATA_START_ROW - 1:]
    if row and str(row[0]).strip() != ""
]
```

4. **Clear only the agent call-capture columns BV:CG** (`Call Status` ... `Remarks`). Do not clear A:BU: the sync script prints those, and it also fills `Yesterday Remarks` (BU). Keep C (`Agent`) and CH (`Actioning Tag`, a formula) as well.
   Better still, find the clear range from the header names `Call Status` → `Remarks`, so a column move does not break it again.
5. **Fail loudly:** if any city is skipped, raise at the end of the task (after pushing the cities that worked), so the run turns red and alerts:

```python
if skipped_cities:
    raise RuntimeError(f"Cities skipped: {skipped_cities}")
```

**Two notes that need a decision:**
- **`critical_risk_tag`:** the old "Critical Risk Tag" column is gone. The closest new one is "Morning List Status" (`Still Critical` / `Out of Critical`), which means something different. Logic that checks `critical_risk_tag = 'Critical_Risk'` (Own Now recovery validity) will match nothing. Either map it to `Critical Now (EOD)` too, or leave it blank and use `risk_type` only.
- **`current_os_surpass_sd`:** this was a Yes/No flag. The new "Live OS + Deposit (Rs)" is a number (negative = owes more than the deposit). Either store the number, or store `Yes` when it is below 0.

### 5b. Delhi NCR sheet

1. Fix the header row: set **E2:M2** to `lead_id, partner_name, city, product_type, elc_filter, car_numbers, OS_Bucket, DP_Bucket, negative_os`.
   Or move Delhi to the same sync script and layout as the other cities. Then the DAG fix above covers Delhi too.
2. Check why the Delhi sheet's own refresh has stopped ("Updated: 6 Days Ago").

## 6. How to check after the fix

1. Trigger the DAG once manually, or wait for the 23:00 run. The log should show `Inserted N rows` and `Cleared <city>` for all 7 cities, and no `ERROR, moving to next city`.
2. Run this in the DB:

```sql
select snapshot_date, source_tab, count(*)
from mv_collections_calling_masterlist
where snapshot_date >= current_date - 1
group by 1, 2 order by 1, 2;
```

   Expect 7 cities for today's date, with row counts close to the 19 Nov run (11,494 rows in total).

3. Spot check a few pilots: `risk_type`, `total_current_os` and `collections_tag` should match the sheet values.

## 7. Files and IDs

| What | Where |
|---|---|
| DAG | Airflow `collections_calling_masterlist_collate` (`/opt/airflow/dags/collections_calling_masterlist_collate.py`) |
| Sheet sync script (new layout) | `collections_bad_debt_validation/city_agent_tracking/sync_calling_masterlist.gs` (data source: zero sheet `raw_v2`) |
| City sheets read by the DAG | Bangalore `1cqtYRXzgrfT9C32oPo50JY0jUDbd0j2LGIHgXAaDv3g` · Chennai `192b4gADIm3KfvshyjeuEvP0DGgVgIPzGehe_uChnE4I` · Delhi NCR `1EgvSmWCBriuIhZWg3XNI5_Smz-U3YwIS4xZ5ohtZIDc` · Hyderabad `1GLzLpDT8enQgXEjmxkuRAypxbToBY8UYiMxnocERGjE` · Kolkata `1vPodl3Ds77tyFT7FAk4F7fYAu9A5RSdC8NRF5Y2MmZI` · Mumbai `1sGaKUCpf1JCqgvoBulZ21oZ8mKWnKbHpJwRGvyfeQGw` · Pune `1YLqE7H-itBtb76LRTOKCAmR28ttQwzu_pNkplAweiso` (tab `Calling_Masterlist`) |
| Target table | `public.mv_collections_calling_masterlist` (no index; a full scan takes about 36 s, so an index on `(partner_et_id, snapshot_date)` would help every reader) |
