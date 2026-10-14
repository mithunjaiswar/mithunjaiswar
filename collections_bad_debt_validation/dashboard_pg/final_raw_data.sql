-- =====================================================================================
-- Collections Dashboard (Summary + WBR) - consolidated Raw_Data query
-- Grain : 1 row per partner per hisaab week (analytics.collections_bad_debt_mv, for_collections = 1)
-- Output: columns A..BS in the SAME order and names as the old Collections Sheet Raw_Data
--         (+ BT os_surpass_deposit_amt, BU bad_debt_collected_nonfunnel, BV mv_last_updated for Summary/WBR)
-- Other queries in this file: QUERY 2 Deposit_Raw, QUERY 3 Recovery_Raw, QUERY 4 sd_bucket,
--         QUERY 5 sd_bucket_V2, QUERY 6 Ownership_CR_Import
-- Window: last 9 hisaab weeks (rolling) - change the 63 below to load more/less history
-- Rule  : MV columns are used AS-IS (MV data fixes are tracked separately in the Validation tab).
--         Other tables are joined ONLY for columns missing in the MV. Every join is pre-aggregated
--         to (partner, hisaab_week) so the result never duplicates MV rows.
-- =====================================================================================
with wk as (            -- rolling list of hisaab weeks (Mondays)
  select generate_series((date_trunc('week', current_date) - interval '63 days')::timestamp,
                         date_trunc('week', current_date)::timestamp, interval '7 days')::date as hw
),
m as (                  -- base: MV rows of those weeks
  select *
  from analytics.collections_bad_debt_mv
  where for_collections = 1
    and hissab_week in (select hw from wk)
),
-- [MISSING 1] collection split by payment type (mv_daily_recovery, hisaab week Mon-Sun)
rec as (
  select employee_id, date_trunc('week', date)::date as hw,
         sum(amount) filter (where recovery_type::text = 'razorpay_recovery')       as razorpay_amt,
         sum(amount) filter (where recovery_type::text = 'other_positive_recovery') as other_amt,
         sum(amount) filter (where recovery_type::text = 'phonepe_recovery')        as phonepe_amt,
         sum(amount) filter (where recovery_type::text = 'positive_adjustment')     as adjustment_amt,
         sum(amount) filter (where recovery_type::text = 'deposit_to_os')           as deposit_to_os_amt
  from mv_daily_recovery
  where date >= (select min(hw) from wk) and date < (select max(hw) + 7 from wk)
  group by 1, 2
),
-- [MISSING 2] ELC filter + calling inputs for asset risk (last calling-masterlist snapshot of the week)
ml as (
  select distinct on (week, partner_et_id) week, partner_et_id, elc_filter, conn_total, att_total, rank,
         current_week_gps_kms, current_week_uber_kms
  from mv_collections_calling_masterlist
  where week in (select hw from wk)
  order by week, partner_et_id, snapshot_date desc
),
-- first day in the hisaab week the partner was tagged Critical_Risk in the calling masterlist (Sheet col BP)
crit as (
  select week, partner_et_id, min(snapshot_date) as first_critical
  from mv_collections_calling_masterlist
  where week in (select hw from wk) and critical_risk_tag = 'Critical_Risk'
  group by 1, 2
),
-- [MISSING 4] car-recovery cases per partner per hisaab week.
--   Same logic as the Central Car Recovery Dash (RawData query + Weekly_Summary):
--   status from rec_tags_id (111 Completed, 112/113 Cancelled, else Pending),
--   close date = last complete/failed/cancelled status log, partner = case driver
--   else driver allocated to the car at activation. MV recovery columns are NOT used (wrong).
rcase as (   -- Query 1 needs only partner + case dates (QUERY 3 has the full case detail)
  select a.id,
    date_trunc('week', a.activation_date)::date as week_start,
    a.activation_date::date as start_date,
    case when a.rec_tags_id in (111, 112, 113)
         then coalesce(ls.close_date, a.updated_at at time zone 'Asia/Kolkata')::date end as close_date,
    case when a.rec_tags_id in (111, 112, 113)
         then date_trunc('week', coalesce(ls.close_date, a.updated_at at time zone 'Asia/Kolkata'))::date
         else date '2099-12-28' end as close_week,
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
  ) al on a.driver_id is null
  left join fleet_driver fd2 on fd2.id = al.driver_id
  where a.activation_date < (select max(hw) from wk) + 7
    and (coalesce(a.rec_tags_id, 0) not in (111, 112, 113) or  -- open cases have rec_tags_id NULL
         coalesce(ls.close_date, a.updated_at) >= (select min(hw) from wk))
),

