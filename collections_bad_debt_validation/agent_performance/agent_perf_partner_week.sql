-- =====================================================================================
-- Collection agent performance: base data, ONE row per partner x week (last 8 weeks incl. current).
-- No agent mapping here (done outside). Aggregate these rows by agent / city to build the report.
-- "Today" metrics = the as-of day of the week: today for the current week, Sunday for past weeks.
-- Population = analytics.collections_bad_debt_mv rows with for_collections = 1 (same as India Collections).
-- Payments = mv_daily_recovery (razorpay, phonepe, other positive, positive adjustment, deposit to OS).
-- Calls = collections_calling_data_raw (Mumbai: only campaign 277, like raw_v2).
-- Runtime: finished under 60 s on the reporting DB (each source read once; no IN (subquery) filter on mv_daily_recovery, that made it > 60 s).
-- =====================================================================================
with b as materialized (
  select distinct on (m.hissab_week, m.partner_etm)
         m.hissab_week as wk, m.partner_etm as etm, m.city, m.revenue_type as product, m.total_os
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1
    and m.hissab_week between date_trunc('week', current_date)::date - 49 and date_trunc('week', current_date)::date
  order by m.hissab_week, m.partner_etm, m.id desc
),
x as materialized (
  select b.*, least(b.wk + 6, current_date) as asof, greatest(-coalesce(b.total_os, 0), 0) as os_amt
  from b
),
p as materialized (   -- payments per pilot per day (fixed floor date keeps hypertable planning fast)
  select r.employee_id as etm, r.date as d, sum(r.amount) as amt
  from mv_daily_recovery r
  where r.date >= date '2026-09-01' and r.date >= date_trunc('week', current_date)::date - 49
    and r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery','positive_adjustment','deposit_to_os')
  group by 1, 2
),
c as materialized (   -- calls per pilot per day
  select k.partner_et_id as etm, k.date as d,
         sum(k.attempt_count) as att, sum(k.connect_count) as conn, sum(k.total_call_duration) as talk
  from public.collections_calling_data_raw k
  where k.week_start >= date_trunc('week', current_date)::date - 49
    and (k.city is distinct from 'Mumbai' or k.campaign_id = '277')
  group by 1, 2
),
pw as (
  select x.wk, x.etm,
         coalesce(sum(p.amt) filter (where p.d < x.asof), 0) as paid_before_day,
         coalesce(sum(p.amt) filter (where p.d = x.asof), 0) as paid_day
  from x left join p on p.etm = x.etm and p.d between x.wk and x.asof
  group by 1, 2
),
cw as (
  select x.wk, x.etm,
         coalesce(sum(c.att), 0) as att_wtd,
         coalesce(sum(c.conn), 0) as conn_wtd,
         coalesce(sum(c.att) filter (where c.d = x.asof), 0) as att_day,
         coalesce(sum(c.conn) filter (where c.d = x.asof), 0) as conn_day,
         coalesce(sum(c.talk) filter (where c.d = x.asof), 0) as talk_day
  from x left join c on c.etm = x.etm and c.d between x.wk and x.asof
  group by 1, 2
)
select
  x.wk                                                     as "Week",
  x.asof                                                   as "As Of Day",
  x.etm                                                    as "Employee ID",
  x.city                                                   as "City",
  x.product                                                as "Product",
  case when x.os_amt > 0 then 1 else 0 end                 as "Has OS (1/0)",
  round(x.os_amt)                                          as "Week OS (Rs)",
  round(pw.paid_before_day + pw.paid_day)                  as "Paid WTD (Rs)",
  round(least(x.os_amt, pw.paid_before_day + pw.paid_day)) as "OS Collected WTD (capped, Rs)",
  round(greatest(x.os_amt - (pw.paid_before_day + pw.paid_day), 0)) as "Pending OS (Rs)",
  round(greatest(x.os_amt - pw.paid_before_day, 0))        as "OS at Start of Day (Rs)",
  round(pw.paid_day)                                       as "Paid on Day (Rs)",
  round(least(greatest(x.os_amt - pw.paid_before_day, 0), pw.paid_day)) as "OS Collected on Day (capped, Rs)",
  case when pw.paid_before_day + pw.paid_day > 0 then 0 else 1 end as "Not Paid WTD (1/0)",
  case when cw.att_wtd > 0 then 1 else 0 end               as "Attempted WTD (1/0)",
  cw.att_wtd                                               as "Attempts WTD #",
  case when cw.conn_wtd > 0 then 1 else 0 end              as "Connected WTD (1/0)",
  case when cw.att_day > 0 then 1 else 0 end               as "Attempted on Day (1/0)",
  cw.att_day                                               as "Attempts on Day #",
  case when cw.conn_day > 0 then 1 else 0 end              as "Connected on Day (1/0)",
  cw.conn_day                                              as "Connects on Day #",
  round(cw.talk_day)                                       as "Talktime on Day (sec)"
from x
join pw on pw.wk = x.wk and pw.etm = x.etm
join cw on cw.wk = x.wk and cw.etm = x.etm
order by x.wk desc, x.city, x.etm;
