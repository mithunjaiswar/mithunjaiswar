-- =====================================================================================
-- Own Now churn + recovery validity: INPUT rows for the view (logic: Own_Now_Churn_Recovery_Validity_Logic.md, Prabhu, 25-Nov-2026).
-- One row per Own Now pilot x car that went inactive in the week (last 4 weeks incl. current). Week = Monday.
-- Inactive list = analytics.ssot_alloc_dealloc_full: is_own_now = 1, jama in the week, no car at the end of the jama day
--   (jama_category Attrition / EIP drop-off). Tenure status / bucket are NOT in the DB: typed in the OwnNow_Tenure_Input tab.
-- Category / Recovery valid / Remark / Final mark are sheet formulas in OwnNow_Churn_View (so the tenure input can change them).
-- Critical (day) = masterlist risk_type or critical_risk_tag = 'Critical_Risk'. Case raise time = recovery_cars.activation_date (IST).
-- =====================================================================================
with pop as materialized (
  select date_trunc('week', s.jama_date)::date as wk, s.employee_id as etm, s.driver_id, s.city, s.team,
         s.car_number, case when s.car_id ~ '^[0-9]+$' then s.car_id::bigint end as car_id,
         s.allocation_id, s.allocation_date, s.jama_date, s.reason as drop_reason, s.user_name_at_jama as dropped_by
  from analytics.ssot_alloc_dealloc_full s
  where s.is_own_now = 1
    and s.jama_date >= date_trunc('week', current_date)::date - 21 and s.jama_date <= current_date
    and coalesce(s.cars_as_of_day_end_jama, 0) = 0
),
cs_now as materialized (   -- car status now (fleet_car). car_status_log per car was too slow (> 60 s)
  select fc.id as car_id, st.name as car_status
  from fleet_car fc join car_status st on st.id = fc.status_id
  where fc.id in (select car_id from pop)
),
rc as materialized (   -- recovery cases on these cars since the allocation date
  select p.wk, p.etm, p.car_id, r.id as case_id, r.activation_date as raised_at, r.rec_tags_id, r.reason as case_reason,
         trim(coalesce(au.first_name, '') || ' ' || coalesce(au.last_name, '')) as raised_by,
         (select b.datetime from recovery_status_logs b
           where b.recovery_id = r.id and b.recovery_status in ('complete', 'failed', 'cancelled')
           order by b.id desc limit 1) as closed_at
  from pop p
  join recovery_cars r on r.car_id = p.car_id and r.activation_date::date >= p.allocation_date and r.activation_date::date <= p.wk + 6
  left join auth_user au on au.id = r.created_by
),
rc1 as materialized (   -- one case per row: raised in the week, closed in the week, or still open first; else the latest
  select distinct on (wk, etm, car_id) *,
         case when rec_tags_id = 111 then 'Completed' when rec_tags_id = 112 then 'Failed'
              when rec_tags_id = 113 then 'Cancelled' else 'Open' end as case_state
  from rc
  order by wk, etm, car_id,
           case when raised_at::date between wk and wk + 6 or closed_at::date between wk and wk + 6
                     or coalesce(rec_tags_id, 0) not in (111, 112, 113) then 0 else 1 end,
           raised_at desc
),
ml as materialized (   -- masterlist days for these pilots (raise weeks can be old, so 120 days back), one row per pilot x day
  select m.partner_et_id as etm, m.snapshot_date as d,
         bool_or(m.risk_type = 'Critical_Risk' or m.critical_risk_tag = 'Critical_Risk') as crit,
         min(m.total_current_os) as total_current_os, max(m.collections_tag) as collections_tag
  from mv_collections_calling_masterlist m
  where m.snapshot_date >= date_trunc('week', current_date)::date - 21 - 120
    and m.partner_et_id in (select etm from pop)
  group by 1, 2
),
mla as materialized (   -- perf: one array row per pilot, so the per-row lookups below never re-scan the masterlist
  select etm, array_agg(d order by d) as ds, array_agg(crit order by d) as cr,
         array_agg(total_current_os order by d) as os, array_agg(collections_tag order by d) as tg
  from ml group by 1
),
upf as (
  select d.employee_id as etm, sum(d.amount) as upfront
  from mv_deposits_raw d
  where d.deposit_type in ('initial-deposit', 'top-up') and d.employee_id in (select etm from pop)
  group by 1
),
ssn as materialized (   -- perf: recent allocations read ONCE (joining ssot per pilot re-scanned the 314 MB table)
  select s.employee_id as etm, s.car_number, s.allocation_date, s.jama_date, s.allocation_id
  from analytics.ssot_alloc_dealloc_full s
  where s.allocation_date >= date_trunc('week', current_date)::date - 21
),
newcar as (   -- given another car after the drop-off (ssot puts 2026-12-09 as jama_date of an open allocation)
  select distinct on (p.wk, p.etm, p.car_id) p.wk, p.etm, p.car_id,
         s.car_number as new_car, s.allocation_date as new_car_date,
         case when s.jama_date is null or s.jama_date > current_date then 'Yes' else 'No' end as new_car_active
  from pop p
  join ssn s on s.etm = p.etm and s.allocation_date >= p.jama_date and s.allocation_id is distinct from p.allocation_id
  order by p.wk, p.etm, p.car_id, s.allocation_date
),
dup as (
  select p.wk, p.etm, p.car_id,
         string_agg(q.car_number, ', ') as other_cars
  from pop p join pop q on q.wk = p.wk and q.etm = p.etm and q.car_id is distinct from p.car_id
  group by 1, 2, 3
)
select
  p.wk                                         as "Week",
  p.etm                                        as "Employee ID",
  p.city                                       as "City",
  p.team                                       as "Team",
  p.car_number                                 as "Car Number",
  p.allocation_date                            as "Allocation Date",
  p.jama_date                                  as "Drop-off Date",
  p.drop_reason                                as "Drop-off Reason",
  p.dropped_by                                 as "Dropped By",
  cw.car_status                                as "Car Status (now)",
  c.case_id                                    as "Case ID",
  to_char(c.raised_at, 'YYYY-MM-DD HH24:MI')   as "Case Raised At",
  c.case_state                                 as "Case State",
  to_char(c.closed_at, 'YYYY-MM-DD HH24:MI')   as "Case Closed At",
  c.case_reason                                as "Case Reason",
  c.raised_by                                  as "Case Raised By",
  case when c.case_id is not null and (c.raised_at::date between p.wk and p.wk + 6 or c.closed_at::date between p.wk and p.wk + 6
                                        or c.case_state = 'Open') then 'Yes' else 'No' end as "Case In Week",
  coalesce(k.crit_days_raise, 0)               as "Critical Days (raise week)",
  k.crit_dates_raise                           as "Critical Dates (raise week)",
  case when c.case_id is null then '' when coalesce(k.days_on_list_raise, 0) > 0 then 'Yes' else 'No' end as "On Masterlist (raise week)",
  coalesce(k.crit_days_drop, 0)                as "Critical Days (drop week)",
  k.crit_dates_drop                            as "Critical Dates (drop week)",
  round(-o.os)                                 as "Live OS Owed Last Week (Rs)",
  o.d                                          as "Live OS Snapshot Date",
  o.tg                                         as "Paid Status Last Week",
  round(up.upfront)                            as "Upfront Paid (Rs)",
  n.new_car                                    as "New Car",
  n.new_car_date                               as "New Car Date",
  n.new_car_active                             as "New Car Active",
  dp.other_cars                                as "Same Driver Other Cars",
  date_trunc('second', now() at time zone 'Asia/Kolkata') as "Last Updated"