-- car recovery dates per partner per hisaab week (Sheet cols BM/BN): latest case open in the week;
--   end date = close date, or today while the case is still pending
rcp as (
  select distinct on (c.employee_id, w.hw) c.employee_id, w.hw, c.start_date,
         coalesce(c.close_date, current_date) as end_date
  from rcase c
  join wk w on c.week_start <= w.hw and c.close_week >= w.hw
  order by c.employee_id, w.hw, c.start_date desc
),
-- [MISSING 6] NOT PAID > 2 WEEKS (+ asset-risk input). Replaces wrong MV flag partners_not_paid_2_weeks.
--   For each partner + hisaab week: look at the 2 PREVIOUS hisaab weeks (hissab_week-14 .. hissab_week-7)
--   and count weeks with 0 collection (total_collected_amount_in_week = 0 or blank) -> 0, 1 or 2.
--   Summary "Not paid > 2 weeks" = partners with not_paid_prev_2w = 2 (both previous weeks unpaid).
--   (Sheet col AA logic: COUNTIFS of own rows in previous 14 days with total_recovery = 0)
np as (
  select partner_etm, hissab_week,
         count(*) filter (where coalesce(total_collected_amount_in_week, 0) = 0)
           over (partition by partner_etm order by hissab_week
                 range between interval '14 days' preceding and interval '1 day' preceding) as not_paid_prev_2w,
         count(*) filter (where total_os < 0 and coalesce(total_collected_100_pct, 0) < 0.6 * abs(total_os))
           over (partition by partner_etm order by hissab_week
                 range between interval '14 days' preceding and interval '1 day' preceding) as lt60_prev_2w
  from analytics.collections_bad_debt_mv
  where for_collections = 1
    and hissab_week >= (select min(hw) from wk) - 14
),
-- Entire week active: pilot held a car on ALL days of the hisaab week (allocation table, till today for the
--   running week). Replaces MV total_allocated_days >= 7 (MV counts car-swap days twice).
fw as (
  select m.hissab_week, m.partner_etm,
         count(distinct d::date) = least(7, current_date - m.hissab_week + 1) as full_week
  from m
  join analytics.ssot_alloc_dealloc_base s
    on s.employee_id = m.partner_etm and s.allocation_date <= m.hissab_week + 6
   and coalesce(s.jama_date, current_date) >= m.hissab_week
  cross join lateral generate_series(greatest(s.allocation_date, m.hissab_week)::timestamp,
                                     least(coalesce(s.jama_date, current_date), m.hissab_week + 6, current_date)::timestamp,
                                     interval '1 day') d
  group by 1, 2
),
-- [MISSING 5] funnel bad debt
-- Funnel bad debt (same rule as old Sheet col AY bad_debt_rec_100pct):
--   money paid in the NEXT hisaab week (all positive mv_daily_recovery types) by a partner who has
--   bad debt this week, capped at the bad debt amount.
bdn as (
  select employee_id, date_trunc('week', date)::date - 7 as hw, sum(amount) filter (where amount > 0) as next_week_paid
  from mv_daily_recovery
  where date >= (select min(hw) from wk) + 7 and date < (select max(hw) from wk) + 14
  group by 1, 2
),
-- source channel and Uber tag (Sheet cols BL/BK): latest non-blank value in the ELC upload data
elc as (
  select employee_id,
         (array_agg(source_channel order by uploading_date desc) filter (where coalesce(source_channel, '') <> ''))[1] as source_channel,
         (array_agg(uber_tag order by uploading_date desc) filter (where coalesce(uber_tag, '') <> ''))[1] as uber_tag
  from mv_elc_upload_data
  where employee_id in (select partner_etm from m)
  group by 1
),
-- latest allocation held in the hisaab week: car number (Sheet col Y) and allocation hub (Sheet col BS)
la as (
  select distinct on (m.hissab_week, m.partner_etm) m.hissab_week, m.partner_etm, s.car_number, s.location
  from m
  join analytics.ssot_alloc_dealloc_base s
    on s.employee_id = m.partner_etm and s.allocation_date <= m.hissab_week + 6
  order by m.hissab_week, m.partner_etm, s.allocation_datetime desc
),
-- attrition (Sheet col BR): car returned in the hisaab week and no allocation after that return
ja as (
  select employee_id, max(allocation_date) as last_alloc, max(jama_date) as last_jama
  from analytics.ssot_alloc_dealloc_base
  where employee_id in (select partner_etm from m)
  group by 1
)
select
  -- Columns A..BS: same names and order as the old Collections Sheet Raw_Data
  m.hissab_week                                                         as hisaab_week,            -- A
  m.city                                                                as location,               -- B (old Sheet: city / hub cluster)
  m.revenue_type,                                                                                  -- C
  m.partner_etm                                                         as partner_et_id,          -- D
  m.total_os                                                            as negative_os,            -- E
  m.city,                                                                                          -- F
  case when m.eip_tag = 1 then 'EIP' else 'SINGLE' end                  as eip_filter,             -- G
  m.product_type,                                                                                  -- H
  coalesce(m.total_collected_amount_in_week, 0)                         as total_recovery,         -- I
  coalesce(r.razorpay_amt, 0)                                           as razorpay_recovery,      -- J
  coalesce(r.other_amt, 0)                                              as other_recovery,         -- K
  coalesce(r.phonepe_amt, 0)                                            as phonepe_recovery,       -- L
  coalesce(r.adjustment_amt, 0)                                         as adjustments,            -- M
  coalesce(r.deposit_to_os_amt, 0)                                      as dp_to_os,               -- N
  least(coalesce(m.collection_till_wed, 0), abs(coalesce(m.total_os, 0))) as till_wed_100pct,      -- O
  sp.razorpay_100pct                                                    as razorpay_recovery_100pct, -- P
  sp.other_100pct                                                       as other_recovery_100pct,  -- Q
  sp.phonepe_100pct,                                                                               -- R
  sp.adjustment_100pct                                                  as adjustments_100pct,     -- S
  sp.deposit_to_rent_100pct                                             as dp_to_os_100pct,        -- T
  coalesce(m.total_collected_100_pct, 0)                                as till_sun_100pct,        -- U
  case when coalesce(m.total_os, 0) >= 0 then 1
       else least(coalesce(m.total_collected_100_pct, 0) / abs(m.total_os), 1) end as recovery_pct, -- V
  m.last_payment_date_till_hissab_week                                  as last_paid_date,         -- W
  m.last_jama_date,                                                                                -- X
  la.car_number                                                         as last_car_number,        -- Y
  lower(m.active_inactive_flag)                                         as "active_today?",        -- Z
  coalesce(np.not_paid_prev_2w, 0)                                      as not_paid_last_2_weeks,  -- AA
  m.week_end_deposit,                                                                              -- AB
  case when fw.full_week then 1 else 0 end                              as entire_week_active,     -- AC
  m.active_inactive_flag                                                as "1d_active",            -- AD
  case when coalesce(m.total_os, 0) >= 0 then 0
       when coalesce(m.week_end_deposit, 0) <= 0 then 1
       else abs(m.total_os) / m.week_end_deposit end                    as os_gt_deposit_pct,      -- AE
  x.payment_habit_week                                                  as payment_habit,          -- AF
  coalesce(m.current_week_nd_count, 0)                                  as not_driven_count,       -- AG
  x.recovery_recommended                                                as recovery_recommended_vehicle, -- AH
  y.gps_inactive,                                                                                  -- AI
  coalesce(ml.att_total, 0)                                             as attempts,               -- AJ
  coalesce(ml.conn_total, 0)                                            as connects,               -- AK
  case y.risk_score when 6 then 'Critical Risk' when 5 then 'High Risk' when 4 then 'Moderate Risk'
                    when 3 then 'Low Risk' when 2 then 'Minimal Risk' else 'No risk' end as asset_risk, -- AL
  ml.rank                                                               as et_rank,                -- AM
  coalesce(ml.elc_filter, 'Non_ELC')                                    as elc_filter,             -- AN
  m.fuel_type,                                                                                     -- AO
  v.net_os_neg                                                          as carry_forward_os,       -- AP
  v.prev_cf                                                             as prev_carry_forward,     -- AQ
  coalesce(m.total_os, 0) - v.prev_cf                                   as current_week_os,        -- AR
  v.prev_rec                                                            as prev_recovery,          -- AS
  coalesce(m.total_collected_100_pct, 0) - v.prev_rec                   as current_recovery,       -- AT
  greatest(coalesce(m.total_collected_amount_in_week, 0) - abs(coalesce(m.total_os, 0)), 0) as advance_recovery, -- AU
  v.net_os,                                                                                        -- AV
  coalesce(m.bad_debt_amount, 0)                                        as bad_debt,               -- AW
  case when m.bad_debt_amount < 0 then coalesce(bdn.next_week_paid, 0) else 0 end as bad_debt_rec, -- AX next-week payments
  v.funnel                                                              as bad_debt_rec_100pct,    -- AY funnel (capped at bad debt)
  v.funnel + coalesce(m.bad_debt_amount, 0)                             as net_bad_debt,           -- AZ
  m.lead_id,                                                                                       -- BA
  m.week_start_deposit                                                  as sd_week_start,          -- BB
  case when m.in_car_recovery_hissab_week then 'Yes' else 'No' end      as in_car_recovery,        -- BC
  m.product_type                                                        as bad_debt_product_type,  -- BD
  case when v.net_os_neg >= 0 then ''
       when -v.net_os_neg < 1000 then '1 to 1K' when -v.net_os_neg < 5000 then '1K to 5K'
       when -v.net_os_neg < 10000 then '5K to 10K' when -v.net_os_neg < 15000 then '10K to 15K'
       when -v.net_os_neg < 20000 then '15K to 20K' when -v.net_os_neg < 25000 then '20K to 25K'
       when -v.net_os_neg < 30000 then '25K to 30K' when -v.net_os_neg < 35000 then '30K to 35K'
       else '35K+' end                                                  as "carry_forward_os_Bu",  -- BE
  case when v.net_os_neg >= 0 then 0 when coalesce(m.week_start_deposit, 0) <= 0 then 1
       else least(-v.net_os_neg / m.week_start_deposit, 1) end          as "sd_Surpass %",         -- BF
  case when coalesce(m.week_start_deposit, 0) <= 0 then '0'
       when m.week_start_deposit <= 3000 then '1 to 3K' when m.week_start_deposit <= 5000 then '3K to 5K'
       when m.week_start_deposit <= 10000 then '5K to 10K' when m.week_start_deposit <= 15000 then '10K to 15K'
       when m.week_start_deposit <= 20000 then '15K to 20K' when m.week_start_deposit <= 30000 then '20K to 30K'
       else '30K+' end                                                  as "Deposit_Bucket",       -- BG
  m.week_start_deposit                                                  as "sd_week_start Filter", -- BH
  case when m.tenure_days <= 30 then '0-30' when m.tenure_days <= 60 then '30-60'
       when m.tenure_days <= 90 then '60-90' when m.tenure_days <= 120 then '90-120'
       else '120+' end                                                  as "Tenure_Buckets",       -- BI
  m.tenure_days,                                                                                   -- BJ
  case when elc.uber_tag ilike 'old%' then 'Old In Uber'
       when elc.uber_tag ilike 'new%' then 'New In Uber' end            as uber_tenure_tag,        -- BK
  elc.source_channel,                                                                              -- BL
  rcp.start_date                                                        as car_recovery_startdate, -- BM
  rcp.end_date                                                          as car_recovery_enddate,   -- BN
  m.recovery_tat                                                        as car_recovery_pending_tat, -- BO
  crit.first_critical                                                   as firstdate_critical_risk, -- BP
  coalesce(np.lt60_prev_2w, 0)                                          as "<60_L2w",              -- BQ
  case when ja.last_jama between m.hissab_week and m.hissab_week + 6
        and ja.last_alloc <= ja.last_jama then 1 else 0 end             as attrition_bad_debt,     -- BR (Sheet header: bad_debt)
  la.location                                                           as allocation_location,    -- BS
  -- Extra columns used by Summary / WBR (not in the old layout)
  case when m.active_inactive_flag = 'Active'
       then greatest(-coalesce(m.total_os, 0) - coalesce(m.week_end_deposit, 0), 0) end as os_surpass_deposit_amt, -- BT
  m.bad_debt_collected                                                  as bad_debt_collected_nonfunnel, -- BU
  m.last_updated                                                        as mv_last_updated         -- BV
