-- =====================================================================================
-- Zero / low deposit: raw_v2 = ONE pilot x week table (raw + Agent_action merged), last week + this week.
-- Column list / meanings: raw_v2/columns.py (162 columns, A:FF). Output: [TEST] raw_v2 sheet, data from A4 (rows 1-3 = section / header / meaning).
-- Built from raw_pilot_week_v7.sql (all raw logic kept; internal window = 3 weeks so the last-week Sunday surpass
-- and the "after last join" flags have history) + the Agent_action CTEs made per week.
-- Agent / Actioning Type come from public.mv_collections_calling_masterlist (the calling sheet snapshot), not sheet formulas.
-- "Now" columns (name, car now, deposit now, last paid, yesterday, today calls, remarks) are the same in both week rows.
-- 18-Nov: Bad Debt Type 2 (left) only on days that already have data (was also set on future days of this week).
-- 18-Nov: + Rent D1..D7 at the end (FG:FM) = rent charged for that day (next day's live OS row; blank until booked).
-- 18-Nov: + Days Not Paid D1..D7 (FN:FT) = days since the last Razorpay / PhonePe / other payment as of that day.
-- 18-Nov: Bad Debt Type 2 (left) = no car that day and last live OS (any earlier day, else weekly OS) owes more than the deposit; counted every day (non-funnel).
-- 19-Nov: Days Not Paid counts from the later of last payment / last join (new joiners were showing 60).
-- 20-Nov: + Deposit for Dash (AA) / Deposit Bucket for Dash (AB): joined this week -> current deposit, else Monday EOD deposit.
-- 20-Nov perf: big tables read once / only for the population (mdr, calls, mcl, pop_drv; dep_tot, lwos, cday, lead filtered).
-- 24-Nov: EIP from collections_bad_debt_mv.product_type (like India Collections), not eip_tag. Product label:
--   Leasing - EIP / D2O - EIP / Own Now - EIP / Leasing - Single; EIP pilots use the EIP risk rule (OS >= 25K).
-- 21-Nov perf: TimescaleDB hypertables (mv_daily_recovery, fleet_dailytrip, car_dead_km, fleet_leasing_total_os) get a fixed floor date
--   so the planner drops old chunks at PLAN time (current_date alone => all ~1000 chunks planned, minutes of index metapage reads).
--   Floor only needs to be <= the oldest date used (cur-56); move it forward once a year to keep planning fast.
-- Guards: fails (division by zero) instead of writing wrong data when mv_daily_recovery is not refreshed
--   (< 100 payments yesterday) or hissab_driver_live_os is mid-sync (< 5000 drivers for today / yesterday).
-- =====================================================================================
with wk as (select generate_series(date_trunc('week', current_date)::date - 14, date_trunc('week', current_date)::date, interval '7 day')::date as wk),
-- ---------- weekly (dashboard) rows ----------
bdm as materialized (   -- 21-Nov perf: collections_bad_debt_mv (313 MB, no week index) read ONCE for mvw + l2w (was 2 full scans)
  select m.id, m.hissab_week, m.partner_etm, m.city, m.product_type, m.revenue_type, m.eip_tag, m.total_os,
         m.last_week_payment_habit, m.tenure_days, m.lead_id, m.collection_pct
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1 and m.hissab_week between date_trunc('week', current_date)::date - 28 and date_trunc('week', current_date)::date
),
mvw as materialized (
  select distinct on (m.hissab_week, m.partner_etm)
         m.hissab_week as wk, m.partner_etm as etm, m.city,
         case when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV_Leasing'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.revenue_type end as product_type,
         coalesce(m.total_os, 0) as weekly_os, m.last_week_payment_habit as habit, m.tenure_days, m.lead_id,
         case when m.product_type = 'EIP' then 'EIP' else 'SINGLE' end as eip_filter   -- 24-Nov: EIP = MV product_type (was eip_tag; D2O / Own Now EIP were missed)
  from bdm m
  where m.hissab_week in (select wk from wk)
  order by m.hissab_week, m.partner_etm, m.id desc
),
-- ---------- daily live OS rows ----------
lod as materialized (
  select h.date as d, date_trunc('week', h.date)::date as wk, h.driver_id,
         coalesce(h.live_os, 0) as live_os, coalesce(h.recovery, 0) as recovery, coalesce(h.total_rent, 0) as rent,
         coalesce(h.weekly_os, 0) as weekly_os_live
  from hissab_driver_live_os h
  where h.date >= (date_trunc('week', current_date)::date - 14) and h.date <= current_date and h.is_active = 1
),
lod_drv as materialized (select distinct driver_id from lod),
fdr as materialized (   -- driver id <-> ETM
  select f.id as driver_id, f.employee_id as etm from fleet_driver f where f.id in (select driver_id from lod_drv)
  union
  select f.id, f.employee_id from fleet_driver f where f.employee_id in (select etm from mvw)
),
lod_e as materialized (select l.*, f.etm from lod l join fdr f on f.driver_id = l.driver_id),
act as materialized (   -- open car allocations now (Agent_action population + Has Car Now)
  select ca.driver_id, ca.car_id, ca.allocation_date
  from car_allocation ca   -- 21-Nov perf: index on deallocation_id IS NULL (~1 s); the car history comes from ss
  where ca.deallocation_id is null and ca.deactivation_date is null and ca.allocation_date::date <= current_date
),
act_e as materialized (select distinct fd.employee_id as etm from act a join fleet_driver fd on fd.id = a.driver_id),
ss_ids as materialized (   -- 21-Nov perf: distinct pilot list for ss; joined by HASH (IN ... OR ... became a non-hashed SubPlan = 10^11 comparisons)
  select etm::text as etm from mvw union select etm::text from act_e union select etm::text from lod_e
),
ss as materialized (   -- 21-Nov perf: analytics.ssot_alloc_dealloc_full (314 MB, no index) read ONCE (was 4 full scans):
  -- every allocation of the dashboard / car / live OS pilots + every join of the last 3 weeks. pop / joins / alloc_last / newjoin come from here.
  select s.employee_id, s.allocation_date, s.allocation_datetime, s.category, s.sd_amount, s.city, s.product_type, s.fuel_type, s.first_allocation_date,
         case when s.car_id ~ '^[0-9]+$' then s.car_id::bigint end as car_id, s.jama_date   -- 21-Nov: car history for car_pop / cday / jama
  from analytics.ssot_alloc_dealloc_full s
  left join ss_ids i on i.etm = s.employee_id
  where s.allocation_date <= date_trunc('week', current_date)::date + 6
    and (i.etm is not null
         or (s.category in ('New Join', 'Rejoin', 'Resurrection') and s.allocation_date >= date_trunc('week', current_date)::date - 14))
),
pop as materialized (
  select wk, etm from mvw
  union   -- Agent_action population: every pilot with an open car allocation now (current week)
  select date_trunc('week', current_date)::date, etm from act_e
  union
  select distinct wk, etm from lod_e
  union   -- 17-Nov: pilots who joined this week but have no live OS row yet (else Daily_Trend 'New joins' showed 76 of 367)
  select distinct date_trunc('week', s.allocation_date)::date, s.employee_id
  from ss s
  where s.category in ('New Join', 'Rejoin', 'Resurrection')
    and s.allocation_date >= (date_trunc('week', current_date)::date - 14) and s.allocation_date <= current_date
),
-- ---------- attributes for pilots that are only in live OS (not in the dashboard rows that week) ----------
pop_drv as materialized (   -- 20-Nov perf: every fleet_driver id of the population (to read big tables only for these pilots)
  select f.id as driver_id, f.employee_id as etm from fleet_driver f where f.employee_id in (select distinct etm from pop)
),
mdr as materialized (   -- 20-Nov perf: mv_daily_recovery read ONCE (8 weeks, 5 types); rec_day / recw / lastpaid / pay_day come from here
  select r.employee_id, r.date, r.recovery_type, r.amount
  from mv_daily_recovery r
  where r.date >= date '2026-09-01' and r.date >= date_trunc('week', current_date)::date - 56
    and r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery','positive_adjustment','deposit_to_os')
),
calls as materialized (   -- 20-Nov perf: collections_calling_data_raw read ONCE (3 weeks); call_day / callw come from here
  select c.partner_et_id, c.date, c.week_start, c.attempt_count, c.connect_count, c.last_attempt_time, c.last_connect_time, c.last_subdisposition
  from public.collections_calling_data_raw c
  where c.week_start >= date_trunc('week', current_date)::date - 14
    and (c.city is distinct from 'Mumbai' or c.campaign_id = '277')   -- 24-Nov: Mumbai = only Outbound_Hawkeye_Driver_Manager_Mumbai (crm.lead_campaign 277)
),
mcl as materialized (   -- 20-Nov perf: calling masterlist read ONCE (4 weeks); cml / remarks come from here
  select m.week, m.partner_et_id, m.date, m.snapshot_date, m.loaded_at, m.agent_username, m.actioning_type,
         m.remarks, m.follow_up_date, m.call_status, m.collections_disposition, m.nd_disposition, m.critical_risk_disposition,
         m.driver_confirmation, m.minimum_uber_trips_pitch
  from public.mv_collections_calling_masterlist m
  where m.week >= date_trunc('week', current_date)::date - 28
),
mv_last as materialized (   -- latest dashboard row of the pilot in the 4 weeks
  select distinct on (etm) etm, city, product_type, habit, tenure_days, eip_filter from mvw order by etm, wk desc
),
joins as materialized (   -- join events (New Join / Rejoin / Resurrection) with deposit at allocation
  select s.employee_id as etm, s.allocation_date, s.category, coalesce(s.sd_amount, 0) as sd_amount, s.city,
         s.product_type, s.first_allocation_date
  from ss s
  where s.category in ('New Join', 'Rejoin', 'Resurrection') and s.employee_id in (select etm from pop)
),
alloc_last as materialized (   -- latest allocation of any kind (city / product fallback)
  select distinct on (s.employee_id) s.employee_id as etm, s.city,
         case when s.product_type = 'leasing' then case when s.fuel_type ilike 'ev%' then 'EV_Leasing' else 'Leasing' end
              when s.product_type = 'DTO' then case when s.fuel_type ilike 'ev%' then 'EV_D2O' else 'D2O' end
              when s.product_type = 'Rev_share' then 'Revenue Share' else s.product_type end as product_type,   -- same names as the dashboard
         s.first_allocation_date
  from ss s
  where s.employee_id in (select etm from pop)
  order by s.employee_id, s.allocation_date desc, s.allocation_datetime desc
),
-- ---------- money ----------
dep_tot as materialized (   -- index-only scan (filter must match idx_mdr_dep_valid_emp)
  select d.employee_id as etm, sum(d.amount) as dep_now
  from mv_deposits_raw d
  where d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[])
    and d.employee_id in (select etm from pop)   -- 20-Nov perf: only the population (was every pilot ever, ~15 s)
  group by 1
),
dep_day as materialized (   -- deposits dated inside the 4 weeks (to rebuild the deposit on each day)
  select d.employee_id as etm, d.date as d, sum(d.amount) as amt
  from mv_deposits_raw d
  where d.date >= (date_trunc('week', current_date)::date - 14) and d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[])
  group by 1, 2
),
rec_day as materialized (
  select r.employee_id as etm, r.date as d, sum(r.amount) as amt
  from mdr r
  where r.date >= (date_trunc('week', current_date)::date - 14) and r.date <= current_date
  group by 1, 2
),
call_day as materialized (
  select c.partner_et_id as etm, c.date as d, sum(c.attempt_count) as att, sum(c.connect_count) as conn
  from calls c
  group by 1, 2
),
-- ---------- GPS at week start (Monday) on the cars the pilot held that day ----------
car_pop as materialized (   -- allocations of the population, from ss (ssot read once; was car_allocation)
  select s.employee_id as etm, s.car_id, s.allocation_date, s.jama_date
  from ss s
  where s.car_id is not null and s.employee_id in (select etm from pop)
    and coalesce(s.jama_date, current_date) >= (date_trunc('week', current_date)::date - 14)
),
car_mon as materialized (
  select w.wk, s.etm, s.car_id
  from wk w join car_pop s on s.allocation_date <= w.wk and coalesce(s.jama_date, current_date) >= w.wk
),
gps_mon as materialized (
  select c.wk, c.etm, sum(coalesce(k.gps_km, 0)) as gps_km
  from car_mon c
  left join (select k0.car_id, k0.date, k0.gps_km from car_dead_km k0
             where k0.date >= date '2026-09-01' and k0.date in (date_trunc('week', current_date)::date, date_trunc('week', current_date)::date - 7, date_trunc('week', current_date)::date - 14, date_trunc('week', current_date)::date - 14)) k on k.car_id = c.car_id and k.date = c.wk   -- only the 4 Mondays (date index)
  group by 1, 2
),
-- ---------- car recovery cases (non-funnel: every case, from recovery_cars) ----------
rclose as materialized (   -- latest close log per recovery case
  select distinct on (b.recovery_id) b.recovery_id, b.datetime as close_date
  from recovery_status_logs b where b.recovery_status in ('complete','failed','cancelled')
  order by b.recovery_id, b.id desc
),
rcase as materialized (
  select fd.employee_id as etm, a.activation_date::date as start_date,
         case when a.rec_tags_id in (111, 112, 113) then coalesce(ls.close_date::date, (a.updated_at at time zone 'Asia/Kolkata')::date) end as close_date
  from recovery_cars a
  left join rclose ls on ls.recovery_id = a.id   -- 18-Nov: one pass over the logs instead of a lateral per case (same rows, 22 s -> 2 s)
  join fleet_driver fd on fd.id = a.driver_id
  where a.activation_date < date_trunc('week', current_date)::date + 7
    and fd.employee_id in (select etm from pop)
),
rc_wk as materialized (   -- case open at any time in the week
  select w.wk, r.etm, min(r.start_date) as rc_start, max(r.close_date) as rc_close,
         bool_or(r.close_date is null or r.close_date > least(w.wk + 6, current_date)) as rc_open_eow
  from wk w join rcase r on r.start_date <= w.wk + 6 and (r.close_date is null or r.close_date >= w.wk)
  group by 1, 2
),
-- ---------- one row per pilot per day ----------
grid as materialized (
  select pp.wk, pp.etm, (pp.wk + g.i)::date as d, g.i + 1 as dn
  from pop pp cross join generate_series(0, 6) g(i)
  where pp.wk + g.i <= current_date
),
dep_after as materialized (   -- deposits dated after each day
  select g.wk, g.etm, g.d, sum(x.amt) as amt
  from grid g join dep_day x on x.etm = g.etm and x.d > g.d
  group by 1, 2, 3
),
dep_run as materialized (   -- deposit as of each day = total now - deposits dated after that day
  select g.wk, g.etm, g.d, g.dn, coalesce(t.dep_now, 0) - coalesce(a.amt, 0) as dep_asof
  from grid g
  left join dep_tot t on t.etm = g.etm
  left join dep_after a on a.wk = g.wk and a.etm = g.etm and a.d = g.d
),
day as materialized (
  select g.wk, g.etm, g.dn, g.dep_asof,
         l.live_os, l.recovery, l.rent, l.weekly_os_live,
         coalesce(r.amt, 0) as coll, coalesce(c.att, 0) as att, coalesce(c.conn, 0) as conn
  from dep_run g
  left join lod_e l on l.etm = g.etm and l.d = g.d
  left join rec_day r on r.etm = g.etm and r.d = g.d
  left join call_day c on c.etm = g.etm and c.d = g.d
),
dayw as materialized (   -- weekly OS of the row: dashboard (MV) value, else Monday weekly OS from live OS table
  select d.*, abs(least(coalesce(m.weekly_os, max(d.weekly_os_live) filter (where d.dn = 1) over (partition by d.wk, d.etm), 0), 0)) as wos_abs,
         coalesce(sum(d.coll) over (partition by d.wk, d.etm order by d.dn rows between unbounded preceding and 1 preceding), 0) as coll_before
  from day d left join mvw m on m.wk = d.wk and m.etm = d.etm
),
dayf as materialized (
  select d.*,
         greatest(0, least(d.coll, d.wos_abs - d.coll_before)) as wcoll,   -- part of today's collection that goes to the weekly OS

         case when d.live_os is null then null
              when d.live_os < 0 and -d.live_os >= greatest(d.dep_asof, 0) then 1 else 0 end as surpass
  from dayw d
),
piv as materialized (
  select wk, etm,
    max(live_os) filter (where dn = 1) lo1, max(live_os) filter (where dn = 2) lo2, max(live_os) filter (where dn = 3) lo3,
    max(live_os) filter (where dn = 4) lo4, max(live_os) filter (where dn = 5) lo5, max(live_os) filter (where dn = 6) lo6,
    max(live_os) filter (where dn = 7) lo7,
    max(coll) filter (where dn = 1) c1, max(coll) filter (where dn = 2) c2, max(coll) filter (where dn = 3) c3,
    max(coll) filter (where dn = 4) c4, max(coll) filter (where dn = 5) c5, max(coll) filter (where dn = 6) c6,
    max(coll) filter (where dn = 7) c7,
    max(surpass) filter (where dn = 1) s1, max(surpass) filter (where dn = 2) s2, max(surpass) filter (where dn = 3) s3,
    max(surpass) filter (where dn = 4) s4, max(surpass) filter (where dn = 5) s5, max(surpass) filter (where dn = 6) s6,
    max(surpass) filter (where dn = 7) s7,
    min(dn) filter (where surpass = 1) as first_surpass_dn,
    max(att) filter (where dn = 1) t1, max(att) filter (where dn = 2) t2, max(att) filter (where dn = 3) t3,
    max(att) filter (where dn = 4) t4, max(att) filter (where dn = 5) t5, max(att) filter (where dn = 6) t6,
    max(att) filter (where dn = 7) t7,
    max(conn) filter (where dn = 1) n1, max(conn) filter (where dn = 2) n2, max(conn) filter (where dn = 3) n3,
    max(conn) filter (where dn = 4) n4, max(conn) filter (where dn = 5) n5, max(conn) filter (where dn = 6) n6,
    max(conn) filter (where dn = 7) n7,
    max(wcoll) filter (where dn = 1) w1, max(wcoll) filter (where dn = 2) w2, max(wcoll) filter (where dn = 3) w3,
    max(wcoll) filter (where dn = 4) w4, max(wcoll) filter (where dn = 5) w5, max(wcoll) filter (where dn = 6) w6,
    max(wcoll) filter (where dn = 7) w7,
    sum(wcoll) as wcoll_week, sum(coll) as coll_week, max(wos_abs) as wos_abs,
    max(dep_asof) filter (where dn = 1) as dep_wk_start,
    (array_agg(dep_asof order by dn desc))[1] as dep_wk_last,   -- deposit at the end of the latest day of the week with data
    max(rent) as day_rent
  from dayf group by 1, 2
),
join_wk as materialized (   -- latest join event up to the week end
  select distinct on (pp.wk, pp.etm) pp.wk, pp.etm, x.allocation_date, x.category, x.sd_amount
  from pop pp join joins x on x.etm = pp.etm and x.allocation_date <= pp.wk + 6
  order by pp.wk, pp.etm, x.allocation_date desc
),
dep_join as materialized (   -- 17-Nov: deposit AT ALLOCATION = balance at the end of the allocation day
  -- (deposit already held from before + paid that day), not only the amount paid on the allocation itself.
  -- = deposit now - deposits dated after the allocation day (refunds / forfeits are negative, so they are added back)
  select ja.etm, ja.allocation_date, coalesce(t.dep_now, 0) - coalesce(sum(d.amount), 0) as bal
  from (select distinct etm, allocation_date from join_wk) ja
  left join dep_tot t on t.etm = ja.etm
  left join mv_deposits_raw d on d.employee_id = ja.etm and d.date > ja.allocation_date
       and d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[])
  group by ja.etm, ja.allocation_date, t.dep_now
),
base as materialized (
  select pp.wk, pp.etm,
    case when m.etm is not null then 1 else 0 end as in_dash,
    coalesce(m.city, ml.city, al.city) as city,
    coalesce(m.product_type, ml.product_type, al.product_type) as product_type,
    coalesce(m.eip_filter, ml.eip_filter, 'SINGLE') as eip_filter,
    coalesce(m.habit, ml.habit, 'Unknown') as habit,
    coalesce(m.tenure_days, ml.tenure_days, (pp.wk + 6) - al.first_allocation_date) as tenure_days,
    m.weekly_os,
    j.allocation_date as last_join_date, j.category as last_join_type,
    case when j.etm is not null then greatest(coalesce(dj.bal, 0), coalesce(j.sd_amount, 0)) end as dep_at_alloc
  from pop pp
  left join mvw m on m.wk = pp.wk and m.etm = pp.etm
  left join mv_last ml on ml.etm = pp.etm
  left join alloc_last al on al.etm = pp.etm
  left join join_wk j on j.wk = pp.wk and j.etm = pp.etm
  left join dep_join dj on dj.etm = j.etm and dj.allocation_date = j.allocation_date
),
r0 as materialized (select
  b.wk                                                   as "Week",
  b.city                                                 as "City",
  b.product_type                                         as "Product Type",
  b.etm                                                  as "Employee ID",
  b.eip_filter                                           as "EIP / Single",
  b.in_dash                                              as "In Collections Dash (1/0)",
  b.dep_at_alloc                                         as "Deposit at Allocation",
  case when b.dep_at_alloc is null then 'Unknown' when b.dep_at_alloc <= 0 then '0 Deposit'
       when b.dep_at_alloc <= 3000 then '1-3K' when b.dep_at_alloc <= 5000 then '3-5K'
       else '5K+' end as "SD Bucket (at allocation)",   -- 17-Nov: buckets 0 / 1-3K / 3-5K / 5K+ (dash filter '<=3K' = 0 Deposit + 1-3K)
  coalesce(dt.dep_now, 0)                                as "Current Deposit",
  case when rc.rc_close between b.wk and b.wk + 6 then rc.rc_close end as "Car Recovery Close Date",   -- was Deposit at Week Start (unused); close date in this week
  case when g.etm is null then 'No Car' when g.gps_km > 0 then 'GPS Active' else 'GPS Inactive' end as "Week Start GPS",
  b.weekly_os                                            as "Weekly OS (dash)",
  -pv.wos_abs                                            as "Weekly OS (incl. live-only pilots)",
  pv.coll_week                                           as "Collection Week Total",
  pv.wcoll_week                                          as "Weekly OS Collected (capped, = dash)",
  coalesce(pv.lo7, pv.lo6, pv.lo5, pv.lo4, pv.lo3, pv.lo2, pv.lo1) as "Total OS (latest live)",
  b.habit                                                as "Payment Habit",
  case when b.tenure_days is null then 'Unknown' when b.tenure_days < 30 then 'ELC' else 'Non_ELC' end as "ELC / Non ELC",   -- ELC = tenure < 30 days (same as Calling Masterlist elc_raw; changed 15-Nov on request, earlier was > 30)
  b.tenure_days                                          as "Tenure Days",
  case when b.last_join_date between b.wk and b.wk + 6 then
            case when b.last_join_type = 'New Join' then 'New Join' else 'Rejoin' end
       else 'Existing' end                               as "Join Type (this week)",
  b.last_join_type                                       as "Last Join Type",
  b.last_join_date                                       as "Last Join Date",
  pv.day_rent                                            as "Daily Rent",
  case when pv.first_surpass_dn is not null then b.wk + pv.first_surpass_dn - 1 end as "First Surpass Date",
  case when rc.etm is null then 'No' when rc.rc_open_eow then 'Open' else 'Closed' end as "Car Recovery (week)",
  rc.rc_start                                            as "Car Recovery Start",
  pv.dep_wk_start as dep_mon_eod, pv.dep_wk_last as dep_wk_last,   -- 20-Nov: for Deposit for Dash
  pv.lo1 as "Live OS D1", pv.lo2 as "Live OS D2", pv.lo3 as "Live OS D3", pv.lo4 as "Live OS D4",
  pv.lo5 as "Live OS D5", pv.lo6 as "Live OS D6", pv.lo7 as "Live OS D7",
  pv.c1 as "Collection D1", pv.c2 as "Collection D2", pv.c3 as "Collection D3", pv.c4 as "Collection D4",
  pv.c5 as "Collection D5", pv.c6 as "Collection D6", pv.c7 as "Collection D7",
  pv.w1 as "WOS Collected D1", pv.w2 as "WOS Collected D2", pv.w3 as "WOS Collected D3", pv.w4 as "WOS Collected D4",
  pv.w5 as "WOS Collected D5", pv.w6 as "WOS Collected D6", pv.w7 as "WOS Collected D7",
  pv.s1 as "Surpass D1", pv.s2 as "Surpass D2", pv.s3 as "Surpass D3", pv.s4 as "Surpass D4",
  pv.s5 as "Surpass D5", pv.s6 as "Surpass D6", pv.s7 as "Surpass D7",
  pv.t1 as "Attempts D1", pv.t2 as "Attempts D2", pv.t3 as "Attempts D3", pv.t4 as "Attempts D4",
  pv.t5 as "Attempts D5", pv.t6 as "Attempts D6", pv.t7 as "Attempts D7",
  pv.n1 as "Connects D1", pv.n2 as "Connects D2", pv.n3 as "Connects D3", pv.n4 as "Connects D4",
  pv.n5 as "Connects D5", pv.n6 as "Connects D6", pv.n7 as "Connects D7",
  to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') as "Last Updated"
from base b
left join piv pv on pv.wk = b.wk and pv.etm = b.etm
left join dep_tot dt on dt.etm = b.etm
left join gps_mon g on g.wk = b.wk and g.etm = b.etm
left join rc_wk rc on rc.wk = b.wk and rc.etm = b.etm
),
cfg as materialized (select date_trunc('week', current_date)::date as cur_wk, extract(isodow from current_date)::int as t,
               exists (select 1 from lod where d = current_date) as has_today),
