-- tenure_days = tenure till the DRIVEN week end (hissab_week - 1)
-- Sum of all driver_profile stints (end_date - start_date + 1); the running stint is cut at hissab_week - 1,
-- stints that start after hissab_week - 1 are not counted.
-- Tables: analytics.collections_bad_debt_mv (plain table, 2,016,953 rows, 2022-01-03 .. 2026-10-05),
--         public.fleet_driver (employee_id unique), public.driver_profile (one row per stint).
-- Needs a WRITE user (the reporting connection is read-only). Run step by step.

-------------------------------------------------------------------------------
-- STEP 1  PREVIEW (read only) - how many rows change for one week
-------------------------------------------------------------------------------
with t as (
  select m.id, m.tenure_days as old_tenure,
         coalesce(sum(least(coalesce(dp.end_date::date, m.hissab_week - 1), m.hissab_week - 1) - dp.start_date::date + 1)
                  filter (where dp.start_date::date <= m.hissab_week - 1), 0) as new_tenure
  from analytics.collections_bad_debt_mv m
  left join fleet_driver fd on fd.employee_id = m.partner_etm
  left join driver_profile dp on dp.driver_id = fd.id
  where m.hissab_week = '2026-09-28'
  group by m.id, m.tenure_days)
select count(*) rows, count(*) filter (where old_tenure is distinct from new_tenure) will_change,
       round(avg(old_tenure - new_tenure), 1) avg_change_days
from t;

-------------------------------------------------------------------------------
-- STEP 2  BACKUP of the current values (keeps a rollback path)
-------------------------------------------------------------------------------
create table analytics.collections_bad_debt_mv_tenure_bkp_20261008 as
select id, hissab_week, partner_etm, tenure_days from analytics.collections_bad_debt_mv;

-------------------------------------------------------------------------------
-- STEP 3  UPDATE ONE WEEK FIRST, check, then commit
-------------------------------------------------------------------------------
begin;
with t as (
  select m.id,
         coalesce(sum(least(coalesce(dp.end_date::date, m.hissab_week - 1), m.hissab_week - 1) - dp.start_date::date + 1)
                  filter (where dp.start_date::date <= m.hissab_week - 1), 0) as new_tenure
  from analytics.collections_bad_debt_mv m
  left join fleet_driver fd on fd.employee_id = m.partner_etm
  left join driver_profile dp on dp.driver_id = fd.id
  where m.hissab_week = '2026-09-28'
  group by m.id)
update analytics.collections_bad_debt_mv m
   set tenure_days = t.new_tenure
  from t
 where m.id = t.id and m.tenure_days is distinct from t.new_tenure;
-- expected: UPDATE 10504 (tested 08-Oct: 12,594 rows in week 2026-09-28, 10,504 change, avg -5.4 days)
-- run STEP 5 check for this week; if OK:
commit;   -- otherwise: rollback;

-------------------------------------------------------------------------------
-- STEP 4  ALL OTHER WEEKS - one batch per hisaab_week range (repeat with the next range)
-------------------------------------------------------------------------------
begin;
with t as (
  select m.id,
         coalesce(sum(least(coalesce(dp.end_date::date, m.hissab_week - 1), m.hissab_week - 1) - dp.start_date::date + 1)
                  filter (where dp.start_date::date <= m.hissab_week - 1), 0) as new_tenure
  from analytics.collections_bad_debt_mv m
  left join fleet_driver fd on fd.employee_id = m.partner_etm
  left join driver_profile dp on dp.driver_id = fd.id
  where m.hissab_week >= '2026-01-01' and m.hissab_week < '2027-01-01'   -- then 2025, 2024, 2023, 2022
  group by m.id)
update analytics.collections_bad_debt_mv m
   set tenure_days = t.new_tenure
  from t
 where m.id = t.id and m.tenure_days is distinct from t.new_tenure;
commit;

-------------------------------------------------------------------------------
-- STEP 5  CHECK (read only) - expected 0 rows different per week
-------------------------------------------------------------------------------
with t as (
  select m.hissab_week, m.id, m.tenure_days,
         coalesce(sum(least(coalesce(dp.end_date::date, m.hissab_week - 1), m.hissab_week - 1) - dp.start_date::date + 1)
                  filter (where dp.start_date::date <= m.hissab_week - 1), 0) as logic
  from analytics.collections_bad_debt_mv m
  left join fleet_driver fd on fd.employee_id = m.partner_etm
  left join driver_profile dp on dp.driver_id = fd.id
  where m.hissab_week >= '2026-08-10'
  group by m.hissab_week, m.id, m.tenure_days)
select hissab_week, count(*) rows, count(*) filter (where tenure_days is distinct from logic) different
from t group by 1 order by 1;

-------------------------------------------------------------------------------
-- ROLLBACK (only if needed)
-------------------------------------------------------------------------------
-- update analytics.collections_bad_debt_mv m set tenure_days = b.tenure_days
--   from analytics.collections_bad_debt_mv_tenure_bkp_20261008 b where b.id = m.id;

-------------------------------------------------------------------------------
-- IMPORTANT: also change the script/DAG that builds this table, or the next refresh puts the old
-- logic (till hissab_week + 6) back. Replace its tenure_days expression with:
--   coalesce(sum(least(coalesce(dp.end_date::date, m.hissab_week - 1), m.hissab_week - 1)
--                - dp.start_date::date + 1)
--            filter (where dp.start_date::date <= m.hissab_week - 1), 0) as tenure_days
-------------------------------------------------------------------------------
