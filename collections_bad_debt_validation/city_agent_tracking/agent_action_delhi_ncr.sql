-- [Delhi NCR Collections] Agent Tracking > Agent_Action (India Collections Raw_Data logic, last 5 hisaab weeks, latest week on top)
-- Automation: start A1, clear BP (68 columns A:BP). Hourly is fine (no agent input columns in this tab).
-- hawkeye_username = this sheet's agent per week (mv_collections_calling_masterlist snapshot); ameyo_username = Ameyo id that
-- most often called that agent's pilots (last 28 days). 'NA' when not known.
with wk as (
  select generate_series((date_trunc('week', current_date) - interval '28 days')::timestamp,
                         date_trunc('week', current_date)::timestamp, interval '7 days')::date as hw
),
lim as materialized (select min(hw) as w0, max(hw) as w1 from wk),
m as materialized (
  select *
  from analytics.collections_bad_debt_mv
  where for_collections = 1
    and hissab_week between (select w0 from lim) - 14 and (select w1 from lim)
    and city = 'Delhi NCR'
),
rec as materialized (
  select employee_id, date_trunc('week', date)::date as hw,
         coalesce(sum(amount) filter (where recovery_type::text = 'razorpay_recovery'), 0)       as razorpay_amt,
         coalesce(sum(amount) filter (where recovery_type::text = 'other_positive_recovery'), 0) as other_amt,
         coalesce(sum(amount) filter (where recovery_type::text = 'phonepe_recovery'), 0)        as phonepe_amt,
         coalesce(sum(amount) filter (where recovery_type::text = 'positive_adjustment'), 0)     as adjustment_amt,
         coalesce(sum(amount) filter (where recovery_type::text = 'deposit_to_os'), 0)           as dp_to_os_amt,
         coalesce(sum(amount) filter (where date < date_trunc('week', date) + interval '3 day'), 0) as mon_wed_amt,
         coalesce(sum(amount), 0)                                                                as total_amt
  from mv_daily_recovery
  where date >= (select w0 from lim) - 14 and date < (select w1 from lim) + 7
    and recovery_type::text in ('razorpay_recovery', 'other_positive_recovery', 'phonepe_recovery',
                                'positive_adjustment', 'deposit_to_os')
  group by 1, 2
),
b as materialized (
  select m.*,
         case when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV_Leasing'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.revenue_type end as rev_type,
         case when m.product_type = 'EV' and m.revenue_type = 'D2O' and m.eip_tag = 1 then 'EV'
              when m.product_type = 'EV' and m.revenue_type = 'D2O' then 'EV_D2O' else m.product_type end as prod_type,
         coalesce(m.total_os, 0)                                   as e_os,
         coalesce(r.total_amt, 0)                                  as i_tot,
         coalesce(r.razorpay_amt, 0) as j_rz, coalesce(r.other_amt, 0) as k_ot, coalesce(r.phonepe_amt, 0) as l_pp,
         coalesce(r.adjustment_amt, 0) as m_ad, coalesce(r.dp_to_os_amt, 0) as n_dp,
         least(coalesce(r.mon_wed_amt, 0), abs(coalesce(m.total_os, 0)))  as o_wed,
         least(coalesce(r.total_amt, 0), abs(coalesce(m.total_os, 0)))    as u_sun,
         case when coalesce(m.total_os, 0) + coalesce(r.total_amt, 0) < 0
              then coalesce(m.total_os, 0) + coalesce(r.total_amt, 0) else 0 end as ap_cf
  from m
  left join rec r on r.employee_id = m.partner_etm and r.hw = m.hissab_week
),
b2 as materialized (
  select b.*,
         case when b.e_os <> 0 then b.u_sun / abs(b.e_os) end as v_pct,
         coalesce(sum(b.ap_cf) over (partition by b.partner_etm order by b.hissab_week
                                     range between interval '7 days' preceding and interval '7 days' preceding), 0) as aq_prev_cf,
         count(*) filter (where b.i_tot = 0) over (partition by b.partner_etm order by b.hissab_week
                                     range between interval '14 days' preceding and interval '1 day' preceding) as aa_np2,
         max(b.week_start_deposit) over (partition by b.partner_etm order by b.hissab_week
                                     range between interval '7 days' preceding and interval '7 days' preceding) as bb_prev
  from b
),
b3 as materialized (
  select b2.*,
         count(*) filter (where b2.v_pct > 0 and b2.v_pct < 0.8) over (partition by b2.partner_etm order by b2.hissab_week
                                     range between interval '14 days' preceding and interval '1 day' preceding) as bq_lt80
  from b2
),
o as materialized (
  select b3.*,
         count(*) over (partition by b3.partner_etm order by b3.hissab_week rows unbounded preceding) as am_rank,
         case when b3.hissab_week < date_trunc('week', current_date)::date then b3.bad_debt_amount end as bd_amt
  from b3
  where b3.hissab_week >= (select w0 from lim)
),
al as materialized (
  select o.hissab_week, o.partner_etm,
         string_agg(distinct s.car_number, ',') as cars,
         (array_agg(s.location order by s.allocation_datetime desc))[1] as alloc_hub,
         bool_or(s.allocation_date <= least(o.hissab_week + 6, current_date)
                 and coalesce(s.jama_date, current_date) >= least(o.hissab_week + 6, current_date)) as on_sunday
  from o
  join analytics.ssot_alloc_dealloc_base s
    on s.employee_id = o.partner_etm and s.allocation_date <= o.hissab_week + 6
   and coalesce(s.jama_date, current_date) >= o.hissab_week
  group by 1, 2
),
elc as materialized (
  select employee_id,
         (array_agg(source_channel order by uploading_date desc) filter (where coalesce(source_channel, '') <> ''))[1] as source_channel,
         (array_agg(uber_tag order by uploading_date desc) filter (where coalesce(uber_tag, '') <> ''))[1] as uber_tag
  from mv_elc_upload_data
  where employee_id in (select partner_etm from o)
  group by 1
),
fdr as materialized (select id, employee_id from fleet_driver where employee_id in (select partner_etm from o)),
fa as materialized (select dp.driver_id, min(dp.start_date)::date as first_alloc from driver_profile dp
                    where dp.driver_id in (select id from fdr) group by 1),
