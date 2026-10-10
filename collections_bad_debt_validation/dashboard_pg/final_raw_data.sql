-- =====================================================================================
-- Collections Dashboard (Summary + WBR) - consolidated Raw_Data query
-- Grain : 1 row per partner per hisaab week (analytics.collections_bad_debt_mv, for_collections = 1)
-- Window: last 9 hisaab weeks (rolling) - change the 63 below to load more/less history
-- Rule  : MV columns are used AS-IS (MV data fixes are tracked separately in the Validation tab).
--         Other tables are joined ONLY for columns missing in the MV. Every join is pre-aggregated
--         to (partner, hisaab_week) so the result never duplicates MV rows.
-- =====================================================================================
with wk as (            -- rolling list of hisaab weeks (Mondays)
  select generate_series(date_trunc('week', current_date)::date - 63,
                         date_trunc('week', current_date)::date, 7)::date as hw
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
  select distinct on (week, partner_et_id) week, partner_et_id, elc_filter, conn_total,
         current_week_gps_kms, current_week_uber_kms
  from mv_collections_calling_masterlist
  where week in (select hw from wk)
  order by week, partner_et_id, snapshot_date desc
),
-- [MISSING 3] deposit AT ALLOCATION: deposit balance on the latest allocation date <= hisaab week end
alloc as (
  select m.hissab_week, m.partner_etm, max(s.allocation_date) as alloc_date
  from m
  join analytics.ssot_alloc_dealloc_base s
    on s.employee_id = m.partner_etm and s.allocation_date <= m.hissab_week + 6
  group by 1, 2
),
dep_alloc as (
  select a.hissab_week, a.partner_etm, a.alloc_date, d.dep_at_alloc
  from alloc a
  cross join lateral (
    select coalesce(sum(x.amount), 0) as dep_at_alloc
    from mv_deposits_raw x
    where x.employee_id = a.partner_etm
      and x.date <= a.alloc_date
      and x.deposit_type not in ('SD_TO_OWNNOW', 'OWNNOW_TO_OWNNOW')
  ) d
),
-- [MISSING 4] car-recovery events per partner per hisaab week (recovery_cars)
rc as (
  select fd.employee_id, w.hw,
    count(*) filter (where r.created_at >= w.hw and r.created_at < w.hw + 7)                         as recovery_initiated,
    count(*) filter (where r.created_at <  w.hw)                                                       as recovery_brought_fwd,
    count(*) filter (where r.recovery_status = 'complete'  and r.updated_at >= w.hw and r.updated_at < w.hw + 7) as recovered_team,
    count(*) filter (where r.recovery_status = 'cancelled' and r.updated_at >= w.hw and r.updated_at < w.hw + 7) as recovered_organic,
    count(*) filter (where r.recovery_status in ('pending', 'active') and r.created_at < w.hw + 7)   as recovery_pending,
    round(max(extract(epoch from r.updated_at - r.created_at) / 3600.0)
          filter (where r.recovery_status = 'complete' and r.updated_at >= w.hw and r.updated_at < w.hw + 7)::numeric, 1) as recovery_tat_hrs,
    min(r.recovery_agent_id) filter (where r.recovery_status = 'complete' and r.updated_at >= w.hw and r.updated_at < w.hw + 7) as recovery_agent_id
  from recovery_cars r
  join fleet_driver fd on fd.id = r.driver_id
  join wk w on r.created_at < w.hw + 7
           and (r.recovery_status not in ('complete', 'cancelled') or r.updated_at >= w.hw)
  group by 1, 2
),
-- [MISSING 6] asset-risk input: no. of the 2 previous hisaab weeks with 0 collection (Sheet col AA logic)
np as (
  select partner_etm, hissab_week,
         count(*) filter (where coalesce(total_collected_amount_in_week, 0) = 0)
           over (partition by partner_etm order by hissab_week
                 range between interval '14 days' preceding and interval '1 day' preceding) as not_paid_prev_2w
  from analytics.collections_bad_debt_mv
  where for_collections = 1
    and hissab_week >= (select min(hw) from wk) - 14
),
-- [MISSING 5] funnel bad debt: first hisaab week the partner went to bad debt (whole MV history)
bd as (
  select partner_etm, min(hissab_week) as first_bad_debt_week
  from analytics.collections_bad_debt_mv
  where bad_debt_amount < 0
  group by 1
)
select
  -- keys & filters (MV)
  m.hissab_week, m.partner_etm, m.lead_id, m.city, m.location, m.product_type, m.revenue_type, m.fuel_type,
  case when m.eip_tag = 1 then 'EIP' else 'SINGLE' end                                       as eip_filter,
  coalesce(ml.elc_filter, 'Non_ELC')                                                         as elc_filter,          -- masterlist
  m.active_inactive_flag,
  case when m.in_car_recovery_hissab_week then 'Yes' else 'No' end                           as in_car_recovery,
  -- outstanding (MV)
  m.total_os, m.weekly_os, m.prev_carryforward_os,
  -- collections (MV)
  coalesce(m.total_collected_amount_in_week, 0) as total_collected_amount_in_week,  -- 0 for non-payers (Not-paid count)
  m.total_collected_100_pct, m.collection_till_wed, m.os_to_deposit,
  -- collection split (mv_daily_recovery); razorpay = 100% total minus the other parts
  coalesce(m.total_collected_100_pct, 0) - coalesce(r.other_amt, 0) - coalesce(r.phonepe_amt, 0)
    - coalesce(r.adjustment_amt, 0) - coalesce(r.deposit_to_os_amt, 0)                       as razorpay_100pct,
  coalesce(r.other_amt, 0)                                                                   as other_100pct,
  coalesce(r.phonepe_amt, 0)                                                                 as phonepe_100pct,
  coalesce(r.adjustment_amt, 0)                                                              as adjustment_100pct,
  coalesce(r.deposit_to_os_amt, 0)                                                           as deposit_to_rent_100pct,
  -- behaviour (MV)
  m.partners_not_paid_2_weeks, m.last_week_payment_habit, m.total_allocated_days,
  case when m.total_allocated_days >= 7 then 1 else 0 end                                    as entire_week_active,
  m.last_payment_date_till_hissab_week, m.last_jama_date, m.tenure_days,
  -- deposit (MV + deposit at allocation)
  m.week_start_deposit, m.week_end_deposit, da.alloc_date, da.dep_at_alloc,
  case when m.active_inactive_flag = 'Active'
       then greatest(-coalesce(m.total_os, 0) - coalesce(m.week_end_deposit, 0), 0) end     as os_surpass_deposit_amt,
  -- bad debt (MV + funnel)
  m.bad_debt_amount,
  m.bad_debt_collected                                                                       as bad_debt_collected_nonfunnel,
  case when bd.first_bad_debt_week < m.hissab_week and m.active_inactive_flag = 'Inactive'
       then coalesce(m.total_collected_100_pct, 0) else 0 end                                as bad_debt_collected_funnel, -- paid after going to bad debt, not rejoined
  -- asset risk (Sheet Raw_Data col AL logic: score of 6 signals -> 6 Critical .. 2 Minimal, 0-1 No risk)
  case y.risk_score when 6 then 'Critical Risk' when 5 then 'High Risk' when 4 then 'Moderate Risk'
                    when 3 then 'Low Risk' when 2 then 'Minimal Risk' else 'No risk' end   as asset_risk,
  x.recovery_recommended,
  m.cars_under_recovery_hissab_week, m.recovery_tat,
  coalesce(rc.recovery_initiated, 0)   as recovery_initiated,
  coalesce(rc.recovery_brought_fwd, 0) as recovery_brought_fwd,
  coalesce(rc.recovered_team, 0)       as recovered_team,
  coalesce(rc.recovered_organic, 0)    as recovered_organic,
  coalesce(rc.recovery_pending, 0)     as recovery_pending,
  rc.recovery_tat_hrs, rc.recovery_agent_id,
  m.last_updated                                                                             as mv_last_updated,
  -- asset-risk inputs (kept for audit)
  y.risk_score, x.payment_habit_week, coalesce(np.not_paid_prev_2w, 0) as not_paid_prev_2w,
  coalesce(m.current_week_nd_count, 0) as nd_count_hw,
  y.gps_inactive, coalesce(ml.conn_total, 0) as connects
from m
left join rec r       on r.employee_id    = m.partner_etm and r.hw          = m.hissab_week
left join ml          on ml.partner_et_id = m.partner_etm and ml.week       = m.hissab_week
left join dep_alloc da on da.partner_etm  = m.partner_etm and da.hissab_week = m.hissab_week
left join rc          on rc.employee_id   = m.partner_etm and rc.hw         = m.hissab_week
left join bd          on bd.partner_etm   = m.partner_etm
left join np          on np.partner_etm   = m.partner_etm and np.hissab_week = m.hissab_week
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
order by m.hissab_week, m.city, m.partner_etm;
