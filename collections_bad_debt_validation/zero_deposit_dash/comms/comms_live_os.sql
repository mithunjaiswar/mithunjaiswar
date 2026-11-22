-- Driver dues comms (WhatsApp template) - built from hissab_driver_live_os = the numbers the driver sees in the app.
-- 20-Nov: moved into the zero sheet (tab Comms). Same filter as the old Driver Dues Comms > For_Coms tab:
--   product = Leasing - Single, current deposit <= 3000, Overall Due < 0 (driver owes).
-- One row per pilot with a live OS row this hisaab week AND (an active car now OR Uber earnings this week).
-- Sign = same as the system: due / owes = NEGATIVE, credit / payment = POSITIVE.
--  {{3}} A earnings  = sum(fare_total + tip_amount) from uber_data (Mon .. today rows)
--  {{4}} B subscription, {{5}} C cash = sum from uber_data
--  {{6}} / {{11}} Uber transfer = sum(uber_revenue) (what the live OS credits)
--  {{8}} rent days = live OS rows with rent; {{10}} rent = -sum(total_rent) (rent is booked on the next day's row)
--  {{9}} last week pending arrears = weekly_os of the latest row
--  {{12}} D = {{9}} + {{10}} + {{11}};  {{14}} = latest live_os (app);  {{13}} E = {{14}} - {{12}} (payments + adjustments)
-- Only small joins: active car numbers, deposit, product / city, lead id - all filtered to the live OS drivers.
with lv0 as materialized (
  select h.driver_id, h.date, h.live_os, h.weekly_os, coalesce(h.total_rent, 0) as rent, coalesce(h.uber_revenue, 0) as uber_rev,
         coalesce(substring(h.uber_data from '"fare_total": (-?[0-9.]+)')::numeric, 0)
       + coalesce(substring(h.uber_data from '"tip_amount": (-?[0-9.]+)')::numeric, 0) as fare,
         coalesce(substring(h.uber_data from '"subscription_charges": (-?[0-9.]+)')::numeric, 0) as subs,
         coalesce(substring(h.uber_data from '"cash_collected": (-?[0-9.]+)')::numeric, 0) as cash
  from hissab_driver_live_os h
  where h.date between date_trunc('week', current_date)::date and current_date and h.is_active = 1
),
lv as materialized (
  select driver_id,
    (array_agg(live_os order by date desc))[1] as lo_now,
    (array_agg(weekly_os order by date desc))[1] as wos,
    max(date) as last_row,
    sum(rent) as rent_cw, count(*) filter (where rent > 0) as rent_days,
    sum(uber_rev) as uber_tr, sum(fare) as fare, sum(abs(subs)) as subs, sum(cash) as cash
  from lv0 group by 1
),
act as materialized (   -- 20-Nov: active cars now; if none, the last car the pilot had (car returned this week) so {{2}} is never blank
  select ca.driver_id,
    string_agg(distinct fc.car_number, ', ') filter (where ca.deallocation_id is null) as cars,
    (array_agg(fc.car_number order by ca.allocation_date desc))[1] as last_car,
    bool_or(ca.deallocation_id is null) as has_car
  from car_allocation ca left join fleet_car fc on fc.id = ca.car_id   -- left join: active-car status survives a fleet_car re-sync
  where ca.deactivation_date is null and ca.allocation_date::date <= current_date
    and ca.driver_id in (select driver_id from lv)
  group by 1
),
drv as materialized (
  select l.*, fd.employee_id as etm, fd.name, coalesce(a.cars, a.last_car) as cars, coalesce(a.has_car, false) as has_car
  from lv l join fleet_driver fd on fd.id = l.driver_id
  left join act a on a.driver_id = l.driver_id
  where coalesce(a.has_car, false) or l.fare > 0
),
mvw as materialized (   -- group by (not distinct on .. order by id: that is 20x slower on this MV)
  select m.partner_etm as etm, max(m.city) as city, max(m.lead_id) as lead_id,
    case when bool_or(m.product_type = 'EV') then 'EV'
         when bool_or(m.revenue_type = 'Leasing') then case when bool_or(m.eip_tag = 1) then 'EIP' else 'SINGLE' end
         else max(m.revenue_type) end as product
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1 and m.hissab_week = date_trunc('week', current_date)::date
  group by 1
),
al as materialized (   -- product / city fallback for pilots not in this week's dashboard (new joiners)
  select distinct on (s.employee_id) s.employee_id as etm, s.city,
    case when s.product_type = 'leasing' then case when s.fuel_type ilike 'ev%' then 'EV' else 'SINGLE' end
         when s.product_type = 'DTO' then case when s.fuel_type ilike 'ev%' then 'EV_D2O' else 'D2O' end
         when s.product_type = 'Rev_share' then 'Revenue Share' else s.product_type end as product
  from analytics.ssot_alloc_dealloc_full s
  where s.allocation_date between current_date - 21 and current_date   -- new joiners only (others are in this week's dashboard); full scan of this table is slow
  order by s.employee_id, s.allocation_date desc, s.allocation_datetime desc
),
dep as materialized (
  select d.employee_id as etm, sum(d.amount) as dep from mv_deposits_raw d
  where d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[]) and d.employee_id in (select etm from drv)
  group by 1
),
ld as materialized (
  select distinct on (l.hawkeye_driver_id) l.hawkeye_driver_id as driver_id, l.lead_id
  from crm.lead_driver l where coalesce(l.is_deleted, 0) = 0 and l.hawkeye_driver_id in (select driver_id from drv)
  order by l.hawkeye_driver_id, l.id desc
),
x as materialized (
  select d.*, coalesce(m.city, a.city) as city, coalesce(m.product, a.product) as product,
    greatest(coalesce(dp.dep, 0), 0) as dep_now, coalesce(m.lead_id::bigint, ld.lead_id) as lead_id,
    coalesce(d.wos, 0) - d.rent_cw + d.uber_tr as pend
  from drv d
  left join mvw m on m.etm = d.etm
  left join al a on a.etm = d.etm
  left join dep dp on dp.etm = d.etm
  left join ld on ld.driver_id = d.driver_id
)
select
  to_char(current_date, 'DD-Mon-YYYY') as "{{1}} Date",
  coalesce(cars, '') as "{{2}} Vehicle No",
  round(fare) as "{{3}} Earnings",
  round(subs) as "{{4}} Subscription Fee",
  round(cash) as "{{5}} Cash Collection",
  round(uber_tr) as "{{6}} Uber Transfer (A-B-C)",
  round(dep_now) as "{{7}} Current Deposit",
  rent_days as "{{8}} Rent Days",
  round(coalesce(wos, 0)) as "{{9}} Last Week Pending Arrears",
  round(-rent_cw) as "{{10}} Rent Amount (Current Week)",
  round(uber_tr) as "{{11}} Uber Transfer",
  round(pend) as "{{12}} Pending Arrears (A+B+C)",
  round(lo_now - pend) as "{{13}} Recovered Amount (Current Week)",
  round(lo_now) as "{{14}} Overall Due (D+E)",
  etm as "partner_et_id",
  name as "partner_name",
  lead_id as "lead_id",
  city as "city",
  'Leasing - Single' as "product",
  case when has_car then 'Active car' else 'No active car (ran this week, last car shown)' end as "car_status",
  to_char(last_row, 'DD-Mon-YYYY') as "live_os_row_date",
  to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') as "last_updated"
from x
where product = 'SINGLE' and dep_now <= 3000 and round(lo_now) < 0
  and (select 1 / (count(*) / 5000) from lv) is not null   -- guard: fail instead of writing a half-synced live OS (< 5000 drivers)
  and (select 1 / (count(*) / 20000) from fleet_car) is not null   -- guard: fleet_car is reloaded (delete + insert) by sync; fail instead of blank Vehicle No
  and (select 1 / (count(*) / 10000) from car_allocation where deallocation_id is null and deactivation_date is null) is not null   -- guard: car_allocation mid-reload
order by city, round(lo_now)