ftd as materialized (select u.driver_id, min(u.date)::date as first_trip from mv_uber_ftd u
                     where u.driver_id in (select id from fdr) group by 1),
utag as materialized (
  select fdr.employee_id,
         case when ftd.first_trip < fa.first_alloc then 'Old In Uber' else 'New In Uber' end as tag
  from fdr left join fa on fa.driver_id = fdr.id left join ftd on ftd.driver_id = fdr.id
),
nt as materialized (select et_id as employee_id,
                           case when min(first_ever_trip_date)::date < min(first_allocation_date) then 'Old In Uber' else 'New In Uber' end as tag
                    from public.new_to_uber where et_id in (select partner_etm from o) group by 1),
chn as materialized (select employee_id, max(main_source) as src from analytics.ssot_alloc_dealloc_full
                     where main_source <> '' and employee_id in (select partner_etm from o) group by 1),
cl as materialized (
  select partner_et_id, week_start, sum(attempt_count) as attempts, sum(connect_count) as connects
  from public.collections_calling_data_raw
  where week_start in (select hw from wk) and partner_et_id in (select partner_etm from o)
  group by 1, 2
),
ml as materialized (
  select distinct on (week, partner_et_id) week, partner_et_id, elc_filter, current_week_gps_kms, current_week_uber_kms
  from mv_collections_calling_masterlist
  where week in (select hw from wk) and partner_et_id in (select partner_etm from o)
  order by week, partner_et_id, snapshot_date desc
),
fw as materialized (
  select o.hissab_week, o.partner_etm,
         bool_or(s.allocation_date <= o.hissab_week
                 and (s.jama_date is null or s.jama_date >= current_date or s.jama_date > o.hissab_week + 6)) as full_week
  from o
  join analytics.ssot_alloc_dealloc_base s
    on s.employee_id = o.partner_etm and s.allocation_date <= o.hissab_week + 6
   and coalesce(s.jama_date, current_date) >= o.hissab_week
  group by 1, 2
),
rcase as materialized (
  select a.activation_date::date as start_date,
         case when a.rec_tags_id in (111, 112, 113)
              then coalesce(ls.close_date, a.updated_at at time zone 'Asia/Kolkata')::date end as close_date,
         coalesce(fd.employee_id, fd2.employee_id) as employee_id
  from recovery_cars a
  left join lateral (
    select b.datetime as close_date from recovery_status_logs b
    where b.recovery_id = a.id and b.recovery_status in ('complete', 'failed', 'cancelled')
    order by b.id desc limit 1
  ) ls on true
  left join fleet_driver fd on fd.id = a.driver_id
  left join lateral (
    select ca.driver_id from car_allocation ca
    where ca.deactivation_date is null and ca.driver_id is not null
      and ca.car_id = a.car_id and ca.allocation_date <= a.activation_date
    order by ca.id desc limit 1
  ) al2 on a.driver_id is null
  left join fleet_driver fd2 on fd2.id = al2.driver_id
  where a.activation_date < (select w1 from lim) + 7
    and (coalesce(a.rec_tags_id, 0) not in (111, 112, 113) or coalesce(ls.close_date, a.updated_at) >= (select w0 from lim))
),
rcp as materialized (
  select distinct on (c.employee_id, w.hw) c.employee_id, w.hw, c.start_date,
         coalesce(c.close_date, greatest(current_date, w.hw + 7)) as end_date
  from rcase c
  join wk w on c.start_date <= w.hw + 6 and coalesce(c.close_date, current_date) >= w.hw
  order by c.employee_id, w.hw, c.start_date desc
),
f as materialized (
  select o.*,
         abs(o.e_os) as abs_os,
         least(o.j_rz, abs(o.e_os))                                                               as p_rz,
         greatest(0, least(o.k_ot, abs(o.e_os) - o.j_rz))                                         as q_ot,
         greatest(0, least(o.l_pp, abs(o.e_os) - o.j_rz - o.k_ot))                                as r_pp,
         greatest(0, least(o.m_ad, abs(o.e_os) - o.j_rz - o.k_ot - o.l_pp))                       as s_ad,
         greatest(0, least(o.n_dp, abs(o.e_os) - o.j_rz - o.k_ot - o.l_pp - o.m_ad))              as t_dp,
         o.u_sun - abs(o.e_os)                                                                    as av_net,
         case when o.e_os = 0 then 'Excellent'
              when o.o_wed / abs(o.e_os) >= 1 then 'Very Good'
              when o.i_tot / abs(o.e_os) >= 1 then 'Good'
              when o.i_tot / abs(o.e_os) >= 0.75 then 'Average'
              else 'Defaulter' end                                                                as af_habit,
         least(abs(o.i_tot), abs(o.aq_prev_cf))                                                   as as_prev_rec
  from o
),
-- calls per day of the hisaab week (Mon..Sun) + last 3 dispositions of the week
cd as materialized (
  select c.partner_et_id as etm, c.week_start as wk, (c.date - c.week_start) as dn,
         sum(c.attempt_count) as att, sum(c.connect_count) as conn,
         max(c.last_attempt_time) as la, max(c.last_connect_time) as lc
  from public.collections_calling_data_raw c
  where c.week_start in (select hw from wk) and c.partner_et_id in (select partner_etm from o)
  group by 1, 2, 3
),
cdw as materialized (
  select etm, wk,
    coalesce(sum(att) filter (where dn = 0), 0) a1, coalesce(sum(att) filter (where dn = 1), 0) a2, coalesce(sum(att) filter (where dn = 2), 0) a3,
    coalesce(sum(att) filter (where dn = 3), 0) a4, coalesce(sum(att) filter (where dn = 4), 0) a5, coalesce(sum(att) filter (where dn = 5), 0) a6,
    coalesce(sum(att) filter (where dn = 6), 0) a7, coalesce(sum(att), 0) at,
    coalesce(sum(conn) filter (where dn = 0), 0) c1, coalesce(sum(conn) filter (where dn = 1), 0) c2, coalesce(sum(conn) filter (where dn = 2), 0) c3,
    coalesce(sum(conn) filter (where dn = 3), 0) c4, coalesce(sum(conn) filter (where dn = 4), 0) c5, coalesce(sum(conn) filter (where dn = 5), 0) c6,
    coalesce(sum(conn) filter (where dn = 6), 0) c7, coalesce(sum(conn), 0) ct,
    coalesce(sum(att) filter (where dn <= 1), 0) att_tue, coalesce(sum(att) filter (where dn <= 2), 0) att_wed,
    coalesce(sum(conn) filter (where dn <= 1), 0) conn_tue, coalesce(sum(conn) filter (where dn <= 2), 0) conn_wed,
    max(la) as la, max(lc) as lc
  from cd group by 1, 2
),
dsp as materialized (
  select distinct on (c.partner_et_id, c.week_start) c.partner_et_id as etm, c.week_start as wk,
         c.third_last_subdisposition, c.second_last_subdisposition, c.last_subdisposition
  from public.collections_calling_data_raw c
  where c.week_start in (select hw from wk) and coalesce(c.attempt_count, 0) > 0 and c.partner_et_id in (select partner_etm from o)
  order by c.partner_et_id, c.week_start, c.last_attempt_time desc nulls last, c.id desc
),
-- assigned agent per week = this sheet's own Calling_Masterlist snapshot (mv_collections_calling_masterlist, 23:00 daily)
agw as materialized (
  select distinct on (s.week, s.partner_et_id) s.week as wk, s.partner_et_id as etm, s.agent_username as hk
  from public.mv_collections_calling_masterlist s
  where s.week in (select hw from wk) and coalesce(s.agent_username, '') not in ('', '-', 'NA', 'NaN')
  order by s.week, s.partner_et_id, s.date desc, s.loaded_at desc
),
-- Hawkeye -> Ameyo id: the Ameyo agent_id that most often called this Hawkeye agent's pilots (last 28 days)
amap as materialized (
  select distinct on (hk) hk, ameyo
  from (select s.agent_username as hk, c.agent_id as ameyo, count(*) as n
        from public.mv_collections_calling_masterlist s
        join public.collections_calling_data_raw c on c.partner_et_id = s.partner_et_id and c.date = s.date
        where s.date >= current_date - 28 and s.city = 'Delhi NCR' and c.week_start >= date_trunc('week', current_date)::date - 28
          and coalesce(s.agent_username, '') not in ('', '-', 'NA', 'NaN') and coalesce(c.agent_id, '') <> ''
        group by 1, 2) x
  order by hk, n desc
)
select
  f.hissab_week as "hisaab_week",
  f.partner_etm as "partner_et_id",
  f.lead_id as "lead_id",
  f.city as "city",
  f.location as "location",
  f.prod_type as "product_type",
  coalesce(ml.elc_filter, 'Non_ELC') as "elc_filter",
  f.e_os as "negative_os",
  f.i_tot as "total_recovery",
  f.j_rz as "razorpay_recovery",
  f.k_ot as "other_recovery",
  f.l_pp as "phonepe_recovery",
  f.m_ad as "adjustments",
  f.n_dp as "dp_to_os",
  f.o_wed as "till_wed_100pct",
  f.p_rz as "razorpay_recovery_100pct",
  f.q_ot as "other_recovery_100pct",
  f.r_pp as "phonepe_100pct",
  f.s_ad as "adjustments_100pct",
  f.t_dp as "dp_to_os_100pct",
  f.u_sun as "till_sun_100pct",
  coalesce(f.week_end_deposit, 0) as "week_end_deposit",
  case when fw.full_week then 1 else 0 end as "entire_week_active",
  case when al.partner_etm is not null then 'Active' else 'Inactive' end as "1d_active",
  case when f.e_os < 0 and coalesce(f.week_end_deposit, 0) = 0 then 1
       when coalesce(f.week_end_deposit, 0) <> 0 then abs(f.e_os) / f.week_end_deposit end as "os_gt_deposit_pct",
  f.af_habit as "payment_habit",
  coalesce(f.current_week_nd_count, 0) as "not_driven_count",
  case when f.av_net >= 0 then 'No' when abs(f.av_net) > coalesce(f.week_end_deposit, 0) then 'Yes' else 'No' end as "recovery_recommended_vehicle",
  case when f.active_inactive_flag = 'Active' and ml.current_week_gps_kms = 0 and coalesce(ml.current_week_uber_kms, 0) = 0 then 1 else 0 end as "gps_inactive",
  case (f.aa_np2 >= 1)::int
       + (case when f.av_net >= 0 then false else abs(f.av_net) > coalesce(f.week_end_deposit, 0) end)::int
       + (f.af_habit = 'Defaulter')::int
       + (coalesce(f.current_week_nd_count, 0) > 2)::int
       + coalesce(f.active_inactive_flag = 'Active' and ml.current_week_gps_kms = 0 and coalesce(ml.current_week_uber_kms, 0) = 0, false)::int
       + (coalesce(cl.connects, 0) <= 0)::int
    when 6 then 'Critical Risk' when 5 then 'High Risk' when 4 then 'Moderate Risk'
    when 3 then 'Low Risk' when 2 then 'Minimal Risk' else 'No risk' end as "asset_risk",
  case when f.e_os < 0 then f.v_pct else 1 end as "recovery_pct",
  coalesce(f.bd_amt, 0) as "bad_debt",
  null::text as "bad_debt",
  case when f.bd_amt < 0 then least(coalesce(f.bad_debt_collected, 0), abs(f.bd_amt)) else 0 end as "bad_debt_rec_100pct",
  coalesce(case when f.bd_amt < 0 then least(coalesce(f.bad_debt_collected, 0), abs(f.bd_amt)) else 0 end, 0) + coalesce(f.bd_amt, 0) as "net_bad_debt",
  f.ap_cf as "carry_forward_os",
  f.last_payment_date_till_hissab_week as "last_paid_date",
  f.last_jama_date as "last_jama_date",
  al.cars as "last_car_number",
  case when al.on_sunday then 'active' else 'inactive' end as "active_today?",
  coalesce(ag.hk, 'NA') as "hawkeye_username",
  coalesce(am.ameyo, 'NA') as "ameyo_username",
  coalesce(w.a1, 0) as "att_Mon", coalesce(w.a2, 0) as "att_Tue", coalesce(w.a3, 0) as "att_Wed", coalesce(w.a4, 0) as "att_Thu",
  coalesce(w.a5, 0) as "att_Fri", coalesce(w.a6, 0) as "att_Sat", coalesce(w.a7, 0) as "att_Sun", coalesce(w.at, 0) as "att_total",
  coalesce(w.c1, 0) as "conn_Mon", coalesce(w.c2, 0) as "conn_Tue", coalesce(w.c3, 0) as "conn_Wed", coalesce(w.c4, 0) as "conn_Thu",
  coalesce(w.c5, 0) as "conn_Fri", coalesce(w.c6, 0) as "conn_Sat", coalesce(w.c7, 0) as "conn_Sun", coalesce(w.ct, 0) as "conn_total",
  coalesce(w.att_tue, 0) as "att_till_tue", coalesce(w.att_wed, 0) as "att_till_wed",
  coalesce(w.conn_tue, 0) as "conn_till_tue", coalesce(w.conn_wed, 0) as "conn_till_wed",
  w.la as "last_attempt_time",
  w.lc as "last_connect_time",
  d.third_last_subdisposition as "third_last_subdisposition",
  d.second_last_subdisposition as "second_last_subdisposition",
  d.last_subdisposition as "last_subdisposition",
  to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') as "last_updated"
