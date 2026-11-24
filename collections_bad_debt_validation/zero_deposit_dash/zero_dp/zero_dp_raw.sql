-- =====================================================================================
-- 0_raw (Zero & Low Deposit Monitoring Dashboard): ONLY 0 deposit pilots, pilot x week, last 3 weeks (like raw_v2).
-- Output at A4 (rows 1-3 = section / header / meaning, kept by hand). 75 columns A:BW.
-- 0 deposit pilot = latest join (New Join / Rejoin / Resurrection) on or before the week end had deposit 0
--   at the end of the join day (deposit now - deposits dated after the join day; at least the amount paid on allocation).
--   Join must be in the last 8 weeks. Days before the join are blank.
-- Active       = live OS row that day (hissab_driver_live_os.is_active = 1).
-- Product      = raw_v2 label from collections_bad_debt_mv (Leasing - Single / Leasing - EIP / D2O - EIP / ...), else the join product.
-- Weekly OS    = collections_bad_debt_mv.total_os of that hisaab week (for_collections = 1), owed amount (0 if none).
-- Rent         = rent of a day, booked on the next day's live OS row (Sunday rent goes into the weekly hisaab).
-- Collected    = Razorpay + PhonePe + other payments (mv_daily_recovery); Adjustment + DP to OS shown separately.
-- Bad debt     = Active: owes >= deposit that day (amount = owed - deposit).
--                Left  : no live OS row and no car that day, last live OS owes more than the deposit.
-- Car recovery = recovery_cars; raised on activation date, closed with tag 111/112/113, recovered = close status 'complete'.
-- =====================================================================================
with cfg as (
  select date_trunc('week', current_date)::date as cur_wk,
         date_trunc('week', current_date)::date - 14 as r0,   -- first shown week
         date_trunc('week', current_date)::date - 49 as w0    -- joins looked back 8 weeks
),
jn0 as materialized (   -- join events (ssot read once)
  select distinct on (s.employee_id, s.allocation_date::date)
         s.employee_id as etm, s.allocation_date::date as jd, s.category as jtype, coalesce(s.sd_amount, 0) as sd_amount, s.city,
         case when s.product_type = 'leasing' then case when s.fuel_type ilike 'ev%' then 'EV_Leasing' else 'Leasing' end
              when s.product_type = 'DTO' then case when s.fuel_type ilike 'ev%' then 'EV_D2O' else 'D2O' end
              when s.product_type = 'Rev_share' then 'Revenue Share' else s.product_type end as product
  from analytics.ssot_alloc_dealloc_full s
  where s.category in ('New Join', 'Rejoin', 'Resurrection')
    and s.allocation_date >= (select w0 from cfg) and s.allocation_date <= current_date
  order by s.employee_id, s.allocation_date::date, s.allocation_datetime desc
),
ids as materialized (select distinct etm from jn0),
dep_tot as materialized (   -- index-only scan (filter must match idx_mdr_dep_valid_emp)
  select d.employee_id as etm, sum(d.amount) as dep_now
  from mv_deposits_raw d
  where d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[])
    and d.employee_id in (select etm from ids)
  group by 1
),
dep_day as materialized (
  select d.employee_id as etm, d.date::date as d, sum(d.amount) as amt
  from mv_deposits_raw d
  where d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[])
    and d.employee_id in (select etm from ids) and d.date >= (select w0 from cfg)
  group by 1, 2
),
jn_after as materialized (
  select j.etm, j.jd, sum(x.amt) as amt
  from jn0 j join dep_day x on x.etm = j.etm and x.d > j.jd
  group by 1, 2
),
jn as materialized (
  select j.*,
         greatest(coalesce(t.dep_now, 0) - coalesce(a.amt, 0), j.sd_amount) as dep_at_join,
         lead(j.jd) over (partition by j.etm order by j.jd) as next_jd
  from jn0 j
  left join dep_tot t on t.etm = j.etm
  left join jn_after a on a.etm = j.etm and a.jd = j.jd
),
zj as materialized (   -- 0 deposit joins, valid from the join day to the day before the next join
  select j.etm, j.jd, j.jtype, j.city, j.product, j.dep_at_join,
         least(coalesce(j.next_jd - 1, current_date), current_date) as last_d
  from jn j where j.dep_at_join <= 0 and least(coalesce(j.next_jd - 1, current_date), current_date) >= (select r0 from cfg)
),
grid as materialized (   -- 0 deposit pilot x day, shown weeks only
  select z.etm, z.jd, z.jtype, z.city, z.product, z.dep_at_join, g.dd::date as d, date_trunc('week', g.dd)::date as wk,
         extract(isodow from g.dd)::int as dn
  from zj z cross join lateral generate_series(greatest(z.jd, (select r0 from cfg)), z.last_d, interval '1 day') g(dd)
),
zids as materialized (select distinct etm from zj),
fdr as materialized (select f.id as driver_id, f.employee_id as etm from fleet_driver f where f.employee_id in (select etm from zids)),
lod as materialized (   -- one live OS row per pilot per day
  select distinct on (f.etm, h.date::date) f.etm, h.date::date as d, h.live_os, h.total_rent, h.is_active
  from hissab_driver_live_os h join fdr f on f.driver_id = h.driver_id
  where h.date >= (select w0 from cfg) and h.date <= current_date + 1
  order by f.etm, h.date::date, h.is_active desc, h.driver_id desc
),
mdr as materialized (   -- collections (fixed floor date: TimescaleDB hypertable)
  select r.employee_id as etm, r.date::date as d,
         sum(r.amount) filter (where r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery')) as paid,
         sum(r.amount) filter (where r.recovery_type in ('positive_adjustment','deposit_to_os')) as adj
  from mv_daily_recovery r
  where r.date >= date '2026-09-01' and r.date >= (select r0 from cfg) and r.date <= current_date
    and r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery','positive_adjustment','deposit_to_os')
    and r.employee_id in (select etm from zids)
  group by 1, 2
),
car as materialized (
  select s.employee_id as etm, s.allocation_date::date as a, coalesce(s.jama_date::date, current_date) as b
  from analytics.ssot_alloc_dealloc_full s
  where s.employee_id in (select etm from zids) and coalesce(s.jama_date, current_date) >= (select r0 from cfg)
),
rc0 as materialized (
  select a.id, f.etm, a.activation_date::date as start_d, a.rec_tags_id, a.updated_at
  from recovery_cars a join fdr f on f.driver_id = a.driver_id
  where a.activation_date <= current_date
),
rclose as materialized (
  select distinct on (b.recovery_id) b.recovery_id, b.datetime as close_dt, b.recovery_status
  from recovery_status_logs b
  where b.recovery_status in ('complete','failed','cancelled') and b.recovery_id in (select id from rc0)
  order by b.recovery_id, b.id desc
),
rcase as materialized (
  select a.etm, a.start_d,
         case when a.rec_tags_id in (111, 112, 113) then coalesce(ls.close_dt::date, (a.updated_at at time zone 'Asia/Kolkata')::date) end as close_d,
         case when a.rec_tags_id in (111, 112, 113) and ls.recovery_status = 'complete' then 1 else 0 end as recovered
  from rc0 a left join rclose ls on ls.recovery_id = a.id
),
calls as materialized (
  select c.partner_et_id as etm, c.date::date as d, sum(c.attempt_count) as att, sum(c.connect_count) as conn
  from public.collections_calling_data_raw c
  where c.week_start >= (select r0 from cfg) and c.partner_et_id in (select etm from zids)
  group by 1, 2
),
wos as materialized (   -- weekly OS of the hisaab week (dashboard MV)
  select distinct on (m.hissab_week, m.partner_etm) m.hissab_week as wk, m.partner_etm as etm, m.total_os,
         case when m.product_type = 'EIP' then m.revenue_type || ' - EIP'   -- 24-Nov: same Product label as raw_v2
              when m.revenue_type = 'Leasing' then 'Leasing - Single'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV_Leasing'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.revenue_type end as product_lbl
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1 and m.hissab_week >= (select r0 from cfg) and m.partner_etm in (select etm from zids)
  order by m.hissab_week, m.partner_etm, m.id desc
),
drv as materialized (
  select distinct on (f.employee_id) f.employee_id as etm, f.name
  from fleet_driver f where f.employee_id in (select etm from zids)
  order by f.employee_id, f.id desc
),
g_after as materialized (
  select g.etm, g.d, sum(x.amt) as amt
  from grid g join dep_day x on x.etm = g.etm and x.d > g.d
  group by 1, 2
),
g_lastlo as materialized (
  select g.etm, g.d, (array_agg(p.live_os order by p.d desc))[1] as last_lo
  from grid g join lod p on p.etm = g.etm and p.d <= g.d and p.is_active = 1
  group by 1, 2
),
g_car as materialized (
  select distinct g.etm, g.d from grid g join car c on c.etm = g.etm and c.a <= g.d and c.b >= g.d
),
g_rc as materialized (
  select g.etm, g.d,
    max(case when r.close_d is null or r.close_d > g.d then 1 else 0 end) as in_rc,
    max(case when r.start_d = g.d then 1 else 0 end) as rc_new,
    max(case when r.close_d = g.d then 1 else 0 end) as rc_closed,
    max(case when r.close_d = g.d and r.recovered = 1 then 1 else 0 end) as rc_rec
  from grid g join rcase r on r.etm = g.etm and r.start_d <= g.d and (r.close_d is null or r.close_d >= g.d)
  group by 1, 2
),
pday as materialized (
  select g.*,
    greatest(coalesce(t.dep_now, 0) - coalesce(ga.amt, 0), 0) as dp,
    l.live_os, case when l.etm is not null then 1 else 0 end as active,
    n.total_rent as rent_d, ll.last_lo,
    case when gc.etm is not null or l.etm is not null then 1 else 0 end as has_car,
    coalesce(m.paid, 0) as paid, coalesce(m.adj, 0) as adj, coalesce(cl.att, 0) as att, coalesce(cl.conn, 0) as conn,
    coalesce(r.in_rc, 0) as in_rc, coalesce(r.rc_new, 0) as rc_new, coalesce(r.rc_closed, 0) as rc_closed, coalesce(r.rc_rec, 0) as rc_rec
  from grid g
  left join dep_tot t on t.etm = g.etm
  left join g_after ga on ga.etm = g.etm and ga.d = g.d
  left join lod l on l.etm = g.etm and l.d = g.d and l.is_active = 1
  left join lod n on n.etm = g.etm and n.d = g.d + 1
  left join g_lastlo ll on ll.etm = g.etm and ll.d = g.d
  left join g_car gc on gc.etm = g.etm and gc.d = g.d
  left join mdr m on m.etm = g.etm and m.d = g.d
  left join calls cl on cl.etm = g.etm and cl.d = g.d
  left join g_rc r on r.etm = g.etm and r.d = g.d
),
pday2 as materialized (
  select p.*,
    case when p.active = 1 and p.live_os < 0 and -p.live_os >= p.dp then 'Active'
         when p.active = 0 and p.has_car = 0 and coalesce(p.last_lo, 0) + p.dp < 0 then 'Left' end as bd_type,
    case when p.active = 1 and p.live_os < 0 and -p.live_os >= p.dp then -p.live_os - p.dp
         when p.active = 0 and p.has_car = 0 and coalesce(p.last_lo, 0) + p.dp < 0 then -(p.last_lo + p.dp) else 0 end as bd_amt
  from pday p
),
pw as materialized (   -- pilot x week (latest 0 deposit join of the week)
  select p.wk, p.etm,
    (array_agg(p.jd order by p.jd desc))[1] as jd,
    (array_agg(p.jtype order by p.jd desc))[1] as jtype,
    (array_agg(p.city order by p.jd desc))[1] as city,
    (array_agg(p.product order by p.jd desc))[1] as product,
    max(p.d) as last_d,
    sum(coalesce(p.rent_d, 0)) as rent_w, sum(p.paid) as paid_w, sum(p.adj) as adj_w,
    sum(p.rc_new) as rc_new_w, sum(p.rc_closed) as rc_closed_w, sum(p.rc_rec) as rc_rec_w,
    sum(p.att) as att_w, sum(p.conn) as conn_w, sum(p.active) as act_days,
    array[max(p.active) filter (where p.dn = 1), max(p.active) filter (where p.dn = 2), max(p.active) filter (where p.dn = 3), max(p.active) filter (where p.dn = 4),
          max(p.active) filter (where p.dn = 5), max(p.active) filter (where p.dn = 6), max(p.active) filter (where p.dn = 7)] as a_act,
    array[max(p.live_os) filter (where p.dn = 1), max(p.live_os) filter (where p.dn = 2), max(p.live_os) filter (where p.dn = 3), max(p.live_os) filter (where p.dn = 4),
          max(p.live_os) filter (where p.dn = 5), max(p.live_os) filter (where p.dn = 6), max(p.live_os) filter (where p.dn = 7)] as a_lo,
    array[max(p.rent_d) filter (where p.dn = 1), max(p.rent_d) filter (where p.dn = 2), max(p.rent_d) filter (where p.dn = 3), max(p.rent_d) filter (where p.dn = 4),
          max(p.rent_d) filter (where p.dn = 5), max(p.rent_d) filter (where p.dn = 6), max(p.rent_d) filter (where p.dn = 7)] as a_rent,
    array[max(p.paid) filter (where p.dn = 1), max(p.paid) filter (where p.dn = 2), max(p.paid) filter (where p.dn = 3), max(p.paid) filter (where p.dn = 4),
          max(p.paid) filter (where p.dn = 5), max(p.paid) filter (where p.dn = 6), max(p.paid) filter (where p.dn = 7)] as a_paid,
    array[max(p.bd_amt) filter (where p.dn = 1), max(p.bd_amt) filter (where p.dn = 2), max(p.bd_amt) filter (where p.dn = 3), max(p.bd_amt) filter (where p.dn = 4),
          max(p.bd_amt) filter (where p.dn = 5), max(p.bd_amt) filter (where p.dn = 6), max(p.bd_amt) filter (where p.dn = 7)] as a_bd,
    array[max(p.in_rc) filter (where p.dn = 1), max(p.in_rc) filter (where p.dn = 2), max(p.in_rc) filter (where p.dn = 3), max(p.in_rc) filter (where p.dn = 4),
          max(p.in_rc) filter (where p.dn = 5), max(p.in_rc) filter (where p.dn = 6), max(p.in_rc) filter (where p.dn = 7)] as a_rc
  from pday2 p
  group by 1, 2
),
pwe as materialized (   -- week end (last shown day of the week) values
  select w.*, e.dp as dep_we, e.live_os as lo_we, e.active as act_we, e.has_car as car_we, e.bd_amt as bd_we, e.bd_type as bdt_we, e.in_rc as rc_we,
         abs(least(coalesce(o.total_os, 0), 0)) as wos, o.product_lbl as mv_product
  from pw w
  join pday2 e on e.etm = w.etm and e.d = w.last_d
  left join wos o on o.wk = w.wk and o.etm = w.etm
)
select
  w.wk                                                    as "Week (Mon)",
  to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') as "Data Refreshed At",
  w.etm                                                   as "Employee ID",
  dr.name                                                 as "Pilot Name",
  w.city                                                  as "City",
  coalesce(w.mv_product, case when w.product = 'Leasing' then 'Leasing - Single' else w.product end) as "Product",
  w.jd                                                    as "Join Date",
  w.jtype                                                 as "Join Type",
  date_trunc('week', w.jd)::date                          as "Join Week",
  case when date_trunc('week', w.jd)::date = w.wk then 'Yes' else 'No' end as "Joined This Week",
  w.last_d - w.jd                                         as "Days Since Join",
  0                                                       as "Deposit at Join (Rs)",
  round(w.dep_we)                                         as "Deposit at Week End (Rs)",
  round(greatest(coalesce(t.dep_now, 0), 0))              as "Deposit Now (Rs)",
  case when coalesce(t.dep_now, 0) <= 0 then '0 Deposit' when t.dep_now <= 3000 then '1-3K' when t.dep_now <= 5000 then '3-5K' else '5K+' end as "Deposit Bucket Now",
  round(w.wos)                                            as "Weekly OS (hisaab) (Rs)",
  round(w.rent_w)                                         as "Rent This Week (Rs)",
  round(w.wos + w.rent_w)                                 as "Total OS to Collect (Rs)",
  round(w.paid_w)                                         as "Collected This Week (Rs)",
  round(w.adj_w)                                          as "Adjustment + DP to OS (Rs)",
  case when w.wos + w.rent_w > 0 then round(w.paid_w / (w.wos + w.rent_w), 4) end as "Collection %",
  round(w.lo_we)                                          as "Live OS at Week End (Rs)",
  w.act_we                                                as "Active at Week End",
  w.car_we                                                as "Has Car at Week End",
  round(w.bd_we)                                          as "Bad Debt at Week End (Rs)",
  coalesce(w.bdt_we, '-')                                 as "Bad Debt Type at Week End",
  w.rc_we                                                 as "In Car Recovery at Week End",
  w.rc_new_w                                              as "Recovery Raised (week)",
  w.rc_closed_w                                           as "Recovery Closed (week)",
  w.rc_rec_w                                              as "Car Recovered (week)",
  w.att_w                                                 as "Calls Attempted (week)",
  w.conn_w                                                as "Calls Connected (week)",
  w.act_days                                              as "Active Days (week)",
  w.a_act[1] as "Active D1", w.a_act[2] as "Active D2", w.a_act[3] as "Active D3", w.a_act[4] as "Active D4",
  w.a_act[5] as "Active D5", w.a_act[6] as "Active D6", w.a_act[7] as "Active D7",
  round(w.a_lo[1]) as "Live OS D1", round(w.a_lo[2]) as "Live OS D2", round(w.a_lo[3]) as "Live OS D3", round(w.a_lo[4]) as "Live OS D4",
  round(w.a_lo[5]) as "Live OS D5", round(w.a_lo[6]) as "Live OS D6", round(w.a_lo[7]) as "Live OS D7",
  round(w.a_rent[1]) as "Rent D1", round(w.a_rent[2]) as "Rent D2", round(w.a_rent[3]) as "Rent D3", round(w.a_rent[4]) as "Rent D4",
  round(w.a_rent[5]) as "Rent D5", round(w.a_rent[6]) as "Rent D6", round(w.a_rent[7]) as "Rent D7",
  round(w.a_paid[1]) as "Collected D1", round(w.a_paid[2]) as "Collected D2", round(w.a_paid[3]) as "Collected D3", round(w.a_paid[4]) as "Collected D4",
  round(w.a_paid[5]) as "Collected D5", round(w.a_paid[6]) as "Collected D6", round(w.a_paid[7]) as "Collected D7",
  round(w.a_bd[1]) as "Bad Debt D1", round(w.a_bd[2]) as "Bad Debt D2", round(w.a_bd[3]) as "Bad Debt D3", round(w.a_bd[4]) as "Bad Debt D4",
  round(w.a_bd[5]) as "Bad Debt D5", round(w.a_bd[6]) as "Bad Debt D6", round(w.a_bd[7]) as "Bad Debt D7",
  w.a_rc[1] as "In Car Recovery D1", w.a_rc[2] as "In Car Recovery D2", w.a_rc[3] as "In Car Recovery D3", w.a_rc[4] as "In Car Recovery D4",
  w.a_rc[5] as "In Car Recovery D5", w.a_rc[6] as "In Car Recovery D6", w.a_rc[7] as "In Car Recovery D7"
from pwe w
left join drv dr on dr.etm = w.etm
left join dep_tot t on t.etm = w.etm
order by w.wk, w.city, w.jd desc, w.etm