from m
left join rec r       on r.employee_id    = m.partner_etm and r.hw          = m.hissab_week
left join ml          on ml.partner_et_id = m.partner_etm and ml.week       = m.hissab_week
left join crit        on crit.partner_et_id = m.partner_etm and crit.week   = m.hissab_week
left join rcp         on rcp.employee_id  = m.partner_etm and rcp.hw        = m.hissab_week
left join bdn         on bdn.employee_id  = m.partner_etm and bdn.hw = m.hissab_week
left join fw          on fw.partner_etm   = m.partner_etm and fw.hissab_week = m.hissab_week
left join np          on np.partner_etm   = m.partner_etm and np.hissab_week = m.hissab_week
left join elc         on elc.employee_id  = m.partner_etm
left join la          on la.partner_etm   = m.partner_etm and la.hissab_week = m.hissab_week
left join ja          on ja.employee_id   = m.partner_etm
cross join lateral (  -- OS bifurcation (Sheet cols AP..AV) and funnel bad debt (Sheet col AY)
  select least(coalesce(m.prev_carryforward_os, 0), 0) as prev_cf,
         least(coalesce(m.total_collected_100_pct, 0), greatest(-least(coalesce(m.prev_carryforward_os, 0), 0), 0)) as prev_rec,
         coalesce(m.total_os, 0) + coalesce(m.total_collected_100_pct, 0) as net_os,
         least(coalesce(m.total_os, 0) + coalesce(m.total_collected_100_pct, 0), 0) as net_os_neg,
         case when m.bad_debt_amount < 0
              then least(coalesce(bdn.next_week_paid, 0), abs(m.bad_debt_amount)) else 0 end as funnel
) v
cross join lateral (  -- collection split waterfall (os = |total_os|)
  select least(coalesce(r.razorpay_amt, 0), abs(coalesce(m.total_os, 0))) as razorpay_100pct,
         greatest(0, least(coalesce(r.other_amt, 0), abs(coalesce(m.total_os, 0)) - coalesce(r.razorpay_amt, 0))) as other_100pct,
         greatest(0, least(coalesce(r.phonepe_amt, 0), abs(coalesce(m.total_os, 0)) - coalesce(r.razorpay_amt, 0)
                                                        - coalesce(r.other_amt, 0))) as phonepe_100pct,
         greatest(0, least(coalesce(r.adjustment_amt, 0), abs(coalesce(m.total_os, 0)) - coalesce(r.razorpay_amt, 0)
                                                        - coalesce(r.other_amt, 0) - coalesce(r.phonepe_amt, 0))) as adjustment_100pct,
         greatest(0, least(coalesce(r.deposit_to_os_amt, 0), abs(coalesce(m.total_os, 0)) - coalesce(r.razorpay_amt, 0)
                                                        - coalesce(r.other_amt, 0) - coalesce(r.phonepe_amt, 0)
                                                        - coalesce(r.adjustment_amt, 0))) as deposit_to_rent_100pct
) sp
cross join lateral (  -- Sheet formulas: payment_habit (col AF) and recovery_recommended_vehicle (col AH)
  select case when coalesce(m.total_os, 0) = 0 then 'Excellent'
              when coalesce(m.collection_till_wed, 0) >= abs(m.total_os) then 'Very Good'
              when coalesce(m.total_collected_amount_in_week, 0) >= abs(m.total_os) then 'Good'
              when coalesce(m.total_collected_amount_in_week, 0) >= 0.75 * abs(m.total_os) then 'Average'
              else 'Defaulter' end as payment_habit_week,
         case when coalesce(m.total_collected_100_pct, 0) - abs(coalesce(m.total_os, 0)) < 0
               and abs(coalesce(m.total_collected_100_pct, 0) - abs(coalesce(m.total_os, 0))) > coalesce(m.week_end_deposit, 0)
              then 'Yes' else 'No' end as recovery_recommended
) x
cross join lateral (  -- risk score = number of risk signals
  select case when m.active_inactive_flag = 'Active' and ml.current_week_gps_kms = 0
                   and coalesce(ml.current_week_uber_kms, 0) = 0 then 1 else 0 end as gps_inactive,  -- car allocated, no GPS km
         (coalesce(np.not_paid_prev_2w, 0) >= 1)::int
       + (x.recovery_recommended = 'Yes')::int
       + (x.payment_habit_week = 'Defaulter')::int
       + (coalesce(m.current_week_nd_count, 0) > 2)::int
       + coalesce(m.active_inactive_flag = 'Active' and ml.current_week_gps_kms = 0 and coalesce(ml.current_week_uber_kms, 0) = 0, false)::int
       + (coalesce(ml.conn_total, 0) <= 0)::int as risk_score
) y

