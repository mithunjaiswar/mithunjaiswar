"""Add / replace the 'Issues_and_Fix_Steps' tab: why each column does not match, steps to fix, SQL to check manually.
Usage: python3 issues_tab.py <D> <token.json>"""
import sys, json, time
import requests

D, TOKEN = sys.argv[1], sys.argv[2]
API = 'https://sheets.googleapis.com/v4/spreadsheets'
TAB = 'Issues_and_Fix_Steps'

W = "'2026-09-28'"  # week used in the sample queries
MV = 'analytics.collections_bad_debt_mv'
BASE = f"from {MV} m\nwhere m.hissab_week = {W} and m.for_collections = 1"

HISAAB_CTE = f"""with h as (
  select m.hissab_week, m.city, m.partner_etm, m.location, m.revenue_type as pg_revenue_type,
         string_agg(distinct case when f.business_vertical_id = 6 then 'D2O'
                                  when f.business_vertical_id = 2 and f.leasing_type ilike 'D2O%' then 'EV on D2O plan'
                                  when f.business_vertical_id = 2 then 'EV_Leasing'
                                  when f.leasing_type ilike '%OWN%' then 'Own Now'
                                  else 'Leasing' end, ' + ') as hisaab_revenue_type
  from {MV} m
  left join fleet_leasing_weeklydata f
         on f.partner_etm = m.partner_etm and f.start_date >= m.driven_week and f.start_date < m.hissab_week
  where m.hissab_week = {W} and m.for_collections = 1
  group by 1,2,3,4,5)"""

