-- sd_bucket!Z (raw lines) -> feeds sd_bucket (Deposit Threshold, SD_Profiles) and sd_bucket_V2 (Deposit [At Allocation],
-- SD_Profiles [At Allocation]) via SPLIT formulas in sd_bucket!A2 / sd_bucket_V2!A2.
--   pilots = everyone who held a car on ANY day of the hisaab week (ssot_alloc_dealloc_base), not only collections pilots
--   deposit = mv_deposits_raw (excl. OWNNOW_TO_OWNNOW, SD_TO_OWNNOW) till week end (dwe) /
--             till end of the week of the pilot's last allocation (dal)
--   city/fuel = MV row of the week (for_collections = 1), else ssot
--   product = MV product_type (row with driven_week = week; else latest MV row in last 8 weeks; else SINGLE)
--             -> user decision 07-Nov: "As per MV rakho"
--   buckets: <=0, (0,2K], (2K,5K], (5K,10K], (10K,20K], >20K
-- Run ONE WEEK AT A TIME (DB timeout 60s): change the date in wk / mvx / mvp / m, then append the output
-- lines to sd_bucket!Z (below the header in Z1).
with wk as (select date '2026-11-02' as hw),
sa as materialized (select w.hw, s.employee_id, s.allocation_date, s.allocation_datetime, s.city, s.fuel_type
  from analytics.ssot_alloc_dealloc_base s join wk w on s.allocation_date <= w.hw + 6 and coalesce(s.jama_date, current_date) >= w.hw),
p as materialized (select distinct on (hw, employee_id) hw, employee_id, allocation_date, city, fuel_type from sa order by hw, employee_id, allocation_datetime desc),
mvx as materialized (select partner_etm, hissab_week, driven_week, product_type from analytics.collections_bad_debt_mv
  where hissab_week between date '2026-11-02' - 56 and date '2026-11-02' + 7 and partner_etm in (select employee_id from p)),
mvp as materialized (select distinct on (partner_etm) partner_etm, product_type from mvx where driven_week = date '2026-11-02' order by partner_etm, hissab_week),
mvl as materialized (select distinct on (partner_etm) partner_etm, product_type from mvx order by partner_etm, hissab_week desc),
dep as materialized (select r.employee_id, r.date::date as dt, sum(r.amount) as amt from mv_deposits_raw r
  where r.deposit_type not in ('SD_TO_OWNNOW','OWNNOW_TO_OWNNOW') and r.employee_id in (select employee_id from p) group by 1, 2),
m as materialized (select partner_etm, city, fuel_type from analytics.collections_bad_debt_mv where for_collections = 1 and hissab_week = date '2026-11-02'),
dr as (select p.hw, p.employee_id, coalesce(m.city, p.city) as city, coalesce(m.fuel_type, p.fuel_type) as fuel,
  coalesce(mvp.product_type, mvl.product_type, 'SINGLE') as prod,
  coalesce(sum(d.amt) filter (where d.dt <= least(p.hw + 6, current_date)), 0) as dwe,
  coalesce(sum(d.amt) filter (where d.dt <= least(date_trunc('week', p.allocation_date)::date + 6, current_date)), 0) as dal
  from p left join dep d on d.employee_id = p.employee_id left join m on m.partner_etm = p.employee_id
  left join mvp on mvp.partner_etm = p.employee_id left join mvl on mvl.partner_etm = p.employee_id
  group by 1, 2, 3, 4, 5)
select string_agg('["'||line||'"]', ', ' order by line) from (select concat_ws('~', hw, city, fuel, prod,
  sum((dwe <= 0)::int), sum((dwe > 0 and dwe <= 2000)::int), sum((dwe > 2000 and dwe <= 5000)::int), sum((dwe > 5000 and dwe <= 10000)::int),
  sum((dwe > 10000 and dwe <= 20000)::int), sum((dwe > 20000)::int), round(avg(dwe)),
  sum((dal <= 0)::int), sum((dal > 0 and dal <= 2000)::int), sum((dal > 2000 and dal <= 5000)::int), sum((dal > 5000 and dal <= 10000)::int),
  sum((dal > 10000 and dal <= 20000)::int), sum((dal > 20000)::int), round(avg(dal))) as line
from dr group by hw, city, fuel, prod) x;
