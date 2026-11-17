-- Driver dues comms (WhatsApp template) - LIGHT version: one row per pilot with a car now OR who ran a car this week, current hisaab week (Mon .. yesterday), Rs.
-- 17-Nov: + Start / End date columns, car_status, os_status, trip_days; 'Check' flag when the car ran but no live OS row (rent not charged)
--  {{1}} date  {{2}} vehicle  {{3}} A earnings (fare + tip)  {{4}} B subscription  {{5}} C cash collected  {{6}} Uber transfer = A - B - C
--  {{7}} current deposit  {{8}} rent days  {{9}} A last week pending arrears  {{10}} B rent (current week)  {{11}} C Uber transfer (credit, negative)
--  {{12}} D pending arrears = A + B + C  {{13}} E recovered (current week)  {{14}} overall due = D - E
-- No driver phone in the reporting DB (crm.lead_lead_view is empty) -> lead_id + partner_et_id for the comms tool.
-- Dues positive, credits negative. Every source is aggregated once for the week (no per-pilot IN filters, no car-day expansion).
with cfg as materialized (select date_trunc('week', current_date)::date as wk, current_date - 1 as yd),
act as materialized (
  select ca.driver_id, string_agg(distinct fc.car_number, ', ') as cars
  from car_allocation ca join fleet_car fc on fc.id = ca.car_id
  where ca.deactivation_date is null and ca.deallocation_id is null and ca.allocation_date::date <= current_date
  group by 1
),
-- trip is defined before drv (moved up) so pilots who ran a car this week without an active allocation are included
trip as materialized (
  select t.driver_id, sum(coalesce(t.fare_total, 0) + coalesce(t.tip_amount, 0)) as fare,
         sum(abs(coalesce(t.subscription_charges, 0))) as subs, sum(coalesce(t.cash_collected, 0)) as cash,
         count(distinct t.date) filter (where coalesce(t.fare_total, 0) > 0) as trip_days,
         string_agg(distinct t.car_number, ', ') as cars_t
  from fleet_dailytrip t
  where t.date between date_trunc('week', current_date)::date and current_date - 1 and t.driver_id is not null
  group by 1
),
drv as materialized (   -- 17-Nov: active car now  UNION  ran a car this week (earnings > 0) even with no active allocation
  select u.driver_id, fd.employee_id as etm, fd.name, coalesce(a.cars, t.cars_t) as cars, (a.driver_id is not null) as has_car,
         coalesce(t.trip_days, 0) as trip_days
  from (select driver_id from act union select driver_id from trip where fare > 0) u
  join fleet_driver fd on fd.id = u.driver_id
  left join act a on a.driver_id = u.driver_id
  left join trip t on t.driver_id = u.driver_id
),
mvw as materialized (
  select distinct on (m.partner_etm) m.partner_etm as etm, m.city, m.lead_id,
    case when m.product_type = 'EV' then 'EV' when m.revenue_type = 'Leasing' then case when m.eip_tag = 1 then 'EIP' else 'SINGLE' end
         else m.revenue_type end as product
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1 and m.hissab_week = date_trunc('week', current_date)::date
  order by m.partner_etm, m.id desc
),
al as materialized (
  select distinct on (s.employee_id) s.employee_id as etm, s.city,
    case when s.product_type = 'leasing' then case when s.fuel_type ilike 'ev%' then 'EV' else 'SINGLE' end
         when s.product_type = 'DTO' then case when s.fuel_type ilike 'ev%' then 'EV_D2O' else 'D2O' end
         when s.product_type = 'Rev_share' then 'Revenue Share' else s.product_type end as product
  from analytics.ssot_alloc_dealloc_full s
  where s.allocation_date <= current_date
  order by s.employee_id, s.allocation_date desc, s.allocation_datetime desc
),
live as materialized (
  select h.driver_id,
    (array_agg(h.live_os order by h.date desc))[1] as lo_last,
    coalesce(sum(h.total_rent) filter (where h.date between date_trunc('week', current_date)::date and current_date - 1), 0) as rent_cw,
    count(distinct h.date) filter (where h.date between date_trunc('week', current_date)::date and current_date - 1) as rent_days
  from hissab_driver_live_os h
  where h.date between date_trunc('week', current_date)::date - 1 and current_date and h.is_active = 1
  group by 1
),
rec as materialized (
  select r.employee_id as etm, sum(r.amount) as rec
  from mv_daily_recovery r
  where r.date between date_trunc('week', current_date)::date and current_date
    and r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery','positive_adjustment','deposit_to_os')
  group by 1
),
dep as materialized (
  select d.employee_id as etm, sum(d.amount) as dep from mv_deposits_raw d
  where d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[])
  group by 1
),
lw as materialized (
  select x.partner_id as driver_id, sum(x.total_os) as lw_os
  from (select driver_id as partner_id, total_os from account_ledger
        where week_start_date >= (date_trunc('week', current_date - interval '1 day') - interval '1 week') and week_start_date < date_trunc('week', current_date - interval '1 day')
        union all
        select partner_id, total_os from fleet_leasing_total_os
        where week_start_date >= (date_trunc('week', current_date - interval '1 day') - interval '1 week') and week_start_date < date_trunc('week', current_date - interval '1 day')) x
  group by 1
),
ld as materialized (
  select distinct on (l.hawkeye_driver_id) l.hawkeye_driver_id as driver_id, l.lead_id
  from crm.lead_driver l where coalesce(l.is_deleted, 0) = 0
  order by l.hawkeye_driver_id, l.id desc
),
x as materialized (
  select d.etm, d.name, d.cars, coalesce(m.city, a.city) as city, coalesce(m.product, a.product) as product,
    coalesce(t.fare, 0) as e_a, coalesce(t.subs, 0) as e_b, coalesce(t.cash, 0) as e_c,
    coalesce(t.fare, 0) - coalesce(t.subs, 0) - coalesce(t.cash, 0) as uber_tr,
    greatest(coalesce(dp.dep, 0), 0) as dep, coalesce(lv.rent_days, 0) as rent_days,
    -coalesce(w.lw_os, 0) as d_a, abs(coalesce(lv.rent_cw, 0)) as d_b, coalesce(r.rec, 0) as rec, lv.lo_last,
    d.has_car, d.trip_days, (lv.driver_id is not null) as has_live,
    coalesce(m.lead_id::bigint, ld.lead_id) as lead_id
  from drv d
  left join mvw m on m.etm = d.etm
  left join al a on a.etm = d.etm
  left join trip t on t.driver_id = d.driver_id
  left join live lv on lv.driver_id = d.driver_id
  left join rec r on r.etm = d.etm
  left join dep dp on dp.etm = d.etm
  left join lw w on w.driver_id = d.driver_id
  left join ld on ld.driver_id = d.driver_id
)
select
  to_char(current_date, 'DD-Mon-YYYY') as "{{1}} Date",
  coalesce(cars, '') as "{{2}} Vehicle No",
  round(e_a) as "{{3}} Earnings",
  round(e_b) as "{{4}} Subscription Fee",
  round(e_c) as "{{5}} Cash Collection",
  round(uber_tr) as "{{6}} Uber Transfer (A-B-C)",
  round(dep) as "{{7}} Current Deposit",
  rent_days as "{{8}} Rent Days",
  round(d_a) as "{{9}} Last Week Pending Arrears",
  round(d_b) as "{{10}} Rent Amount (Current Week)",
  round(-uber_tr) as "{{11}} Uber Transfer",
  round(d_a + d_b - uber_tr) as "{{12}} Pending Arrears (A+B+C)",
  round(rec) as "{{13}} Recovered Amount (Current Week)",
  round(d_a + d_b - uber_tr - rec) as "{{14}} Overall Due (D-E)",
  to_char(date_trunc('week', current_date), 'DD-Mon-YYYY') as "Start Date",
  to_char(current_date - 1, 'DD-Mon-YYYY') as "End Date (earnings, rent)",
  to_char(current_date, 'DD-Mon-YYYY') as "Recovery till",
  etm as "partner_et_id",
  name as "partner_name",
  lead_id as "lead_id",
  city as "city",
  product as "product_type",
  round(-lo_last) as "check: live OS due",
  round(d_a + d_b - uber_tr - rec + coalesce(lo_last, 0)) as "check: diff vs live OS",
  case when has_car then 'Active car' else 'No active car (ran this week)' end as "car_status",
  case when has_live then 'Live OS' else 'No Live OS (rent not charged)' end as "os_status",
  trip_days as "trip_days (this week)",
  case when not has_live and trip_days > 0 then 'Check - car ran, OS not generated'
       when round(d_a + d_b - uber_tr - rec) > 0 then 'Send' else 'Skip' end as "send_flag",
  to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') as "last_updated"
from x
order by city, round(d_a + d_b - uber_tr - rec) desc