r1 as materialized (
  select r0.*,
    array[r0."Live OS D1",r0."Live OS D2",r0."Live OS D3",r0."Live OS D4",r0."Live OS D5",r0."Live OS D6",r0."Live OS D7"] as alo, array[r0."Collection D1",r0."Collection D2",r0."Collection D3",r0."Collection D4",r0."Collection D5",r0."Collection D6",r0."Collection D7"] as aco, array[r0."Surpass D1",r0."Surpass D2",r0."Surpass D3",r0."Surpass D4",r0."Surpass D5",r0."Surpass D6",r0."Surpass D7"] as asu, array[r0."Attempts D1",r0."Attempts D2",r0."Attempts D3",r0."Attempts D4",r0."Attempts D5",r0."Attempts D6",r0."Attempts D7"] as aat, array[r0."Connects D1",r0."Connects D2",r0."Connects D3",r0."Connects D4",r0."Connects D5",r0."Connects D6",r0."Connects D7"] as acn,
    case when r0."EIP / Single" = 'EIP' then 'EIP'   -- 24-Nov: every EIP pilot (also on D2O / Own Now cars) uses the EIP risk rule
         when r0."Product Type" = 'Leasing' then 'SINGLE'
         when left(r0."Product Type", 3) = 'EV_' then 'EV' else r0."Product Type" end as pk,
    greatest(coalesce(r0."Current Deposit", 0), 0) as dp,
    coalesce(r0."Daily Rent", 0) as rr,
    case when r0."Week" = (select cur_wk from cfg) then (select case when has_today then t else greatest(1, t - 1) end from cfg) else 7 end as co
  from r0
),
r2 as materialized (
  select r1.*, x.mam, x.meod, x.ea, x.eb
  from r1
  cross join lateral (
    select array_agg(am order by i) as mam, array_agg(eod order by i) as meod,
           coalesce(min(i) filter (where lo is not null), 0) as ea,
           (array_agg(lo order by i desc) filter (where lo is not null))[1] as eb
    from (
      select i, lo,
        case when lo is null then null else
          (case when pk = 'Own Now' then oa >= 30000 when oa <= 0 then false
                when pk = 'D2O' then dp > 0 and oa >= 0.7 * dp
                when pk in ('SINGLE','EV') then (dp - oa) <= rr
                when pk in ('Revenue Share','Fixed Pay') then dp > 0 and oa >= dp
                when pk = 'EIP' then oa >= 25000 else false end
           or (oa > 0 and oa >= dp) or s = 1)::int end as am,
        case when lo is null then null else
          (case when pk = 'Own Now' then oe >= 30000 when oe <= 0 then false
                when pk = 'D2O' then dp > 0 and oe >= 0.7 * dp
                when pk in ('SINGLE','EV') then (dp - oe) <= rr
                when pk in ('Revenue Share','Fixed Pay') then dp > 0 and oe >= dp
                when pk = 'EIP' then oe >= 25000 else false end
           or s = 1)::int end as eod
      from (select g.i, r1.alo[g.i] as lo, -(r1.alo[g.i] - coalesce(r1.aco[g.i], 0)) as oa, -r1.alo[g.i] as oe,
                   coalesce(r1.asu[g.i], 0) as s
            from generate_series(1, 7) g(i)) d0
    ) d1
  ) x
),
r3 as materialized (
  select r2.*,
    case when alo[co] is not null then 1 else 0 end as cp,
    greatest(0, -coalesce(alo[co], 0)) as cq,
    coalesce(asu[co], 0) as cr,
    coalesce(mam[co], 0) as cs,
    coalesce(meod[co], 0) as ct,
    case when eb is not null then greatest(-eb - dp, 0) else 0 end as ec,
    greatest(0, case when coalesce("Weekly OS (dash)", 0) < 0 then -"Weekly OS (dash)" else 0 end - coalesce("Weekly OS Collected (capped, = dash)", 0)) as ee,
    case when "Last Join Date" is not null then date_trunc('week', "Last Join Date")::date end as da
  from r2
),
r4 as materialized (
  select r3.*,
    bool_or(cr_any = 1 and "Week" >= coalesce(da, date '1900-01-01')) over (partition by "Employee ID") as dv,
    bool_or("Car Recovery (week)" in ('Open','Closed') and "Week" >= coalesce(da, date '1900-01-01')) over (partition by "Employee ID") as dw,
    bool_or("Car Recovery (week)" = 'Closed' and "Week" >= coalesce(da, date '1900-01-01')) over (partition by "Employee ID") as dx,
    1 as dummy
  from (select r3.*, (select max(v) from unnest(asu) v) as cr_any from r3) r3
),
prevs7 as materialized (select "Week" + 7 as wk, "Employee ID" as etm from r0 where r0."Surpass D7" = 1),
-- =================== Agent_action fields, per week (18-Nov unified raw_v2) ===================
cw as materialized (select date_trunc('week', current_date)::date as wk, current_date - 1 as yd),
drv as materialized (   -- name (latest driver id of the ETM)
  select distinct on (fd.employee_id) fd.employee_id as etm, fd.id as driver_id, fd.name
  from fleet_driver fd where fd.employee_id in (select etm from pop)
  order by fd.employee_id, fd.id desc
),
lead as materialized (
  select distinct on (l.hawkeye_driver_id) l.hawkeye_driver_id as driver_id, l.lead_id
  from crm.lead_driver l where coalesce(l.is_deleted, 0) = 0 and l.hawkeye_driver_id in (select driver_id from drv)
  order by l.hawkeye_driver_id, l.id desc
),
lead_mv as materialized (select distinct on (etm) etm, lead_id from mvw where lead_id is not null order by etm, wk desc),
gnow as materialized (   -- 24-Nov: car in garage now = latest job card (last 30 days) of the current car, not handed over
  select g.car_id, 'Yes - ' || coalesce(st.status, 'In Garage') || ' (since ' || to_char(g.activation_date, 'DD-Mon') || ')' as lbl
  from (select distinct on (j.car_id) j.car_id, j.status_id, j.activation_date, j.deactivation_date
        from garage_jobcard j
        where j.activation_date >= current_date - 30 and j.car_id in (select car_id from act)
        order by j.car_id, j.activation_date desc) g
  left join garage_garage_status st on st.id = g.status_id
  where g.status_id is distinct from 23 and g.deactivation_date is null   -- 23 = Handover Done (jc_handovertime is filled even while In Repair)
),
cars_now as materialized (
  select fd.employee_id as etm, string_agg(distinct fc.car_number, ', ') as car_numbers,
         (array_agg(cm.name order by a.allocation_date desc))[1] as car_model,
         max(gn.lbl) as garage
  from act a join fleet_driver fd on fd.id = a.driver_id
  join fleet_car fc on fc.id = a.car_id left join fleet_car_model cm on cm.id = fc.model_id
  left join gnow gn on gn.car_id = a.car_id
  group by 1
),
cday as materialized (   -- one row per allocated car per day, 2 weeks ago Monday .. yesterday; 21-Nov: from car_pop (ssot) instead of car_allocation
  select d.dd::date as d, date_trunc('week', d.dd)::date as wk, c.car_id, c.etm
  from car_pop c
  cross join lateral generate_series(greatest(c.allocation_date, date_trunc('week', current_date)::date - 14),
                                     least(coalesce(c.jama_date, current_date), current_date - 1), interval '1 day') d(dd)
  where c.allocation_date <= current_date - 1
),
trip as materialized (
  select t.car_id, t.date as d, sum(t.trips) as trips, sum(t.dispatch_trips) as disp, sum(t.accepted_trips) as acc,
         sum(t.fare_total) as fare, sum(t.tip_amount) as tip, sum(t.cash_collected) as cash, sum(t.subscription_charges) as subs
  from fleet_dailytrip t
  where t.date >= date '2026-09-01' and t.date between date_trunc('week', current_date)::date - 14 and (current_date - 1) and t.trips > 0 and t.car_id is not null
  group by 1, 2
),
ola_yd as materialized (
  select o.car_id, sum(o.trips) as trips from fleet_ola_dailytrip o
  where o.date::date = (current_date - 1) and o.car_id is not null group by 1
),
kms as materialized (
  select k.car_id, k.date as d, sum(k.gps_km) as gps, sum(k.uber_km) as uber, sum(k.dead_km) as dead
  from car_dead_km k where k.date >= date '2026-09-01' and k.date between date_trunc('week', current_date)::date - 7 and (current_date - 1) and coalesce(k.is_deleted, 0) = 0 group by 1, 2
),
drivew as materialized (   -- per pilot per week
  select c.etm, c.wk,
    count(distinct c.car_id) as car_count, count(*) as active_days,
    count(*) filter (where coalesce(t.trips, 0) <= 0) as nd_days,
    coalesce(sum(t.fare + t.tip), 0) as fare, coalesce(sum(t.cash), 0) as cash, coalesce(sum(t.subs), 0) as subs,
    coalesce(sum(k.gps), 0) as gps, coalesce(sum(k.uber), 0) as uber_km, coalesce(sum(k.dead), 0) as dead_km,
    coalesce(sum(t.trips), 0) as trips, sum(t.acc) as acc, sum(t.disp) as disp
  from cday c
  left join trip t on t.car_id = c.car_id and t.d = c.d
  left join kms k on k.car_id = c.car_id and k.d = c.d
  group by 1, 2
),
ydd as materialized (   -- yesterday (Now)
  select c.etm, coalesce(sum(k.gps), 0) as gps_yd, coalesce(sum(t.trips), 0) + coalesce(sum(o.trips), 0) as trips_yd
  from cday c
  left join trip t on t.car_id = c.car_id and t.d = c.d
  left join kms k on k.car_id = c.car_id and k.d = c.d
  left join ola_yd o on o.car_id = c.car_id
  where c.d = current_date - 1
  group by 1
),
rent_day as materialized (   -- 18-Nov: rent charged FOR a day = total_rent of the next day's live OS row (booked one day late)
  select etm, d - 1 as d, sum(rent) as amt from lod_e group by 1, 2
),
rent_piv as materialized (
  select g.wk, g.etm,
    max(r.amt) filter (where g.dn = 1) r1, max(r.amt) filter (where g.dn = 2) r2, max(r.amt) filter (where g.dn = 3) r3,
    max(r.amt) filter (where g.dn = 4) r4, max(r.amt) filter (where g.dn = 5) r5, max(r.amt) filter (where g.dn = 6) r6,
    max(r.amt) filter (where g.dn = 7) r7
  from grid g join rent_day r on r.etm = g.etm and r.d = g.d
  where g.wk >= date_trunc('week', current_date)::date - 7
  group by 1, 2
),
rentw as materialized (   -- rent is booked one day late (Monday row = last Sunday's rent) -> week of (date - 1 day)
  select etm, date_trunc('week', d - 1)::date as wk, sum(rent) as rent_w
  from lod_e group by 1, 2
),
recw as materialized (
  select r.employee_id as etm, date_trunc('week', r.date)::date as wk,
    coalesce(sum(r.amount) filter (where r.recovery_type = 'razorpay_recovery'), 0) as rz,
    coalesce(sum(r.amount) filter (where r.recovery_type = 'other_positive_recovery'), 0) as oth,
    coalesce(sum(r.amount) filter (where r.recovery_type = 'phonepe_recovery'), 0) as pp,
    coalesce(sum(r.amount) filter (where r.recovery_type = 'positive_adjustment'), 0) as adj,
    coalesce(sum(r.amount) filter (where r.recovery_type = 'deposit_to_os'), 0) as dpo
  from mdr r
  where r.date >= date_trunc('week', current_date)::date - 7 and r.date <= current_date
  group by 1, 2
),
lastpaid as materialized (
  select r.employee_id as etm, max(r.date) as d from mdr r
  where r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery')
    and r.employee_id is not null group by 1
),
lwos as materialized (   -- previous hisaab week closing OS (ledger) -> row week = ledger week + 7
  select fd.employee_id as etm, (os.week_start_date::date + 7) as wk, sum(os.total_os)::int as os
  from (select driver_id as partner_id, week_start_date, total_os from account_ledger
        where week_start_date >= date_trunc('week', current_date) - interval '14 days' and week_start_date < date_trunc('week', current_date)
          and driver_id in (select driver_id from pop_drv)   -- 20-Nov perf
        union all
        select partner_id, week_start_date, total_os from fleet_leasing_total_os
        where created_at >= timestamptz '2026-09-01' and created_at >= date_trunc('week', current_date) - interval '14 days' and week_start_date >= date_trunc('week', current_date) - interval '14 days' and week_start_date < date_trunc('week', current_date)
          and partner_id in (select driver_id from pop_drv)) os   -- 20-Nov perf
  join fleet_driver fd on fd.id = os.partner_id
  group by 1, 2
),
jama as materialized (   -- last car return (only pilots with no car now); 21-Nov: from ss (ssot) instead of car_allocation
  select s.employee_id as etm,
         max(s.jama_date) as last_jama_4w,
         max(s.jama_date) filter (where s.jama_date >= date_trunc('week', current_date)::date - 7) as last_jama_1w
  from ss s
  where s.jama_date >= date_trunc('week', current_date)::date - 28
    and s.employee_id not in (select etm from act_e where etm is not null)
  group by 1
),
callw as materialized (
  select c.partner_et_id as etm, c.week_start as wk,
    max(c.last_attempt_time) as last_att, max(c.last_connect_time) as last_conn,
    (array_agg(c.last_subdisposition order by c.last_connect_time desc nulls last) filter (where coalesce(c.last_subdisposition, '') <> ''))[1] as last_dispo
  from calls c
  where c.week_start >= date_trunc('week', current_date)::date - 7
  group by 1, 2
),
remarks as materialized (   -- latest remarks of the calling sheet (23:00 snapshot), yesterday's week
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
  from mcl
  where coalesce(call_status, '') <> '' and week = date_trunc('week', current_date - 1)::date
  order by partner_et_id, date desc, loaded_at desc
),
cml as materialized (   -- calling sheet snapshot: agent + actioning type per week (latest snapshot of the week)
  select distinct on (week, partner_et_id) week as wk, partner_et_id as etm,
         nullif(nullif(nullif(trim(agent_username), ''), 'NA'), 'NaN') as agent, nullif(trim(actioning_type), '') as act_type
  from mcl
  order by week, partner_et_id, snapshot_date desc, loaded_at desc
),
agent_wk as materialized (   -- agent of the week, else latest earlier week (like raw!DC), else Unassigned
  select distinct on (pp.wk, pp.etm) pp.wk, pp.etm, c.agent
  from pop pp join cml c on c.etm = pp.etm and c.wk <= pp.wk and c.agent is not null
  order by pp.wk, pp.etm, c.wk desc
),
act_type as materialized (select distinct on (etm) etm, act_type from cml where act_type is not null order by etm, wk desc),
l2w as materialized (
  select w.wk, m.partner_etm as etm,
    count(*) filter (where coalesce(m.collection_pct, 0) <= 0) as n0,
    count(*) filter (where m.collection_pct > 0 and m.collection_pct <= 0.8) as n1
  from wk w join bdm m on m.hissab_week in (w.wk - 7, w.wk - 14)
  group by 1, 2
),
newjoin as materialized (
  select distinct s.employee_id as etm from ss s
  where s.allocation_date >= date '2026-08-17' and s.category in ('New Join', 'Resurrection')
),
rc_now as materialized (   -- open car recovery case now -> pending days
  select etm, max(current_date - start_date) as open_tat from rcase
  where close_date is null or close_date > current_date group by 1
),
slab(city, min_trips, tier) as (values
  ('Mumbai',0,'0 - 14'),('Mumbai',15,'15 - 29'),('Mumbai',30,'Base Tier'),
  ('Pune',0,'0 - 14'),('Pune',15,'15 - 39'),('Pune',40,'Base Tier'),
  ('Chennai',0,'0 - 14'),('Chennai',15,'15 - 39'),('Chennai',40,'Base Tier'),
  ('Kolkata',0,'0 - 14'),('Kolkata',15,'15 - 39'),('Kolkata',40,'Base Tier'),
  ('Hyderabad',0,'0 - 14'),('Hyderabad',15,'15 - 40'),('Hyderabad',41,'Base Tier'),
  ('Delhi NCR',0,'0 - 14'),('Delhi NCR',15,'15 - 34'),('Delhi NCR',35,'Base Tier'),
  ('Bangalore',0,'0 - 14'),('Bangalore',15,'15 - 44'),('Bangalore',45,'Base Tier')
),
car_day as materialized (   -- 18-Nov: days the pilot held a car (car-day rows till yesterday + open allocation today)
  select distinct etm, d from cday
  union
  select etm, current_date from act_e
),
pay_day as materialized (   -- actual payments (Razorpay / PhonePe / other), last 8 weeks
  select r.employee_id as etm, r.date as d from mdr r
  where r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery')
    and r.date <= current_date and r.amount > 0 and r.employee_id is not null
  group by 1, 2
),
nopay0 as materialized (   -- last payment on or before each day (join + group, no per-row lookup)
  select g.wk, g.etm, g.dn, g.d, max(p.d) as lp
  from grid g left join pay_day p on p.etm = g.etm and p.d <= g.d
  where g.wk >= date_trunc('week', current_date)::date - 7
  group by 1, 2, 3, 4
),
joind as materialized (   -- 19-Nov: latest join (New Join / Rejoin / Resurrection) on or before each day
  select g.wk, g.etm, g.dn, max(x.allocation_date) as jd
  from grid g join joins x on x.etm = g.etm and x.allocation_date <= g.d
  where g.wk >= date_trunc('week', current_date)::date - 7
  group by 1, 2, 3
),
nopay as materialized (   -- days since the last payment OR the last join (whichever is later), as of each day.
  -- 0 = paid / joined that day; no payment and no join in 8 weeks = 60. 19-Nov: was counted from the payment only, so new joiners showed 60.
  select a.wk, a.etm,
    max(a.d - greatest(coalesce(a.lp, a.d - 60), coalesce(b.jd, a.d - 60))) filter (where a.dn = 1) dnp1,
    max(a.d - greatest(coalesce(a.lp, a.d - 60), coalesce(b.jd, a.d - 60))) filter (where a.dn = 2) dnp2,
    max(a.d - greatest(coalesce(a.lp, a.d - 60), coalesce(b.jd, a.d - 60))) filter (where a.dn = 3) dnp3,
    max(a.d - greatest(coalesce(a.lp, a.d - 60), coalesce(b.jd, a.d - 60))) filter (where a.dn = 4) dnp4,
    max(a.d - greatest(coalesce(a.lp, a.d - 60), coalesce(b.jd, a.d - 60))) filter (where a.dn = 5) dnp5,
    max(a.d - greatest(coalesce(a.lp, a.d - 60), coalesce(b.jd, a.d - 60))) filter (where a.dn = 6) dnp6,
    max(a.d - greatest(coalesce(a.lp, a.d - 60), coalesce(b.jd, a.d - 60))) filter (where a.dn = 7) dnp7
  from nopay0 a left join joind b on b.wk = a.wk and b.etm = a.etm and b.dn = a.dn
  group by 1, 2
),
car_wk as materialized (   -- car held on day 1..7 of each week (array, for the bad debt type)
  select date_trunc('week', d)::date as wk, etm,
    array[bool_or(extract(isodow from d) = 1), bool_or(extract(isodow from d) = 2), bool_or(extract(isodow from d) = 3), bool_or(extract(isodow from d) = 4),
          bool_or(extract(isodow from d) = 5), bool_or(extract(isodow from d) = 6), bool_or(extract(isodow from d) = 7)] as hc
  from car_day group by 1, 2
),
ll0 as materialized (   -- 18-Nov: last live OS on or before each day (also from earlier weeks) + deposit as of that day
  select g.wk, g.etm, g.dn, (array_agg(l.live_os order by l.d desc))[1] as lo
  from grid g join lod_e l on l.etm = g.etm and l.d <= g.d
  where g.wk >= date_trunc('week', current_date)::date - 7
  group by 1, 2, 3
),
llw as materialized (
  select x.wk, x.etm,
    array[max(x.lo) filter (where x.dn = 1), max(x.lo) filter (where x.dn = 2), max(x.lo) filter (where x.dn = 3), max(x.lo) filter (where x.dn = 4),
          max(x.lo) filter (where x.dn = 5), max(x.lo) filter (where x.dn = 6), max(x.lo) filter (where x.dn = 7)] as llo,
    array[max(x.dep) filter (where x.dn = 1), max(x.dep) filter (where x.dn = 2), max(x.dep) filter (where x.dn = 3), max(x.dep) filter (where x.dn = 4),
          max(x.dep) filter (where x.dn = 5), max(x.dep) filter (where x.dn = 6), max(x.dep) filter (where x.dn = 7)] as ldp
  from (select a.wk, a.etm, a.dn, a.lo, dr.dep_asof as dep
        from ll0 a left join dep_run dr on dr.wk = a.wk and dr.etm = a.etm and dr.dn = a.dn) x
  group by 1, 2
),
bd as materialized (   -- 18-Nov: 1 = active bad debt (live OS that day and owes >= deposit);
  -- 2 = left bad debt (no car that day and the last live OS - from any earlier day, else the weekly OS - owes more than the deposit). Non-funnel: every pilot in raw_v2.
  select r4."Week" as wk, r4."Employee ID" as etm,
         array_agg(z.t order by z.i) as bdt, array_agg(z.a order by z.i) as bda
  from r4
  left join car_wk cw on cw.wk = r4."Week" and cw.etm = r4."Employee ID"
  left join llw lw on lw.wk = r4."Week" and lw.etm = r4."Employee ID"
  cross join lateral (
    select g.i,
      coalesce(lw.llo[g.i], r4."Weekly OS (dash)") as lo_last,
      greatest(coalesce(lw.ldp[g.i], r4.dp), 0) as dep_d,
      (r4."Week" + g.i - 1 < (select case when has_today then current_date + 1 else current_date end from cfg)) as day_ok
    from generate_series(1, 7) g(i)) y
  cross join lateral (
    select y.i,
      case when r4.alo[y.i] is not null and coalesce(r4.asu[y.i], 0) = 1 then 1
           when y.day_ok and r4.alo[y.i] is null and not coalesce(cw.hc[y.i], false) and y.lo_last + y.dep_d < 0 then 2 end as t,
      case when r4.alo[y.i] is not null and coalesce(r4.asu[y.i], 0) = 1 then greatest(0, -r4.alo[y.i] - r4.dp)
           when y.day_ok and r4.alo[y.i] is null and not coalesce(cw.hc[y.i], false) and y.lo_last + y.dep_d < 0 then -(y.lo_last + y.dep_d) end as a
  ) z
  where r4."Week" >= date_trunc('week', current_date)::date - 7
  group by 1, 2
),
u as materialized (   -- raw row + Agent_action fields, shown weeks only (last week + this week)
  select r.*, p.etm as prev_s7,
    bd.bdt, bd.bda,
    case when r."EIP / Single" = 'EIP' then r."Product Type" || ' - EIP'   -- 24-Nov: Leasing - EIP / D2O - EIP / Own Now - EIP
         when r."Product Type" = 'Leasing' then 'Leasing - Single' else r."Product Type" end as product_lbl,
    dr.name, coalesce(lm.lead_id::bigint, ld.lead_id) as lead_id,
    cn.car_numbers, cn.car_model, cn.garage, (ae.etm is not null) as has_car,
    coalesce(aw.agent, 'Unassigned') as agent,
    case when r."Product Type" = 'D2O' then coalesce(at.act_type, 'Penalty') else '' end as act_type,
    coalesce(rw.rz, 0) as rz, coalesce(rw.oth, 0) as oth, coalesce(rw.pp, 0) as pp, coalesce(rw.adj, 0) as adj, coalesce(rw.dpo, 0) as dpo,
    coalesce(r."Weekly OS (dash)", 0) as neg_os,
    coalesce(lw.os, 0) as lw_os,
    lp.d as last_paid,
    coalesce(dw.active_days, 0) as active_days, coalesce(dw.nd_days, 0) as nd_days, coalesce(dw.car_count, 0) as car_count,
    coalesce(dw.fare, 0) as fare, coalesce(dw.cash, 0) as cash, coalesce(dw.subs, 0) as subs, coalesce(dw.trips, 0) as trips,
    coalesce(dw.gps, 0) as gps, coalesce(dw.uber_km, 0) as uber_km, coalesce(dw.dead_km, 0) as dead_km, dw.acc, dw.disp,
    coalesce(dl.trips, 0) as trips_lw, coalesce(dl.active_days, 0) as lw_active, coalesce(dl.nd_days, 0) as lw_nd,
    (yd.etm is not null) as alloc_yd, coalesce(yd.gps_yd, 0) as gps_yd, coalesce(yd.trips_yd, 0) as trips_yd,
    coalesce(rt.rent_w, 0) as rent_w,
    j.last_jama_4w, j.last_jama_1w, cl.last_att, cl.last_conn, cl.last_dispo, rm.txt as remarks,
    l2.n0, l2.n1, (nj.etm is not null) as is_newjoin, rn.open_tat,
    coalesce(cdt.att, 0) as att_td, coalesce(cdt.conn, 0) as conn_td,
    rp.r1, rp.r2, rp.r3, rp.r4, rp.r5, rp.r6, rp.r7,
    np.dnp1, np.dnp2, np.dnp3, np.dnp4, np.dnp5, np.dnp6, np.dnp7,
    case when r."City" = 'Delhi' then 'Delhi NCR' else r."City" end as slab_city
  from r4 r
  left join prevs7 p on p.wk = r."Week" and p.etm = r."Employee ID"
  left join bd on bd.wk = r."Week" and bd.etm = r."Employee ID"
  left join drv dr on dr.etm = r."Employee ID"
  left join lead_mv lm on lm.etm = r."Employee ID"
  left join lead ld on ld.driver_id = dr.driver_id
  left join cars_now cn on cn.etm = r."Employee ID"
  left join act_e ae on ae.etm = r."Employee ID"
  left join agent_wk aw on aw.wk = r."Week" and aw.etm = r."Employee ID"
  left join act_type at on at.etm = r."Employee ID"
  left join recw rw on rw.wk = r."Week" and rw.etm = r."Employee ID"
  left join lwos lw on lw.wk = r."Week" and lw.etm = r."Employee ID"
  left join lastpaid lp on lp.etm = r."Employee ID"
  left join drivew dw on dw.wk = r."Week" and dw.etm = r."Employee ID"
  left join drivew dl on dl.wk = r."Week" - 7 and dl.etm = r."Employee ID"
  left join ydd yd on yd.etm = r."Employee ID"
  left join rentw rt on rt.wk = r."Week" and rt.etm = r."Employee ID"
  left join jama j on j.etm = r."Employee ID"
  left join callw cl on cl.wk = r."Week" and cl.etm = r."Employee ID"
  left join remarks rm on rm.etm = r."Employee ID"
  left join l2w l2 on l2.wk = r."Week" and l2.etm = r."Employee ID"
  left join newjoin nj on nj.etm = r."Employee ID"
  left join rc_now rn on rn.etm = r."Employee ID"
  left join call_day cdt on cdt.etm = r."Employee ID" and cdt.d = current_date
  left join rent_piv rp on rp.wk = r."Week" and rp.etm = r."Employee ID"
  left join nopay np on np.wk = r."Week" and np.etm = r."Employee ID"
  where r."Week" >= date_trunc('week', current_date)::date - 7
),
v as materialized (
  select u.*,
    coalesce(u."Collection Week Total", 0) as tot_rec,
    least(coalesce(u."Collection Week Total", 0), abs(u.neg_os)) as rec_capped,
    coalesce(u."Total OS (latest live)", 0) as lo_latest,
    case when u."Product Type" in ('Leasing') and u."EIP / Single" <> 'EIP' or u."Product Type" = 'Own Now' then 'Base Tier'
         when u."Product Type" = 'D2O' then case when u.is_newjoin then 'Base Tier'
              else (select s.tier from slab s where s.city = u.slab_city and s.min_trips <= u.trips_lw order by s.min_trips desc limit 1) end
    end as trip_tier,
    -- 20-Nov: Deposit for Dash = joined in this week -> current deposit (past week: end of that week);
    -- else deposit at Monday EOD of the week, so a pilot who leaves mid-week and gets the deposit adjusted
    -- does not move into the 0-deposit count.
    greatest(case when u."Last Join Date" between u."Week" and u."Week" + 6
                  then case when u."Week" = date_trunc('week', current_date)::date then u.dp else coalesce(u.dep_wk_last, u.dp) end
                  else coalesce(u.dep_mon_eod, u.dp) end, 0) as dep_dash
  from u
)

select
  v."Week" as "Week (Mon)",
  to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') as "Data Refreshed At",
  v."Employee ID" as "Employee ID",
  v.lead_id as "Lead ID",
  coalesce(v.name, '') as "Pilot Name",
  v."City" as "City",
  v.product_lbl as "Product",
  v."ELC / Non ELC" as "ELC / Non-ELC",
  v."Tenure Days" as "Tenure Days",
  coalesce(v.car_numbers, '') as "Car Numbers (now)",
  coalesce(v.car_model, '') as "Car Model (now)",
  v.car_count as "Cars Held This Week",
  case when v.has_car then 'Active' else 'Inactive' end as "Has Car Now",
  v.agent as "Agent (this week)",
  v.act_type as "Actioning Type",
  row_number() over (partition by v."Week", v."City" order by v.pk, v.neg_os, v."Employee ID") as "Rank in City",
  -- 19-Nov: P0 - Critical (Not in car recovery) only from the 2nd day after the last join (joined 16th -> P0 from 18th);
  -- before that the pilot falls to the next action (OFC / Near surpass / OS not collected).
  coalesce(case when v.ct = 1 and (v."Car Recovery (week)" = 'Open' or v."Last Join Date" is null
                                   or v."Week" + v.co - 1 - v."Last Join Date" >= 2)
                then case when v."Car Recovery (week)" = 'Open' then 'P0 - Critical (In car recovery)' else 'P0 - Critical (Not in car recovery)' end
       when v."Car Recovery (week)" = 'Open' and v.dp - v.cq > 0 then 'P1 - Cancel the car recovery (OFC)'
       when v.cq > 0 and v.dp - v.cq <= v.rr then 'P1 - Near surpass (<=1 day rent to deposit)'
       when v.cq > 0 or v.ee > 0 then 'P2 - OS not collected' end
           || case when v.garage is not null then ' - (Car in Garage)' else '' end, 'No action') as "Action To Take",   -- 24-Nov: garage suffix
  case when v."Car Recovery (week)" = 'Closed' then '6. Car Recovery Closed' when v."Car Recovery (week)" = 'Open' then '5. In Car Recovery'
       when v.cp = 0 then '0. Not Active' when v.cr = 1 then '4. Owes >= Deposit - START RECOVERY'
       when v.ct = 1 then '3. Critical' when v.cq > 0 then '2. Owes - not critical yet' else '1. Paid Up' end as "Stage Today",
  coalesce(v."Last Join Type", '') as "Last Join Type",
  v."Last Join Date" as "Last Join Date",
  v."Join Type (this week)" as "Joined This Week",
  case when v."Last Join Date" is not null then v."Week" + v.co - 1 - v."Last Join Date" end as "Days Since Join",
  v."Deposit at Allocation" as "Deposit at Allocation (Rs)",
  v."SD Bucket (at allocation)" as "Deposit Bucket at Allocation",
  v.dp as "Deposit Now (Rs)",
  case when v.dp <= 0 then '0 Deposit' when v.dp <= 3000 then '1-3K' when v.dp <= 5000 then '3-5K' else '5K+' end as "Deposit Bucket Now",
  v.dep_dash as "Deposit for Dash (Rs)",   -- 20-Nov: moved here (AA:AB) from the end
  case when v.dep_dash <= 0 then '0 Deposit' when v.dep_dash <= 3000 then '1-3K' when v.dep_dash <= 5000 then '3-5K' else '5K+' end as "Deposit Bucket for Dash",
  case when v."Join Type (this week)" <> 'Existing' and v."SD Bucket (at allocation)" = '0 Deposit' then 'Yes' else 'No' end as "Joined This Week at 0 Deposit",
  v.lw_os as "Last Week Closing OS (Rs)",
  v."Weekly OS (dash)" as "Weekly OS to Collect (Rs)",
  v."Weekly OS (incl. live-only pilots)" as "Weekly OS incl. Live-only Pilots (Rs)",
  case when abs(v.neg_os) <= 500 then '0-500' when abs(v.neg_os) <= 1000 then '500-1K' when abs(v.neg_os) <= 2000 then '1-2K'
       when abs(v.neg_os) <= 3000 then '2-3K' when abs(v.neg_os) <= 5000 then '3-5K' when abs(v.neg_os) <= 10000 then '5-10K'
       when abs(v.neg_os) <= 15000 then '10-15K' when abs(v.neg_os) <= 20000 then '15-20K' when abs(v.neg_os) <= 25000 then '20-25K'
       when abs(v.neg_os) <= 30000 then '25-30K' else '30K+' end as "OS Bucket",
  v.tot_rec as "Collected This Week (Rs)",
  v.rz as "Razorpay (Rs)",
  v.pp as "PhonePe (Rs)",
  v.oth as "Other Payment (Rs)",
  v.adj as "Positive Adjustment (Rs)",
  v.dpo as "Deposit to OS (Rs)",
  v."Weekly OS Collected (capped, = dash)" as "Weekly OS Collected (100% cap) (Rs)",
  v.neg_os + v.rec_capped as "Weekly OS Left (Rs)",
  case when v.neg_os = 0 then 0 else round(v.rec_capped::numeric / abs(v.neg_os), 4) end as "Collection %",
  case when v."In Collections Dash (1/0)" = 0 then '' when v.neg_os = 0 or v.rec_capped >= abs(v.neg_os) or abs(v.neg_os) - v.tot_rec < 100 then 'Full Paid'
       when v.rec_capped > 0 then 'Partial Paid' else 'Not Paid' end as "Collection Status",
  greatest(0, v.lw_os + v.tot_rec) as "Last Week OS + Recovery (Rs)",
  v.last_paid as "Last Paid Date",
  v.active_days as "Days Rented This Week",
  -abs(v.rent_w) as "Rent This Week (Rs)",
  v."Daily Rent" as "Daily Rent (Rs)",
  v."Total OS (latest live)" as "Live OS Now (Rs)",
  case when v."Total OS (latest live)" is not null then v.lo_latest + v.dp end as "Live OS + Deposit (Rs)",
  case when v.cs = 1 then 'Yes' else 'No' end as "Risk - Morning",
  case when v.ct = 1 then 'Yes' else 'No' end as "Risk - That Day (EOD)",
  case when v.cs = 1 then case when v.ct = 1 then 'Still Critical' else 'Out of Critical' end else '' end as "Morning List Status",
  case when v.cr = 1 then 'Yes' else 'No' end as "Owes >= Deposit (that day)",
  v."First Surpass Date" as "First Surpass Date",
  case when v."First Surpass Date" = v."Week" and v.prev_s7 is not null then null else v."First Surpass Date" end as "New Surpass Date",
  v."Payment Habit" as "Payment Habit",
  case when coalesce(v.n0, 0) >= 2 then 'L2W: 0%' when coalesce(v.n1, 0) >= 2 then 'L2W: 1%-80%' else '' end as "L2W Payment Tag",
  v."Car Recovery (week)" as "In Car Recovery",
  v."Car Recovery Start" as "Recovery Start Date",
  v."Car Recovery Close Date" as "Recovery Close Date",
  v.open_tat as "Recovery Pending Days",
  coalesce(v.dv, false)::int as "Surpassed After Last Join",
  coalesce(v.dw, false)::int as "Recovery Raised After Last Join",
  coalesce(v.dx, false)::int as "Recovered After Last Join",
  v.last_jama_4w as "Last Jama Date (4 weeks)",
  v.last_jama_1w as "Last Jama Date (this + last week)",
  v.fare as "Uber Earnings (Rs)",
  v.cash as "Cash Collected (Rs)",
  v.subs as "Uber Subscription (Rs)",
  v.trips as "Uber Trips",
  v.trips_lw as "Uber Trips Last Week",
  case when coalesce(v.disp, 0) > 0 then round(v.acc::numeric / v.disp, 4) end as "Acceptance Rate",
  v.gps as "GPS km",
  v.uber_km as "Uber km",
  v.dead_km as "Dead km",
  v.active_days as "Days With Car",
  v.nd_days as "Not-Driven Days",
  v.lw_active as "Days With Car (last week)",
  v.lw_nd as "Not-Driven Days (last week)",
  case when v.has_car and v.alloc_yd and v.trips_yd = 0 then 'ND' else '' end as "Not Driven Yesterday",
  case when v."Product Type" in ('D2O','Own Now') or (v."Product Type" = 'Leasing' and v."EIP / Single" <> 'EIP') then case when v.gps_yd > 0 then 'GPS>0' else 'GPS=0' end else '' end as "GPS Yesterday",
  v."Week Start GPS" as "Week Start GPS",
  case when v."Product Type" = 'D2O' and v.is_newjoin then 'New Join + Resurrection (>= 17 Aug)' else '' end as "Allocation Type (D2O)",
  coalesce(v.trip_tier, '') as "Trip Tier",
  (select sum(x) from unnest(v.aat) x) as "Calls Attempted (week)",
  (select sum(x) from unnest(v.acn) x) as "Calls Connected (week)",
  v.att_td as "Calls Attempted Today",
  v.conn_td as "Calls Connected Today",
  v.last_att as "Last Attempt Time",
  v.last_conn as "Last Connect Time",
  coalesce(v.last_dispo, '') as "Last Disposition",
  coalesce(v.remarks, '') as "Yesterday Remarks",
  v."In Collections Dash (1/0)" as "In Collections Dash",
  v.alo[1] as "Live OS D1",
  v.alo[2] as "Live OS D2",
  v.alo[3] as "Live OS D3",
  v.alo[4] as "Live OS D4",
  v.alo[5] as "Live OS D5",
  v.alo[6] as "Live OS D6",
  v.alo[7] as "Live OS D7",
  v.aco[1] as "Collection D1",
  v.aco[2] as "Collection D2",
  v.aco[3] as "Collection D3",
  v.aco[4] as "Collection D4",
  v.aco[5] as "Collection D5",
  v.aco[6] as "Collection D6",
  v.aco[7] as "Collection D7",
  v."WOS Collected D1" as "Weekly OS Collected (100% cap) D1",
  v."WOS Collected D2" as "Weekly OS Collected (100% cap) D2",
  v."WOS Collected D3" as "Weekly OS Collected (100% cap) D3",
  v."WOS Collected D4" as "Weekly OS Collected (100% cap) D4",
  v."WOS Collected D5" as "Weekly OS Collected (100% cap) D5",
  v."WOS Collected D6" as "Weekly OS Collected (100% cap) D6",
  v."WOS Collected D7" as "Weekly OS Collected (100% cap) D7",
  v.mam[1] as "Risk Morning D1",
  v.mam[2] as "Risk Morning D2",
  v.mam[3] as "Risk Morning D3",
  v.mam[4] as "Risk Morning D4",
  v.mam[5] as "Risk Morning D5",
  v.mam[6] as "Risk Morning D6",
  v.mam[7] as "Risk Morning D7",
  v.meod[1] as "Risk That Day D1",
  v.meod[2] as "Risk That Day D2",
  v.meod[3] as "Risk That Day D3",
  v.meod[4] as "Risk That Day D4",
  v.meod[5] as "Risk That Day D5",
  v.meod[6] as "Risk That Day D6",
  v.meod[7] as "Risk That Day D7",
  v.asu[1] as "Owes >= Deposit D1",
  v.asu[2] as "Owes >= Deposit D2",
  v.asu[3] as "Owes >= Deposit D3",
  v.asu[4] as "Owes >= Deposit D4",
  v.asu[5] as "Owes >= Deposit D5",
  v.asu[6] as "Owes >= Deposit D6",
  v.asu[7] as "Owes >= Deposit D7",
  v.aat[1] as "Calls Attempted D1",
  v.aat[2] as "Calls Attempted D2",
  v.aat[3] as "Calls Attempted D3",
  v.aat[4] as "Calls Attempted D4",
  v.aat[5] as "Calls Attempted D5",
  v.aat[6] as "Calls Attempted D6",
  v.aat[7] as "Calls Attempted D7",
  v.acn[1] as "Calls Connected D1",
  v.acn[2] as "Calls Connected D2",
  v.acn[3] as "Calls Connected D3",
  v.acn[4] as "Calls Connected D4",
  v.acn[5] as "Calls Connected D5",
  v.acn[6] as "Calls Connected D6",
  v.acn[7] as "Calls Connected D7",
  v.bdt[1] as "Bad Debt Type D1",
  v.bdt[2] as "Bad Debt Type D2",
  v.bdt[3] as "Bad Debt Type D3",
  v.bdt[4] as "Bad Debt Type D4",
  v.bdt[5] as "Bad Debt Type D5",
  v.bdt[6] as "Bad Debt Type D6",
  v.bdt[7] as "Bad Debt Type D7",
  v.bda[1] as "Bad Debt (Rs) D1",
  v.bda[2] as "Bad Debt (Rs) D2",
  v.bda[3] as "Bad Debt (Rs) D3",
  v.bda[4] as "Bad Debt (Rs) D4",
  v.bda[5] as "Bad Debt (Rs) D5",
  v.bda[6] as "Bad Debt (Rs) D6",
  v.bda[7] as "Bad Debt (Rs) D7",
  v.r1 as "Rent D1",
  v.r2 as "Rent D2",
  v.r3 as "Rent D3",
  v.r4 as "Rent D4",
  v.r5 as "Rent D5",
  v.r6 as "Rent D6",
  v.r7 as "Rent D7",
  v.dnp1 as "Days Not Paid D1",
  v.dnp2 as "Days Not Paid D2",
  v.dnp3 as "Days Not Paid D3",
  v.dnp4 as "Days Not Paid D4",
  v.dnp5 as "Days Not Paid D5",
  v.dnp6 as "Days Not Paid D6",
  v.dnp7 as "Days Not Paid D7",
  coalesce(v.garage, 'No') as "Car in Garage"   -- 24-Nov: FW
from v
where (select 1 / (count(*) / 100) from rec_day where d = current_date - 1) is not null
  and (select 1 / (count(distinct driver_id) / 5000) from lod where d >= current_date - 1) is not null
order by v."Week", v."City", v."Employee ID"
