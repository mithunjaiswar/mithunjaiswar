-- sd_bucket!Z (raw lines) -> feeds sd_bucket (Deposit Threshold, SD_Profiles) and sd_bucket_V2 (Deposit [At Allocation],
-- SD_Profiles [At Allocation]) via SPLIT formulas in sd_bucket!A2 / sd_bucket_V2!A2.
-- Same logic as the old SD Bucket sheet (Raw_Data + Dash / Dash_V2) = QUERY 4 / QUERY 5 in final_raw_data.sql:
--   pilots = everyone who held a car on ANY day of the hisaab week (ssot_alloc_dealloc_base), not only collections pilots
--   deposit = mv_deposits_raw (excl. OWNNOW_TO_OWNNOW, SD_TO_OWNNOW) till week end (wk_end) /
--             till end of the week of the pilot's last allocation (at_alloc)
--   product = old SD rule on the car's current team: Fixed Pay > EIP > D2O > Own Now > EV > Revenue Share > SINGLE
--   buckets: <=0, (0,2K], (2K,5K], (5K,10K], (10K,20K], >20K
-- Run ONE WEEK AT A TIME (DB timeout 60s): change the date in wk and in m, then append the output lines to sd_bucket!Z (below the header in Z1).
with wk as (select date '2026-11-02' as hw),
sa as materialized (
  select w.hw, s.employee_id, s.allocation_date, s.allocation_datetime, s.city, s.fuel_type, s.car_number
  from analytics.ssot_alloc_dealloc_base s join wk w on s.allocation_date <= w.hw + 6 and coalesce(s.jama_date, current_date) >= w.hw
),
p as materialized (select distinct on (hw, employee_id) hw, employee_id, allocation_date, city, fuel_type from sa order by hw, employee_id, allocation_datetime desc),
cars as materialized (select fc.id car_id, fc.car_number, fc.model_id from fleet_car fc where fc.car_number in (select car_number from sa)),
car_team as materialized (
  select distinct on (fct.car_id) fct.car_id, ft.payment_model_id as pm
  from fleet_car_team fct left join fleet_team ft on ft.id = fct.team_id
  where fct.car_id in (select car_id from cars)
  order by fct.car_id, coalesce(fct.end_date, current_date) desc, fct.start_date desc
),
rk as materialized (
  select sa.hw, sa.employee_id,
         max(case when ct.pm = 3 then 99 when ct.pm in (7, 8) then 6 when ct.pm = 6 then 5 when ct.pm = 9 then 4
                  when c.model_id in (8, 16, 20, 52, 53, 54, 55, 40, 41, 42, 43) then 3 when ct.pm = 1 then 2 else 1 end) as rk
  from sa left join cars c on c.car_number = sa.car_number left join car_team ct on ct.car_id = c.car_id
  group by 1, 2
),
dep as materialized (
  select r.employee_id, r.date::date as dt, sum(r.amount) as amt
  from mv_deposits_raw r
  where r.deposit_type not in ('SD_TO_OWNNOW', 'OWNNOW_TO_OWNNOW') and r.employee_id in (select employee_id from p)
  group by 1, 2
),
m as materialized (select partner_etm, city, fuel_type from analytics.collections_bad_debt_mv
                   where for_collections = 1 and hissab_week = date '2026-11-02'),
dr as (
  select p.hw, p.employee_id, coalesce(m.city, p.city) as city, coalesce(m.fuel_type, p.fuel_type) as fuel,
         case rk.rk when 99 then 'Fixed Pay' when 6 then 'EIP' when 5 then 'D2O' when 4 then 'Own Now' when 3 then 'EV'
                    when 2 then 'Revenue Share' else 'SINGLE' end as prod,
         coalesce(sum(d.amt) filter (where d.dt <= least(p.hw + 6, current_date)), 0) as dwe,
         coalesce(sum(d.amt) filter (where d.dt <= least(date_trunc('week', p.allocation_date)::date + 6, current_date)), 0) as dal
  from p left join dep d on d.employee_id = p.employee_id
  left join m on m.partner_etm = p.employee_id
  left join rk on rk.employee_id = p.employee_id and rk.hw = p.hw
  group by 1, 2, 3, 4, 5
)
select concat_ws('~', hw, city, fuel, prod,
  sum((dwe <= 0)::int), sum((dwe > 0 and dwe <= 2000)::int), sum((dwe > 2000 and dwe <= 5000)::int),
  sum((dwe > 5000 and dwe <= 10000)::int), sum((dwe > 10000 and dwe <= 20000)::int), sum((dwe > 20000)::int), round(avg(dwe)),
  sum((dal <= 0)::int), sum((dal > 0 and dal <= 2000)::int), sum((dal > 2000 and dal <= 5000)::int),
  sum((dal > 5000 and dal <= 10000)::int), sum((dal > 10000 and dal <= 20000)::int), sum((dal > 20000)::int), round(avg(dal))) as line
from dr
group by hw, city, fuel, prod
order by 1;
