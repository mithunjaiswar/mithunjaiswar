# "collection_month" = this task (saved 24-Nov-2026)

When Mithun says **"collection_month pe kaam karna hain"**, it means this work.

Goal: build summed (aggregated) data from the raw tabs below, in the same raw-data style. Grain, metrics and where to put the output are not decided yet; ask Mithun.

## Source 1: Collections Monthly View
- Sheet: https://docs.google.com/spreadsheets/d/1tjLP_T-JAxqetxyKCA9wK85Yi8V2Kgq9PmkOga7_Aeg (id 1tjLP_T-JAxqetxyKCA9wK85Yi8V2Kgq9PmkOga7_Aeg)
- Tab: `car_recovery_data` (gid 1325204672), ~38K rows, 28 columns A:AB, one row per car recovery case:
  start_month, end_month, recovery_id, week_start, close_week, start_date, close_date, tat_days, tat_seconds,
  city, location, fuel_type, product_type, payment_habit, sd_amount, sd_bucket, partner_etid, car_number,
  created_by, agent_name, reason, remarks, final_status, cancel_reason, audit_dt, checkin_dt, jama_date, last_updated
- Other tabs in the same file: Dash, Raw_Data, monthly_active_data, collections_data, rejoin_data, BadDebt_Dash_V1/V2, Dash_V2, Raw_Data_V2, own_now_deposit, For_backend_push.

## Source 2: SSOT Everest Sourcing Scorecards
- Sheet: https://docs.google.com/spreadsheets/d/14hL5rbI66NHylDV2UvWW9mulzsYzLzyPKSpuoSofzg0 (id 14hL5rbI66NHylDV2UvWW9mulzsYzLzyPKSpuoSofzg0)
- Tab: `raw_performance` (gid 1439703784), ~20K rows, 81 columns. Grain = date x city x fuel_type (daily, from Dec-2022),
  with month, Week, year, Week Num. Metrics: fleet / allotted / active cars (model-wise), product EOD cars
  (dto, own_now, leasing, salary, rev_share + EIP / individual), newjoin / rejoin / resurrection (by channel),
  attrition, EIP add-on / drop-off, active_partners, avg_deposit_of_new_joins, Uber NULP, cars_ftd, inactive cars.
- Link given was gid 165188822 = `Weekly Scorecard` (daily pacing built on raw_performance: Total Recruitment,
  Net EIP add, Cars on Road, Week-ending Util; plan vs actual).