ISSUES = [
 # (column, issue, rows 06-Oct, status 07-Oct, owner, steps, sql, sheet check)
 ('revenue_type -> revenue_type',
  'PG revenue_type is blank. In the 06-Oct run every PG row with a blank location also had a blank revenue_type: PG could not resolve the partner hub (Delhi Honda Sector 35 Office / Sukhrali, Kolkata) plus 107 Chennai (Vanagram) partners. At hisaab these partners were D2O / Own Now.',
  '21-Sep 400 | 28-Sep 389 | 05-Oct 354', 'Fixed for 21-Sep and 28-Sep in the 07-Oct refresh (0 blanks). 05-Oct still has 353 blanks / 318 blank locations.', 'PG (data team)',
  '1. Derive revenue_type from the driven-week hisaab row (fleet_leasing_weeklydata: business_vertical_id + leasing_type), not from the hub lookup.\n2. Add missing hubs to the location mapping (Honda Sector 35 Office, Delhi-Sukhrali, Kolkata, Chennai Vanagram).\n3. Re-run the MV and re-check with the query (expect 0 rows).',
  HISAAB_CTE + "\nselect * from h where pg_revenue_type is null order by city, partner_etm;",
  'Filter Raw_Data on the same week + ET ID; revenue_type there should equal hisaab_revenue_type.'),
 ('revenue_type -> revenue_type',
  'PG shows a different product than the hisaab record of the driven week (e.g. hisaab Leasing, PG D2O). Sheet matches hisaab.',
  '21-Sep 160 | 28-Sep 145 | 05-Oct 142', '07-Oct refresh: 32 / 54 / 147 rows still differ.', 'PG (data team)',
  '1. In the MV, take revenue_type from fleet_leasing_weeklydata rows with start_date between driven_week and hissab_week - 1.\n2. Do not use the latest / current allocation or the hisaab-week row.\n3. Re-run the MV and re-check (expect 0 rows except mid-week changes).',
  HISAAB_CTE + "\nselect * from h\nwhere hisaab_revenue_type not like '%+%' and hisaab_revenue_type <> 'EV on D2O plan'\n  and pg_revenue_type <> hisaab_revenue_type\norder by city, partner_etm;",
  'Sheet value should equal hisaab_revenue_type.'),
 ('revenue_type -> revenue_type',
  'Partner changed product inside the same driven week (two hisaab rows, e.g. D2O + Leasing). Sheet and PG each picked a different one - both exist in hisaab.',
  '21-Sep 82 | 28-Sep 70 | 05-Oct 67', 'Still present (rule not agreed).', 'Business decision, then both',
  '1. Agree one rule, e.g. use the LAST hisaab row of the driven week (max start_date) or the product with most rental days.\n2. Apply the same rule in the Sheet query and in the PG MV.',
  HISAAB_CTE + "\nselect * from h where hisaab_revenue_type like '%+%' order by city, partner_etm;\n\n-- detail for one partner:\nselect partner_etm, start_date, end_date, business_vertical_id, leasing_type, car_number, active_days\nfrom fleet_leasing_weeklydata where partner_etm = 'ETB060010' and start_date >= '2026-09-14' order by start_date;",
  'Check which product the Sheet picked for these partners.'),
 ('revenue_type -> revenue_type',
  'EV car (business vertical 2) on a D2O plan (leasing_type D2O SINGLE / EIP). Sheet labels it EV_Leasing / EV_Rent To Own, PG labels it D2O.',
  '21-Sep 63 | 28-Sep 69 | 05-Oct 69', 'Still present (63 / 70 / 71).', 'Business decision, then both',
  '1. Agree the label for EV-on-D2O (e.g. EV_Rent To Own).\n2. Map business_vertical_id = 2 + leasing_type like D2O% to that label in both Sheet and PG.',
  HISAAB_CTE + "\nselect * from h where hisaab_revenue_type = 'EV on D2O plan' order by city, partner_etm;",
  'Sheet shows EV_Leasing / EV_Rent To Own for these partners.'),
 ('product_type -> product_type',
  'Follows revenue_type: when PG revenue_type is blank PG product_type falls back to SINGLE (Sheet D2O / Own Now). Also PG product_type = EIP while eip_tag = 0.',
  '21-Sep 655 | 28-Sep 619 | 05-Oct 598', '07-Oct: EIP with eip_tag 0 = 88 rows on 05-Oct.', 'PG (data team)',
  '1. Fix revenue_type first (issues 1-2).\n2. Derive product_type from revenue_type + eip_tag so they can never disagree.',
  f"select m.partner_etm, m.city, m.revenue_type, m.product_type, m.eip_tag\n{BASE}\n  and (m.revenue_type is null or (m.product_type = 'EIP' and coalesce(m.eip_tag,0) = 0))\norder by m.city, m.partner_etm;",
  'Compare product_type in Raw_Data for the same partners.'),
 ('lead_id -> lead_id',
  'Sheet lead_id is different from crm.lead_driver; PG lead_id matches CRM for all 123 rows (every employee has one lead).',
  '21-Sep 71 | 28-Sep 38 | 05-Oct 14', 'Sheet issue - no PG change needed.', 'Sheet owner',
  '1. Refresh the lead_id lookup in the Sheet from crm.lead_driver (hawkeye_employee_id -> lead_id).\n2. Re-check with the query.',
  f"select m.partner_etm, m.lead_id as pg_lead_id, l.lead_id as crm_lead_id\nfrom {MV} m\nleft join crm.lead_driver l on l.hawkeye_employee_id = m.partner_etm\nwhere m.hissab_week = {W} and m.for_collections = 1\n  and m.partner_etm in ('ETB09951','ETB060121','ETB064215');",
  'Sheet lead_id for these partners should equal crm_lead_id.'),
 ('city -> city',
  "Sheet city = 'NA' for 20 partners (Sheet city lookup missing); 4 partners have a different city.",
  '21-Sep 21 | 28-Sep 2 | 05-Oct 1', 'Sheet issue.', 'Sheet owner',
  "1. Fix the Sheet city lookup for the 'NA' partners.\n2. For the 4 others check the partner's city in fleet_driver.",
  f"select m.partner_etm, m.city as pg_city, m.location\n{BASE}\n  and m.partner_etm in ('ETB062415','ETB52366','ETP035643','ETP09703');",
  "Filter Raw_Data city = 'NA'."),
 ('negative_os -> total_os',
  'Matches for 99.98% of rows; 5 Kolkata partners differ by small amounts.',
  '21-Sep 2 | 28-Sep 0 | 05-Oct 3', 'Need to Deep Dive.', 'Data team',
  '1. Check OS ledger for these 3 partners (adjustment posted after one of the refreshes?).',
  f"select m.hissab_week, m.partner_etm, m.total_os, m.weekly_os, m.prev_carryforward_os, m.os_to_deposit, m.last_updated\nfrom {MV} m\nwhere m.hissab_week in ('2026-09-21','2026-10-05') and m.partner_etm in ('ETK17122','ETK17354','ETK022328');",
  'Compare negative_os in Raw_Data.'),
 ('current_week_os -> weekly_os  /  prev_carry_forward -> prev_carryforward_os',
  'Definition difference. PG: total_os = weekly_os + prev_carryforward_os + os_to_deposit, and PG keeps a positive (advance) carry-forward. Sheet: prev_carry_forward is floored at 0 / only the part of old OS recovered, and current_week_os = negative_os - prev_carry_forward.',
  'weekly_os: 4,815 / 4,753 / 4,809; prev_cf: 3,038 / 3,035 / 3,203', 'Still present (definition).', 'Business decision, then both',
  '1. Agree one definition of carry-forward (show positive advance or floor at 0?) and whether OS-to-deposit belongs to current week OS.\n2. Implement the same formula in Sheet and PG. total_os already matches, so only the split changes.',
  f"select m.partner_etm, m.total_os, m.weekly_os, m.prev_carryforward_os, m.os_to_deposit,\n       m.total_os - (m.weekly_os + coalesce(m.prev_carryforward_os,0) + coalesce(m.os_to_deposit,0)) as should_be_zero,\n       least(coalesce(m.prev_carryforward_os,0),0) as sheet_style_prev_cf,\n       m.total_os - least(coalesce(m.prev_carryforward_os,0),0) as sheet_style_current_week_os\n{BASE}\n  and (m.prev_carryforward_os > 0 or m.os_to_deposit is not null);",
  'Compare current_week_os / prev_carry_forward with the sheet_style_* columns.'),
 ('dp_to_os -> os_to_deposit',
  'Not the same metric. PG os_to_deposit = weekly deposit instalment taken from OS (-500 / -1000). Sheet dp_to_os = deposit adjusted against OS as recovery.',
  '4,658 / 4,395 / 3,081', 'Not comparable.', 'Data team',
  '1. Do not compare these two.\n2. If dp_to_os is needed in PG, add it as a new column from mv_daily_recovery (recovery_type = deposit_to_os).',
  "select employee_id, date_trunc('week', date)::date as week_start, sum(amount) as deposit_to_os\nfrom mv_daily_recovery\nwhere recovery_type = 'deposit_to_os' and date >= '2026-09-21' and date < '2026-09-28'\ngroup by 1,2 order by 3 desc;",
  'Compare with dp_to_os in Raw_Data for week 21-Sep.'),
 ('total_recovery -> total_collected_amount_in_week',
  '100% match for 21-Sep and 28-Sep. Only the in-progress week 05-Oct differs (collections posted after the PG refresh).',
  '21-Sep 0 | 28-Sep 0 | 05-Oct 1,573', 'Timing only.', 'Process',
  '1. Validate only closed hisaab weeks, or refresh Sheet and PG at the same time.',
  f"select m.partner_etm, m.total_collected_amount_in_week, m.collection_till_wed, m.last_updated\nfrom {MV} m where m.hissab_week = '2026-10-05' and m.for_collections = 1 order by 2 desc nulls last;",
  'Re-pull Raw_Data after the same refresh time.'),
 ('till_wed_100pct -> collection_till_wed',
  'Sheet caps Mon-Wed collection at 100% of OS (till_wed_100pct); PG stores the actual uncapped amount.',
  '853 / 1,091 / 1,809', 'Definition.', 'Business decision',
  '1. Either add a capped column in PG = LEAST(collection_till_wed, -total_os) or compare Sheet against the capped value.',
  f"select m.partner_etm, m.total_os, m.collection_till_wed,\n       least(coalesce(m.collection_till_wed,0), greatest(-m.total_os,0)) as till_wed_capped_like_sheet\n{BASE}\n  and coalesce(m.collection_till_wed,0) > greatest(-m.total_os,0);",
  'till_wed_100pct in Raw_Data should equal till_wed_capped_like_sheet.'),
 ('bad_debt_rec -> bad_debt_collected',
  'PG logic issue: bad_debt_collected is filled with the whole week collection even when the partner has no bad debt (bad_debt_amount = 0 / NULL). Sheet bad_debt_rec = 0.',
  '6,451 / 6,384 / 2,242', '07-Oct: still 6,076 / 6,015 / 2,249 rows.', 'PG (data team)',
  '1. In the MV set bad_debt_collected = 0 when bad_debt_amount is NULL or 0.\n2. Count only recovery against the bad-debt amount (cap at -bad_debt_amount).',
  f"select m.partner_etm, m.bad_debt_amount, m.bad_debt_collected, m.total_collected_amount_in_week\n{BASE}\n  and coalesce(m.bad_debt_amount,0) = 0 and coalesce(m.bad_debt_collected,0) > 0;",
  'bad_debt_rec in Raw_Data is 0 for these partners.'),
 ('bad_debt -> bad_debt_amount',
  'Matches 99.5%; 150 inactive (jama) partners differ - reason not found in data.',
  '21-Sep 43 | 28-Sep 107 | 05-Oct 0', 'Need to Deep Dive.', 'Data team',
  '1. For these partners check deposit adjustment at jama and the OS on jama date.\n2. Agree whether bad debt = total_os + deposit at jama or at week end.',
  f"select m.partner_etm, m.bad_debt_amount, m.total_os, m.week_start_deposit, m.week_end_deposit, m.last_jama_date, m.active_inactive_flag\n{BASE}\n  and m.bad_debt_amount is not null order by m.bad_debt_amount;",
  'Compare bad_debt in Raw_Data (list in Employee_Level, filter bad_debt Matched? = Not Matched).'),
 ('last_paid_date -> last_payment_date_till_hissab_week',
  'Sheet last_paid_date blank while PG has a date; PG includes payments up to hisaab-week end (Sheet snapshot earlier). In 05-Oct Sheet rows are misaligned (see issue 25).',
  '892 / 1,008 / 10,317', 'Mostly Sheet.', 'Sheet owner',
  '1. Fill blank last_paid_date in the Sheet query.\n2. Use the same cut-off (hisaab week end) in both.',
  f"select m.partner_etm, m.last_payment_date_till_hissab_week\n{BASE}\norder by 2 desc nulls last;",
  'Filter Raw_Data last_paid_date blank.'),
 ('last_jama_date -> last_jama_date',
  'PG issue: last_jama_date holds a future date (e.g. 2026-10-20, later than today) for active partners; Sheet is blank. Also PG keeps an old jama of an earlier allocation where Sheet shows only current allocation.',
  '8,576 / 8,608 / 10,904', '07-Oct: future jama date still on 7,494 / 8,036 / 9,225 rows.', 'PG (data team)',
  '1. In the MV, set last_jama_date = NULL when the date is after the hisaab week end / today (it looks like next_join_date is being used).\n2. Agree: last jama of any allocation or only of the current allocation.',
  f"select m.hissab_week, count(*) as partners, count(*) filter (where m.last_jama_date > current_date) as jama_date_in_future\nfrom {MV} m\nwhere m.hissab_week in ('2026-09-21','2026-09-28','2026-10-05') and m.for_collections = 1\ngroup by 1 order by 1;",
  'Raw_Data last_jama_date is blank for these partners.'),
 ('last_car_number -> last_car_number',
  'PG shows the latest car at refresh time (same car for every week); Sheet shows the car driven in that week. Also Sheet blank for ~1k rows and 05-Oct misaligned.',
  '2,471 / 1,630 / 10,919', 'Still present.', 'PG + Sheet owner',
  '1. PG: take the car allocated in the driven week (ssot_alloc_dealloc_base, allocation_date < hissab_week and jama_date >= driven_week, latest allocation).\n2. Sheet: fill blank car numbers; fix 05-Oct paste (issue 25).',
  f"select m.partner_etm, m.last_car_number as pg_car, string_agg(distinct s.car_number, ', ') as cars_allocated_in_driven_week\nfrom {MV} m\nleft join analytics.ssot_alloc_dealloc_base s\n       on s.employee_id = m.partner_etm and s.allocation_date < m.hissab_week and coalesce(s.jama_date,'2099-01-01') >= m.driven_week\nwhere m.hissab_week = {W} and m.for_collections = 1\ngroup by 1,2\nhaving bool_or(s.car_number = m.last_car_number) is not true\norder by 1;",
  'Sheet last_car_number should be in cars_allocated_in_driven_week.'),
 ('sd_week_start -> week_start_deposit',
  'Sheet sd_week_start often shows the agreed / full security deposit (round amount) or adds back deposit-to-OS; 129 rows double counted (2 x PG). PG shows actual deposit balance at week start.',
  '1,847 / 1,577 / 10,602 (05-Oct misaligned)', 'Definition + Sheet issue.', 'Business decision + Sheet owner',
  '1. Agree: actual deposit balance (PG) or agreed deposit (Sheet).\n2. Fix double counting in the Sheet (duplicate deposit rows).',
  f"select m.partner_etm, m.week_start_deposit, m.os_to_deposit, m.week_end_deposit, m.next_week_end_deposit\n{BASE}\norder by 1;",
  'Compare sd_week_start in Raw_Data.'),
 ('week_end_deposit -> week_end_deposit',
  "Sheet week_end_deposit = deposit at week START (excludes this week's OS-to-deposit instalment / deposit-to-OS); PG applies them.",
  '2,997 / 2,670 / 10,641', 'Definition.', 'Sheet owner',
  '1. Sheet should take the deposit after this week movements (= PG week_end_deposit), or rename the Sheet column to week_start_deposit.',
  f"select m.partner_etm, m.week_start_deposit, m.os_to_deposit, m.week_end_deposit\n{BASE}\n  and m.week_start_deposit is distinct from m.week_end_deposit;",
  'Raw_Data week_end_deposit = PG week_start_deposit for these partners.'),
 ('payment_habit -> last_week_payment_habit',
  'PG logic issue: PG uses the habit of the fixed week 2026-09-21 for every hisaab week. Sheet uses the habit of the same week (matches driver_repayment_habit).',
  '2,336 / 6,182 / 8,071', '07-Oct: still fixed (05-Oct: 0 rows equal own-week habit).', 'PG (data team)',
  '1. Join driver_repayment_habit on week_start_date = hissab_week (not a hard-coded date).\n2. Re-check: pg_equals_own_week_habit should equal partners.',
  f"select m.hissab_week, count(*) as partners,\n       count(*) filter (where h21.payment_habit = m.last_week_payment_habit) as pg_equals_21sep_habit,\n       count(*) filter (where hw.payment_habit = m.last_week_payment_habit) as pg_equals_own_week_habit\nfrom {MV} m\njoin fleet_driver fd on fd.employee_id = m.partner_etm\nleft join driver_repayment_habit h21 on h21.driver_id = fd.id and h21.week_start_date = '2026-09-21'\nleft join driver_repayment_habit hw on hw.driver_id = fd.id and hw.week_start_date = m.hissab_week\nwhere m.hissab_week in ('2026-09-21','2026-09-28','2026-10-05') and m.for_collections = 1\ngroup by 1 order by 1;",
  'Raw_Data payment_habit = habit of the same week.'),
 ('not_driven_count -> current_week_nd_count',
  '05-Oct: PG counts not-driven days of the running week (future days counted). 21-Sep: PG is 1 day higher for 3,065 partners (date window boundary). 538 rows unexplained.',
  '3,340 / 272 / 9,733', 'Timing + definition.', 'PG (data team)',
  '1. Count not-driven days only for the driven week (driven_week to hissab_week - 1).\n2. Check the 21-Sep window boundary (start / end date inclusive).',
  f"select m.partner_etm, m.current_week_nd_count, m.last_week_nd_count, m.total_allocated_days, m.uber_active_days, m.d2o_leave_days\n{BASE}\norder by 2 desc;",
  'Compare not_driven_count in Raw_Data.'),
 ('tenure_days -> tenure_days',
  'Tenure calculated on different reference dates (PG on its refresh date, Sheet on its own date) - differences of 3-6 days. 3,154 rows differ by more; 2,887 rows Sheet tenure = 0.',
  '10,656 / 9,116 / 10,380', 'Definition.', 'Business decision',
  '1. Agree reference date (e.g. tenure as of hisaab week start).\n2. Fill Sheet tenure where it is 0.',
  f"select m.partner_etm, m.tenure_days, m.last_updated\n{BASE}\norder by 2;",
  'Compare tenure_days in Raw_Data.'),
 ('1d_active -> active_inactive_flag',
  '05-Oct: PG flags activity of the running hisaab week; Sheet shows the completed driven week. Closed weeks match 99.9% (29 rows deep dive).',
  '17 / 12 / 9,664', 'Timing.', 'Process',
  '1. Validate closed weeks only, or compute PG flag on the driven week.',
  f"select m.partner_etm, m.active_inactive_flag, m.hissab_week_active_days, m.uber_active_days\n{BASE}\norder by 1;",
  'Compare 1d_active in Raw_Data.'),
 ('in_car_recovery -> in_car_recovery_hissab_week',
  '05-Oct: recovery status changed between refreshes. Closed weeks 99.5% match; 110 rows deep dive (Sheet Yes / PG false and vice versa).',
  '56 / 54 / 2,189', 'Timing + deep dive.', 'Data team',
  '1. Check car recovery records for the 110 partners (Deep dive list in Employee_Level, filter in_car_recovery Matched? = Not Matched).',
  f"select m.partner_etm, m.in_car_recovery_driven_week, m.in_car_recovery_hissab_week, m.cars_under_recovery_hissab_week, m.recovery_tat\n{BASE}\n  and m.partner_etm in ('ETB061835','ETH050415','ETM092479');",
  'Compare in_car_recovery in Raw_Data.'),
 ('not_paid_last_2_weeks -> partners_not_paid_2_weeks',
  'Definition: PG flag = 1 only when last_week_collection AND previous_week_collection are both 0 (reproduced 100%). Sheet counts unpaid weeks (0/1/2) on a different window.',
  '1,896 / 1,973 / 2,094', 'Definition.', 'Business decision',
  '1. Agree one definition (flag vs count, which 2 weeks).\n2. Implement the same in both.',
  f"select m.partner_etm, m.partners_not_paid_2_weeks, m.last_week_collection, m.previous_week_collection, m.total_collected_amount_in_week\n{BASE}\norder by 2 desc;",
  'Compare not_paid_last_2_weeks in Raw_Data.'),
 ('car_recovery_pending_tat -> recovery_tat',
  'TAT counted to different refresh dates; some rows blank on one side.',
  '669 / 644 / 2,029', 'Timing.', 'Process',
  '1. Agree TAT reference date (hisaab week end).',
  f"select m.partner_etm, m.recovery_tat, m.in_car_recovery_hissab_week\n{BASE}\n  and m.recovery_tat is not null order by 2 desc;",
  'Compare car_recovery_pending_tat in Raw_Data.'),
 ('allocation_location -> location',
  'Sheet allocation_location not filled for 05-Oct; for closed weeks the hub name differs for ~2.8k partners per week (hub transfer / hub naming).',
  '2,845 / 2,771 / 10,610', 'Need to Deep Dive + Sheet issue.', 'Sheet owner + Data team',
  '1. Fill allocation_location in the Sheet for every week.\n2. Agree hub master (PG location names vs Sheet hub names).',
  f"select m.location, count(*) as partners, count(*) filter (where m.revenue_type is null) as revenue_type_blank\n{BASE}\ngroup by 1 order by 2 desc;",
  'Pivot Raw_Data allocation_location for the same week.'),
 ('Row presence (for_collections)',
  'Sheet = PG rows with for_collections = 1. 84 PG partners with for_collections = 1 are missing in the Sheet; 14 Sheet partners have for_collections = 0 in PG.',
  '22 / 37 / 39', 'Need to Deep Dive.', 'Data team + Sheet owner',
  '1. Check the Sheet filter for these partners (Mumbai heavy).\n2. Check why PG marks the 14 partners for_collections = 0.',
  f"select m.hissab_week, m.city, m.partner_etm, m.for_collections, m.total_os, m.active_inactive_flag\nfrom {MV} m\nwhere m.hissab_week = {W} and m.partner_etm in ('ETM01685','ETM04232','ETB41988','ETN58774','ETB14168');",
  'VLOOKUP these ET IDs in Raw_Data for the same week.'),
 ('Sheet 05-Oct rows (general)',
  'Sheet issue: in Raw_Data week 05-Oct the block last_car_number / week_end_deposit / sd_week_start / last_paid_date belongs to a different partner than the ET ID in the row (rows got shuffled when pasted). Checked against car_allocation (e.g. ETN093136 never had HR55AY7780).',
  '05-Oct ~10,600 rows', 'Sheet issue.', 'Sheet owner',
  '1. Re-paste the 05-Oct block in Raw_Data with all columns sorted the same way (or use one query that returns all columns together).\n2. Re-run the validation.',
  "select fd.employee_id, fc.car_number, ca.allocation_date, cd.date as jama_date\nfrom car_allocation ca\njoin fleet_driver fd on fd.id = ca.driver_id\njoin fleet_car fc on fc.id = ca.car_id\nleft join car_deallocation cd on cd.id = ca.deallocation_id\nwhere ca.deactivation_date is null and fd.employee_id = 'ETN093136' and ca.allocation_date >= '2026-08-01'\norder by ca.allocation_date;",
  "Raw_Data 05-Oct row for ETN093136 shows car HR55AY7780 - not in this partner's allocations."),
]

