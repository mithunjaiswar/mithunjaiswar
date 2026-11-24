-- =====================================================================================
-- 0dp_raw v2 (Zero & Low Deposit Monitoring Dashboard), 24-Nov. Pilot x week, last 3 weeks. Output at A4 (rows 1-3 by hand).
-- 0 DP pilot = CURRENT deposit 0: deposit balance (mv_deposits_raw, excl. OWNNOW_TO_OWNNOW / SD_TO_OWNNOW) at the end of a day
--   the pilot had a car is 0 or less. On the day the pilot returns the car, the balance of the day before is used
--   (deposit is moved to OS at exit). In the first 2 days of an allocation the deposit paid on allocation (sd_amount) counts.
-- Rows: every pilot-week where the pilot was 0 DP on a car day, plus EVERY pilot who joined that week (any deposit, for join counts).
-- Joined at 0 deposit = New Join / Rejoin / Resurrection with deposit 0 at the end of the join day.
-- Left (0 DP) = returned the car that day, no car the next day, and was 0 DP. OS left = OS owed on the last live OS row.
-- Active = live OS row that day (hissab_driver_live_os.is_active = 1). Live OS owed = -live OS when below 0.
-- After the last car day the pilot keeps the 0 DP status of that day (payments / car recovery after leaving still count).
-- Collected = Razorpay + PhonePe + other payments (mv_daily_recovery).
-- Net OS = total_os + total_collected_100_pct of the hisaab that covers the week (hisaab week = week + 7); current week = -live OS owed today.
-- Car recovery = recovery_cars: raised on activation date, closed with tag 111/112/113, car recovered = close status 'complete'.
--   Amount recovered = payments made while the pilot was in car recovery (raised .. closed).
-- =====================================================================================
with cfg as (
  select date_trunc('week', current_date)::date - 14 as r0, current_date as t0
),
car0 as materialized (
  select s.employee_id as etm, s.allocation_date::date as a, s.jama_date::date as b, s.city, s.category,
         coalesce(s.sd_amount, 0) as sd_amount, s.allocation_datetime,
         case when s.product_type = 'leasing' then case when s.fuel_type ilike 'ev%' then 'EV_Leasing' else 'Leasing - Single' end
              when s.product_type = 'DTO' then case when s.fuel_type ilike 'ev%' then 'EV_D2O' else 'D2O' end
              when s.product_type = 'Rev_share' then 'Revenue Share' else s.product_type end as product
  from analytics.ssot_alloc_dealloc_full s
  where s.allocation_date::date <= (select t0 from cfg)
    and coalesce(s.jama_date::date, date '9999-12-31') >= (select r0 from cfg)
),
cday as materialized (   -- pilot x day with a car (one row per day); active allocations carry a future jama_date
  select distinct on (c.etm, g.dd::date) c.etm, g.dd::date as d, c.a, c.sd_amount,
         (c.b = g.dd::date) as jama_d
  from car0 c
  cross join lateral generate_series(greatest(c.a, (select r0 from cfg)),
                                     least(coalesce(c.b, (select t0 from cfg)), (select t0 from cfg)), interval '1 day') g(dd)
  order by c.etm, g.dd::date, (c.b = g.dd::date) asc, c.a desc
),
cids as materialized (select distinct etm from car0),
dd as materialized (
  select d.employee_id as etm, d.date::date as d, sum(d.amount) as amt
  from mv_deposits_raw d
  where d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[]) and d.employee_id in (select etm from cids)
  group by 1, 2
),
base as materialized (select etm, sum(amt) as b0 from dd where d < (select r0 from cfg) group by 1),   -- balance before the window
cw as materialized (   -- running balance change inside the window, valid from d to nd - 1
  select etm, d, coalesce(lead(d) over (partition by etm order by d), date '9999-12-31') as nd,
         sum(amt) over (partition by etm order by d) as run
  from dd where d >= (select r0 from cfg)
),
cbal as materialized (
  select c.*, coalesce(b.b0, 0) + coalesce(w1.run, 0) as bal_d, coalesce(b.b0, 0) + coalesce(w0.run, 0) as bal_prev,
         (c.jama_d and coalesce(lead(c.d) over (partition by c.etm order by c.d), date '9999-12-31') <> c.d + 1) as left_d
  from cday c
  left join base b on b.etm = c.etm
  left join cw w1 on w1.etm = c.etm and w1.d <= c.d and w1.nd > c.d
  left join cw w0 on w0.etm = c.etm and w0.d <= c.d - 1 and w0.nd > c.d - 1
),
zday as materialized (
  select c.*,
         greatest(case when c.left_d then c.bal_prev else c.bal_d end,
                  case when c.d - c.a <= 1 then c.sd_amount else 0 end) as dp
  from cbal c
),
jn as materialized (   -- joins in the shown weeks (any deposit)
  select distinct on (c.etm, c.a) c.etm, c.a as jd, c.category as jtype,
         greatest(coalesce(z.bal_d, 0), c.sd_amount) as dep_at_join
  from car0 c left join zday z on z.etm = c.etm and z.d = c.a
  where c.category in ('New Join', 'Rejoin', 'Resurrection') and c.a >= (select r0 from cfg)
  order by c.etm, c.a, c.allocation_datetime desc
),
pwk as materialized (   -- pilot-weeks to show
  select distinct etm, date_trunc('week', d)::date as wk from zday where dp <= 0
  union
  select etm, date_trunc('week', jd)::date from jn
),
zids as materialized (select distinct etm from pwk),
zz as materialized (select distinct etm from zday where dp <= 0),   -- 0 DP pilots (heavy joins only for them)
grid as materialized (   -- every day of the shown weeks (till today) for the shown pilots
  select p.etm, p.wk, g.dd::date as d, extract(isodow from g.dd)::int as dn
  from pwk p cross join lateral generate_series(p.wk, least(p.wk + 6, (select t0 from cfg)), interval '1 day') g(dd)
),
fdr as materialized (select f.id as driver_id, f.employee_id as etm from fleet_driver f where f.employee_id in (select etm from zz)),
lod as materialized (
  select distinct on (f.etm, h.date::date) f.etm, h.date::date as d, h.live_os, h.is_active
  from hissab_driver_live_os h join fdr f on f.driver_id = h.driver_id
  where h.date >= (select r0 from cfg) - 14 and h.date <= (select t0 from cfg) and h.is_active = 1
  order by f.etm, h.date::date, h.driver_id desc
),
mdr as materialized (
  select r.employee_id as etm, r.date::date as d, sum(r.amount) as paid
  from mv_daily_recovery r
  where r.date >= date '2026-09-01' and r.date >= (select r0 from cfg) and r.date <= (select t0 from cfg)
    and r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery')
    and r.employee_id in (select etm from zz)
  group by 1, 2
),
rc0 as materialized (
  select a.id, f.etm, a.activation_date::date as start_d, a.rec_tags_id, a.updated_at
  from recovery_cars a join fdr f on f.driver_id = a.driver_id
  where a.activation_date <= (select t0 from cfg)
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
g_rc as materialized (
  select g.etm, g.d,
    max(case when r.close_d is null or r.close_d >= g.d then 1 else 0 end) as in_rc,
    max(case when r.start_d = g.d then 1 else 0 end) as rc_new,
    max(case when r.close_d = g.d then 1 else 0 end) as rc_closed,
    max(case when r.close_d = g.d and r.recovered = 1 then 1 else 0 end) as rc_car
  from grid g join rcase r on r.etm = g.etm and r.start_d <= g.d and (r.close_d is null or r.close_d >= g.d)
  group by 1, 2
),
g_last as materialized (   -- latest car day on or before each grid day (carries the 0 DP status forward)
  select distinct on (g.etm, g.d) g.etm, g.d, z.d as zd, z.dp, z.left_d
  from grid g join zday z on z.etm = g.etm and z.d <= g.d and z.d >= g.wk - 60
  order by g.etm, g.d, z.d desc
),
g_lastlo as materialized (   -- OS owed on the last active live OS row (for pilots who left that day)
  select g.etm, g.d, (array_agg(p.live_os order by p.d desc))[1] as last_lo
  from grid g join zday z on z.etm = g.etm and z.d = g.d and z.left_d and z.dp <= 0
  join lod p on p.etm = g.etm and p.d <= g.d
  group by 1, 2
),
pday as materialized (
  select g.etm, g.wk, g.d, g.dn,
    case when gl.dp <= 0 then 1 else 0 end as z_last,                                    -- 0 DP status (carried)
    case when gl.zd = g.d and gl.dp <= 0 and not gl.left_d then 1 else 0 end as z_car,  -- 0 DP with car at day end
    case when gl.zd = g.d and gl.dp <= 0 and gl.left_d then 1 else 0 end as z_left,     -- 0 DP pilot left today
    case when gl.zd = g.d then 1 else 0 end as car_d,
    case when j.etm is not null then 1 else 0 end as j_all,
    case when j.dep_at_join <= 0 then 1 else 0 end as j_zero,
    case when gl.zd = g.d and gl.dp <= 0 and gl.left_d then -least(coalesce(ll.last_lo, 0), 0) else 0 end as os_left,
    case when gl.zd = g.d and gl.dp <= 0 and not gl.left_d and l.etm is not null then 1 else 0 end as z_act,
    case when gl.zd = g.d and gl.dp <= 0 and not gl.left_d and l.etm is not null then -least(l.live_os, 0) else 0 end as lo_act,
    case when gl.dp <= 0 then coalesce(m.paid, 0) else 0 end as paid,
    case when gl.dp <= 0 then coalesce(r.rc_new, 0) else 0 end as rc_new,
    case when gl.dp <= 0 then coalesce(r.rc_closed, 0) else 0 end as rc_closed,
    case when gl.dp <= 0 then coalesce(r.rc_car, 0) else 0 end as rc_car,
    case when gl.dp <= 0 and r.in_rc = 1 then coalesce(m.paid, 0) else 0 end as rc_amt
  from grid g
  left join g_last gl on gl.etm = g.etm and gl.d = g.d
  left join jn j on j.etm = g.etm and j.jd = g.d
  left join g_lastlo ll on ll.etm = g.etm and ll.d = g.d
  left join lod l on l.etm = g.etm and l.d = g.d
  left join mdr m on m.etm = g.etm and m.d = g.d
  left join g_rc r on r.etm = g.etm and r.d = g.d
),
pw as materialized (
  select p.etm, p.wk, max(p.d) as last_d,
    max(p.z_last) as z_week, sum(p.z_left) as left_w, sum(p.os_left) as os_left_w,
    sum(p.paid) as paid_w, sum(p.rc_new) as rc_new_w, sum(p.rc_closed) as rc_closed_w, sum(p.rc_car) as rc_car_w, sum(p.rc_amt) as rc_amt_w,
    array_agg(p.z_car order by p.dn) as a_zc, array_agg(p.j_all order by p.dn) as a_ja, array_agg(p.j_zero * p.j_all order by p.dn) as a_jz,
    array_agg(p.z_left order by p.dn) as a_zl, array_agg(p.os_left order by p.dn) as a_ol, array_agg(p.z_act order by p.dn) as a_za,
    array_agg(p.lo_act order by p.dn) as a_lo, array_agg(p.paid order by p.dn) as a_pd, array_agg(p.rc_new order by p.dn) as a_rn,
    array_agg(p.rc_closed order by p.dn) as a_rcl, array_agg(p.rc_amt order by p.dn) as a_ra,
    array_agg(p.dn order by p.dn) as a_dn
  from pday p group by 1, 2
),
pwe as materialized (
  select w.*, e.z_car as zc_we, e.z_act as za_we, e.lo_act as lo_we, e.car_d as car_we
  from pw w join pday e on e.etm = w.etm and e.d = w.last_d
),
wj as materialized (   -- latest join of the week
  select distinct on (j.etm, date_trunc('week', j.jd)::date) j.etm, date_trunc('week', j.jd)::date as wk, j.jd, j.jtype, j.dep_at_join
  from jn j order by j.etm, date_trunc('week', j.jd)::date, j.jd desc
),
wos as materialized (   -- net OS of the hisaab that covers this driven week (hisaab week = driven week + 7)
  select distinct on (m.hissab_week, m.partner_etm) m.hissab_week::date - 7 as wk, m.partner_etm as etm,
         coalesce(m.total_os, 0) + coalesce(m.total_collected_100_pct, 0) as net_os,
         case when m.product_type = 'EIP' then m.revenue_type || ' - EIP'
              when m.revenue_type = 'Leasing' then 'Leasing - Single'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV_Leasing'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.revenue_type end as product_lbl
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1 and m.hissab_week >= (select r0 from cfg) + 7 and m.partner_etm in (select etm from zids)
  order by m.hissab_week, m.partner_etm, m.id desc
),
pinfo as materialized (   -- latest city / product per pilot
  select distinct on (c.etm) c.etm, c.city, c.product from car0 c where c.etm in (select etm from zids)
  order by c.etm, c.a desc, c.allocation_datetime desc
),
drv as materialized (
  select distinct on (f.employee_id) f.employee_id as etm, f.name
  from fleet_driver f where f.employee_id in (select etm from zids) order by f.employee_id, f.id desc
),
dnow as materialized (select etm, sum(amt) as dep_now from dd where etm in (select etm from zids) group by 1)
select
  w.wk                                                     as "Week (Mon)",
  to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') as "Data Refreshed At",
  w.etm                                                    as "Employee ID",
  dr.name                                                  as "Pilot Name",
  pi.city                                                  as "City",
  coalesce(o.product_lbl, pi.product)                      as "Product",
  case when j.etm is not null then 'Yes' else 'No' end     as "Joined This Week",
  j.jd                                                     as "Join Date",
  coalesce(j.jtype, '-')                                   as "Join Type",
  round(j.dep_at_join)                                     as "Deposit at Join (Rs)",
  case when j.dep_at_join <= 0 then 'Yes' else 'No' end    as "Joined at 0 Deposit",
  w.z_week                                                 as "0 DP in Week",
  w.zc_we                                                  as "0 DP with Car at Week End",
  round(greatest(coalesce(dn.dep_now, 0), 0))              as "Deposit Now (Rs)",
  w.za_we                                                  as "0 DP Active at Week End",
  round(w.lo_we)                                           as "OS Owed - 0 DP Active at Week End (Rs)",
  case when w.left_w > 0 and w.car_we = 0 then 1 else 0 end as "0 DP Left This Week",
  round(case when w.car_we = 0 then w.os_left_w else 0 end) as "OS Left - 0 DP Left (Rs)",
  case when w.z_week = 1 then round(coalesce(o.net_os, -w.lo_we)) end as "Net OS (Rs)",   -- current week: no hisaab yet -> live OS owed today
  round(w.paid_w)                                          as "Collected - 0 DP (Rs)",
  w.rc_new_w                                               as "Car Recovery Raised",
  w.rc_closed_w                                            as "Car Recovery Closed",
  w.rc_car_w                                               as "Car Recovered (complete)",
  round(w.rc_amt_w)                                        as "Amount Recovered in Car Recovery (Rs)",
  w.a_zc[1] as "0DP Car D1", w.a_zc[2] as "0DP Car D2", w.a_zc[3] as "0DP Car D3", w.a_zc[4] as "0DP Car D4", w.a_zc[5] as "0DP Car D5", w.a_zc[6] as "0DP Car D6", w.a_zc[7] as "0DP Car D7",
  w.a_ja[1] as "Joined D1", w.a_ja[2] as "Joined D2", w.a_ja[3] as "Joined D3", w.a_ja[4] as "Joined D4", w.a_ja[5] as "Joined D5", w.a_ja[6] as "Joined D6", w.a_ja[7] as "Joined D7",
  w.a_jz[1] as "Joined 0DP D1", w.a_jz[2] as "Joined 0DP D2", w.a_jz[3] as "Joined 0DP D3", w.a_jz[4] as "Joined 0DP D4", w.a_jz[5] as "Joined 0DP D5", w.a_jz[6] as "Joined 0DP D6", w.a_jz[7] as "Joined 0DP D7",
  w.a_zl[1] as "Left D1", w.a_zl[2] as "Left D2", w.a_zl[3] as "Left D3", w.a_zl[4] as "Left D4", w.a_zl[5] as "Left D5", w.a_zl[6] as "Left D6", w.a_zl[7] as "Left D7",
  round(w.a_ol[1]) as "OS Left D1", round(w.a_ol[2]) as "OS Left D2", round(w.a_ol[3]) as "OS Left D3", round(w.a_ol[4]) as "OS Left D4", round(w.a_ol[5]) as "OS Left D5", round(w.a_ol[6]) as "OS Left D6", round(w.a_ol[7]) as "OS Left D7",
  w.a_za[1] as "Active D1", w.a_za[2] as "Active D2", w.a_za[3] as "Active D3", w.a_za[4] as "Active D4", w.a_za[5] as "Active D5", w.a_za[6] as "Active D6", w.a_za[7] as "Active D7",
  round(w.a_lo[1]) as "OS Owed Active D1", round(w.a_lo[2]) as "OS Owed Active D2", round(w.a_lo[3]) as "OS Owed Active D3", round(w.a_lo[4]) as "OS Owed Active D4", round(w.a_lo[5]) as "OS Owed Active D5", round(w.a_lo[6]) as "OS Owed Active D6", round(w.a_lo[7]) as "OS Owed Active D7",
  round(w.a_pd[1]) as "Collected D1", round(w.a_pd[2]) as "Collected D2", round(w.a_pd[3]) as "Collected D3", round(w.a_pd[4]) as "Collected D4", round(w.a_pd[5]) as "Collected D5", round(w.a_pd[6]) as "Collected D6", round(w.a_pd[7]) as "Collected D7",
  w.a_rn[1] as "RC Raised D1", w.a_rn[2] as "RC Raised D2", w.a_rn[3] as "RC Raised D3", w.a_rn[4] as "RC Raised D4", w.a_rn[5] as "RC Raised D5", w.a_rn[6] as "RC Raised D6", w.a_rn[7] as "RC Raised D7",
  w.a_rcl[1] as "RC Closed D1", w.a_rcl[2] as "RC Closed D2", w.a_rcl[3] as "RC Closed D3", w.a_rcl[4] as "RC Closed D4", w.a_rcl[5] as "RC Closed D5", w.a_rcl[6] as "RC Closed D6", w.a_rcl[7] as "RC Closed D7",
  round(w.a_ra[1]) as "RC Amount D1", round(w.a_ra[2]) as "RC Amount D2", round(w.a_ra[3]) as "RC Amount D3", round(w.a_ra[4]) as "RC Amount D4", round(w.a_ra[5]) as "RC Amount D5", round(w.a_ra[6]) as "RC Amount D6", round(w.a_ra[7]) as "RC Amount D7"
from pwe w
left join wj j on j.etm = w.etm and j.wk = w.wk
left join wos o on o.etm = w.etm and o.wk = w.wk
left join pinfo pi on pi.etm = w.etm
left join drv dr on dr.etm = w.etm
left join dnow dn on dn.etm = w.etm
order by w.wk, pi.city, w.etm
