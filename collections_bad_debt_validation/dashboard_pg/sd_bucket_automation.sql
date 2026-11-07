-- sd_bucket!Z automation version (SQL query Automation sheet, tab collections_queries).
-- Same logic as deposit_buckets.sql, but all 8 hisaab weeks in one run (current week + 7 old weeks).
-- Output: 1 column "raw_line" (values joined with ~). Write to sd_bucket!Z1, clear Z.
-- sd_bucket!A2 and sd_bucket_V2!A2 SPLIT these lines, so no other change is needed.
with wk as (
  select generate_series((date_trunc('week', current_date) - interval '49 days')::date,
                         date_trunc('week', current_date)::date, interval '7 days')::date as hw
),
sa as materialized (
  select w.hw, s.employee_id, s.allocation_date, s.allocation_datetime, s.city, s.fuel_type
  from analytics.ssot_alloc_dealloc_base s
  join wk w on s.allocation_date <= w.hw + 6 and coalesce(s.jama_date, current_date) >= w.hw
),
p as materialized (
  select distinct on (hw, employee_id) hw, employee_id, allocation_date, city, fuel_type
  from sa order by hw, employee_id, allocation_datetime desc
),
mvx as materialized (
  select partner_etm, hissab_week, driven_week, product_type, city, fuel_type, for_collections
  from analytics.collections_bad_debt_mv
  where hissab_week between (select min(hw) from wk) - 56 and (select max(hw) from wk) + 7
    and partner_etm in (select employee_id from p)
),
-- product: MV row whose driven_week = the week; else latest MV row in the 8 weeks before; else SINGLE
mvp as materialized (
  select distinct on (w.hw, x.partner_etm) w.hw, x.partner_etm, x.product_type
  from wk w join mvx x on x.driven_week = w.hw
  order by w.hw, x.partner_etm, x.hissab_week
),
mvl as materialized (
  select distinct on (w.hw, x.partner_etm) w.hw, x.partner_etm, x.product_type
  from wk w join mvx x on x.hissab_week between w.hw - 56 and w.hw + 7
  order by w.hw, x.partner_etm, x.hissab_week desc
),
-- city / fuel: MV row of the week (for_collections = 1), else ssot
m as materialized (
  select hissab_week as hw, partner_etm, city, fuel_type from mvx
  where for_collections = 1 and hissab_week in (select hw from wk)
),
dep as materialized (
  select r.employee_id, r.date::date as dt, sum(r.amount) as amt
  from mv_deposits_raw r
  where r.deposit_type not in ('SD_TO_OWNNOW', 'OWNNOW_TO_OWNNOW')
    and r.employee_id in (select employee_id from p)
  group by 1, 2
),
dr as (
  select p.hw, p.employee_id, coalesce(m.city, p.city) as city, coalesce(m.fuel_type, p.fuel_type) as fuel,
         coalesce(mvp.product_type, mvl.product_type, 'SINGLE') as prod,
         coalesce(sum(d.amt) filter (where d.dt <= least(p.hw + 6, current_date)), 0) as dwe,
         coalesce(sum(d.amt) filter (where d.dt <= least(date_trunc('week', p.allocation_date)::date + 6, current_date)), 0) as dal
  from p
  left join dep d on d.employee_id = p.employee_id
  left join m on m.partner_etm = p.employee_id and m.hw = p.hw
  left join mvp on mvp.partner_etm = p.employee_id and mvp.hw = p.hw
  left join mvl on mvl.partner_etm = p.employee_id and mvl.hw = p.hw
  group by 1, 2, 3, 4, 5
)
select concat_ws('~', hw, city, fuel, prod,
  sum((dwe <= 0)::int), sum((dwe > 0 and dwe <= 2000)::int), sum((dwe > 2000 and dwe <= 5000)::int), sum((dwe > 5000 and dwe <= 10000)::int),
  sum((dwe > 10000 and dwe <= 20000)::int), sum((dwe > 20000)::int), round(avg(dwe)),
  sum((dal <= 0)::int), sum((dal > 0 and dal <= 2000)::int), sum((dal > 2000 and dal <= 5000)::int), sum((dal > 5000 and dal <= 10000)::int),
  sum((dal > 10000 and dal <= 20000)::int), sum((dal > 20000)::int), round(avg(dal))) as raw_line
from dr
group by hw, city, fuel, prod
order by 1;