hdr = ['#', 'Column (Sheet -> PG)', 'Issue - why it does not match', 'Rows not matching (06-Oct check: 21-Sep / 28-Sep / 05-Oct)',
       'Status in PG refresh 07-Oct 08:23', 'Who needs to fix', 'Steps to make it match', 'SQL to check manually (change the week in WHERE)',
       'How to check in Sheet']
rows = [hdr] + [[i + 1, *r[:5], r[5], r[6], r[7]] for i, r in enumerate(ISSUES)]

tok = json.load(open(TOKEN))
r = requests.post(tok['token_uri'], data=dict(client_id=tok['client_id'], client_secret=tok['client_secret'],
                                              refresh_token=tok['refresh_token'], grant_type='refresh_token'), timeout=60)
r.raise_for_status()
H = {'Authorization': 'Bearer ' + r.json()['access_token']}
def call(method, url, **kw):
    for attempt in range(6):
        resp = requests.request(method, url, headers=H, timeout=300, **kw)
        if resp.status_code in (429, 500, 502, 503):
            time.sleep(2 ** attempt * 2); continue
        if not resp.ok:
            raise SystemExit(f'{resp.status_code}: {resp.text[:500]}')
        return resp.json()

sid = json.load(open(f'{D}/out/new_gsheet.json'))['spreadsheetId']
meta = call('GET', f'{API}/{sid}', params={'fields': 'sheets.properties'})
reqs = [{'deleteSheet': {'sheetId': s['properties']['sheetId']}} for s in meta['sheets'] if s['properties']['title'] == TAB]
reqs.append({'addSheet': {'properties': {'title': TAB, 'index': 0, 'gridProperties': {
    'rowCount': len(rows) + 3, 'columnCount': len(hdr), 'frozenRowCount': 1, 'frozenColumnCount': 2}}}})