order by 1, 6, 4;   -- week, city, partner



-- =====================================================================================
-- QUERY 2 - Deposit_Raw (Summary rows "Deposit Threshold" and "Deposit [At Allocation]")
-- Grain : 1 row per pilot who held a car at ANY time in the hisaab week (allocation table, not only MV).
-- Why separate: these ~12K pilots/week include ~2K not in the MV; adding them to Raw_Data would
--   push the Google Sheet over its 10M cell limit, so they load into the small Deposit_Raw tab.
-- Columns: hissab_week, partner_etm, city, fuel_type, product_type, last_alloc_date, deposit_week_end (G),
--   deposit_at_alloc_week_end (H). Summary rows read G and H.
-- deposit_week_end          = deposit balance till hisaab week end (today for the running week)
-- deposit_at_alloc_week_end = deposit balance till the end of the week of the pilot's LAST allocation
-- (both exclude SD_TO_OWNNOW / OWNNOW_TO_OWNNOW). City / fuel: MV row of that week if present, else allocation table.
-- Product: old Sheet SD Bucket rule (see rk / eip below).
-- =====================================================================================
with wk as (
  select generate_series((date_trunc('week', current_date) - interval '63 days')::timestamp,
                         date_trunc('week', current_date)::timestamp, interval '7 days')::date as hw
),
alloc as (
  select w.hw, s.employee_id, s.allocation_date, s.city, s.fuel_type, s.product_type,
         row_number() over (partition by w.hw, s.employee_id order by s.allocation_datetime desc) as rn
  from analytics.ssot_alloc_dealloc_base s
  join wk w on s.allocation_date <= w.hw + 6 and (s.jama_date is null or s.jama_date >= w.hw)
),
p as (select * from alloc where rn = 1),
-- product = old Sheet (SD Bucket) rule on the car's CURRENT team (fleet_car_team), highest priority over
--   the pilot's cars in the week: Fixed Pay (pm 3) > EIP (pm 7/8) > D2O (pm 6) > Own Now (pm 9) > EV (EV model)
--   > Revenue Share (pm 1) > SINGLE
car_team as (
  select distinct on (fct.car_id) fct.car_id, ft.payment_model_id as pm, fcar.model_id
  from fleet_car_team fct
  left join fleet_team ft on ft.id = fct.team_id
  left join fleet_car fcar on fcar.id = fct.car_id
  order by fct.car_id, coalesce(fct.end_date, current_date) desc, fct.start_date desc
),
rk as (
  select w.hw, s.employee_id,
         max(case when ct.pm = 3 then 99 when ct.pm in (7, 8) then 6 when ct.pm = 6 then 5 when ct.pm = 9 then 4
                  when ct.model_id in (8, 16, 20, 52, 53, 54, 55, 40, 41, 42, 43) then 3 when ct.pm = 1 then 2 else 1 end) as rk
  from analytics.ssot_alloc_dealloc_base s
  join wk w on s.allocation_date <= w.hw + 6 and (s.jama_date is null or s.jama_date >= w.hw)
  left join car_team ct on ct.car_id = s.car_id::int
  group by 1, 2
),
dep as (
  select employee_id, date::date as dt, sum(amount) as amt
  from mv_deposits_raw
  where deposit_type not in ('SD_TO_OWNNOW', 'OWNNOW_TO_OWNNOW')
    and employee_id in (select employee_id from p)
  group by 1, 2
),
m as (
  select hissab_week, partner_etm, city, fuel_type, product_type
  from analytics.collections_bad_debt_mv
  where for_collections = 1 and hissab_week in (select hw from wk)
)
select
  p.hw                                                                         as hissab_week,
  p.employee_id                                                                as partner_etm,
  coalesce(m.city, p.city)                                                     as city,
  coalesce(m.fuel_type, p.fuel_type)                                           as fuel_type,
  case when rk.rk = 99 then 'Fixed Pay' when rk.rk = 6 then 'EIP' when rk.rk = 5 then 'D2O'
       when rk.rk = 4 then 'Own Now' when rk.rk = 3 then 'EV' when rk.rk = 2 then 'Revenue Share' else 'SINGLE' end as product_type,
  p.allocation_date                                                            as last_alloc_date,
  round(coalesce(sum(d.amt) filter (where d.dt <= least(p.hw + 6, current_date)), 0))                                     as deposit_week_end,
  round(coalesce(sum(d.amt) filter (where d.dt <= least(date_trunc('week', p.allocation_date)::date + 6, current_date)), 0)) as deposit_at_alloc_week_end
