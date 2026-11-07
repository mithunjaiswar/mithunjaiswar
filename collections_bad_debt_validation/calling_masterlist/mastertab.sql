-- =====================================================================================
-- Calling sheet "Copy of MasterTab" (1SLwHdIlVkbtggXXJntgtwFVYoSlg7S1A0WhTiyqHRW8) as ONE query.
-- Output = columns A..BS (71), same order/names as the sheet (row 2 headers).
-- Rows = collections_list (MV for_collections = 1, current hisaab week, negative OS)
--        + every partner who held a car at any time today (active_list logic, but jama today also kept).
--
-- Critical risk (2 columns):
--   AI "Risk_Type"          = rule on LIVE numbers (payments/deposits till now)            -> "check" column
--   BI "Critical Risk Tag"  = same rule on START-OF-DAY numbers (payments/deposits dated before today)
--                             = the "stored" list. If stored = critical: still critical now -> 'Critical_Risk',
--                             else 'Out of Critical'. Not in stored list -> ''.
-- Sheet bugs kept as they are (so numbers match the sheet) are marked "SHEET BUG".
-- =====================================================================================
with p as (select date_trunc('week', current_date)::date as w, current_date as t,
                  date_trunc('week', current_date - 1)::date as rw),   -- rw = week of collections_raw (yesterday's week)
-- ---------- rows ----------
cl as materialized (   -- collections_list
  select m.partner_etm as etm, m.lead_id, m.city, m.total_os,
         case when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 0 then 'EV_D2O' else m.product_type end as product
  from analytics.collections_bad_debt_mv m, p
  where m.for_collections = 1 and m.hissab_week = p.w and m.total_os < 0
),
alloc_today as materialized (   -- allocations live at any time today
  select ca.driver_id, ca.car_id, cd.date as jama_dt, ca.deallocation_id
  from car_allocation ca left join car_deallocation cd on cd.id = ca.deallocation_id, p
  where ca.deactivation_date is null and ca.allocation_date::date <= p.t
    and (ca.deallocation_id is null or cd.date::date >= p.t)
),
eipset as materialized (   -- EIP plan pilots last week (active_list rule)
  select distinct flw.partner_id from fleet_leasing_weeklydata flw, p
  where flw.leasing_type = 'EIP' and flw.start_date = p.w - 7
),
act as materialized (   -- active_list product logic (team of the car)
  select distinct on (a.driver_id) a.driver_id, fd.employee_id as etm, team.city,
    case when team.pm = 3 then 'Fixed Pay'
         when team.model_id in (8,16,20,52,53,54,55,40,41,42,43) then 'EV'
         when eip.partner_id is not null then 'EIP'
         when team.pm in (7, 8) then 'EIP'
         when team.pm = 6 then 'D2O'
         when team.pm = 9 then 'Own Now'
         when team.pm = 1 then 'Revenue Share'
         else 'SINGLE' end as product,
    greatest(case when team.pm = 3 then 99 else 0 end, case when team.pm in (7, 8) then 6 else 0 end,
             case when team.pm = 6 then 5 else 0 end, case when team.pm = 9 then 4 else 0 end,
             case when team.model_id in (8,16,20,52,53,54,55,40,41,42,43) then 3 else 0 end,
             case when team.pm = 1 then 2 else 0 end, 1) as rk
  from alloc_today a
  join fleet_driver fd on fd.id = a.driver_id
  left join lateral (
    select coalesce(fcity.name, fcity2.name) as city, ft.payment_model_id as pm, fcar.model_id
    from fleet_car_team fct
    left join fleet_team ft on ft.id = fct.team_id
    left join fleet_company_loc fcl on fcl.id = ft.loc_id
    left join fleet_city fcity on fcity.id = fcl.city_id
    left join fleet_car fcar on fcar.id = fct.car_id
    left join fleet_city fcity2 on fcity2.id = fcar.city_id
    where fct.car_id = a.car_id and fct.start_date <= coalesce(a.jama_dt::date, current_date)
    order by coalesce(fct.end_date, current_date) desc limit 1
  ) team on true
  left join eipset eip on eip.partner_id = a.driver_id
  order by a.driver_id, rk desc
),
pop as materialized (
  select etm, city, product, 1 as in_cl from cl
  union all
  select act.etm, act.city, act.product, 0 from act where act.etm not in (select etm from cl)
),
drv as materialized (
  select pop.*, fd.id as driver_id, fd.name as partner_name, ld.lead_id
  from pop
  join lateral (select f.id, f.name from fleet_driver f where f.employee_id = pop.etm order by f.id desc limit 1) fd on true
  left join lateral (select l.lead_id from crm.lead_driver l where l.hawkeye_driver_id = fd.id
                     order by l.id desc limit 1) ld on true
),
-- ---------- money ----------
rec as materialized (
  select r.employee_id as etm,
         sum(r.amount) filter (where r.recovery_type::text = 'razorpay_recovery')       as rz,
         sum(r.amount) filter (where r.recovery_type::text = 'other_positive_recovery') as ot,
         sum(r.amount) filter (where r.recovery_type::text = 'phonepe_recovery')        as pp,
         sum(r.amount) filter (where r.recovery_type::text = 'positive_adjustment')     as adj,
         sum(r.amount) filter (where r.recovery_type::text = 'deposit_to_os')           as dp,
         sum(r.amount) filter (where r.date < (select t from p))                       as tot_sod   -- start of day
  from mv_daily_recovery r, p
  where r.date between p.rw and p.rw + 6
    and r.recovery_type::text in ('razorpay_recovery','other_positive_recovery','phonepe_recovery','positive_adjustment','deposit_to_os')
    and r.employee_id in (select etm from drv)
  group by 1
),
dep as materialized (
  select d.employee_id as etm, sum(d.amount) as dep_now,
         sum(d.amount) filter (where d.date < (select t from p)) as dep_sod
  from mv_deposits_raw d
  where d.deposit_type not in ('OWNNOW_TO_OWNNOW', 'SD_TO_OWNNOW') and d.employee_id in (select etm from drv)
  group by 1
),
lwos as materialized (   -- total_os_raw: last week OS (account_ledger + fleet_leasing_total_os)
  select os.partner_id as driver_id, sum(os.total_os)::int as os
  from (
    select driver_id as partner_id, total_os from account_ledger, p
    where driver_id in (select driver_id from drv) and week_start_date >= p.w - 7 and week_start_date < p.w
    union all
    select partner_id, total_os from fleet_leasing_total_os, p
    where partner_id in (select driver_id from drv) and week_start_date >= p.w - 7 and week_start_date < p.w
  ) os
  where os.partner_id in (select a.partner_id from fleet_leasing_weeklydata a, p
                          where a.partner_id in (select driver_id from drv) and a.start_date >= p.w - 7 and a.start_date < p.w
                          union
                          select a.driver_id from fleet_weeklydata a, p
                          where a.driver_id in (select driver_id from drv) and a.week_start_date >= p.w - 7 and a.week_start_date < p.w)
  group by 1
  having sum(os.total_os)::int <> 0
),
habit as materialized (
  select distinct on (h.driver_id) h.driver_id, coalesce(h.payment_habit, 'Good') as habit
  from driver_repayment_habit h, p
  where h.week_start_date < p.w and h.driver_id in (select driver_id from drv)
  order by h.driver_id, h.week_start_date desc, h.id desc
),
-- ---------- daily car rows (earnings_raw + nd_raw), from Monday of last week till yesterday ----------
days as (select generate_series((select w from p) - 8, (select t from p) - 1, interval '1 day')::date as d),
cday as materialized (
  select dy.d, ca.driver_id, ca.car_id
  from days dy
  join car_allocation ca on ca.deactivation_date is null and ca.allocation_date::date <= dy.d
  left join car_deallocation cd on cd.id = ca.deallocation_id
  where coalesce(cd.date::date, current_date) >= dy.d and ca.driver_id in (select driver_id from drv)
),
tint as materialized (   -- team of each car as date intervals (latest start_date, then highest id)
  select fct.car_id, fct.start_date::date as sd,
         lead(fct.start_date::date) over (partition by fct.car_id order by fct.start_date, fct.id) as nd,
         ft.id as team_id, ft.business_vertical_id, ft.city_id, ft.loc_id, ft.bv_pm_map_id
  from fleet_car_team fct join fleet_team ft on ft.id = fct.team_id
  where fct.car_id in (select car_id from cday)
),
mint as materialized (   -- leasing car model (car_type) as date intervals
  select lcm.car_id, lcm.start_date::date as sd,
         lead(lcm.start_date::date) over (partition by lcm.car_id order by lcm.start_date, lcm.id) as nd, lcm.model_type
  from fleet_leasing_car_model lcm
  where lcm.car_id in (select car_id from cday)
),
cteam as materialized (
  select c.*, tm.team_id, tm.business_vertical_id, tm.city_id, tm.loc_id, tm.bv_pm_map_id, mm.model_type
  from cday c
  left join tint tm on tm.car_id = c.car_id and tm.sd <= c.d and (tm.nd is null or tm.nd > c.d)
  left join mint mm on mm.car_id = c.car_id and mm.sd <= c.d and (mm.nd is null or mm.nd > c.d)
),
trip as materialized (
  select fdt.date as d, fdt.car_id, sum(fdt.trips) as trips, sum(fdt.dispatch_trips) as disp, sum(fdt.accepted_trips) as acc,
         round(sum(fdt.fare_total)) as fare, round(sum(fdt.cash_collected)) as cash, round(sum(fdt.tip_amount)) as tip,
         round(sum(fdt.subscription_charges)) as subs
  from fleet_dailytrip fdt
  where fdt.date between (select w from p) - 8 and (select t from p) - 1 and fdt.trips > 0 and fdt.car_id is not null
    and fdt.car_id in (select car_id from cday)
  group by 1, 2
),
km as materialized (
  select k.date as d, k.car_id, sum(k.gps_km) as gps, sum(k.uber_km) as uber, sum(k.dead_km) as dead
  from car_dead_km k
  where k.date between (select w from p) - 8 and (select t from p) - 1 and k.car_id in (select car_id from cday)
  group by 1, 2
),
rg as materialized (   -- rental_guide (current)
  select distinct on (car_type, city_id, loc_id, vertical_payment_id) car_type, city_id, loc_id, vertical_payment_id, coalesce(rent, 0) as rent
  from fleet_leasing_rentalguide
  where start_date <= current_date and (end_date is null or end_date >= current_date) and min_trips = 0
  order by car_type, city_id, loc_id, vertical_payment_id, start_date desc, id desc
),
loc1 as (select city_id, min(id) as loc_id from fleet_company_loc where is_active = 1 group by 1),
earn as materialized (   -- earnings_raw, current week only (date >= Monday)
  select c.driver_id, count(distinct fc.car_number) as car_cnt, count(*) as rent_days,
         sum(coalesce(rg.rent, 0)) as rent, sum(coalesce(tr.fare, 0) + coalesce(tr.tip, 0)) as fare_tip,
         sum(coalesce(tr.cash, 0)) as cash, sum(coalesce(tr.subs, 0)) as subs
  from cteam c
  join fleet_car fc on fc.id = c.car_id
  left join loc1 on loc1.city_id = c.city_id
  left join rg on rg.car_type = c.model_type and rg.city_id = c.city_id and rg.loc_id = coalesce(c.loc_id, loc1.loc_id)
              and rg.vertical_payment_id = case when c.bv_pm_map_id is null and fc.model_id in (8,16,20,40,41,42,43,52,53,54,55) then 12
                                                when c.bv_pm_map_id is null then 2 else c.bv_pm_map_id end
  left join trip tr on tr.d = c.d and tr.car_id = c.car_id
  where c.d >= (select w from p)
  group by 1
),
nd as materialized (   -- nd_raw rows (bv 3/4 and listed teams excluded)
  select c.driver_id, c.d, coalesce(tr.trips, 0) as trips, coalesce(tr.disp, 0) as disp, coalesce(tr.acc, 0) as acc,
         coalesce(k.gps, 0) as gps, coalesce(k.uber, 0) as uber, coalesce(k.dead, 0) as dead
  from cteam c
  left join trip tr on tr.d = c.d and tr.car_id = c.car_id
  left join km k on k.d = c.d and k.car_id = c.car_id
  where coalesce(c.business_vertical_id, 0) not in (3, 4)
    and coalesce(c.team_id, 0) <> all (array[1125,1126,1127,1128,1129,1130,1131,1177,1179,1283,1284,1292,1303,1304,
        1312,1313,1314,1390,1440,1469,1470,1471,1475,1479,1483,1484,1488,1489,1490,1494,1495,1496,1497,1625,1627,1628,
        1630,1862,1864,1879,1892,1934,1935,1941,1942,1946,1949,1950,1951,1952,1953,1970,1971,1972,1973,1974,1976,1989,
        2076,2138,2139,2147,2194,2199,2240,2244,2245,2246,2247,2249,2253,2254,2261,2262,2293,2294,2359,2360,2363,2364,
        2365,2375,2392,2393,2394,2417,2423,2426,2456,2458,2463,2476,2488]::int[])
),
nda as materialized (
  select n.driver_id,
    count(*) filter (where n.d >= p.w - 1)                         as lw_active,   -- SHEET BUG: ">=A-7" and ">=A-1" -> from last Sunday
    count(*) filter (where n.d >= p.w - 1 and n.trips <= 0)        as lw_nd,
    count(*) filter (where n.d >= p.w)                             as cw_active,
    count(*) filter (where n.d >= p.w and n.trips <= 0)            as cw_nd,
    sum(n.gps)   filter (where n.d >= p.w) as gps,  sum(n.uber) filter (where n.d >= p.w) as uber,
    sum(n.dead)  filter (where n.d >= p.w) as dead, sum(n.trips) filter (where n.d >= p.w) as trips,
    sum(n.trips) filter (where n.d >= p.w - 7 and n.d < p.w)       as lw_trips,
    sum(n.gps)   filter (where n.d = p.t - 1)                      as gps_yday,
    sum(n.acc)   filter (where n.d >= p.w) as acc, sum(n.disp) filter (where n.d >= p.w) as disp
  from nd n, p group by n.driver_id
),
-- ---------- other lookups ----------
cars_now as materialized (
  select a.driver_id, string_agg(distinct fc.car_number, ', ') as cars
  from alloc_today a join fleet_car fc on fc.id = a.car_id where a.deallocation_id is null group by 1
),
model_now as materialized (   -- car_model_mapping: model name of the latest allocated car
  select distinct on (ca.driver_id) ca.driver_id, fcm.name as car_model
  from car_allocation ca join fleet_car fc on fc.id = ca.car_id left join fleet_car_model fcm on fcm.id = fc.model_id
  where ca.deactivation_date is null and ca.driver_id in (select driver_id from drv)
  order by ca.driver_id, ca.allocation_date desc
),
elc as materialized (
  select dp.driver_id from driver_profile dp
  where dp.driver_id in (select driver_id from drv)
    and exists (select 1 from car_allocation ca left join car_deallocation cd on cd.id = ca.deallocation_id
                where ca.driver_id = dp.driver_id and ca.deactivation_date is null
                  and (cd.date is null or cd.date >= date_trunc('week', current_date) - interval '15 weeks'))
  group by 1 having sum(dp.tenure) < 30
),
rcar as materialized (   -- car_recovery_raw: cases open today
  select a.driver_id, min(a.activation_date)::date as act_dt
  from recovery_cars a
  left join lateral (select b.datetime as close_date from recovery_status_logs b
                     where b.recovery_id = a.id and b.recovery_status in ('complete','failed','cancelled')
                     order by b.id desc limit 1) ls on true
  where a.activation_date < current_date + 1 and (ls.close_date is null or ls.close_date >= current_date)
  group by 1
),
lpaid as materialized (
  select employee_id as etm, max(date) as d from mv_daily_recovery
  where recovery_type::text in ('razorpay_recovery','other_positive_recovery','phonepe_recovery')
    and date >= (date_trunc('week', current_date) - interval '8 weeks')::date and employee_id in (select etm from drv)
  group by 1
),
ljama as materialized (   -- last jama, only for partners with no live car
  select ca.driver_id, max(cd.date)::date as d, (max(cd.date) filter (where cd.date >= (select w from p) - 7))::date as d_lw
  from car_allocation ca join car_deallocation cd on cd.id = ca.deallocation_id
  where ca.deactivation_date is null and cd.date >= (date_trunc('week', current_date) - interval '8 weeks')::date
    and ca.driver_id in (select driver_id from drv)
    and not exists (select 1 from car_allocation c2 where c2.driver_id = ca.driver_id and c2.deactivation_date is null and c2.deallocation_id is null)
  group by 1
),
calls as materialized (
  select c.partner_et_id as etm,
         sum(c.attempt_count) as att, sum(c.connect_count) as conn,
         max(c.last_attempt_time) as last_att, max(c.last_connect_time) as last_conn,
         sum(c.attempt_count) filter (where c.date = current_date) as att_today,
         sum(c.connect_count) filter (where c.date = current_date) as conn_today
  from public.collections_calling_data_raw c, p
  where c.week_start = p.w and c.partner_et_id in (select etm from drv)
  group by 1
),
call_disp as materialized (   -- SHEET BUG kept: row whose last_attempt_time = max(last_connect_time)
  select distinct on (c.partner_et_id) c.partner_et_id as etm, c.last_subdisposition
  from public.collections_calling_data_raw c join calls on calls.etm = c.partner_et_id and c.last_attempt_time = calls.last_conn, p
  where c.week_start = p.w
  order by c.partner_et_id, c.id
),
newjoin as materialized (
  select employee_id as etm, (array_agg(category order by allocation_date desc))[1] as cat
  from analytics.ssot_alloc_dealloc_full
  where allocation_date >= '2026-08-17' and category in ('New Join', 'Resurrection') and employee_id in (select etm from drv)
  group by 1
),
ndlist as materialized (   -- nd_list: live car now, and 0 trips (Uber + Ola) yesterday on all cars held yesterday
  select ad.driver_id
  from (select distinct ca.driver_id, ca.car_id from car_allocation ca left join car_deallocation cd on cd.id = ca.deallocation_id
        where ca.deactivation_date is null and ca.allocation_date::date <= current_date - 1
          and coalesce(cd.date::date, current_date) >= current_date - 1 and ca.driver_id in (select driver_id from drv)) ad
  left join (select car_id, sum(trips) as tt from (
               select car_id, trips from fleet_dailytrip where car_id is not null and date = current_date - 1
               union all
               select car_id, trips from fleet_ola_dailytrip where car_id is not null and date::date = current_date - 1) x
             group by 1) te on te.car_id = ad.car_id
  where ad.driver_id in (select driver_id from alloc_today where deallocation_id is null)
  group by 1 having sum(coalesce(te.tt, 0)) = 0
),
remarks as materialized (
  select distinct on (partner_et_id) partner_et_id as etm,
    concat_ws(chr(10),
      case when coalesce(remarks, '') <> '' then 'Remarks:  ' || remarks end,
      case when follow_up_date is not null then 'Follow-up Date:  ' || follow_up_date end,
      case when coalesce(call_status, '') <> '' then 'Call Status:  ' || call_status end,
      case when coalesce(collections_disposition, '') <> '' then 'Collections Disposition:  ' || collections_disposition end,
      case when coalesce(nd_disposition, '') <> '' then 'ND Disposition:  ' || nd_disposition end,
      case when coalesce(critical_risk_disposition, '') <> '' then 'Critical Risk Disposition:  ' || critical_risk_disposition end,
      case when coalesce(driver_confirmation, '') <> '' then 'Driver Confirmation:  ' || driver_confirmation end,
      case when coalesce(minimum_uber_trips_pitch, '') <> '' then 'Minimum Uber Trips Pitch:  ' || minimum_uber_trips_pitch end) as txt
  from public.mv_collections_calling_masterlist
  where coalesce(call_status, '') <> '' and week = date_trunc('week', current_date - 1)::date
  order by partner_et_id, date desc, loaded_at desc
),
l2w as materialized (   -- notpaid_last2weeks_data (ASSUMED logic, see notes): last 2 hisaab weeks
  select m.partner_etm as etm,
         bool_and(coalesce(m.total_collected_amount_in_week, 0) <= 0) as zero_both,
         bool_and(m.collection_pct > 0 and m.collection_pct < 0.8)       as low_both
  from analytics.collections_bad_debt_mv m, p
  where m.for_collections = 1 and m.total_os < 0 and m.hissab_week in (p.w - 7, p.w - 14)
    and m.partner_etm in (select etm from drv)
  group by 1 having count(*) = 2
),
slab_tier(city, min_trips, tier, add_trips) as (values
  ('Mumbai',0,'0 - 14',5),('Mumbai',15,'15 - 29',10),('Mumbai',30,'Base Tier',null),
  ('Pune',0,'0 - 14',5),('Pune',15,'15 - 39',10),('Pune',40,'Base Tier',null),
  ('Chennai',0,'0 - 14',5),('Chennai',15,'15 - 39',10),('Chennai',40,'Base Tier',null),
  ('Kolkata',0,'0 - 14',5),('Kolkata',15,'15 - 39',10),('Kolkata',40,'Base Tier',null),
  ('Hyderabad',0,'0 - 14',5),('Hyderabad',15,'15 - 40',10),('Hyderabad',41,'Base Tier',null),
  ('Delhi NCR',0,'0 - 14',5),('Delhi NCR',15,'15 - 34',10),('Delhi NCR',35,'Base Tier',null),
  ('Bangalore',0,'0 - 14',5),('Bangalore',15,'15 - 44',10),('Bangalore',45,'Base Tier',null)),
slab_base(city, base_target) as (values
  ('Mumbai',40),('Pune',50),('Chennai',50),('Kolkata',65),('Hyderabad',50),('Delhi NCR',45),('Bangalore',55)),
-- ---------- base numbers per partner ----------
b as materialized (
  select d.*, p.w, p.t,
    coalesce(cl.total_os, 0) as m_os,
    coalesce(r.rz, 0) as q, coalesce(r.ot, 0) as r_, coalesce(r.pp, 0) as s, coalesce(r.adj, 0) as t_, coalesce(r.dp, 0) as u,
    coalesce(r.rz, 0) + coalesce(r.ot, 0) + coalesce(r.pp, 0) + coalesce(r.adj, 0) + coalesce(r.dp, 0) as n_rec,
    coalesce(r.tot_sod, 0) as n_rec_sod,
    case when coalesce(dp.dep_now, 0) >= 1 then round(dp.dep_now)::int else 0 end as v_dep,
    case when coalesce(dp.dep_sod, 0) >= 1 then round(dp.dep_sod)::int else 0 end as v_dep_sod,
    coalesce(lw.os, 0) as y_lwos,
    coalesce(e.car_cnt, 0) as z_cars, coalesce(e.rent_days, 0) as aa_days, -abs(coalesce(e.rent, 0)) as ab_rent,
    coalesce(e.fare_tip, 0) as ac_fare, coalesce(e.cash, 0) as ad_cash, coalesce(e.subs, 0) as ae_subs,
    mn.car_model
  from drv d cross join p
  left join cl on cl.etm = d.etm
  left join rec r on r.etm = d.etm
  left join dep dp on dp.etm = d.etm
  left join lwos lw on lw.driver_id = d.driver_id
  left join earn e on e.driver_id = d.driver_id
  left join model_now mn on mn.driver_id = d.driver_id
),
b2 as materialized (
  select b.*,
    b.m_os + least(b.n_rec, abs(b.m_os))         as o_net,
    b.m_os + least(b.n_rec_sod, abs(b.m_os))     as o_net_sod,
    (b.y_lwos + b.n_rec) + (b.ac_fare - b.ad_cash) + b.ab_rent + b.ae_subs     as af_os,
    (b.y_lwos + b.n_rec_sod) + (b.ac_fare - b.ad_cash) + b.ab_rent + b.ae_subs as af_os_sod,
    case when b.car_model ~* 'wagon ?r.*2026' then 20000
         when b.car_model ~* 'wagon ?r|celerio|s-?presso' then 15000
         when b.car_model ~* 'rumion' then 45000 else 30000 end as own_now_thr
  from b
),
b3 as materialized (   -- AI rule, evaluated on live (now) and start-of-day (sod) numbers
  select b2.*,
    coalesce(case when b2.product <> 'Own Now' and b2.af_os > 0 then false
          else (b2.product = 'D2O' and coalesce(abs(b2.af_os) / nullif(b2.v_dep, 0), 0) >= 0.7)
            or (b2.product = 'Own Now' and b2.o_net <= -b2.own_now_thr)
            or (b2.product in ('SINGLE', 'EV') and case when b2.aa_days = 0 then coalesce(abs(b2.af_os) / nullif(b2.v_dep, 0), 0) >= 0.8
                                                         else (b2.af_os + b2.v_dep) <= abs(b2.ab_rent::numeric / b2.aa_days) end)
            or (b2.product in ('Revenue Share', 'Fixed Pay') and coalesce(abs(b2.af_os) / nullif(b2.v_dep, 0), 0) >= 1)
            or (b2.product = 'EIP' and case when b2.z_cars >= 10 then b2.af_os <= -50000 else b2.af_os <= -25000 end)
     end, false) as crit_now,
    coalesce(case when b2.product <> 'Own Now' and b2.af_os_sod > 0 then false
          else (b2.product = 'D2O' and coalesce(abs(b2.af_os_sod) / nullif(b2.v_dep_sod, 0), 0) >= 0.7)
            or (b2.product = 'Own Now' and b2.o_net_sod <= -b2.own_now_thr)
            or (b2.product in ('SINGLE', 'EV') and case when b2.aa_days = 0 then coalesce(abs(b2.af_os_sod) / nullif(b2.v_dep_sod, 0), 0) >= 0.8
                                                         else (b2.af_os_sod + b2.v_dep_sod) <= abs(b2.ab_rent::numeric / b2.aa_days) end)
            or (b2.product in ('Revenue Share', 'Fixed Pay') and coalesce(abs(b2.af_os_sod) / nullif(b2.v_dep_sod, 0), 0) >= 1)
            or (b2.product = 'EIP' and case when b2.z_cars >= 10 then b2.af_os_sod <= -50000 else b2.af_os_sod <= -25000 end)
     end, false) as crit_sod
  from b2
)
select
  x.w                                                   as "week",
  x.t                                                   as "date",
  'Agent Missing'                                       as "agent_username",
  x.etm                                                 as "partner_et_id",
  x.lead_id                                             as "lead_id",
  x.partner_name                                        as "partner_name",
  x.city                                                as "city",
  x.product                                             as "product_type",
  case when elc.driver_id is not null then 'ELC' else 'Non_ELC' end as "elc_filter",
  coalesce(cn.cars, '')                                 as "car_numbers",
  case when abs(x.m_os) <= 500 then '0-500' when abs(x.m_os) <= 1000 then '500-1K' when abs(x.m_os) <= 2000 then '1-2K'
       when abs(x.m_os) <= 3000 then '2-3K' when abs(x.m_os) <= 5000 then '3-5K' when abs(x.m_os) <= 10000 then '5-10K'
       when abs(x.m_os) <= 15000 then '10-15K' when abs(x.m_os) <= 20000 then '15-20K' when abs(x.m_os) <= 25000 then '20-25K'
       when abs(x.m_os) <= 30000 then '25-30K' else '30K+' end as "OS_Bucket",
  case when x.v_dep <= 3000 then '0-3K' when x.v_dep <= 5000 then '3-5K' when x.v_dep <= 10000 then '5-10K'
       when x.v_dep <= 15000 then '10-15K' when x.v_dep <= 20000 then '15-20K' when x.v_dep <= 25000 then '20-25K'
       when x.v_dep <= 30000 then '25-30K' when x.v_dep <= 50000 then '30-50K' else '50K+' end as "DP_Bucket",
  x.m_os                                                as "negative_os",
  x.n_rec                                               as "total_recovery",
  x.o_net                                               as "net_os",
  case when x.m_os = 0 then 0 else least(x.n_rec, abs(x.m_os)) / abs(x.m_os) end as "recovery_pct",
  x.q as "razorpay_recovery", x.r_ as "other_recovery", x.s as "phonepe_recovery", x.t_ as "adjustments", x.u as "dp_to_os",
  x.v_dep                                               as "current_deposit",
  case when exists (select 1 from alloc_today a where a.driver_id = x.driver_id and a.deallocation_id is null)
       then 'Active' else 'Inactive' end                as "active / inactive",
  coalesce(h.habit, 'Good')                             as "last_payment_habit",
  x.y_lwos                                              as "Last Week OS",
  x.z_cars                                              as "Car Count",
  x.aa_days                                             as "Current Week Rented Days",
  x.ab_rent                                             as "Current Week Lease Rent",
  x.ac_fare                                             as "Current Week fare_total (Inc. Tip & Toll)",
  x.ad_cash                                             as "Current Week Cash Collected",
  x.ae_subs                                             as "Current Week subscription_charges",
  x.af_os                                               as "Total Current OS",
  x.af_os + x.v_dep                                     as "Current OS Surpass SD",
  case when rc.driver_id is not null then 'Yes' else 'No' end as "Is_in Car Recovery",
  case when x.crit_now then 'Critical_Risk' else '' end as "Risk_Type",
  coalesce(n.lw_active, 0) as "last_week_active_days", coalesce(n.lw_nd, 0) as "last_week_nd_days",
  coalesce(n.cw_active, 0) as "current_week_active_days", coalesce(n.cw_nd, 0) as "current_week_nd_days",
  coalesce(n.gps, 0) as "current_week_gps_kms", coalesce(n.uber, 0) as "current_week_uber_kms",
  coalesce(n.dead, 0) as "current_week_dead_kms", coalesce(n.trips, 0) as "current_week_uber_trips",
  lp.d                                                  as "last_paid_date",
  lj.d                                                  as "last_jama_date",
  coalesce(c.att, 0) as "att_total", coalesce(c.conn, 0) as "conn_total",
  c.last_att as "last_attempt_time", c.last_conn as "last_connect_time",
  coalesce(cdp.last_subdisposition, '')                 as "last_disposition",
  coalesce(c.att_today, 0) as "att_today", coalesce(c.conn_today, 0) as "conn_today",
  case when x.product in ('D2O', 'SINGLE', 'OWN')       -- SHEET BUG: 'OWN' (Own Now never matches)
       then case when coalesce(n.gps_yday, 0) > 0 then 'GPS>0' else 'GPS=0' end else '-' end as "GPS_Tag",
  case when x.product = 'D2O' then coalesce(nj.cat, '') else '' end as "allocation_type",
  case when x.product = 'D2O' then 'Penalty' else '' end as "actioning_type",
  case when coalesce(n.disp, 0) = 0 then '-' else round(n.acc::numeric / n.disp, 4)::text end as "acceptance_rate",
  tr.trip_tier                                          as "trip_tier",
  tr.target_trips                                       as "target_trips",
  case when x.product in ('D2O', 'SINGLE', 'Own Now') then greatest(coalesce(tr.target_trips, 0) - coalesce(n.trips, 0), 0)::text
       else '-' end                                     as "min_remaining_trips",
  case when x.in_cl = 0 then ''
       when least(x.n_rec, abs(x.m_os)) >= abs(x.m_os) or abs(x.m_os) - x.n_rec < 100 then 'Full Paid'
       when x.n_rec > 0 then 'Partial Paid' else 'Not Paid' end as "Collections Tag",
  case when x.crit_sod then case when x.crit_now then 'Critical_Risk' else 'Out of Critical' end else '' end as "Critical Risk Tag",
  case when ndl.driver_id is not null then 'ND' else '' end as "Yesterday ND Tag",
  null::int                                             as "RANK (read rnnk appscript)",
  coalesce(rm.txt, '-')                                 as "Yesterday Remarks",
  case when rc.driver_id is null then '-' else (x.t - rc.act_dt)::text end as "Car_Recovery Pending TAT",
  case when l.zero_both then 'L2W: 0%' when l.low_both then 'L2W: 1%-80%' else '-' end as "L2W 1% to 80% ",
  coalesce(lj.d_lw::text, '-')                          as "last_jama_date",
  ''                                                    as " ",
  greatest(0, x.y_lwos + x.n_rec)                       as "  ",
  ''                                                    as "   ",
  coalesce(x.car_model, '')                             as "car_model"
from b3 x
left join elc on elc.driver_id = x.driver_id
left join cars_now cn on cn.driver_id = x.driver_id
left join habit h on h.driver_id = x.driver_id
left join rcar rc on rc.driver_id = x.driver_id
left join nda n on n.driver_id = x.driver_id
left join lpaid lp on lp.etm = x.etm
left join ljama lj on lj.driver_id = x.driver_id
left join calls c on c.etm = x.etm
left join call_disp cdp on cdp.etm = x.etm
left join newjoin nj on nj.etm = x.etm
left join ndlist ndl on ndl.driver_id = x.driver_id
left join remarks rm on rm.etm = x.etm
left join l2w l on l.etm = x.etm
left join lateral (
  select case when x.product in ('SINGLE', 'Own Now') then 'Base Tier'
              when x.product = 'D2O' then case when nj.etm is not null then 'Base Tier' else st.tier end end as trip_tier,
         case when x.product in ('SINGLE', 'Own Now') then sb.base_target
              when x.product = 'D2O' then case when nj.etm is not null or st.tier = 'Base Tier' then sb.base_target
                                               else coalesce(n.lw_trips, 0) + st.add_trips end end as target_trips
  from (select 1) one
  left join slab_base sb on sb.city = case when x.city = 'Delhi' then 'Delhi NCR' else x.city end
  left join lateral (select s.tier, s.add_trips from slab_tier s
                     where s.city = case when x.city = 'Delhi' then 'Delhi NCR' else x.city end and s.min_trips <= coalesce(n.lw_trips, 0)
                     order by s.min_trips desc limit 1) st on true
) tr on true
order by x.in_cl desc, x.city, x.etm
