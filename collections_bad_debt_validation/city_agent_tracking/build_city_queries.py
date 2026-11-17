"""Builds the SQL for the 7 city Agent Tracking sheets (2 tabs each).
  calling_masterlist_<city>.sql  -> tab Calling_Masterlist, A2, 64 data columns (A:BL). Agent capture columns BM:BX are NOT written.
  agent_action_<city>.sql        -> tab Agent_Action, A1, 68 columns (A:BP), last 5 hisaab weeks (latest on top).
Sources: ../zero_deposit_dash/agent_action_masterlist.sql (MasterTab logic, fast version) and
         ../dashboard_pg/raw_data_v3 logic (India Collections Raw_Data) from the automation copy.
"""
import re, pathlib
HERE = pathlib.Path(__file__).parent
CITIES = ['Bangalore', 'Chennai', 'Delhi NCR', 'Hyderabad', 'Kolkata', 'Mumbai', 'Pune']
slug = lambda c: c.lower().replace(' ', '_')

# ---------------- Calling_Masterlist ----------------
aa = (HERE / '../zero_deposit_dash/agent_action_masterlist.sql').read_text()
cte_part = aa[aa.index('with cfg'):aa.index('\nselect\n', aa.index('b4 as materialized'))]
extra = """,
-- agent + actioning type as the city sheet had them (daily 23:00 snapshot of the city Calling_Masterlist, last 14 days)
agm as materialized (
  select distinct on (partner_et_id) partner_et_id as etm, agent_username
  from public.mv_collections_calling_masterlist
  where date >= current_date - 14 and coalesce(agent_username, '') not in ('', '-', 'NA', 'NaN')
  order by partner_et_id, date desc, loaded_at desc
),
aga as materialized (
  select distinct on (partner_et_id) partner_et_id as etm, actioning_type
  from public.mv_collections_calling_masterlist
  where date >= current_date - 14 and coalesce(actioning_type, '') not in ('', '-', 'NA', 'NaN')
  order by partner_et_id, date desc, loaded_at desc
)"""
cm_select = """
select
  b.wk as "week",
  to_char(now() at time zone 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') as "date",
  coalesce(g.agent_username, '') as "agent_username",
  b.etm as "partner_et_id",
  b.lead_id as "lead_id",
  b.name as "partner_name",
  b.city as "city",
  b.product as "product_type",
  case when b.tenure is null then 'Unknown' when b.tenure < 30 then 'ELC' else 'Non_ELC' end as "elc_filter",
  b.car_numbers as "car_numbers",
  case when abs(b.neg_os) <= 500 then '0-500' when abs(b.neg_os) <= 1000 then '500-1K' when abs(b.neg_os) <= 2000 then '1-2K'
       when abs(b.neg_os) <= 3000 then '2-3K' when abs(b.neg_os) <= 5000 then '3-5K' when abs(b.neg_os) <= 10000 then '5-10K'
       when abs(b.neg_os) <= 15000 then '10-15K' when abs(b.neg_os) <= 20000 then '15-20K' when abs(b.neg_os) <= 25000 then '20-25K'
       when abs(b.neg_os) <= 30000 then '25-30K' else '30K+' end as "OS_Bucket",
  case when b.dep <= 3000 then '0-3K' when b.dep <= 5000 then '3-5K' when b.dep <= 10000 then '5-10K' when b.dep <= 15000 then '10-15K'
       when b.dep <= 20000 then '15-20K' when b.dep <= 25000 then '20-25K' when b.dep <= 30000 then '25-30K' when b.dep <= 50000 then '30-50K'
       else '50K+' end as "DP_Bucket",
  b.neg_os as "negative_os",
  b.tot_rec as "total_recovery",
  b.net_os as "net_os",
  round(b.rec_pct, 4) as "recovery_pct",
  b.rz as "razorpay_recovery",
  b.oth as "other_recovery",
  b.pp as "phonepe_recovery",
  b.adj as "adjustments",
  b.dpo as "dp_to_os",
  b.dep as "current_deposit",
  case when b.is_active then 'Active' else 'Inactive' end as "active / inactive",
  b.habit as "last_payment_habit",
  b.lw_os as "Last Week OS",
  coalesce(b.car_count, 0) as "Car Count",
  coalesce(b.rented_days, 0) as "Current Week Rented Days",
  -abs(coalesce(b.rent_cw, 0)) as "Current Week Lease Rent",
  coalesce(b.fare, 0) as "Current Week fare_total (Inc. Tip & Toll)",
  coalesce(b.cash, 0) as "Current Week Cash Collected",
  coalesce(b.subs, 0) as "Current Week subscription_charges",
  b.cur_os as "Total Current OS",
  b.cur_os + b.dep as "Current OS Surpass SD",
  case when b.rc_open then 'Yes' else 'No' end as "Is_in Car Recovery",
  case when b.risk_now then 'Critical_Risk' else '' end as "Risk_Type",
  coalesce(b.lw_active, 0) as "last_week_active_days",
  coalesce(b.lw_nd, 0) as "last_week_nd_days",
  coalesce(b.cw_active, 0) as "current_week_active_days",
  coalesce(b.cw_nd, 0) as "current_week_nd_days",
  coalesce(b.gps, 0) as "current_week_gps_kms",
  coalesce(b.uber_km, 0) as "current_week_uber_kms",
  coalesce(b.dead_km, 0) as "current_week_dead_kms",
  coalesce(b.trips_cw, 0) as "current_week_uber_trips",
  b.last_paid as "last_paid_date",
  b.last_jama_4w as "last_jama_date",
  coalesce(b.att, 0) as "att_total",
  coalesce(b.conn, 0) as "conn_total",
  b.last_att as "last_attempt_time",
  b.last_conn as "last_connect_time",
  b.last_dispo as "last_disposition",
  coalesce(b.att_td, 0) as "att_today",
  coalesce(b.conn_td, 0) as "conn_today",
  case when b.product in ('D2O','SINGLE','Own Now') then case when coalesce(b.gps_yd, 0) > 0 then 'GPS>0' else 'GPS=0' end else '-' end as "GPS_Tag",
  case when b.product = 'D2O' and b.is_newjoin then 'New Join + Resurrection (>= 17 Aug)' else '' end as "allocation_type",
  coalesce(a2.actioning_type, '') as "actioning_type",
  case when coalesce(b.disp, 0) > 0 then round(b.acc::numeric / b.disp, 4)::text else '-' end as "acceptance_rate",
  coalesce(b.trip_tier, '') as "trip_tier",
  b.target_trips as "target_trips",
  case when b.product in ('D2O','SINGLE','Own Now') then greatest(coalesce(b.target_trips, 0) - coalesce(b.trips_cw, 0), 0)::text else '-' end as "min_remaining_trips",
  case when not b.in_list then '' when b.rec_pct >= 1 or abs(b.neg_os) - b.tot_rec < 100 then 'Full Paid'
       when b.rec_pct > 0 then 'Partial Paid' else 'Not Paid' end as "Collections Tag",
  case when b.risk_am then case when b.risk_now then 'Critical_Risk' else 'Out of Critical' end else '' end as "Critical Risk Tag",
  case when b.is_active and coalesce(b.alloc_yd, false) and coalesce(b.trips_yd, 0) = 0 then 'ND' else '' end as "ND Tag",
  row_number() over (order by b.product, b.neg_os, b.etm) as "RANK",
  coalesce(nullif(b.remarks, ''), '-') as "Yesterday Remarks"
from b4 b
left join agm g on g.etm = b.etm
left join aga a2 on a2.etm = b.etm
where b.city = '{city}'
  and (select 1 / (count(*) / 5000) from live) is not null   -- guard: fail instead of writing wrong OS when live OS table is mid-sync
order by b.product, b.neg_os, b.etm
"""
cm_head = """-- [{city} Collections] Agent Tracking > Calling_Masterlist (daily calling list, MasterTab logic, current hisaab week)
-- Automation: start A3 (automation writes NO header when start is not A1; keep the header in row 2), clear BX (clears A3:BX incl. yesterday's agent captures, which the 23:00 snapshot already saved), writes A:BL = 64 data columns
-- Run ONCE in the morning (e.g. 7:15 AM) - an hourly refresh would re-order rows under the agents' captures.
-- agent_username / actioning_type = latest value in mv_collections_calling_masterlist (23:00 snapshot of this sheet, last 14 days).
"""