tid = call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT', f"{API}/{sid}/values/'{TAB}'!A1", params={'valueInputOption': 'RAW'}, json={'values': rows})
widths = [40, 220, 380, 200, 220, 160, 380, 520, 260]
reqs = [{'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': len(rows)},
                        'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP', 'verticalAlignment': 'TOP'}},
                        'fields': 'userEnteredFormat(wrapStrategy,verticalAlignment)'}},
        {'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': 1},
                        'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'wrapStrategy': 'WRAP',
                                                       'backgroundColor': {'red': 0.85, 'green': 0.9, 'blue': 0.97}}},
                        'fields': 'userEnteredFormat(textFormat,backgroundColor,wrapStrategy)'}},
        {'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 1, 'endRowIndex': len(rows), 'startColumnIndex': 7, 'endColumnIndex': 8},
                        'cell': {'userEnteredFormat': {'textFormat': {'fontFamily': 'Roboto Mono', 'fontSize': 9}}},
                        'fields': 'userEnteredFormat.textFormat'}},
        {'setBasicFilter': {'filter': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': len(rows),
                                                 'startColumnIndex': 0, 'endColumnIndex': len(hdr)}}}}]
reqs += [{'updateDimensionProperties': {'range': {'sheetId': tid, 'dimension': 'COLUMNS', 'startIndex': i, 'endIndex': i + 1},
                                        'properties': {'pixelSize': w}, 'fields': 'pixelSize'}} for i, w in enumerate(widths)]
call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})
open(f'{D}/out/issue_queries.sql', 'w').write('\n\n'.join(f'-- {i + 1}. {r[0]}\n{r[6]}' for i, r in enumerate(ISSUES)))
print('done', len(ISSUES), 'issues')
