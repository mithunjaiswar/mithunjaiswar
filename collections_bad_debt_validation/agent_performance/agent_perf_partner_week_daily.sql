-- =====================================================================================
-- Collection agent performance: ONE row per partner x week, last 8 weeks (incl. current), with day columns D1..D7
-- (D1 = Monday ... D7 = Sunday), same style as zero-deposit raw_v2. No agent mapping (join on Employee ID outside).
-- Future days of the current week are blank.
-- Population = analytics.collections_bad_debt_mv rows with for_collections = 1 (same as India Collections).
-- Week OS = -total_os (what the partner owes at the start of the week).
-- Payments = mv_daily_recovery (razorpay, phonepe, other positive, positive adjustment, deposit to OS).
-- OS Collected (capped) = part of the day's payment that goes to the week OS (never above what was still pending).
-- Calls = collections_calling_data_raw (Mumbai: only campaign 277, like raw_v2). Talktime = total_call_duration (sec).
-- Perf: each source read once, joined on (pilot, day) by hash; no IN (subquery) filter (that made it > 60 s).
-- =====================================================================================
with b as materialized (
  select distinct on (m.hissab_week, m.partner_etm)
         m.hissab_week as wk, m.partner_etm as etm, m.city, m.revenue_type as product,
         greatest(-coalesce(m.total_os, 0), 0) as os_amt
  from analytics.collections_bad_debt_mv m
  where m.for_collections = 1
    and m.hissab_week between date_trunc('week', current_date)::date - 49 and date_trunc('week', current_date)::date
  order by m.hissab_week, m.partner_etm, m.id desc
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
d as materialized (   -- partner x day (only days up to today)
  select b.wk, b.etm, b.os_amt, n.dn, b.wk + n.dn - 1 as d,
         coalesce(p.amt, 0) as paid, coalesce(c.att, 0) as att, coalesce(c.conn, 0) as conn, coalesce(c.talk, 0) as talk
  from b
  cross join generate_series(1, 7) as n(dn)
  left join p on p.etm = b.etm and p.d = b.wk + n.dn - 1
  left join c on c.etm = b.etm and c.d = b.wk + n.dn - 1
  where b.wk + n.dn - 1 <= current_date
),
g as (
  select d.*,
         greatest(d.os_amt - coalesce(sum(d.paid) over w_before, 0), 0) as os_start
  from d
  window w_before as (partition by d.wk, d.etm order by d.dn rows between unbounded preceding and 1 preceding)
),
g2 as (
  select g.*, least(g.os_start, g.paid) as coll_cap from g
)
select
  b.wk                                                     as "Week",
  b.etm                                                    as "Employee ID",
  b.city                                                   as "City",
  b.product                                                as "Product",
  round(b.os_amt)                                          as "Week OS (Rs)",
  round(sum(g.paid))                                       as "Paid WTD (Rs)",
  round(sum(g.coll_cap))                                   as "OS Collected WTD (capped, Rs)",
  round(b.os_amt - sum(g.coll_cap))                        as "Pending OS (Rs)",
  case when sum(g.paid) > 0 then 0 else 1 end              as "Not Paid WTD (1/0)",
  sum(g.att)                                               as "Attempts WTD #",
  case when sum(g.att) > 0 then 1 else 0 end               as "Attempted WTD (1/0)",
  sum(g.conn)                                              as "Connects WTD #",
  case when sum(g.conn) > 0 then 1 else 0 end              as "Connected WTD (1/0)",
  round(sum(g.talk))                                       as "Talktime WTD (sec)",
  max(round(g.os_start)) filter (where g.dn = 1) as "OS at Start of Day (Rs) D1",
  max(round(g.os_start)) filter (where g.dn = 2) as "OS at Start of Day (Rs) D2",
  max(round(g.os_start)) filter (where g.dn = 3) as "OS at Start of Day (Rs) D3",
  max(round(g.os_start)) filter (where g.dn = 4) as "OS at Start of Day (Rs) D4",
  max(round(g.os_start)) filter (where g.dn = 5) as "OS at Start of Day (Rs) D5",
  max(round(g.os_start)) filter (where g.dn = 6) as "OS at Start of Day (Rs) D6",
  max(round(g.os_start)) filter (where g.dn = 7) as "OS at Start of Day (Rs) D7",
  max(round(g.paid)) filter (where g.dn = 1) as "Paid (Rs) D1",
  max(round(g.paid)) filter (where g.dn = 2) as "Paid (Rs) D2",
  max(round(g.paid)) filter (where g.dn = 3) as "Paid (Rs) D3",
  max(round(g.paid)) filter (where g.dn = 4) as "Paid (Rs) D4",
  max(round(g.paid)) filter (where g.dn = 5) as "Paid (Rs) D5",
  max(round(g.paid)) filter (where g.dn = 6) as "Paid (Rs) D6",
  max(round(g.paid)) filter (where g.dn = 7) as "Paid (Rs) D7",
  max(round(g.coll_cap)) filter (where g.dn = 1) as "OS Collected (capped, Rs) D1",
  max(round(g.coll_cap)) filter (where g.dn = 2) as "OS Collected (capped, Rs) D2",
  max(round(g.coll_cap)) filter (where g.dn = 3) as "OS Collected (capped, Rs) D3",
  max(round(g.coll_cap)) filter (where g.dn = 4) as "OS Collected (capped, Rs) D4",
  max(round(g.coll_cap)) filter (where g.dn = 5) as "OS Collected (capped, Rs) D5",
  max(round(g.coll_cap)) filter (where g.dn = 6) as "OS Collected (capped, Rs) D6",
  max(round(g.coll_cap)) filter (where g.dn = 7) as "OS Collected (capped, Rs) D7",
  max(g.att) filter (where g.dn = 1) as "Attempts # D1",
  max(g.att) filter (where g.dn = 2) as "Attempts # D2",
  max(g.att) filter (where g.dn = 3) as "Attempts # D3",
  max(g.att) filter (where g.dn = 4) as "Attempts # D4",
  max(g.att) filter (where g.dn = 5) as "Attempts # D5",
  max(g.att) filter (where g.dn = 6) as "Attempts # D6",
  max(g.att) filter (where g.dn = 7) as "Attempts # D7",
  max(g.conn) filter (where g.dn = 1) as "Connects # D1",
  max(g.conn) filter (where g.dn = 2) as "Connects # D2",
  max(g.conn) filter (where g.dn = 3) as "Connects # D3",
  max(g.conn) filter (where g.dn = 4) as "Connects # D4",
  max(g.conn) filter (where g.dn = 5) as "Connects # D5",
  max(g.conn) filter (where g.dn = 6) as "Connects # D6",
  max(g.conn) filter (where g.dn = 7) as "Connects # D7",
  max(round(g.talk)) filter (where g.dn = 1) as "Talktime (sec) D1",
  max(round(g.talk)) filter (where g.dn = 2) as "Talktime (sec) D2",
  max(round(g.talk)) filter (where g.dn = 3) as "Talktime (sec) D3",
  max(round(g.talk)) filter (where g.dn = 4) as "Talktime (sec) D4",
  max(round(g.talk)) filter (where g.dn = 5) as "Talktime (sec) D5",
  max(round(g.talk)) filter (where g.dn = 6) as "Talktime (sec) D6",
  max(round(g.talk)) filter (where g.dn = 7) as "Talktime (sec) D7"
from b
join g2 g on g.wk = b.wk and g.etm = b.etm
group by b.wk, b.etm, b.city, b.product, b.os_amt
order by b.wk desc, b.city, b.etm;