from p
left join dep d on d.employee_id = p.employee_id
left join m on m.partner_etm = p.employee_id and m.hissab_week = p.hw
left join rk on rk.employee_id = p.employee_id and rk.hw = p.hw
group by 1, 2, 3, 4, 5, 6
order by 1, 3, 2;


-- =====================================================================================
-- QUERY 3 - Recovery_Raw (Summary rows "Car Recovery": initiated, brought fwd, recovered, pending, TAT, per agent)
-- Grain : 1 row per car recovery case per hisaab week it is open in.
-- Same logic as Central Car Recovery Dash (RawData + Weekly_Summary).
-- Why separate: ~1.5K cases belong to pilots with no MV row that week; a join onto Raw_Data would lose them.
-- Team = Completed with no reason (before 07-Sep: all Completed, as Recovery Dash); TAT only for team cases.
-- =====================================================================================
with wk as (            -- rolling list of hisaab weeks (Mondays)
  select generate_series((date_trunc('week', current_date) - interval '63 days')::timestamp,
                         date_trunc('week', current_date)::timestamp, interval '7 days')::date as hw
),
-- [MISSING 4] car-recovery cases per partner per hisaab week.
--   Same logic as the Central Car Recovery Dash (RawData query + Weekly_Summary):
--   status from rec_tags_id (111 Completed, 112/113 Cancelled, else Pending),
--   close date = last complete/failed/cancelled status log, partner = case driver
--   else driver allocated to the car at activation. MV recovery columns are NOT used (wrong).
rcase as (
  select a.id, a.recovery_agent_id, coalesce(ee.name, '') as agent_name,
    date_trunc('week', a.activation_date)::date as week_start,
    case when a.rec_tags_id in (111, 112, 113)
         then date_trunc('week', coalesce(ls.close_date, a.updated_at at time zone 'Asia/Kolkata'))::date
         else date '2099-12-28' end as close_week,
    case when a.rec_tags_id = 111 then 'Completed' when a.rec_tags_id in (112, 113) then 'Cancelled' else 'Pending' end as final_status,
    case when a.rec_tags_id = 111 then coalesce(a.payment_reason, '') else coalesce(a.cancel_reason, '') end as reason,  -- Recovery Dash finalstatus_reason
    cc.id is not null as has_checkin,
    extract(epoch from (coalesce(ls.close_date, now()) - a.activation_date)) / 3600.0 as tat_hrs,
    coalesce(fd.employee_id, fd2.employee_id) as employee_id,
    fcity.name as city,
    case when fcar.model_id in (8,16,20,40,41,42,43,52,53,54,55) then 'EV' else 'CNG' end as fuel_type,
    case when ft.bv_pm_map_id in (11,12,13,19) then 'EV' when ft.bv_pm_map_id in (14,6) then 'EIP'
         when ft.bv_pm_map_id = 7 then 'D2O' when ft.bv_pm_map_id = 18 then 'Own Now'
         when ft.bv_pm_map_id = 1 then 'Revenue Share' when ft.bv_pm_map_id = 3 then 'Fixed Pay'
         when ft.bv_pm_map_id = 8 then 'ETS' when ft.bv_pm_map_id = 9 then 'Intercity'
         when ft.bv_pm_map_id = 10 then 'Last Mile Delivery' else 'SINGLE' end as product_type
  from recovery_cars a
  left join lateral (
    select b.datetime as close_date from recovery_status_logs b
    where b.recovery_id = a.id and b.recovery_status in ('complete', 'failed', 'cancelled')
    order by b.id desc limit 1
  ) ls on true
  left join fleet_car fcar on fcar.id = a.car_id
  left join fleet_driver fd on fd.id = a.driver_id
  left join lateral (
    select fct.team_id from fleet_car_team fct
    where fct.car_id = a.car_id and fct.start_date <= a.activation_date
      and fct.start_date <= coalesce(fct.end_date, current_date)   -- skip bad team rows (end before start), as Recovery Dash
    order by fct.start_date desc limit 1
  ) tm on true
  left join fleet_team ft on ft.id = tm.team_id
  left join fleet_city fcity on fcity.id = ft.city_id
  left join everest_employee ee on ee.id = a.recovery_agent_id
  left join car_checkin cc on cc.id = a.checkin_id
  left join lateral (
    select ca.driver_id from car_allocation ca
    where ca.deactivation_date is null and ca.driver_id is not null
      and ca.car_id = a.car_id and ca.allocation_date <= a.activation_date
    order by ca.id desc limit 1
  ) al on a.driver_id is null
  left join fleet_driver fd2 on fd2.id = al.driver_id
  where a.activation_date < (select max(hw) from wk) + 7
    and (coalesce(a.rec_tags_id, 0) not in (111, 112, 113) or  -- open cases have rec_tags_id NULL
         coalesce(ls.close_date, a.updated_at) >= (select min(hw) from wk))
)
select
  w.hw as rec_week,
  c.employee_id as partner_etm,
  c.city,
  c.product_type,
  c.fuel_type,
  c.id as recovery_id,
  (c.week_start = w.hw)::int as recovery_initiated,
  (c.week_start < w.hw)::int as recovery_brought_fwd,
  (c.close_week = w.hw and c.final_status = 'Completed' and (c.reason = '' or w.hw < date '2026-09-07'))::int as recovered_team,
  (c.close_week = w.hw and c.final_status = 'Cancelled' and ((c.reason = 'Driver Dropped Vehicle' and not c.has_checkin) or (c.reason = '' and c.has_checkin)))::int as recovered_organic,
  (c.close_week > w.hw)::int as recovery_pending,
  case when c.close_week = w.hw and c.final_status = 'Completed' and c.reason = '' then round(c.tat_hrs::numeric, 1) end as recovery_tat_hrs,
  case when c.close_week = w.hw and c.final_status = 'Completed' and c.reason = '' then c.agent_name end as recovery_agent