from pop p
left join cs_now cw on cw.car_id = p.car_id
left join rc1 c on c.wk = p.wk and c.etm = p.etm and c.car_id = p.car_id
left join mla a on a.etm = p.etm
left join lateral (   -- Critical days: raise week (Mon-Sun of the case raise) and drop week (Mon to the drop-off date)
  select count(*) filter (where u.c and u.d between rw.mon and rw.mon + 6) as crit_days_raise,
         string_agg(to_char(u.d, 'DD Mon'), ', ' order by u.d) filter (where u.c and u.d between rw.mon and rw.mon + 6) as crit_dates_raise,
         count(*) filter (where u.d between rw.mon and rw.mon + 6) as days_on_list_raise,
         count(*) filter (where u.c and u.d between p.wk and p.jama_date) as crit_days_drop,
         string_agg(to_char(u.d, 'DD Mon'), ', ' order by u.d) filter (where u.c and u.d between p.wk and p.jama_date) as crit_dates_drop
  from (select date_trunc('week', c.raised_at)::date as mon) rw, unnest(a.ds, a.cr) as u(d, c)
) k on true
left join lateral (   -- Live OS + paid status: latest snapshot in the drop week on/before the drop date, else the earliest of the week
  select u.d, u.os, u.tg
  from unnest(a.ds, a.os, a.tg) as u(d, os, tg)
  where u.d between p.wk and p.wk + 6
  order by (u.d <= p.jama_date) desc, case when u.d <= p.jama_date then p.wk - u.d else u.d - p.wk end
  limit 1
) o on true
left join upf up on up.etm = p.etm
left join newcar n on n.wk = p.wk and n.etm = p.etm and n.car_id is not distinct from p.car_id
left join dup dp on dp.wk = p.wk and dp.etm = p.etm and dp.car_id is not distinct from p.car_id
order by p.wk desc, p.city, p.etm, p.car_number;
