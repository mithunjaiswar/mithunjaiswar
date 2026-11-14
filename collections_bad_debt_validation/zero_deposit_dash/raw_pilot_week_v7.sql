-- =====================================================================================
-- Zero / low deposit monitoring: RAW DATA, one row per pilot per hisaab week (last 4 weeks incl. current)
-- Population = distinct ETM from collections_bad_debt_mv (for_collections = 1, same rows as the India Collections
--              dashboard Raw_Data)  UNION  pilots with an active row in hissab_driver_live_os that week.
--   in_dash = 1  -> row is in the India Collections dashboard (weekly OS / collection must match it)
-- Day columns: d1 = week start (Mon) ... d7 = Sunday. Future days are blank.
--   live_os_dN   = end-of-day live OS (hissab_driver_live_os.live_os, after that day's recovery), negative = owes
--   coll_dN      = collection that day (mv_daily_recovery: razorpay, other positive, phonepe, positive adj, deposit to OS)
--   wos_coll_dN  = part of that day's collection that clears the weekly OS (weekly OS is cleared first; the rest goes to live OS)
--                  -> sum of the week = "Weekly OS Collected (capped)" = India Collections dashboard collection (till_sun_100pct)
--   surpass_dN   = 1 when the pilot owes at least his deposit at end of day: live_os < 0 and -live_os >= deposit as of that day
--   crit_am_dN   = 1 when OS before that day's payment >= one day rent  (morning critical)
--   crit_pm_dN   = 1 when OS after that day's payment  >= one day rent  (still critical at day end)
--   att_dN / conn_dN = collection calls attempted / connected that day
-- =====================================================================================
-- NOTE: date filters are written with current_date directly (not a CTE value) so TimescaleDB can skip old chunks
with wk as (select generate_series(date_trunc('week', current_date)::date - 21, date_trunc('week', current_date)::date, interval '7 day')::date as wk),
-- ---------- weekly (dashboard) rows ----------
mvw as materialized (
  select distinct on (m.hissab_week, m.partner_etm)
         m.hissab_week as wk, m.partner_etm as etm, m.city,
         case when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV_Leasing'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.revenue_type end as product_type,
         coalesce(m.total_os, 0) as weekly_os, m.last_week_payment_habit as habit, m.tenure_days,
         case when m.eip_tag = 1 then 'EIP' else 'SINGLE' end as eip_filter
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1 and m.hissab_week in (select wk from wk)
  order by m.hissab_week, m.partner_etm, m.id desc
),
-- ---------- daily live OS rows ----------
lod as materialized (
  select h.date as d, date_trunc('week', h.date)::date as wk, h.driver_id,
         coalesce(h.live_os, 0) as live_os, coalesce(h.recovery, 0) as recovery, coalesce(h.total_rent, 0) as rent,
         coalesce(h.weekly_os, 0) as weekly_os_live
  from hissab_driver_live_os h
  where h.date >= (date_trunc('week', current_date)::date - 21) and h.date <= current_date and h.is_active = 1
),
lod_drv as materialized (select distinct driver_id from lod),
fdr as materialized (   -- driver id <-> ETM
  select f.id as driver_id, f.employee_id as etm from fleet_driver f where f.id in (select driver_id from lod_drv)
  union
  select f.id, f.employee_id from fleet_driver f where f.employee_id in (select etm from mvw)
),
lod_e as materialized (select l.*, f.etm from lod l join fdr f on f.driver_id = l.driver_id),
pop as materialized (
  select wk, etm from mvw
  union
  select distinct wk, etm from lod_e
),
-- ---------- attributes for pilots that are only in live OS (not in the dashboard rows that week) ----------
mv_last as materialized (   -- latest dashboard row of the pilot in the 4 weeks
  select distinct on (etm) etm, city, product_type, habit, tenure_days, eip_filter from mvw order by etm, wk desc
),
joins as materialized (   -- join events (New Join / Rejoin / Resurrection) with deposit at allocation
  select s.employee_id as etm, s.allocation_date, s.category, coalesce(s.sd_amount, 0) as sd_amount, s.city,
         s.product_type, s.first_allocation_date
  from analytics.ssot_alloc_dealloc_full s
  where s.category in ('New Join', 'Rejoin', 'Resurrection') and s.employee_id in (select etm from pop)
    and s.allocation_date <= date_trunc('week', current_date)::date + 6
),
alloc_last as materialized (   -- latest allocation of any kind (city / product fallback)
  select distinct on (s.employee_id) s.employee_id as etm, s.city,
         case when s.product_type = 'leasing' then case when s.fuel_type ilike 'ev%' then 'EV_Leasing' else 'Leasing' end
              when s.product_type = 'DTO' then case when s.fuel_type ilike 'ev%' then 'EV_D2O' else 'D2O' end
              when s.product_type = 'Rev_share' then 'Revenue Share' else s.product_type end as product_type,   -- same names as the dashboard
         s.first_allocation_date
  from analytics.ssot_alloc_dealloc_full s
  where s.employee_id in (select etm from pop) and s.allocation_date <= date_trunc('week', current_date)::date + 6
  order by s.employee_id, s.allocation_date desc, s.allocation_datetime desc
),
-- ---------- money ----------
dep_tot as materialized (   -- index-only scan (filter must match idx_mdr_dep_valid_emp)
  select d.employee_id as etm, sum(d.amount) as dep_now
  from mv_deposits_raw d
  where d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[])
  group by 1
),
dep_day as materialized (   -- deposits dated inside the 4 weeks (to rebuild the deposit on each day)
  select d.employee_id as etm, d.date as d, sum(d.amount) as amt
  from mv_deposits_raw d
  where d.date >= (date_trunc('week', current_date)::date - 21) and d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[])
  group by 1, 2
),
rec_day as materialized (
  select r.employee_id as etm, r.date as d, sum(r.amount) as amt
  from mv_daily_recovery r
  where r.date >= (date_trunc('week', current_date)::date - 21) and r.date <= current_date
    and r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery','positive_adjustment','deposit_to_os')
  group by 1, 2
),
call_day as materialized (
  select c.partner_et_id as etm, c.date as d, sum(c.attempt_count) as att, sum(c.connect_count) as conn
  from public.collections_calling_data_raw c
  where c.week_start >= date_trunc('week', current_date)::date - 21
  group by 1, 2
),
-- ---------- GPS at week start (Monday) on the cars the pilot held that day ----------
car_pop as materialized (   -- allocations of the population (read once)
  select s.employee_id as etm, s.car_id::bigint as car_id, s.allocation_date, s.jama_date
  from analytics.ssot_alloc_dealloc_base s
  where s.employee_id in (select etm from pop) and s.car_id ~ '^[0-9]+$'
    and coalesce(s.jama_date, current_date) >= (date_trunc('week', current_date)::date - 21)
),
car_mon as materialized (
  select w.wk, s.etm, s.car_id
  from wk w join car_pop s on s.allocation_date <= w.wk and coalesce(s.jama_date, current_date) >= w.wk
),
gps_mon as materialized (
  select c.wk, c.etm, sum(coalesce(k.gps_km, 0)) as gps_km
  from car_mon c
  left join (select k0.car_id, k0.date, k0.gps_km from car_dead_km k0
             where k0.date in (date_trunc('week', current_date)::date, date_trunc('week', current_date)::date - 7, date_trunc('week', current_date)::date - 14, date_trunc('week', current_date)::date - 21)) k on k.car_id = c.car_id and k.date = c.wk   -- only the 4 Mondays (date index)
  group by 1, 2
),
-- ---------- car recovery cases (non-funnel: every case, from recovery_cars) ----------
rcase as materialized (
  select fd.employee_id as etm, a.activation_date::date as start_date,
         case when a.rec_tags_id in (111, 112, 113) then coalesce(ls.close_date::date, (a.updated_at at time zone 'Asia/Kolkata')::date) end as close_date
  from recovery_cars a
  left join lateral (select b.datetime as close_date from recovery_status_logs b
                     where b.recovery_id = a.id and b.recovery_status in ('complete','failed','cancelled')
                     order by b.id desc limit 1) ls on true
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
              when d.live_os < 0 and -d.live_os >= greatest(d.dep_asof, 0) then 1 else 0 end as surpass,
         case when d.live_os is null or d.rent <= 0 then null
              when -(d.live_os - d.recovery) >= d.rent then 1 else 0 end as crit_am,
         case when d.live_os is null or d.rent <= 0 then null
              when -d.live_os >= d.rent then 1 else 0 end as crit_pm
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
    max(crit_am) filter (where dn = 1) a1, max(crit_am) filter (where dn = 2) a2, max(crit_am) filter (where dn = 3) a3,
    max(crit_am) filter (where dn = 4) a4, max(crit_am) filter (where dn = 5) a5, max(crit_am) filter (where dn = 6) a6,
    max(crit_am) filter (where dn = 7) a7,
    max(crit_pm) filter (where dn = 1) e1, max(crit_pm) filter (where dn = 2) e2, max(crit_pm) filter (where dn = 3) e3,
    max(crit_pm) filter (where dn = 4) e4, max(crit_pm) filter (where dn = 5) e5, max(crit_pm) filter (where dn = 6) e6,
    max(crit_pm) filter (where dn = 7) e7,
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
    max(rent) as day_rent
  from dayf group by 1, 2
),
join_wk as materialized (   -- latest join event up to the week end
  select distinct on (pp.wk, pp.etm) pp.wk, pp.etm, x.allocation_date, x.category, x.sd_amount
  from pop pp join joins x on x.etm = pp.etm and x.allocation_date <= pp.wk + 6
  order by pp.wk, pp.etm, x.allocation_date desc
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
    j.allocation_date as last_join_date, j.category as last_join_type, j.sd_amount as dep_at_alloc
  from pop pp
  left join mvw m on m.wk = pp.wk and m.etm = pp.etm
  left join mv_last ml on ml.etm = pp.etm
  left join alloc_last al on al.etm = pp.etm
  left join join_wk j on j.wk = pp.wk and j.etm = pp.etm
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
       when b.dep_at_alloc <= 10000 then '5-10K' else '10K+' end as "SD Bucket (at allocation)",
  coalesce(dt.dep_now, 0)                                as "Current Deposit",
  case when rc.rc_close between b.wk and b.wk + 6 then rc.rc_close end as "Car Recovery Close Date",   -- was Deposit at Week Start (unused); close date in this week
  case when g.etm is null then 'No Car' when g.gps_km > 0 then 'GPS Active' else 'GPS Inactive' end as "Week Start GPS",
  b.weekly_os                                            as "Weekly OS (dash)",
  -pv.wos_abs                                            as "Weekly OS (incl. live-only pilots)",
  pv.coll_week                                           as "Collection Week Total",
  pv.wcoll_week                                          as "Weekly OS Collected (capped, = dash)",
  coalesce(pv.lo7, pv.lo6, pv.lo5, pv.lo4, pv.lo3, pv.lo2, pv.lo1) as "Total OS (latest live)",
  b.habit                                                as "Payment Habit",
  case when b.tenure_days is null then 'Unknown' when b.tenure_days > 30 then 'ELC' else 'Non_ELC' end as "ELC / Non ELC",   -- as asked: ELC = more than 30 days in the organisation
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
  b.wk + 0 as "D1 Date", b.wk + 1 as "D2 Date", b.wk + 2 as "D3 Date", b.wk + 3 as "D4 Date",
  b.wk + 4 as "D5 Date", b.wk + 5 as "D6 Date", b.wk + 6 as "D7 Date",
  pv.lo1 as "Live OS D1", pv.lo2 as "Live OS D2", pv.lo3 as "Live OS D3", pv.lo4 as "Live OS D4",
  pv.lo5 as "Live OS D5", pv.lo6 as "Live OS D6", pv.lo7 as "Live OS D7",
  pv.c1 as "Collection D1", pv.c2 as "Collection D2", pv.c3 as "Collection D3", pv.c4 as "Collection D4",
  pv.c5 as "Collection D5", pv.c6 as "Collection D6", pv.c7 as "Collection D7",
  pv.w1 as "WOS Collected D1", pv.w2 as "WOS Collected D2", pv.w3 as "WOS Collected D3", pv.w4 as "WOS Collected D4",
  pv.w5 as "WOS Collected D5", pv.w6 as "WOS Collected D6", pv.w7 as "WOS Collected D7",
  pv.s1 as "Surpass D1", pv.s2 as "Surpass D2", pv.s3 as "Surpass D3", pv.s4 as "Surpass D4",
  pv.s5 as "Surpass D5", pv.s6 as "Surpass D6", pv.s7 as "Surpass D7",
  pv.a1 as "Critical AM D1", pv.a2 as "Critical AM D2", pv.a3 as "Critical AM D3", pv.a4 as "Critical AM D4",
  pv.a5 as "Critical AM D5", pv.a6 as "Critical AM D6", pv.a7 as "Critical AM D7",
  pv.e1 as "Critical EOD D1", pv.e2 as "Critical EOD D2", pv.e3 as "Critical EOD D3", pv.e4 as "Critical EOD D4",
  pv.e5 as "Critical EOD D5", pv.e6 as "Critical EOD D6", pv.e7 as "Critical EOD D7",
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
    case when r0."Product Type" = 'Leasing' then case when r0."EIP / Single" = 'EIP' then 'EIP' else 'SINGLE' end
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
bd as materialized (
  select r4."Week" as wk, r4."Employee ID" as etm,
         array_agg(t order by i) as bdt, array_agg(a order by i) as bda
  from r4 cross join lateral (
    select g.i,
      case when r4.alo[g.i] is not null and coalesce(r4.asu[g.i], 0) = 1 then 1
           when r4.ea > 0 and r4.ea < g.i and r4.alo[g.i] is null and r4.ec > 0 then
             case when r4."Join Type (this week)" <> 'Existing' and r4."Last Join Date" >= r4."Week" then 2
                  when r4."Join Type (this week)" = 'Existing' and r4."In Collections Dash (1/0)" = 1 and coalesce(r4."Weekly OS (dash)", 0) < 0 then 2 else 2 end
      end as t,
      case when r4.alo[g.i] is not null and coalesce(r4.asu[g.i], 0) = 1 then greatest(0, -r4.alo[g.i] - r4.dp)
           when r4.ea > 0 and r4.ea < g.i and r4.alo[g.i] is null and r4.ec > 0 and (true or 
                (r4."Join Type (this week)" <> 'Existing' and r4."Last Join Date" >= r4."Week") or
                (r4."Join Type (this week)" = 'Existing' and r4."In Collections Dash (1/0)" = 1 and coalesce(r4."Weekly OS (dash)", 0) < 0)) then r4.ec
      end as a
    from generate_series(1, 7) g(i)) z
  group by 1, 2
)
select
r."Week",
  r."City",
  r."Product Type",
  r."Employee ID",
  r."EIP / Single",
  r."In Collections Dash (1/0)",
  r."Deposit at Allocation",
  r."SD Bucket (at allocation)",
  r."Current Deposit",
  r."Car Recovery Close Date",
  r."Week Start GPS",
  r."Weekly OS (dash)",
  r."Weekly OS (incl. live-only pilots)",
  r."Collection Week Total",
  r."Weekly OS Collected (capped, = dash)",
  r."Total OS (latest live)",
  r."Payment Habit",
  r."ELC / Non ELC",
  r."Tenure Days",
  r."Join Type (this week)",
  r."Last Join Type",
  r."Last Join Date",
  r."Daily Rent",
  r."First Surpass Date",
  r."Car Recovery (week)",
  r."Car Recovery Start",
  r."D1 Date",
  r."D2 Date",
  r."D3 Date",
  r."D4 Date",
  r."D5 Date",
  r."D6 Date",
  r."D7 Date",
  r."Live OS D1",
  r."Live OS D2",
  r."Live OS D3",
  r."Live OS D4",
  r."Live OS D5",
  r."Live OS D6",
  r."Live OS D7",
  r."Collection D1",
  r."Collection D2",
  r."Collection D3",
  r."Collection D4",
  r."Collection D5",
  r."Collection D6",
  r."Collection D7",
  r."WOS Collected D1",
  r."WOS Collected D2",
  r."WOS Collected D3",
  r."WOS Collected D4",
  r."WOS Collected D5",
  r."WOS Collected D6",
  r."WOS Collected D7",
  r."Surpass D1",
  r."Surpass D2",
  r."Surpass D3",
  r."Surpass D4",
  r."Surpass D5",
  r."Surpass D6",
  r."Surpass D7",
  r."Critical AM D1",
  r."Critical AM D2",
  r."Critical AM D3",
  r."Critical AM D4",
  r."Critical AM D5",
  r."Critical AM D6",
  r."Critical AM D7",
  r."Critical EOD D1",
  r."Critical EOD D2",
  r."Critical EOD D3",
  r."Critical EOD D4",
  r."Critical EOD D5",
  r."Critical EOD D6",
  r."Critical EOD D7",
  r."Attempts D1",
  r."Attempts D2",
  r."Attempts D3",
  r."Attempts D4",
  r."Attempts D5",
  r."Attempts D6",
  r."Attempts D7",
  r."Connects D1",
  r."Connects D2",
  r."Connects D3",
  r."Connects D4",
  r."Connects D5",
  r."Connects D6",
  r."Connects D7",
  r."Last Updated",
  null::text as "Dash Status (formula in EU)",
  case when r."Product Type" = 'Leasing' then case when r."EIP / Single" = 'EIP' then 'Leasing - EIP' else 'Leasing - Single' end else r."Product Type" end as "Product (EIP split)",
  r.co as "Latest Day #",
  r.cp as "Active Latest Day (1/0)",
  r.cq as "Owed Latest Day (Rs)",
  r.cr as "Surpassed Latest Day (1/0)",
  r.cs as "Critical AM Latest Day (MasterTab rule)",
  r.ct as "Critical EOD Latest Day (MasterTab rule)",
  coalesce(r.aat[r.co], 0) as "Attempts Latest Day",
  (select coalesce(sum(v), 0) from unnest(r.aat) v) as "Attempts Week",
  (select coalesce(sum(v), 0) from unnest(r.acn) v) as "Connects Week",
  case when coalesce(r.cr_any, 0) > 0 then 1 else 0 end as "Surpassed Any Day (1/0)",
  coalesce(r.aco[r.co], 0) as "Collection Latest Day",
  greatest(r.cq - r.dp, 0) as "Unsecured Exposure (owed above deposit)",
  r.da as "Join Week",
  case when r."Last Join Date" is not null then r."Week" + r.co - 1 - r."Last Join Date" end as "Days Since Join",
  case when r."Car Recovery (week)" = 'Closed' then '6. Car Recovery Closed' when r."Car Recovery (week)" = 'Open' then '5. In Car Recovery'
       when r.cp = 0 then '0. Not Active' when r.cr = 1 then '4. Owes >= Deposit - START RECOVERY'
       when r.ct = 1 then '3. Critical (MasterTab rule)' when r.cq > 0 then '2. Owes - not critical yet' else '1. Paid Up' end as "Stage Today",
  null::text as "ok_1 (formula in EW)",
  null::text as "ok_2 (formula in EX)",
  null::text as "ok_3 (formula in EY)",
  null::text as "ok_4 (formula in EZ)",
  r.mam[1] as "MT Critical AM D1",
  r.mam[2] as "MT Critical AM D2",
  r.mam[3] as "MT Critical AM D3",
  r.mam[4] as "MT Critical AM D4",
  r.mam[5] as "MT Critical AM D5",
  r.mam[6] as "MT Critical AM D6",
  r.mam[7] as "MT Critical AM D7",
  r.meod[1] as "MT Critical EOD D1",
  r.meod[2] as "MT Critical EOD D2",
  r.meod[3] as "MT Critical EOD D3",
  r.meod[4] as "MT Critical EOD D4",
  r.meod[5] as "MT Critical EOD D5",
  r.meod[6] as "MT Critical EOD D6",
  r.meod[7] as "MT Critical EOD D7",
  coalesce(r.dv, false)::int as "Surpassed after last join (4w, 1/0)",
  coalesce(r.dw, false)::int as "Car recovery raised after last join (4w, 1/0)",
  coalesce(r.dx, false)::int as "Car recovered / case closed after last join (4w, 1/0)",
  case when r."First Surpass Date" = r."Week" and p.etm is not null then null else r."First Surpass Date" end as "New Surpass Date (not surpassed day before)",
  null::text as "Weekly Agent (formula in EV)",
  r.ea as "First Active Day # (week)",
  r.eb as "Last Live OS in week",
  r.ec as "Owed above deposit after leaving (Rs)",
  (r."Week" - date '1899-12-30')::text || '|' || r."Employee ID" as "Key (week|ID)",
  r.ee as "Weekly OS pending (Rs)",
  case when r.ct = 1 then case when r."Car Recovery (week)" = 'Open' then 'P0 - Critical (In car recovery)' else 'P0 - Critical (Not in car recovery)' end
       when r.cq > 0 and r.dp - r.cq <= r.rr then 'P1 - Near surpass (<=1 day rent to deposit)'
       when r.cq > 0 or r.ee > 0 then 'P2 - OS not collected' end as "Action Tag",
  b.bdt[1] as "Bad Debt Type D1",
  b.bdt[2] as "Bad Debt Type D2",
  b.bdt[3] as "Bad Debt Type D3",
  b.bdt[4] as "Bad Debt Type D4",
  b.bdt[5] as "Bad Debt Type D5",
  b.bdt[6] as "Bad Debt Type D6",
  b.bdt[7] as "Bad Debt Type D7",
  b.bda[1] as "Bad Debt Amt D1",
  b.bda[2] as "Bad Debt Amt D2",
  b.bda[3] as "Bad Debt Amt D3",
  b.bda[4] as "Bad Debt Amt D4",
  b.bda[5] as "Bad Debt Amt D5",
  b.bda[6] as "Bad Debt Amt D6",
  b.bda[7] as "Bad Debt Amt D7"
from r4 r
left join prevs7 p on p.wk = r."Week" and p.etm = r."Employee ID"
left join bd b on b.wk = r."Week" and b.etm = r."Employee ID"
order by r."Week", r."City", r."Employee ID"
