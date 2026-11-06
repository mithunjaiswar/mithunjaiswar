-- Deposit_Threshold tab (Summary: "Deposit Threshold")
-- Active pilots of each hisaab week (MV active_inactive_flag = 'Active'), bucketed by week-end deposit.
-- Window: last 4 hisaab weeks for testing (change 21 to 49 for 8 weeks when going live).
-- Output columns = Deposit_Threshold tab A..J.
with wk as (select generate_series((date_trunc('week', current_date) - interval '21 days')::date,
                                   date_trunc('week', current_date)::date, interval '7 days')::date as hw),
m as (
  select m.hissab_week, m.city, coalesce(m.week_end_deposit, 0) as dep,
         case when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.product_type end as prod
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1 and m.active_inactive_flag = 'Active' and m.hissab_week in (select hw from wk)
)
select hissab_week as week, city, case when prod like 'EV%' then 'EV' else 'CNG' end as fuel_type, prod as product_type,
       sum((dep <= 0)::int)                    as "Deposit <= 0",
       sum((dep > 0 and dep < 2000)::int)      as "Deposit 0-2000",
       sum((dep >= 2000 and dep < 5000)::int)  as "Deposit 2000-5000",
       sum((dep >= 5000 and dep < 10000)::int) as "Deposit 5000-10000",
       sum((dep >= 10000 and dep < 20000)::int) as "Deposit 10000-20000",
       sum((dep >= 20000)::int)                as "Deposit 20000+"
from m
group by hissab_week, city, prod
order by 1, 2, 4;