from f
left join al  on al.partner_etm  = f.partner_etm and al.hissab_week  = f.hissab_week
left join cl  on cl.partner_et_id = f.partner_etm and cl.week_start  = f.hissab_week
left join ml  on ml.partner_et_id = f.partner_etm and ml.week        = f.hissab_week
left join fw  on fw.partner_etm  = f.partner_etm and fw.hissab_week  = f.hissab_week
left join cdw w on w.etm = f.partner_etm and w.wk = f.hissab_week
left join dsp d on d.etm = f.partner_etm and d.wk = f.hissab_week
left join agw ag on ag.etm = f.partner_etm and ag.wk = f.hissab_week
left join amap am on am.hk = ag.hk
where f.city = 'Delhi NCR'
order by f.hissab_week desc,
  case (f.aa_np2 >= 1)::int
       + (case when f.av_net >= 0 then false else abs(f.av_net) > coalesce(f.week_end_deposit, 0) end)::int
       + (f.af_habit = 'Defaulter')::int
       + (coalesce(f.current_week_nd_count, 0) > 2)::int
       + coalesce(f.active_inactive_flag = 'Active' and ml.current_week_gps_kms = 0 and coalesce(ml.current_week_uber_kms, 0) = 0, false)::int
       + (coalesce(cl.connects, 0) <= 0)::int when 6 then 1 when 5 then 2 when 4 then 3 when 3 then 4 when 2 then 5 else 6 end,
  f.e_os, f.partner_etm
