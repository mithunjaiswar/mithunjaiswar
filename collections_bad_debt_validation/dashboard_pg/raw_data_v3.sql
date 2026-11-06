-- =====================================================================================
-- Collections Dashboard - Raw_Data query v3 (same 75 columns A..BW as the old Collections Sheet Raw_Data)
-- Grain : 1 row per partner per hisaab week (analytics.collections_bad_debt_mv, for_collections = 1)
-- Window: last 9 hisaab weeks, same as old Sheet (change the 56 below). 2 extra older weeks are read only for the
--         "previous week" columns (AA, AQ, BH, BQ) and are not output.
-- Column rules (user spec, Nov-2026):
--   I  total_recovery      = mv_daily_recovery (5 types) paid in the hisaab week (updates hourly)
--   O  till_wed_100pct     = MIN(Mon-Wed payments, |OS|)             (old Sheet col O)
--   P..T                   = waterfall razorpay > other > phonepe > adjustment > dp_to_os, capped at |OS|
--   U  till_sun_100pct     = MIN(I, |OS|);  V recovery_pct = U / |OS|
--   Y  last_car_number     = all cars held in the hisaab week (ssot_alloc_dealloc_base), comma separated
--   Z  active_today?       = car allotted on Sunday of the hisaab week (today for the running week)
--   AD 1d_active           = car allotted on at least 1 day of the hisaab week
--   AJ/AK attempts/connects= public.collections_calling_data_raw, week_start = hisaab week
--   AA, AE, AF, AH, AL, AM, AO, AP..AV, AZ, BE..BI, BQ = old Sheet formulas (row 87926) as SQL
--   AX bad_debt_rec        = mv_daily_recovery paid AFTER the hisaab week and after the pilot left (jama)
--   BM/BN/BO car recovery  = recovery_cars: start date, close date (today if pending), days between
-- =====================================================================================
with wk as (
  select generate_series((date_trunc('week', current_date) - interval '56 days')::timestamp,
                         date_trunc('week', current_date)::timestamp, interval '7 days')::date as hw
),
lim as materialized (select min(hw) as w0, max(hw) as w1 from wk),
-- MV rows: output weeks + 2 older weeks for the "previous week" columns
m as materialized (
  select *
  from analytics.collections_bad_debt_mv
  where for_collections = 1
    and hissab_week between (select w0 from lim) - 14 and (select w1 from lim)
),
-- payments by type per partner per hisaab week (same as old Sheet collections_data)
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
-- per-row values the old Sheet computes with formulas, plus "previous week" lookups
b as materialized (
  select m.*,
         -- EV car: on EIP plan (eip_tag = 1) = EV / EV_Leasing; on D2O = EV_D2O; everything else = MV value
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
         -- AQ prev_carry_forward = AP of the same partner in the previous hisaab week
         coalesce(sum(b.ap_cf) over (partition by b.partner_etm order by b.hissab_week
                                     range between interval '7 days' preceding and interval '7 days' preceding), 0) as aq_prev_cf,
         -- AA not_paid_last_2_weeks = previous 2 weeks with total_recovery = 0
         count(*) filter (where b.i_tot = 0) over (partition by b.partner_etm order by b.hissab_week
                                     range between interval '14 days' preceding and interval '1 day' preceding) as aa_np2,
         -- BH sd_week_start Filter = higher of this week and previous week week-start deposit
         max(b.week_start_deposit) over (partition by b.partner_etm order by b.hissab_week
                                     range between interval '7 days' preceding and interval '7 days' preceding) as bb_prev
  from b
),
b3 as materialized (
  select b2.*,
         -- BQ <60_L2w = previous 2 weeks with collection % between 0% and 80% (old Sheet formula)
         count(*) filter (where b2.v_pct > 0 and b2.v_pct < 0.8) over (partition by b2.partner_etm order by b2.hissab_week
                                     range between interval '14 days' preceding and interval '1 day' preceding) as bq_lt80
  from b2
),
o as materialized (   -- output weeks only; AM et_rank = number of loaded weeks of the partner up to this week
  select b3.*,
         count(*) over (partition by b3.partner_etm order by b3.hissab_week rows unbounded preceding) as am_rank,
         -- bad debt only for closed weeks (old Sheet shows 0 for the running week)
         case when b3.hissab_week < date_trunc('week', current_date)::date then b3.bad_debt_amount end as bd_amt
  from b3
  where b3.hissab_week >= (select w0 from lim)
),
-- cars held in the hisaab week, active on Sunday, active at least 1 day (allocation table)
al as materialized (
  select o.hissab_week, o.partner_etm,
         string_agg(distinct s.car_number, ',') as cars,
         (array_agg(s.location order by s.allocation_datetime desc))[1] as alloc_hub,   -- BS hub of latest allocation
         bool_or(s.allocation_date <= least(o.hissab_week + 6, current_date)
                 and coalesce(s.jama_date, current_date) >= least(o.hissab_week + 6, current_date)) as on_sunday
  from o
  join analytics.ssot_alloc_dealloc_base s
    on s.employee_id = o.partner_etm and s.allocation_date <= o.hissab_week + 6
   and coalesce(s.jama_date, current_date) >= o.hissab_week
  group by 1, 2
),
-- BK uber tag / BL source channel: latest non-blank value in the ELC upload data
elc as materialized (
  select employee_id,
         (array_agg(source_channel order by uploading_date desc) filter (where coalesce(source_channel, '') <> ''))[1] as source_channel,
         (array_agg(uber_tag order by uploading_date desc) filter (where coalesce(uber_tag, '') <> ''))[1] as uber_tag
  from mv_elc_upload_data
  where employee_id in (select partner_etm from o)
  group by 1
),
-- calling attempts / connects in the hisaab week
-- BK fallback: Uber first trip (mv_uber_ftd) before first allocation (driver_profile) = Old, else New
--   (same rule as the old Sheet's FT Tracker; ELC tag wins when present)
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
-- BL source channel: joining source in ssot_alloc_dealloc_full (old Sheet: Allocations Cohort sheet), ELC as fallback
chn as materialized (select employee_id, max(main_source) as src from analytics.ssot_alloc_dealloc_full
                     where main_source <> '' and employee_id in (select partner_etm from o) group by 1),
cl as materialized (
  select partner_et_id, week_start, sum(attempt_count) as attempts, sum(connect_count) as connects
  from public.collections_calling_data_raw
  where week_start in (select hw from wk) and partner_et_id in (select partner_etm from o)
  group by 1, 2
),
-- calling inputs for ELC filter and GPS signal (last masterlist snapshot of the week)
ml as materialized (
  select distinct on (week, partner_et_id) week, partner_et_id, elc_filter, current_week_gps_kms, current_week_uber_kms
  from mv_collections_calling_masterlist
  where week in (select hw from wk) and partner_et_id in (select partner_etm from o)
  order by week, partner_et_id, snapshot_date desc
),
-- entire week active: car allocated on all days of the hisaab week (till today for the running week)
fw as materialized (
  -- old Sheet rule: one allocation that started on/before Monday and was still running after Sunday
  -- (car swap in the week or car returned on Sunday = not entire week)
  select o.hissab_week, o.partner_etm,
         bool_or(s.allocation_date <= o.hissab_week
                 and (s.jama_date is null or s.jama_date >= current_date or s.jama_date > o.hissab_week + 6)) as full_week
  from o
  join analytics.ssot_alloc_dealloc_base s
    on s.employee_id = o.partner_etm and s.allocation_date <= o.hissab_week + 6
   and coalesce(s.jama_date, current_date) >= o.hissab_week
  group by 1, 2
),
-- AX bad_debt_rec: money paid after the hisaab week and after the pilot left (bad debt rows only)
bdo as materialized (   -- bad debt rows only
  select hissab_week, partner_etm, last_jama_date from o where bd_amt < 0
),
pay as materialized (     -- daily payments of those partners after the first output week
  select employee_id, date::date as d, sum(amount) as amt
  from mv_daily_recovery
  where employee_id in (select partner_etm from bdo)
    and date >= (select w0 from lim) + 7
    and recovery_type::text in ('razorpay_recovery', 'other_positive_recovery', 'phonepe_recovery',
                                'positive_adjustment', 'deposit_to_os')
  group by 1, 2
),
bdr as materialized (
  select bdo.hissab_week, bdo.partner_etm, sum(p.amt) as paid_after_left
  from bdo
  join pay p on p.employee_id = bdo.partner_etm
            and p.d >= bdo.hissab_week + 7
            and p.d > coalesce(bdo.last_jama_date, bdo.hissab_week + 6)
  group by 1, 2
),
-- car recovery cases (recovery_cars): partner = case driver, else driver allocated to the car at activation
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
-- latest case open in the hisaab week
rcp as materialized (
  select distinct on (c.employee_id, w.hw) c.employee_id, w.hw, c.start_date,
         coalesce(c.close_date, current_date) as end_date
  from rcase c
  join wk w on c.start_date <= w.hw + 6 and coalesce(c.close_date, current_date) >= w.hw
  order by c.employee_id, w.hw, c.start_date desc
),
f as materialized (   -- one more step for values that need several of the above
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
)
select
  f.hissab_week                                                         as "hisaab_week",          -- A
  f.location                                                            as "location",             -- B
  f.rev_type                                                              as "revenue_type",         -- C (EV car on D2O = EV_D2O)
  f.partner_etm                                                         as "partner_et_id",        -- D
  f.e_os                                                                as "negative_os",          -- E
  f.city                                                                as "city",                 -- F
  case when f.eip_tag = 1 then 'EIP' else 'SINGLE' end                  as "eip_filter",           -- G
  f.prod_type                                                             as "product_type",         -- H
  f.i_tot                                                               as "total_recovery",       -- I
  f.j_rz                                                                as "razorpay_recovery",    -- J
  f.k_ot                                                                as "other_recovery",       -- K
  f.l_pp                                                                as "phonepe_recovery",     -- L
  f.m_ad                                                                as "adjustments",          -- M
  f.n_dp                                                                as "dp_to_os",             -- N
  f.o_wed                                                               as "till_wed_100pct",      -- O
  f.p_rz                                                                as "razorpay_recovery_100pct", -- P
  f.q_ot                                                                as "other_recovery_100pct",  -- Q
  f.r_pp                                                                as "phonepe_100pct",       -- R
  f.s_ad                                                                as "adjustments_100pct",   -- S
  f.t_dp                                                                as "dp_to_os_100pct",      -- T
  f.u_sun                                                               as "till_sun_100pct",      -- U
  case when f.e_os < 0 then f.v_pct else 1 end                         as "recovery_pct",         -- V (1 when OS >= 0, as old Sheet)
  f.last_payment_date_till_hissab_week                                  as "last_paid_date",       -- W
  f.last_jama_date                                                      as "last_jama_date",       -- X
  al.cars                                                               as "last_car_number",      -- Y
  case when al.on_sunday then 'active' else 'inactive' end              as "active_today?",        -- Z
  f.aa_np2                                                              as "not_paid_last_2_weeks",  -- AA
  coalesce(f.week_end_deposit, 0)                                       as "week_end_deposit",     -- AB
  case when fw.full_week then 1 else 0 end                              as "entire_week_active",   -- AC
  case when al.partner_etm is not null then 'Active' else 'Inactive' end as "1d_active",           -- AD
  case when f.e_os < 0 and coalesce(f.week_end_deposit, 0) = 0 then 1
       when coalesce(f.week_end_deposit, 0) <> 0 then abs(f.e_os) / f.week_end_deposit end as "os_gt_deposit_pct", -- AE
  f.af_habit                                                            as "payment_habit",        -- AF
  coalesce(f.current_week_nd_count, 0)                                  as "not_driven_count",     -- AG
  case when f.av_net >= 0 then 'No' when abs(f.av_net) > coalesce(f.week_end_deposit, 0) then 'Yes' else 'No' end
                                                                        as "recovery_recommended_vehicle", -- AH
  case when f.active_inactive_flag = 'Active' and ml.current_week_gps_kms = 0
        and coalesce(ml.current_week_uber_kms, 0) = 0 then 1 else 0 end as "gps_inactive",         -- AI
  coalesce(cl.attempts, 0)                                              as "attempts",             -- AJ
  coalesce(cl.connects, 0)                                              as "connects",             -- AK
  case (f.aa_np2 >= 1)::int
       + (case when f.av_net >= 0 then false else abs(f.av_net) > coalesce(f.week_end_deposit, 0) end)::int
       + (f.af_habit = 'Defaulter')::int
       + (coalesce(f.current_week_nd_count, 0) > 2)::int
       + coalesce(f.active_inactive_flag = 'Active' and ml.current_week_gps_kms = 0 and coalesce(ml.current_week_uber_kms, 0) = 0, false)::int
       + (coalesce(cl.connects, 0) <= 0)::int
    when 6 then 'Critical Risk' when 5 then 'High Risk' when 4 then 'Moderate Risk'
    when 3 then 'Low Risk' when 2 then 'Minimal Risk' else 'No risk' end as "asset_risk",          -- AL
  f.am_rank                                                             as "et_rank",              -- AM
  coalesce(ml.elc_filter, 'Non_ELC')                                    as "elc_filter",           -- AN
  case when left(f.rev_type, 3) = 'EV_' then 'EV' else 'CNG' end         as "fuel_type",            -- AO
  f.ap_cf                                                               as "carry_forward_os",     -- AP
  f.aq_prev_cf                                                          as "prev_carry_forward",   -- AQ
  f.e_os - f.aq_prev_cf                                                 as "current_week_os",      -- AR
  f.as_prev_rec                                                         as "prev_recovery",        -- AS
  least(f.i_tot - f.as_prev_rec, abs(f.e_os - f.aq_prev_cf))            as "current_recovery",     -- AT
  f.i_tot - f.as_prev_rec - least(f.i_tot - f.as_prev_rec, abs(f.e_os - f.aq_prev_cf)) as "advance_recovery", -- AU
  f.av_net                                                              as "net_os",               -- AV
  coalesce(f.bd_amt, 0)                                        as "bad_debt",             -- AW (0 when no bad debt, as old Sheet)
  case when f.bd_amt < 0 then coalesce(bdr.paid_after_left, 0) else 0 end as "bad_debt_rec", -- AX
  case when f.bd_amt < 0
       then least(coalesce(bdr.paid_after_left, 0), abs(f.bd_amt)) else 0 end as "bad_debt_rec_100pct", -- AY
  coalesce(case when f.bd_amt < 0
                then least(coalesce(bdr.paid_after_left, 0), abs(f.bd_amt)) else 0 end, 0)
    + coalesce(f.bd_amt, 0)                                    as "net_bad_debt",         -- AZ = AY + AW
  f.lead_id                                                             as "lead_id",              -- BA
  f.week_start_deposit                                                  as "sd_week_start",        -- BB
  case when f.in_car_recovery_hissab_week then 'Yes' else 'No' end      as "in_car_recovery",      -- BC
  case when f.eip_tag = 1 then 'EIP' else f.prod_type end              as "bad_debt_product_type",  -- BD (EIP plan pilots = EIP, as old Sheet)
  case when f.ap_cf = 0 then ''
       when abs(f.ap_cf) < 1000 then '1 to 1K' when abs(f.ap_cf) < 5000 then '1K to 5K'
       when abs(f.ap_cf) < 10000 then '5K to 10K' when abs(f.ap_cf) < 15000 then '10K to 15K'
       when abs(f.ap_cf) < 20000 then '15K to 20K' when abs(f.ap_cf) < 25000 then '20K to 25K'
       when abs(f.ap_cf) < 30000 then '25K to 30K' when abs(f.ap_cf) < 35000 then '30K to 35K'
       else '35K+' end                                                  as "carry_forward_os_Bu",  -- BE
  case when coalesce(f.week_end_deposit, 0) = 0 and f.ap_cf = 0 then 0
       when coalesce(f.week_end_deposit, 0) = 0 then 1
       when f.ap_cf = 0 then 0
       else abs(f.ap_cf) / f.week_end_deposit end                       as "sd_Surpass %",         -- BF
  case when greatest(f.week_start_deposit, f.bb_prev) is null then ''
       when greatest(f.week_start_deposit, f.bb_prev) <= 0 then '0'
       when greatest(f.week_start_deposit, f.bb_prev) <= 3000 then '1 to 3K'
       when greatest(f.week_start_deposit, f.bb_prev) <= 5000 then '3K to 5K'
       when greatest(f.week_start_deposit, f.bb_prev) <= 10000 then '5K to 10K'
       when greatest(f.week_start_deposit, f.bb_prev) <= 15000 then '10K to 15K'
       when greatest(f.week_start_deposit, f.bb_prev) <= 20000 then '15K to 20K'
       when greatest(f.week_start_deposit, f.bb_prev) <= 30000 then '20K to 30K'
       else '30K+' end                                                  as "Deposit_Bucket",       -- BG
  greatest(f.week_start_deposit, f.bb_prev)                             as "sd_week_start Filter", -- BH
  case when f.tenure_days is null then ''
       when f.tenure_days <= 30 then '0-30' when f.tenure_days <= 60 then '30-60'
       when f.tenure_days <= 90 then '60-90' when f.tenure_days <= 120 then '90-120'
       else '120+' end                                                  as "Tenure_Buckets",       -- BI
  f.tenure_days                                                         as "tenure_days",          -- BJ
  case when elc.uber_tag ilike 'old%' then 'Old In Uber'
       when elc.uber_tag ilike 'new%' then 'New In Uber' else utag.tag end as "uber_tenure_tag",    -- BK
  coalesce(chn.src, elc.source_channel)                                 as "source_channel",       -- BL
  rcp.start_date                                                        as "car_recovery_startdate",   -- BM
  rcp.end_date                                                          as "car_recovery_enddate",     -- BN
  rcp.end_date - rcp.start_date                                         as "car_recovery_pending_tat", -- BO
  null::text                                                            as "firstdate_critical_risk",  -- BP
  f.bq_lt80                                                             as "<60_L2w",              -- BQ
  null::text                                                            as "bad_debt",             -- BR
  al.alloc_hub                                                          as "allocation_location",  -- BS
  null::text                                                            as "allocation_location",  -- BT
  null::text                                                            as "OWN NOW SWASTIK",      -- BU
  null::text                                                            as " ",                    -- BV
  null::text                                                            as "bad_debt_attrition"    -- BW
from f
left join al  on al.partner_etm  = f.partner_etm and al.hissab_week  = f.hissab_week
left join cl  on cl.partner_et_id = f.partner_etm and cl.week_start  = f.hissab_week
left join ml  on ml.partner_et_id = f.partner_etm and ml.week        = f.hissab_week
left join fw  on fw.partner_etm  = f.partner_etm and fw.hissab_week  = f.hissab_week
left join bdr on bdr.partner_etm = f.partner_etm and bdr.hissab_week = f.hissab_week
left join rcp on rcp.employee_id = f.partner_etm and rcp.hw          = f.hissab_week
left join elc on elc.employee_id = f.partner_etm
left join utag on utag.employee_id = f.partner_etm
left join chn on chn.employee_id = f.partner_etm
order by f.hissab_week, f.city, f.partner_etm;
