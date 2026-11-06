-- OS_Surpass tab (Summary: "Live OS Tracking - Active drivers")
-- Active pilots of each hisaab week (MV active_inactive_flag = 'Active'), live OS on the last day of the week
-- (Sunday; today for the running week) from public.hissab_driver_live_os, compared with week-end deposit.
-- Surpass = -live_os - deposit. Buckets: <=0 not surpass, <500, 500-2K, 2K-5K, 5K-10K, 10K-30K, 30K-50K, 50K+.
-- Output columns = OS_Surpass tab A..N (C = product, D blank, M = product, N = fuel).
with wk as (select generate_series((date_trunc('week', current_date) - interval '56 days')::date,
                                   date_trunc('week', current_date)::date, interval '7 days')::date as hw),
m as materialized (
  select m.hissab_week, m.partner_etm, m.city, m.revenue_type, m.product_type, m.eip_tag, coalesce(m.week_end_deposit, 0) as dep
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1 and m.active_inactive_flag = 'Active' and m.hissab_week in (select hw from wk)
),
fd as materialized (select id, employee_id from fleet_driver where employee_id in (select partner_etm from m)),
lo as materialized (   -- live OS on the last available day of each week
  select distinct on (fd.employee_id, date_trunc('week', h.date)::date)
         fd.employee_id, date_trunc('week', h.date)::date as hw, h.live_os
  from public.hissab_driver_live_os h join fd on fd.id = h.driver_id
  where h.is_active = 1 and h.date >= (select min(hw) from wk) and h.date <= current_date
  order by fd.employee_id, date_trunc('week', h.date)::date, h.date desc
),
x as (
  select m.*,
         case when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.product_type end as prod,
         greatest(-coalesce(lo.live_os, 0), 0) - m.dep as sp
  from m left join lo on lo.employee_id = m.partner_etm and lo.hw = m.hissab_week
)
select hissab_week as "Week", city as "City", prod as "Business Model", '' as "Single Or EIP",
       sum((sp <= 0)::int)                    as "Live OS Not Surpass deposit",
       sum((sp > 0 and sp < 500)::int)        as "Live OS Surpass Deposit - Below 500",
       sum((sp >= 500 and sp < 2000)::int)    as "Live OS Surpass Deposit - 500 to 2K",
       sum((sp >= 2000 and sp < 5000)::int)   as "Live OS Surpass Deposit - 2K to 5K",
       sum((sp >= 5000 and sp < 10000)::int)  as "Live OS Surpass Deposit - 5K to 10K",
       sum((sp >= 10000 and sp < 30000)::int) as "Live OS Surpass Deposit - 10K to 30K",
       sum((sp >= 30000 and sp < 50000)::int) as "Live OS Surpass Deposit - 30K to 50K",
       sum((sp >= 50000)::int)                as "Live OS Surpass Deposit - More than 50K",
       prod as "Business Model ", case when prod like 'EV%' then 'EV' else 'CNG' end as "fuel type"
from x
group by hissab_week, city, prod
order by 1, 2, 3;
