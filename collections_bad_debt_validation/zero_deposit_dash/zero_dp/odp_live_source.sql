-- =====================================================================================
-- 0 DP | Live Source (25-Nov). Feeds '0 DP | Week to Date' and '0 DP | Weekly' (replaces the pasted
-- '0 DP | Allocation Source' / '0 DP | Recovery Source' snapshots). Automation output at A1 (header row 1).
-- Window: origin O = Monday 2 weeks ago .. today; pilots = anyone with a car in the last ~7 weeks. Day strings start with 'x' (keeps leading zeros as text);
-- character k+1 of a string = day O + k - 1.
-- Blocks (side by side, padded by row number):
--   A:E  week key "YYYY-MM-DD|ETM" (last week + this week), latest join (NJ / Rejoin / Resurrection) date,
--        deposit at that join (balance at the end of the join day, at least sd_amount; -1 = no join found),
--        car-at-day-end mask (bit 0 = Monday), drop-off mask (bit = left that day: returned the car, no car at day end)
--   F:J  recovery case id, employee, raised IST date, closed IST date, outcome
--        (Open / Payment = complete with payment_received / Recovered = complete / Cancelled / Failed);
--        cases open at any time since O
--   K:L  employee, exit class by day: 1 vehicle recovered, 2 driver-led reason, 3 other / unclear, 0 none
--   M:O  employee, car-at-day-end flags (1/0), drop-off flags (1/0)
--   P:Q  "ETM|date serial", recorded jama reason (exits since O)
--   R:T  row 2 only: origin date, data-through date (today), refreshed at (IST)
-- =====================================================================================
with cfg as (select date_trunc('week', current_date)::date - 14 as o, current_date as t),
car0 as materialized (
  select s.employee_id as etm, s.allocation_date::date as a, s.jama_date::date as b, s.category, coalesce(s.sd_amount, 0) as sd_amount,
         s.allocation_datetime, s.reason
  from analytics.ssot_alloc_dealloc_full s
  where s.allocation_date::date <= (select t from cfg) and coalesce(s.jama_date::date, date '9999-12-31') >= (select o from cfg) - 35   -- pilots with a car in the last ~7 weeks
),
ids as materialized (select distinct etm from car0),
days as materialized (select g::date as d, (g::date - (select o from cfg)) as k from generate_series((select o from cfg), (select t from cfg), interval '1 day') g),
cday as materialized (   -- car at the end of the day
  select distinct c.etm, x.d
  from car0 c join days x on c.a <= x.d and (c.b is null or c.b > x.d)
),
leftd as materialized (  -- left that day: a car returned that day and no car at the end of that day
  select distinct c.etm, c.b as d, c.reason
  from car0 c
  where c.b between (select o from cfg) and (select t from cfg)
    and not exists (select 1 from cday z where z.etm = c.etm and z.d = c.b)
),
-- recovery cases
fdr as materialized (select f.id as driver_id, f.employee_id as etm from fleet_driver f where f.employee_id is not null),
rc0 as materialized (
  select a.id, f.etm, (a.activation_date)::date as raised, a.recovery_status, a.rec_tags_id, a.payment_received, a.updated_at
  from recovery_cars a join fdr f on f.driver_id = a.driver_id
  where a.activation_date::date <= (select t from cfg)
),
rclose as materialized (
  select distinct on (b.recovery_id) b.recovery_id, (b.datetime at time zone 'Asia/Kolkata')::date as close_d, b.recovery_status
  from recovery_status_logs b
  where b.recovery_status in ('complete','failed','cancelled') and b.recovery_id in (select id from rc0)
  order by b.recovery_id, b.id desc
),
rc as materialized (
  select r.id, r.etm, r.raised,
         case when r.recovery_status in ('complete','failed','cancelled')
              then coalesce(l.close_d, (r.updated_at at time zone 'Asia/Kolkata')::date) end as closed,
         case when r.recovery_status = 'complete' and r.payment_received = 1 then 'Payment'
              when r.recovery_status = 'complete' then 'Recovered'
              when r.recovery_status = 'cancelled' then 'Cancelled'
              when r.recovery_status = 'failed' then 'Failed' else 'Open' end as outcome
  from rc0 r left join rclose l on l.recovery_id = r.id
),
rcw as materialized (select * from rc where closed is null or closed >= (select o from cfg)),
-- exit class per day
rrec as materialized (select distinct etm, closed from rc where outcome = 'Recovered' and closed >= (select o from cfg) - 1),
lcls as materialized (
  select l.etm, l.d,
         case when l.reason ilike '%recovery%' or l.reason ilike 'defaulter%' or l.reason ilike 'forced%'
                   or exists (select 1 from rrec x where x.etm = l.etm and x.closed between l.d - 1 and l.d + 1) then '1'
              when l.reason in ('Going to Village','Personal Issue','Health Issue','Going For Festival','Family/Personal Obligations',
                                'Final Left','Bought his own car','Earning Issue','Hisaab/ Earning Issue','Dont Want To Drive In Uber',
                                'Moving to another business model','Payment Issue') then '2'
              else '3' end as cls
  from leftd l
),
-- per employee day strings
estr as materialized (
  select i.etm,
         'x' || string_agg(case when z.etm is not null then '1' else '0' end, '' order by x.d) as car_flags,
         'x' || string_agg(case when l.etm is not null then '1' else '0' end, '' order by x.d) as left_flags,
         'x' || string_agg(coalesce(lc.cls, '0'), '' order by x.d) as exit_cls
  from ids i cross join days x
  left join cday z on z.etm = i.etm and z.d = x.d
  left join (select distinct etm, d from leftd) l on l.etm = i.etm and l.d = x.d
  left join (select etm, d, min(cls) as cls from lcls group by 1, 2) lc on lc.etm = i.etm and lc.d = x.d
  group by 1
),
-- week records (last week + this week)
wks as (select (select o from cfg) + 7 as wk union all select (select o from cfg) + 14),
dd as materialized (
  select d.employee_id as etm, d.date::date as d, sum(d.amount) as amt
  from mv_deposits_raw d
  where d.deposit_type::text <> all (array['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[]) and d.employee_id in (select etm from ids)
  group by 1, 2
),
joins as materialized (
  select s.employee_id as etm, s.allocation_date::date as jd, max(coalesce(s.sd_amount, 0)) as sd_amount
  from analytics.ssot_alloc_dealloc_full s
  where s.category in ('New Join','Rejoin','Resurrection') and s.employee_id in (select etm from ids) and s.allocation_date::date <= (select t from cfg)
  group by 1, 2
),
wpop as materialized (select w.wk, i.etm from wks w cross join ids i),   -- every pilot of the window, both weeks (no car that week -> masks 0)
wjoin as materialized (
  select p.wk, p.etm, max(j.jd) as jd
  from wpop p join joins j on j.etm = p.etm and j.jd <= least(p.wk + 6, (select t from cfg))
  group by 1, 2
),
wdep as materialized (
  select w.wk, w.etm, sum(x.amt) as bal
  from wjoin w join dd x on x.etm = w.etm and x.d <= w.jd
  group by 1, 2
),
wcar as materialized (
  select p.wk, p.etm, sum(power(2, x.d - p.wk)::int) as car_mask
  from wpop p join cday x on x.etm = p.etm and x.d between p.wk and p.wk + 6
  group by 1, 2
),
wleft as materialized (
  select p.wk, p.etm, sum(power(2, l.d - p.wk)::int) as left_mask
  from wpop p join (select distinct etm, d from leftd) l on l.etm = p.etm and l.d between p.wk and p.wk + 6
  group by 1, 2
),
wrec2 as materialized (
  select p.wk, p.etm, wj.jd,
         case when wj.jd is null then -1 else greatest(coalesce(wd.bal, 0), j.sd_amount) end as dep,
         coalesce(wc.car_mask, 0) as car_mask, coalesce(wl.left_mask, 0) as left_mask
  from wpop p
  left join wjoin wj on wj.wk = p.wk and wj.etm = p.etm
  left join joins j on j.etm = p.etm and j.jd = wj.jd
  left join wdep wd on wd.wk = p.wk and wd.etm = p.etm
  left join wcar wc on wc.wk = p.wk and wc.etm = p.etm
  left join wleft wl on wl.wk = p.wk and wl.etm = p.etm
),
b1 as (select row_number() over (order by wk, etm) as rn, to_char(wk, 'YYYY-MM-DD') || '|' || etm as week_key, jd as latest_join,
              round(dep) as deposit_at_join, car_mask, left_mask from wrec2),
b2 as (select row_number() over (order by id) as rn, id as recovery_id, etm as rc_employee, raised as raised_date, closed as closed_date, outcome from rcw),
b3 as (select row_number() over (order by etm) as rn, etm as ex_employee, exit_cls, etm as fl_employee, car_flags, left_flags from estr),
b4 as (select row_number() over (order by etm, d) as rn, etm || '|' || (d - date '1899-12-30') as exit_key, reason as exit_reason
       from (select distinct on (etm, d) etm, d, reason from leftd order by etm, d, reason) z),
n as (select generate_series(1, greatest((select count(*) from b1), (select count(*) from b2), (select count(*) from b3), (select count(*) from b4))) as rn)
select b1.week_key, b1.latest_join, b1.deposit_at_join, b1.car_mask, b1.left_mask,
       b2.recovery_id, b2.rc_employee, b2.raised_date, b2.closed_date, b2.outcome,
       b3.ex_employee, b3.exit_cls, b3.fl_employee, b3.car_flags, b3.left_flags,
       b4.exit_key, b4.exit_reason,
       case when n.rn = 1 then (select o from cfg) end as origin_date,
       case when n.rn = 1 then (select t from cfg) end as data_through,
       case when n.rn = 1 then to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') end as refreshed_at
from n
left join b1 on b1.rn = n.rn
left join b2 on b2.rn = n.rn
left join b3 on b3.rn = n.rn
left join b4 on b4.rn = n.rn
order by n.rn