from rcase c
join wk w on c.week_start <= w.hw and c.close_week >= w.hw
order by 1, 3, 2;


-- =====================================================================================
-- QUERY 4 - sd_bucket (feeds tab "SD_Profiles"; same layout as the old SD Bucket sheet tab "Dash")
-- Grain : 1 row per hisaab week x city x fuel x payment model; pilots counted by deposit at hisaab week end (Deposit_Raw col G).
-- Base  : the same pilots and deposit logic as QUERY 2 (Deposit_Raw).
-- =====================================================================================
with wk as (
  select generate_series((date_trunc('week', current_date) - interval '63 days')::timestamp,
                         date_trunc('week', current_date)::timestamp, interval '7 days')::date as hw
),
alloc as (
  select w.hw, s.employee_id, s.allocation_date, s.city, s.fuel_type, s.product_type,
         row_number() over (partition by w.hw, s.employee_id order by s.allocation_datetime desc) as rn
  from analytics.ssot_alloc_dealloc_base s
  join wk w on s.allocation_date <= w.hw + 6 and (s.jama_date is null or s.jama_date >= w.hw)
),
p as (select * from alloc where rn = 1),
-- product = old Sheet (SD Bucket) rule on the car's CURRENT team (fleet_car_team), highest priority over
--   the pilot's cars in the week: Fixed Pay (pm 3) > EIP (pm 7/8) > D2O (pm 6) > Own Now (pm 9) > EV (EV model)
--   > Revenue Share (pm 1) > SINGLE
car_team as (
  select distinct on (fct.car_id) fct.car_id, ft.payment_model_id as pm, fcar.model_id
  from fleet_car_team fct
  left join fleet_team ft on ft.id = fct.team_id
  left join fleet_car fcar on fcar.id = fct.car_id
  order by fct.car_id, coalesce(fct.end_date, current_date) desc, fct.start_date desc
),
rk as (
  select w.hw, s.employee_id,
         max(case when ct.pm = 3 then 99 when ct.pm in (7, 8) then 6 when ct.pm = 6 then 5 when ct.pm = 9 then 4
                  when ct.model_id in (8, 16, 20, 52, 53, 54, 55, 40, 41, 42, 43) then 3 when ct.pm = 1 then 2 else 1 end) as rk
  from analytics.ssot_alloc_dealloc_base s
  join wk w on s.allocation_date <= w.hw + 6 and (s.jama_date is null or s.jama_date >= w.hw)
  left join car_team ct on ct.car_id = s.car_id::int
  group by 1, 2
),
dep as (
  select employee_id, date::date as dt, sum(amount) as amt
  from mv_deposits_raw
  where deposit_type not in ('SD_TO_OWNNOW', 'OWNNOW_TO_OWNNOW')
    and employee_id in (select employee_id from p)
  group by 1, 2
),
m as (
  select hissab_week, partner_etm, city, fuel_type, product_type
  from analytics.collections_bad_debt_mv
  where for_collections = 1 and hissab_week in (select hw from wk)
),
dr as (
select
  p.hw                                                                         as hissab_week,
  p.employee_id                                                                as partner_etm,
  coalesce(m.city, p.city)                                                     as city,
  coalesce(m.fuel_type, p.fuel_type)                                           as fuel_type,
  case when rk.rk = 99 then 'Fixed Pay' when rk.rk = 6 then 'EIP' when rk.rk = 5 then 'D2O'
       when rk.rk = 4 then 'Own Now' when rk.rk = 3 then 'EV' when rk.rk = 2 then 'Revenue Share' else 'SINGLE' end as product_type,
  p.allocation_date                                                            as last_alloc_date,
  round(coalesce(sum(d.amt) filter (where d.dt <= least(p.hw + 6, current_date)), 0))                                     as deposit_week_end,
  round(coalesce(sum(d.amt) filter (where d.dt <= least(date_trunc('week', p.allocation_date)::date + 6, current_date)), 0)) as deposit_at_alloc_week_end
from p
left join dep d on d.employee_id = p.employee_id
left join m on m.partner_etm = p.employee_id and m.hissab_week = p.hw
left join rk on rk.employee_id = p.employee_id and rk.hw = p.hw
group by 1, 2, 3, 4, 5, 6
)
select
  hissab_week                                                    as week_start,
  city,
  fuel_type,
  product_type                                                   as payment_model,
  count(distinct partner_etm) filter (where deposit_week_end <= 0)                       as "Deposit <= 0",
  count(distinct partner_etm) filter (where deposit_week_end > 0 and deposit_week_end <= 2000)      as "Deposit Between 0-2000",
  count(distinct partner_etm) filter (where deposit_week_end > 2000 and deposit_week_end <= 5000)   as "Deposit Between 2000-5000",
  count(distinct partner_etm) filter (where deposit_week_end > 5000 and deposit_week_end <= 10000)  as "Deposit Between 5000-10000",
  count(distinct partner_etm) filter (where deposit_week_end > 10000 and deposit_week_end <= 20000) as "Deposit Between 10000-20000",
  count(distinct partner_etm) filter (where deposit_week_end > 20000)                    as "Deposit 20000+",
  round(avg(deposit_week_end), 2)                                           as "City Avg deposit"
