-- Driver dues comms (WhatsApp template) - one row per active pilot, current hisaab week (Mon .. yesterday), amounts in Rs.
-- Same base as zero sheet Agent_action (agent_action_masterlist.sql). Template variables:
--  {{1}} date  {{2}} vehicle  {{3}} A earnings (fare + tip)  {{4}} B subscription  {{5}} C cash collected  {{6}} Uber transfer = A - B - C
--  {{7}} current deposit  {{8}} rent days  {{9}} A last week pending arrears  {{10}} B rent (current week)  {{11}} C Uber transfer (credit, shown negative)
--  {{12}} D pending arrears = A + B + C  {{13}} E recovered (current week)  {{14}} overall due = D - E
-- Sign rule: dues are positive, credits negative, so D = A + B + C and Overall = D - E work as written in the template.
with cfg as materialized (
  select date_trunc('week', current_date)::date as wk,
         current_date as td, current_date - 1 as yd
),
mvw as materialized (
  select distinct on (m.partner_etm) m.partner_etm as etm, m.lead_id, m.city,
         case when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV_Leasing'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.revenue_type end as product_type,
         m.eip_tag, coalesce(m.total_os, 0) as total_os, m.tenure_days
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1
    and m.hissab_week = (select max(hissab_week) from analytics.collections_bad_debt_mv where for_collections = 1 and hissab_week <= current_date)
  order by m.partner_etm, m.id desc
),
act as materialized (
  select ca.driver_id, ca.car_id, ca.allocation_date
  from car_allocation ca
  where ca.deactivation_date is null and ca.deallocation_id is null and ca.allocation_date::date <= current_date
),
act_e as materialized (select distinct fd.employee_id as etm from act a join fleet_driver fd on fd.id = a.driver_id),
pop as materialized (select etm from mvw union select etm from act_e),
drv as materialized (
  select distinct on (fd.employee_id) fd.employee_id as etm, fd.id as driver_id, fd.name
  from fleet_driver fd where fd.employee_id in (select etm from pop)
  order by fd.employee_id, fd.id desc
),
lead as materialized (
  select distinct on (l.hawkeye_driver_id) l.hawkeye_driver_id as driver_id, l.lead_id
  from crm.lead_driver l where coalesce(l.is_deleted, 0) = 0
  order by l.hawkeye_driver_id, l.id desc
),
alloc_last as materialized (
  select distinct on (s.employee_id) s.employee_id as etm, s.city,
         case when s.product_type = 'leasing' then case when s.fuel_type ilike 'ev%' then 'EV_Leasing' else 'Leasing' end
              when s.product_type = 'DTO' then case when s.fuel_type ilike 'ev%' then 'EV_D2O' else 'D2O' end
              when s.product_type = 'Rev_share' then 'Revenue Share' else s.product_type end as product_type,
         s.first_allocation_date
  from analytics.ssot_alloc_dealloc_full s
  where s.allocation_date <= current_date
  order by s.employee_id, s.allocation_date desc, s.allocation_datetime desc
),
newjoin as materialized (
  select distinct s.employee_id as etm from analytics.ssot_alloc_dealloc_full s
  where s.allocation_date >= date '2026-08-17' and s.category in ('New Join', 'Resurrection')
),
cars_now as materialized (
  select fd.employee_id as etm, string_agg(distinct fc.car_number, ', ') as car_numbers,
         (array_agg(cm.name order by a.allocation_date desc))[1] as car_model
  from act a join fleet_driver fd on fd.id = a.driver_id
  join fleet_car fc on fc.id = a.car_id left join fleet_car_model cm on cm.id = fc.model_id
  group by 1
),
-- one row per allocated car per day, last week Mon .. yesterday (same base as earnings_raw / nd_raw)
cday as materialized (
  select d.dd::date as d, ca.car_id, ca.driver_id
  from car_allocation ca
  left join car_deallocation cd on cd.id = ca.deallocation_id
  cross join lateral generate_series(greatest(ca.allocation_date::date, date_trunc('week', current_date)::date - 7),
                                     least(coalesce(cd.date::date, current_date), current_date - 1), interval '1 day') d(dd)
  where ca.deactivation_date is null and ca.allocation_date::date <= current_date - 1
    and coalesce(cd.date::date, current_date) >= date_trunc('week', current_date)::date - 7
),
trip as materialized (
  select t.car_id, t.date as d, sum(t.trips) as trips, sum(t.dispatch_trips) as disp, sum(t.accepted_trips) as acc,
         sum(t.fare_total) as fare, sum(t.tip_amount) as tip, sum(t.cash_collected) as cash, sum(t.subscription_charges) as subs
  from fleet_dailytrip t
  where t.date between date_trunc('week', current_date)::date - 7 and (current_date - 1) and t.trips > 0 and t.car_id is not null
  group by 1, 2
),
ola_yd as materialized (
  select o.car_id, sum(o.trips) as trips from fleet_ola_dailytrip o
  where o.date::date = (current_date - 1) and o.car_id is not null group by 1
),
kms as materialized (
  select k.car_id, k.date as d, sum(k.gps_km) as gps, sum(k.uber_km) as uber, sum(k.dead_km) as dead
  from car_dead_km k where k.date between date_trunc('week', current_date)::date and (current_date - 1) and coalesce(k.is_deleted, 0) = 0 group by 1, 2
),
drive as materialized (
  select c.driver_id,
    count(distinct c.car_id) filter (where c.d >= cfg.wk) as car_count,
    count(*) filter (where c.d >= cfg.wk) as rented_days,
    count(*) filter (where c.d < cfg.wk) as lw_active,
    count(*) filter (where c.d < cfg.wk and coalesce(t.trips, 0) <= 0) as lw_nd,
    count(*) filter (where c.d >= cfg.wk) as cw_active,
    count(*) filter (where c.d >= cfg.wk and coalesce(t.trips, 0) <= 0) as cw_nd,
    coalesce(sum(t.fare + t.tip) filter (where c.d >= cfg.wk), 0) as fare,
    coalesce(sum(t.cash) filter (where c.d >= cfg.wk), 0) as cash,
    coalesce(sum(t.subs) filter (where c.d >= cfg.wk), 0) as subs,
    coalesce(sum(k.gps) filter (where c.d >= cfg.wk), 0) as gps,
    coalesce(sum(k.uber) filter (where c.d >= cfg.wk), 0) as uber_km,
    coalesce(sum(k.dead) filter (where c.d >= cfg.wk), 0) as dead_km,
    coalesce(sum(t.trips) filter (where c.d >= cfg.wk), 0) as trips_cw,
    coalesce(sum(t.trips) filter (where c.d < cfg.wk), 0) as trips_lw,
    sum(t.acc) filter (where c.d >= cfg.wk) as acc, sum(t.disp) filter (where c.d >= cfg.wk) as disp,
    bool_or(c.d = cfg.yd) as alloc_yd,
    coalesce(sum(k.gps) filter (where c.d = cfg.yd), 0) as gps_yd,
    coalesce(sum(t.trips) filter (where c.d = cfg.yd), 0) + coalesce(sum(o.trips) filter (where c.d = cfg.yd), 0) as trips_yd
  from cday c cross join cfg
  left join trip t on t.car_id = c.car_id and t.d = c.d
  left join kms k on k.car_id = c.car_id and k.d = c.d
  left join ola_yd o on o.car_id = c.car_id and c.d = cfg.yd
  group by c.driver_id
),
live as materialized (
  select h.driver_id,
         (array_agg(h.live_os order by h.date desc))[1] as lo_last,
         (array_agg(h.live_os order by h.date desc) filter (where h.date <= (current_date - 1)))[1] as lo_yd,
         (array_agg(h.total_rent order by h.date desc))[1] as day_rent,
         sum(h.total_rent) filter (where h.date between date_trunc('week', current_date)::date and (current_date - 1)) as rent_cw
  from hissab_driver_live_os h
  where h.date between date_trunc('week', current_date)::date - 1 and current_date and h.is_active = 1
  group by 1
),
rec as materialized (
  select r.employee_id as etm,
    coalesce(sum(r.amount) filter (where r.recovery_type = 'razorpay_recovery'), 0) as rz,
    coalesce(sum(r.amount) filter (where r.recovery_type = 'other_positive_recovery'), 0) as oth,
    coalesce(sum(r.amount) filter (where r.recovery_type = 'phonepe_recovery'), 0) as pp,
    coalesce(sum(r.amount) filter (where r.recovery_type = 'positive_adjustment'), 0) as adj,
    coalesce(sum(r.amount) filter (where r.recovery_type = 'deposit_to_os'), 0) as dpo
  from mv_daily_recovery r
  where r.date >= date_trunc('week', current_date)::date and r.date <= current_date
    and r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery','positive_adjustment','deposit_to_os')
  group by 1
),
lastpaid as materialized (
  select r.employee_id as etm, max(r.date) as d from mv_daily_recovery r
  where r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery')
    and r.date >= date_trunc('week', current_date)::date - 56 and r.employee_id is not null group by 1
),
dep as materialized (
  select d.employee_id as etm, sum(d.amount) as dep from mv_deposits_raw d
  where d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[])
  group by 1
),
habit as materialized (
  select distinct on (a.driver_id) a.driver_id, coalesce(a.payment_habit, 'Good') as habit
  from driver_repayment_habit a
  where a.week_start_date < (date_trunc('week', current_date) - interval '7 days')::date   -- no driver_id IN (drv) filter: that plan took >15 min, all drivers = 1 s
  order by a.driver_id, a.week_start_date desc, a.id desc
),
lwos as materialized (
  select fd.employee_id as etm, sum(os.total_os)::int as os
  from (select driver_id as partner_id, total_os from account_ledger
        where week_start_date >= (date_trunc('week', current_date - interval '1 day') - interval '1 week') and week_start_date < date_trunc('week', current_date - interval '1 day')
        union all
        select partner_id, total_os from fleet_leasing_total_os
        where week_start_date >= (date_trunc('week', current_date - interval '1 day') - interval '1 week') and week_start_date < date_trunc('week', current_date - interval '1 day')) os   -- range filter (index on week_start_date); date_trunc() on the column scanned all 14M rows
  join fleet_driver fd on fd.id = os.partner_id
  group by 1
),
jama as materialized (
  select fd.employee_id as etm,
         max(cd.date::date) as last_jama_4w,
         max(cd.date::date) filter (where cd.date::date >= cfg.wk - 7) as last_jama_1w
  from car_allocation ca join car_deallocation cd on cd.id = ca.deallocation_id
  join fleet_driver fd on fd.id = ca.driver_id cross join cfg
  where ca.deactivation_date is null and cd.date >= cfg.wk - 28
    and not exists (select 1 from car_allocation c2 where c2.driver_id = ca.driver_id and c2.deactivation_date is null and c2.deallocation_id is null)
  group by 1
),
calls as materialized (
  select c.partner_et_id as etm,
    sum(c.attempt_count) as att, sum(c.connect_count) as conn,
    max(c.last_attempt_time) as last_att, max(c.last_connect_time) as last_conn,
    (array_agg(c.last_subdisposition order by c.last_connect_time desc nulls last) filter (where coalesce(c.last_subdisposition, '') <> ''))[1] as last_dispo,
    coalesce(sum(c.attempt_count) filter (where c.date = cfg.td), 0) as att_td,
    coalesce(sum(c.connect_count) filter (where c.date = cfg.td), 0) as conn_td
  from collections_calling_data_raw c, cfg
  where c.week_start = cfg.wk group by 1
),
rcase as materialized (
  select fd.employee_id as etm,
    max(current_date - a.activation_date::date) filter (where ls.close_date is null or ls.close_date::date >= current_date) as open_tat,
    bool_or(ls.close_date is null or ls.close_date::date >= current_date) as is_open,
    bool_or(ls.close_date::date between cfg.wk and current_date - 1) as closed_cw
  from recovery_cars a
  left join lateral (select b.datetime as close_date from recovery_status_logs b
                     where b.recovery_id = a.id and b.recovery_status in ('complete','failed','cancelled')
                     order by b.id desc limit 1) ls on true
  join fleet_driver fd on fd.id = a.driver_id cross join cfg
  where a.activation_date < current_date + 1
    and (ls.close_date is null or ls.close_date::date >= cfg.wk)
  group by 1
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
      case when coalesce(minimum_uber_trips_pitch, '') <> '' then 'Minimum Uber Trips Pitch:  ' || minimum_uber_trips_pitch end
    ) as txt
  from public.mv_collections_calling_masterlist
  where coalesce(call_status, '') <> '' and week = date_trunc('week', current_date - 1)::date
  order by partner_et_id, date desc, loaded_at desc
),
l2w as materialized (
  select m.partner_etm as etm,
    count(*) filter (where coalesce(m.collection_pct, 0) <= 0) as n0,
    count(*) filter (where m.collection_pct > 0 and m.collection_pct <= 0.8) as n1
  from analytics.collections_bad_debt_mv m, cfg
  where m.for_collections = 1 and m.hissab_week in (cfg.wk - 7, cfg.wk - 14)
  group by 1
),
slab(city, min_trips, tier, add_trips) as (values
  ('Mumbai',0,'0 - 14',5),('Mumbai',15,'15 - 29',10),('Mumbai',30,'Base Tier',null),
  ('Pune',0,'0 - 14',5),('Pune',15,'15 - 39',10),('Pune',40,'Base Tier',null),
  ('Chennai',0,'0 - 14',5),('Chennai',15,'15 - 39',10),('Chennai',40,'Base Tier',null),
  ('Kolkata',0,'0 - 14',5),('Kolkata',15,'15 - 39',10),('Kolkata',40,'Base Tier',null),
  ('Hyderabad',0,'0 - 14',5),('Hyderabad',15,'15 - 40',10),('Hyderabad',41,'Base Tier',null),
  ('Delhi NCR',0,'0 - 14',5),('Delhi NCR',15,'15 - 34',10),('Delhi NCR',35,'Base Tier',null),
  ('Bangalore',0,'0 - 14',5),('Bangalore',15,'15 - 44',10),('Bangalore',45,'Base Tier',null)
),
base_target(city, target) as (values
  ('Mumbai',40),('Pune',50),('Chennai',50),('Kolkata',65),('Hyderabad',50),('Delhi NCR',45),('Bangalore',55)
),
b0 as materialized (
  select p.etm, cfg.wk, d.driver_id, d.name,
    coalesce(m.lead_id::bigint, ld.lead_id) as lead_id,
    coalesce(m.city, al.city) as city,
    case when coalesce(m.product_type, al.product_type) = 'Leasing' then case when coalesce(m.eip_tag, 0) = 1 then 'EIP' else 'SINGLE' end
         when coalesce(m.product_type, al.product_type) = 'EV_Leasing' then 'EV'
         else coalesce(m.product_type, al.product_type) end as product,
    coalesce(m.tenure_days, current_date - al.first_allocation_date) as tenure,
    (m.etm is not null) as in_list,
    coalesce(m.total_os, 0) as neg_os,
    coalesce(r.rz, 0) as rz, coalesce(r.oth, 0) as oth, coalesce(r.pp, 0) as pp, coalesce(r.adj, 0) as adj, coalesce(r.dpo, 0) as dpo,
    case when coalesce(dp.dep, 0) >= 1 then dp.dep::int else 0 end as dep,
    (ae.etm is not null) as is_active,
    coalesce(h.habit, 'Good') as habit,
    coalesce(lw.os, 0) as lw_os,
    cn.car_numbers, cn.car_model,
    dv.car_count, dv.rented_days, dv.lw_active, dv.lw_nd, dv.cw_active, dv.cw_nd, dv.fare, dv.cash, dv.subs,
    dv.gps, dv.uber_km, dv.dead_km, dv.trips_cw, dv.trips_lw, dv.acc, dv.disp, dv.alloc_yd, dv.gps_yd, dv.trips_yd,
    lv.lo_last, lv.lo_yd, lv.day_rent, lv.rent_cw,
    lp.d as last_paid, j.last_jama_4w, j.last_jama_1w,
    cl.att, cl.conn, cl.last_att, cl.last_conn, cl.last_dispo, cl.att_td, cl.conn_td,
    coalesce(rc.is_open, false) as rc_open, coalesce(rc.closed_cw, false) as rc_closed_cw, rc.open_tat,
    rm.txt as remarks, l.n0, l.n1,
    (nj.etm is not null) as is_newjoin
  from pop p cross join cfg
  left join mvw m on m.etm = p.etm
  left join drv d on d.etm = p.etm
  left join lead ld on ld.driver_id = d.driver_id
  left join alloc_last al on al.etm = p.etm
  left join rec r on r.etm = p.etm
  left join dep dp on dp.etm = p.etm
  left join act_e ae on ae.etm = p.etm
  left join habit h on h.driver_id = d.driver_id
  left join lwos lw on lw.etm = p.etm
  left join cars_now cn on cn.etm = p.etm
  left join drive dv on dv.driver_id = d.driver_id
  left join live lv on lv.driver_id = d.driver_id
  left join lastpaid lp on lp.etm = p.etm
  left join jama j on j.etm = p.etm
  left join calls cl on cl.etm = p.etm
  left join rcase rc on rc.etm = p.etm
  left join remarks rm on rm.etm = p.etm
  left join l2w l on l.etm = p.etm
  left join newjoin nj on nj.etm = p.etm
),
b1 as materialized (
  select b.*,
    b.rz + b.oth + b.pp + b.adj + b.dpo as tot_rec,
    coalesce(b.lo_last, b.neg_os + b.rz + b.oth + b.pp + b.adj + b.dpo) as cur_os,
    coalesce(b.lo_yd, b.lo_last, b.neg_os) as am_os,
    case when b.city = 'Delhi' then 'Delhi NCR' else b.city end as slab_city,
    case when lower(coalesce(b.car_model, '')) ~ 'wagon ?r.*2026' then 20000
         when lower(coalesce(b.car_model, '')) ~ 'wagon ?r|celerio|s-?presso' then 15000
         when lower(coalesce(b.car_model, '')) ~ 'rumion' then 45000 else 30000 end as own_thr
  from b0 b
),
b2 as materialized (
  select b.*,
    b.neg_os + least(b.tot_rec, abs(b.neg_os)) as net_os,
    case when b.neg_os = 0 then 0 else least(b.tot_rec, abs(b.neg_os))::numeric / abs(b.neg_os) end as rec_pct
  from b1 b
),
b3 as materialized (
  select b.*,
    -- MasterTab Risk_Type rule, on live OS now (risk_now) and on yesterday end-of-day OS (risk_am = morning list)
    case when b.product <> 'Own Now' and b.cur_os > 0 then false
         when b.product = 'D2O' then b.dep > 0 and abs(b.cur_os) / b.dep >= 0.7
         when b.product = 'Own Now' then b.net_os <= -b.own_thr
         when b.product in ('SINGLE','EV') then case when coalesce(b.rented_days, 0) = 0 then b.dep > 0 and abs(b.cur_os) / b.dep >= 0.8
                                                     else (b.cur_os + b.dep) <= abs(coalesce(b.rent_cw, 0) / b.rented_days) end
         when b.product in ('Revenue Share','Fixed Pay') then b.dep > 0 and abs(b.cur_os) / b.dep >= 1
         when b.product = 'EIP' then case when coalesce(b.car_count, 0) >= 10 then b.cur_os <= -50000 else b.cur_os <= -25000 end
         else false end as risk_now,
    case when b.product <> 'Own Now' and b.am_os > 0 then false
         when b.product = 'D2O' then b.dep > 0 and abs(b.am_os) / b.dep >= 0.7
         when b.product = 'Own Now' then b.net_os <= -b.own_thr
         when b.product in ('SINGLE','EV') then case when coalesce(b.rented_days, 0) = 0 then b.dep > 0 and abs(b.am_os) / b.dep >= 0.8
                                                     else (b.am_os + b.dep) <= abs(coalesce(b.rent_cw, 0) / b.rented_days) end
         when b.product in ('Revenue Share','Fixed Pay') then b.dep > 0 and abs(b.am_os) / b.dep >= 1
         when b.product = 'EIP' then case when coalesce(b.car_count, 0) >= 10 then b.am_os <= -50000 else b.am_os <= -25000 end
         else false end as risk_am,
    case when b.product in ('SINGLE','Own Now') then 'Base Tier'
         when b.product = 'D2O' then case when b.is_newjoin then 'Base Tier'
              else (select s.tier from slab s where s.city = b.slab_city and s.min_trips <= coalesce(b.trips_lw, 0) order by s.min_trips desc limit 1) end
    end as trip_tier
  from b2 b
),
b4 as materialized (
  select b.*,
    case when b.product in ('SINGLE','Own Now') then (select t.target from base_target t where t.city = b.slab_city)
         when b.product = 'D2O' then case when b.trip_tier = 'Base Tier' then (select t.target from base_target t where t.city = b.slab_city)
              else coalesce(b.trips_lw, 0) + (select s.add_trips from slab s where s.city = b.slab_city and s.tier = b.trip_tier) end
    end as target_trips
  from b3 b
)
,
ph as materialized (select l.id as lead_id, l.phone from crm.lead_lead_view l where coalesce(l.is_deleted, 0) = 0),
cm as materialized (
  select b.*, coalesce(b.fare, 0) as e_a, abs(coalesce(b.subs, 0)) as e_b, coalesce(b.cash, 0) as e_c,
         coalesce(b.fare, 0) - abs(coalesce(b.subs, 0)) - coalesce(b.cash, 0) as uber_tr,
         -coalesce(b.lw_os, 0) as d_a, abs(coalesce(b.rent_cw, 0)) as d_b
  from b4 b
  where b.is_active
)
select
  to_char(current_date, 'DD-Mon-YYYY') as "{{1}} Date",
  coalesce(c.car_numbers, '') as "{{2}} Vehicle No",
  round(c.e_a) as "{{3}} Earnings",
  round(c.e_b) as "{{4}} Subscription Fee",
  round(c.e_c) as "{{5}} Cash Collection",
  round(c.uber_tr) as "{{6}} Uber Transfer (A-B-C)",
  c.dep as "{{7}} Current Deposit",
  coalesce(c.rented_days, 0) as "{{8}} Rent Days",
  round(c.d_a) as "{{9}} Last Week Pending Arrears",
  round(c.d_b) as "{{10}} Rent Amount (Current Week)",
  round(-c.uber_tr) as "{{11}} Uber Transfer",
  round(c.d_a + c.d_b - c.uber_tr) as "{{12}} Pending Arrears (A+B+C)",
  round(c.tot_rec) as "{{13}} Recovered Amount (Current Week)",
  round(c.d_a + c.d_b - c.uber_tr - c.tot_rec) as "{{14}} Overall Due (D-E)",
  c.etm as "partner_et_id",
  c.name as "partner_name",
  p.phone as "phone",
  c.city as "city",
  c.product as "product_type",
  round(-c.cur_os) as "check: live OS due",
  round(c.d_a + c.d_b - c.uber_tr - c.tot_rec + c.cur_os) as "check: diff vs live OS",
  case when round(c.d_a + c.d_b - c.uber_tr - c.tot_rec) > 0 and coalesce(p.phone, '') <> '' then 'Send' else 'Skip' end as "send_flag",
  to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') as "last_updated"
from cm c
left join ph p on p.lead_id = c.lead_id
order by c.city, round(c.d_a + c.d_b - c.uber_tr - c.tot_rec) desc
