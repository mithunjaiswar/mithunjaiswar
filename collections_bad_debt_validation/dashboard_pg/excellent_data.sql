-- excellent_data tab (Summary > Payment Behaviour > Excellent).
-- Excellent = Active pilot in the hisaab week whose total OS is 0 or more (nothing pending).
-- Columns match the tab: A week_start, B city, C revenue_type (holds product type, same values as Raw_Data!H),
-- D is_eip, E fuel_type (same rule as Raw_Data!AO), F partner_count, G last_updated. Last 9 hisaab weeks.
with wk as (
  select generate_series((date_trunc('week', current_date) - interval '56 days')::date,
                         date_trunc('week', current_date)::date, interval '7 days')::date as hw
),
m as (
  select m.hissab_week, m.partner_etm, m.city, m.eip_tag,
         case when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV_Leasing'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.revenue_type end as rev_type,
         case when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.product_type end as prod
  from analytics.collections_bad_debt_mv m
  where m.hissab_week in (select hw from wk)
    and m.active_inactive_flag = 'Active'
    and coalesce(m.total_os, 0) >= 0
)
select hissab_week as week_start, city, prod as revenue_type,
       case when eip_tag = 1 then 'EIP' else 'SINGLE' end as is_eip,
       case when left(rev_type, 3) = 'EV_' then 'EV' else 'CNG' end as fuel_type,
       count(distinct partner_etm) as partner_count,
       to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') as last_updated
from m
group by 1, 2, 3, 4, 5
order by 1, 2, 3, 4, 5