from dr
group by 1, 2, 3, 4
order by 1, 2, 3, 4;

-- =====================================================================================
-- QUERY 5 - sd_bucket_V2 (feeds tab "SD_Profiles [At Allocation]"; same layout as the old SD Bucket sheet tab "Dash_V2")
-- Grain : 1 row per hisaab week x city x fuel x payment model; pilots counted by deposit at week end of the last allocation (Deposit_Raw col H).
-- Base  : the same pilots and deposit logic as QUERY 2 (Deposit_Raw).
-- =====================================================================================
with wk as (
  select generate_series((date_trunc('week', current_date) - interval '63 days')::timestamp,
                         date_trunc('week', current_date)::timestamp, interval '7 days')::date as hw
),
alloc as (
  select w.hw, s.employee_id, s.allocation_date, s.city, s.fuel_type, s.product_type,
         row_number() over (partition by w.hw, s.employee_id order by s.allocation_datetime desc) as rn
  from analytics.ssot_alloc_dealloc_base s
  join wk w on s.allocation_date <= w.hw + 6 and (s.jama_date is null or s.jama_date >= w.hw)
),
p as (select * from alloc where rn = 1),
-- product = old Sheet (SD Bucket) rule on the car's CURRENT team (fleet_car_team), highest priority over
--   the pilot's cars in the week: Fixed Pay (pm 3) > EIP (pm 7/8) > D2O (pm 6) > Own Now (pm 9) > EV (EV model)
--   > Revenue Share (pm 1) > SINGLE
car_team as (
  select distinct on (fct.car_id) fct.car_id, ft.payment_model_id as pm, fcar.model_id
  from fleet_car_team fct
  left join fleet_team ft on ft.id = fct.team_id
  left join fleet_car fcar on fcar.id = fct.car_id
  order by fct.car_id, coalesce(fct.end_date, current_date) desc, fct.start_date desc
),
rk as (
  select w.hw, s.employee_id,
         max(case when ct.pm = 3 then 99 when ct.pm in (7, 8) then 6 when ct.pm = 6 then 5 when ct.pm = 9 then 4
                  when ct.model_id in (8, 16, 20, 52, 53, 54, 55, 40, 41, 42, 43) then 3 when ct.pm = 1 then 2 else 1 end) as rk
  from analytics.ssot_alloc_dealloc_base s
  join wk w on s.allocation_date <= w.hw + 6 and (s.jama_date is null or s.jama_date >= w.hw)
  left join car_team ct on ct.car_id = s.car_id::int
  group by 1, 2
),
dep as (
  select employee_id, date::date as dt, sum(amount) as amt
  from mv_deposits_raw
  where deposit_type not in ('SD_TO_OWNNOW', 'OWNNOW_TO_OWNNOW')
    and employee_id in (select employee_id from p)
  group by 1, 2
),
m as (
  select hissab_week, partner_etm, city, fuel_type, product_type
  from analytics.collections_bad_debt_mv
  where for_collections = 1 and hissab_week in (select hw from wk)
),
dr as (
select
  p.hw                                                                         as hissab_week,
  p.employee_id                                                                as partner_etm,
  coalesce(m.city, p.city)                                                     as city,
  coalesce(m.fuel_type, p.fuel_type)                                           as fuel_type,
  case when rk.rk = 99 then 'Fixed Pay' when rk.rk = 6 then 'EIP' when rk.rk = 5 then 'D2O'
       when rk.rk = 4 then 'Own Now' when rk.rk = 3 then 'EV' when rk.rk = 2 then 'Revenue Share' else 'SINGLE' end as product_type,
  p.allocation_date                                                            as last_alloc_date,
  round(coalesce(sum(d.amt) filter (where d.dt <= least(p.hw + 6, current_date)), 0))                                     as deposit_week_end,
  round(coalesce(sum(d.amt) filter (where d.dt <= least(date_trunc('week', p.allocation_date)::date + 6, current_date)), 0)) as deposit_at_alloc_week_end
from p
left join dep d on d.employee_id = p.employee_id
left join m on m.partner_etm = p.employee_id and m.hissab_week = p.hw
left join rk on rk.employee_id = p.employee_id and rk.hw = p.hw
group by 1, 2, 3, 4, 5, 6
)
select
  hissab_week                                                    as week_start,
  city,
  fuel_type,
  product_type                                                   as payment_model,
  count(distinct partner_etm) filter (where deposit_at_alloc_week_end <= 0)                       as "Deposit <= 0",
  count(distinct partner_etm) filter (where deposit_at_alloc_week_end > 0 and deposit_at_alloc_week_end <= 2000)      as "Deposit Between 0-2000",
  count(distinct partner_etm) filter (where deposit_at_alloc_week_end > 2000 and deposit_at_alloc_week_end <= 5000)   as "Deposit Between 2000-5000",
  count(distinct partner_etm) filter (where deposit_at_alloc_week_end > 5000 and deposit_at_alloc_week_end <= 10000)  as "Deposit Between 5000-10000",
  count(distinct partner_etm) filter (where deposit_at_alloc_week_end > 10000 and deposit_at_alloc_week_end <= 20000) as "Deposit Between 10000-20000",
  count(distinct partner_etm) filter (where deposit_at_alloc_week_end > 20000)                    as "Deposit 20000+",
  round(avg(deposit_at_alloc_week_end), 2)                                           as "City Avg deposit"
from dr
group by 1, 2, 3, 4
order by 1, 2, 3, 4;