# ---------------- Agent_Action ----------------
raw = (HERE / '_base_raw_data_v3.sql').read_text().rstrip().rstrip(';')
raw = raw.replace("(date_trunc('week', current_date) - interval '56 days')::timestamp", "(date_trunc('week', current_date) - interval '28 days')::timestamp", 1)
assert "interval '28 days'" in raw
rcte = raw[:raw.index('\nselect\n  f.hissab_week')]
# city filter on the MV base table (plain column filter, table stats -> same plan shape, ~7x less work)
_m = "  where for_collections = 1\n    and hissab_week between (select w0 from lim) - 14 and (select w1 from lim)"
assert rcte.count(_m) == 1
rcte = rcte.replace(_m, _m + "\n    and city = '{city}'")
aa_extra = """,
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
        where s.date >= current_date - 28 and s.city = '{city}' and c.week_start >= date_trunc('week', current_date)::date - 28
          and coalesce(s.agent_username, '') not in ('', '-', 'NA', 'NaN') and coalesce(c.agent_id, '') <> ''
        group by 1, 2) x
  order by hk, n desc
)"""
aa_select = """
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
where f.city = '{city}'
order by f.hissab_week desc,
  case (f.aa_np2 >= 1)::int
       + (case when f.av_net >= 0 then false else abs(f.av_net) > coalesce(f.week_end_deposit, 0) end)::int
       + (f.af_habit = 'Defaulter')::int
       + (coalesce(f.current_week_nd_count, 0) > 2)::int
       + coalesce(f.active_inactive_flag = 'Active' and ml.current_week_gps_kms = 0 and coalesce(ml.current_week_uber_kms, 0) = 0, false)::int
       + (coalesce(cl.connects, 0) <= 0)::int when 6 then 1 when 5 then 2 when 4 then 3 when 3 then 4 when 2 then 5 else 6 end,
  f.e_os, f.partner_etm
"""
aa_head = """-- [{city} Collections] Agent Tracking > Agent_Action (India Collections Raw_Data logic, last 5 hisaab weeks, latest week on top)
-- Automation: start A1, clear BP (68 columns A:BP). Hourly is fine (no agent input columns in this tab).
-- hawkeye_username = this sheet's agent per week (mv_collections_calling_masterlist snapshot); ameyo_username = Ameyo id that
-- most often called that agent's pilots (last 28 days). 'NA' when not known.
"""
for c in CITIES:
    (HERE / f'calling_masterlist_{slug(c)}.sql').write_text(cm_head.format(city=c) + cte_part + extra + cm_select.format(city=c))
    (HERE / f'agent_action_{slug(c)}.sql').write_text(aa_head.format(city=c) + rcte.replace('{city}', c) + aa_extra.replace('{city}', c) + aa_select.format(city=c))
print('ok')
