with cfg as (
 select date_trunc('week', current_date)::date - 49 as w0
),
jn0 as materialized (
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
dep_tot as materialized (
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
zj as materialized (
 select j.etm, j.jd, j.jtype, j.city, j.product, j.dep_at_join,
 least(coalesce(j.next_jd - 1, current_date), current_date) as last_d
 from jn j where j.dep_at_join <= 0
),
grid as materialized (
 select z.etm, z.jd, z.jtype, z.city, z.product, z.dep_at_join, g.dd::date as d
 from zj z cross join lateral generate_series(z.jd, z.last_d, interval '1 day') g(dd)
),
zids as materialized (select distinct etm from zj),
fdr as materialized (select f.id as driver_id, f.employee_id as etm from fleet_driver f where f.employee_id in (select etm from zids)),
lod as materialized (
 select distinct on (f.etm, h.date::date) f.etm, h.date::date as d, h.live_os, h.total_rent, h.is_active
 from hissab_driver_live_os h join fdr f on f.driver_id = h.driver_id
 where h.date >= (select w0 from cfg) - 7 and h.date <= current_date + 1
 order by f.etm, h.date::date, h.is_active desc, h.driver_id desc
),
mdr as materialized (
 select r.employee_id as etm, r.date::date as d,
 sum(r.amount) filter (where r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery')) as paid,
 sum(r.amount) filter (where r.recovery_type in ('positive_adjustment','deposit_to_os')) as adj
 from mv_daily_recovery r
 where r.date >= date '2026-09-01' and r.date >= (select w0 from cfg) and r.date <= current_date
 and r.recovery_type in ('razorpay_recovery','other_positive_recovery','phonepe_recovery','positive_adjustment','deposit_to_os')
 and r.employee_id in (select etm from zids)
 group by 1, 2
),
car as materialized (
 select s.employee_id as etm, s.allocation_date::date as a, coalesce(s.jama_date::date, current_date) as b
 from analytics.ssot_alloc_dealloc_full s
 where s.employee_id in (select etm from zids) and coalesce(s.jama_date, current_date) >= (select w0 from cfg)
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
 where c.week_start >= (select w0 from cfg) and c.partner_et_id in (select etm from zids)
 group by 1, 2
),
drv as materialized (
 select distinct on (f.employee_id) f.employee_id as etm, f.name
 from fleet_driver f where f.employee_id in (select etm from ids)
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
 select distinct g.etm, g.d
 from grid g join car c on c.etm = g.etm and c.a <= g.d and c.b >= g.d
),
g_rc as materialized (
 select g.etm, g.d,
 max(case when r.close_d is null or r.close_d > g.d then 1 else 0 end) as in_rc,
 max(case when r.start_d = g.d then 1 else 0 end) as rc_new,
 max(case when r.close_d = g.d then 1 else 0 end) as rc_closed,
 max(case when r.close_d = g.d and r.recovered = 1 then 1 else 0 end) as rc_recovered
 from grid g join rcase r on r.etm = g.etm and r.start_d <= g.d and (r.close_d is null or r.close_d >= g.d)
 group by 1, 2
),
pday as materialized (
 select g.*,
 coalesce(t.dep_now, 0) - coalesce(ga.amt, 0) as dep_asof,
 l.live_os, case when l.etm is not null then 1 else 0 end as active,
 n.total_rent as rent_d,
 ll.last_lo,
 case when gc.etm is not null then 1 else 0 end as car_flag,
 coalesce(m.paid, 0) as paid, coalesce(m.adj, 0) as adj,
 coalesce(cl.att, 0) as att, coalesce(cl.conn, 0) as conn,
 coalesce(r.in_rc, 0) as in_rc, coalesce(r.rc_new, 0) as rc_new, coalesce(r.rc_closed, 0) as rc_closed, coalesce(r.rc_recovered, 0) as rc_recovered
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
 select p.*, greatest(p.dep_asof, 0) as dp,
 case when p.active = 1 and p.live_os < 0 and -p.live_os >= greatest(p.dep_asof, 0) then 1 else 0 end as bd_a,
 case when p.active = 0 and p.car_flag = 0 and coalesce(p.last_lo, 0) + greatest(p.dep_asof, 0) < 0 then 1 else 0 end as bd_l
 from pday p
),
out as (
 select 'JOIN' as row_type, j.jd as d, j.etm, j.city, j.product, j.jd, j.jtype, j.dep_at_join,
 null::numeric as dep_asof, null::int as active, null::int as has_car, null::numeric as live_os, null::numeric as rent_d,
 null::numeric as paid, null::numeric as adj, null::int as bd_a, null::numeric as bd_a_amt, null::int as bd_l, null::numeric as bd_l_amt,
 null::int as in_rc, null::int as rc_new, null::int as rc_closed, null::int as rc_recovered, null::numeric as att, null::numeric as conn
 from jn j
 union all
 select 'DAY', p.d, p.etm, p.city, p.product, p.jd, p.jtype, p.dep_at_join,
 p.dep_asof, p.active, greatest(p.car_flag, p.active), p.live_os, p.rent_d, p.paid, p.adj,
 p.bd_a, case when p.bd_a = 1 then -p.live_os - p.dp else 0 end,
 p.bd_l, case when p.bd_l = 1 then -(p.last_lo + p.dp) else 0 end,
 p.in_rc, p.rc_new, p.rc_closed, p.rc_recovered, p.att, p.conn
 from pday2 p
)
select
 o.row_type as "Row Type",
 o.d as "Date",
 date_trunc('week', o.d)::date as "Week (Mon)",
 o.city as "City",
 o.product as "Product",
 o.etm as "Employee ID",
 dr.name as "Pilot Name",
 o.jd as "Join Date",
 o.jtype as "Join Type",
 date_trunc('week', o.jd)::date as "Join Week",
 round(o.dep_at_join) as "Deposit at Join (Rs)",
 case when o.dep_at_join <= 0 then 'Yes' else 'No' end as "Joined at 0 Deposit",
 o.d - o.jd as "Days Since Join",
 o.active as "Active (Live OS)",
 o.has_car as "Has Car",
 round(o.dep_asof) as "Deposit That Day (Rs)",
 case when o.row_type = 'JOIN' then null when o.dep_asof <= 0 then '0 Deposit' when o.dep_asof <= 3000 then '1-3K'
 when o.dep_asof <= 5000 then '3-5K' else '5K+' end as "Deposit Bucket That Day",
 round(o.live_os) as "Live OS (Rs)",
 round(o.rent_d) as "Rent for Day (Rs)",
 round(o.paid) as "Paid That Day (Rs)",
 round(o.adj) as "Adjustment + DP to OS (Rs)",
 o.bd_a as "Active Bad Debt",
 round(o.bd_a_amt) as "Active Bad Debt (Rs)",
 o.bd_l as "Left Bad Debt",
 round(o.bd_l_amt) as "Left Bad Debt (Rs)",
 o.in_rc as "In Car Recovery",
 o.rc_new as "Recovery Raised",
 o.rc_closed as "Recovery Closed",
 o.rc_recovered as "Car Recovered",
 o.att as "Calls Attempted",
 o.conn as "Calls Connected",
 to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') as "Data Refreshed At"
from out o
left join drv dr on dr.etm = o.etm
order by o.row_type desc, o.d, o.city, o.etm