-- =====================================================================================
-- QUERY 6 - Ownership_CR_Import (feeds tab "Ownership_Dash" car recovery rows 21-44)
-- Same logic as the Central Car Recovery Dash tab Ownership_CR_Aggregate_City (last 8 hisaab weeks):
--   open case at week w      = started on/before w and not closed by end of w (pending or closed after w)
--   cases_open / pending     = open cases;  raised = started in w;  carry_forward = open cases started before w
--   completed_same_week      = started in w, closed in w, no close reason
--   aging_*                  = open cases by start date: 0-6 = started in w, 7-15 = w-9..w-1, 16-30 = w-24..w-10, 30+ = before w-24
--   negative_os_open         = sum of the partner's MV total_os in week w for the open cases
--                              (Recovery Dash uses its own per-case OS sheet; this uses the MV OS of that week)
-- =====================================================================================
with wk as (            -- rolling list of hisaab weeks (Mondays)
  select generate_series((date_trunc('week', current_date) - interval '49 days')::timestamp,
                         date_trunc('week', current_date)::timestamp, interval '7 days')::date as hw
),
-- [MISSING 4] car-recovery cases per partner per hisaab week.
--   Same logic as the Central Car Recovery Dash (RawData query + Weekly_Summary):
--   status from rec_tags_id (111 Completed, 112/113 Cancelled, else Pending),
--   close date = last complete/failed/cancelled status log, partner = case driver
--   else driver allocated to the car at activation. MV recovery columns are NOT used (wrong).
rcase as (
  select a.id, a.recovery_agent_id, coalesce(ee.name, '') as agent_name,
    date_trunc('week', a.activation_date)::date as week_start,
    a.activation_date::date as start_date,
    case when a.rec_tags_id in (111, 112, 113)
         then date_trunc('week', coalesce(ls.close_date, a.updated_at at time zone 'Asia/Kolkata'))::date
         else date '2099-12-28' end as close_week,
    case when a.rec_tags_id = 111 then 'Completed' when a.rec_tags_id in (112, 113) then 'Cancelled' else 'Pending' end as final_status,
    case when a.rec_tags_id = 111 then coalesce(a.payment_reason, '') else coalesce(a.cancel_reason, '') end as reason,  -- Recovery Dash finalstatus_reason
    cc.id is not null as has_checkin,
    extract(epoch from (coalesce(ls.close_date, now()) - a.activation_date)) / 3600.0 as tat_hrs,
    coalesce(fd.employee_id, fd2.employee_id) as employee_id,
    fcity.name as city,
    case when fcar.model_id in (8,16,20,40,41,42,43,52,53,54,55) then 'EV' else 'CNG' end as fuel_type,
    case when ft.bv_pm_map_id in (11,12,13,19) then 'EV' when ft.bv_pm_map_id in (14,6) then 'EIP'
         when ft.bv_pm_map_id = 7 then 'D2O' when ft.bv_pm_map_id = 18 then 'Own Now'
         when ft.bv_pm_map_id = 1 then 'Revenue Share' when ft.bv_pm_map_id = 3 then 'Fixed Pay'
         when ft.bv_pm_map_id = 8 then 'ETS' when ft.bv_pm_map_id = 9 then 'Intercity'
         when ft.bv_pm_map_id = 10 then 'Last Mile Delivery' else 'SINGLE' end as product_type
  from recovery_cars a
  left join lateral (
    select b.datetime as close_date from recovery_status_logs b
    where b.recovery_id = a.id and b.recovery_status in ('complete', 'failed', 'cancelled')
    order by b.id desc limit 1
  ) ls on true
  left join fleet_car fcar on fcar.id = a.car_id
  left join fleet_driver fd on fd.id = a.driver_id
  left join lateral (
    select fct.team_id from fleet_car_team fct
    where fct.car_id = a.car_id and fct.start_date <= a.activation_date
      and fct.start_date <= coalesce(fct.end_date, current_date)   -- skip bad team rows (end before start), as Recovery Dash
    order by fct.start_date desc limit 1
  ) tm on true
  left join fleet_team ft on ft.id = tm.team_id
  left join fleet_city fcity on fcity.id = ft.city_id
  left join everest_employee ee on ee.id = a.recovery_agent_id
  left join car_checkin cc on cc.id = a.checkin_id
  left join lateral (
    select ca.driver_id from car_allocation ca
    where ca.deactivation_date is null and ca.driver_id is not null
      and ca.car_id = a.car_id and ca.allocation_date <= a.activation_date
    order by ca.id desc limit 1
  ) al on a.driver_id is null
  left join fleet_driver fd2 on fd2.id = al.driver_id
  where a.activation_date < (select max(hw) from wk) + 7
    and (coalesce(a.rec_tags_id, 0) not in (111, 112, 113) or  -- open cases have rec_tags_id NULL
         coalesce(ls.close_date, a.updated_at) >= (select min(hw) from wk))
),
os as (
  select hissab_week, partner_etm, total_os
  from analytics.collections_bad_debt_mv
  where for_collections = 1 and hissab_week in (select hw from wk)
)
select
  w.hw                                                                   as week,
  c.product_type,
  c.city,
  count(*) filter (where c.close_week > w.hw)                            as cases_open,
  coalesce(sum(o.total_os) filter (where c.close_week > w.hw), 0)        as negative_os_open,
  count(*) filter (where c.week_start = w.hw)                            as raised,
  count(*) filter (where c.week_start < w.hw and c.close_week > w.hw)    as carry_forward,
  count(*) filter (where c.week_start = w.hw and c.close_week = w.hw and c.reason = '') as completed_same_week,
  count(*) filter (where c.close_week > w.hw)                            as pending,
  count(*) filter (where c.close_week > w.hw and c.start_date between w.hw and w.hw + 6)       as aging_0_6,
  count(*) filter (where c.close_week > w.hw and c.start_date between w.hw - 9 and w.hw - 1)   as aging_7_15,
  count(*) filter (where c.close_week > w.hw and c.start_date between w.hw - 24 and w.hw - 10) as aging_16_30,
  count(*) filter (where c.close_week > w.hw and c.start_date < w.hw - 24)                     as aging_30_plus
from wk w
join rcase c on c.week_start <= w.hw and c.close_week >= w.hw
left join os o on o.partner_etm = c.employee_id and o.hissab_week = w.hw
where c.city is not null
group by 1, 2, 3
order by 1, 2, 3;
