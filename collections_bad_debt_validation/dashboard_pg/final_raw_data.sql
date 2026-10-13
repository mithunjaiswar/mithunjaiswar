-- =====================================================================================
-- Collections Dashboard (Summary + WBR) - consolidated Raw_Data query
-- Grain : PART 1 = 1 row per partner per hisaab week (analytics.collections_bad_debt_mv, for_collections = 1)
--         PART 2 = 1 row per car recovery case per hisaab week (row_type = 'Recovery case')
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
  select distinct on (week, partner_et_id) week, partner_et_id, elc_filter, conn_total,
         current_week_gps_kms, current_week_uber_kms
  from mv_collections_calling_masterlist
  where week in (select hw from wk)
  order by week, partner_et_id, snapshot_date desc
),
-- [MISSING 3] deposit AT ALLOCATION (Active pilots): deposit balance on the day of the LAST
--   allocation BEFORE the hisaab week starts (allocation_date < hissab_week).
--   Pilot first allocated inside the week (no earlier allocation) -> that allocation is used.
alloc as (
  select m.hissab_week, m.partner_etm,
         coalesce(max(s.allocation_date) filter (where s.allocation_date < m.hissab_week),
                  min(s.allocation_date) filter (where s.allocation_date >= m.hissab_week))::date as alloc_date
  from m
  join analytics.ssot_alloc_dealloc_base s
    on s.employee_id = m.partner_etm and s.allocation_date < m.hissab_week + 7
  where m.active_inactive_flag = 'Active'
  group by 1, 2
),
dep_alloc as (
  select a.hissab_week, a.partner_etm, a.alloc_date, d.dep_at_alloc
  from alloc a
  cross join lateral (
    select coalesce(sum(x.amount), 0) as dep_at_alloc
    from mv_deposits_raw x
    where x.employee_id = a.partner_etm
      and x.date::date <= a.alloc_date
      and x.deposit_type not in ('SD_TO_OWNNOW', 'OWNNOW_TO_OWNNOW')
  ) d
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
    coalesce(a.cancel_reason, '') as reason,
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
    and (a.rec_tags_id not in (111, 112, 113) or coalesce(ls.close_date, a.updated_at) >= (select min(hw) from wk))
),
rc as (
  select c.employee_id, w.hw,
    count(*) filter (where c.week_start = w.hw)                                                   as recovery_initiated,
    count(*) filter (where c.week_start < w.hw)                                                   as recovery_brought_fwd,
    count(*) filter (where c.close_week = w.hw and c.final_status = 'Completed' and c.reason = '') as recovered_team,
    count(*) filter (where c.close_week = w.hw and c.final_status = 'Cancelled'
                       and (c.reason = 'Driver Dropped Vehicle' or (c.reason = '' and c.has_checkin))) as recovered_organic,
    count(*) filter (where c.close_week > w.hw)                                                   as recovery_pending,
    round(avg(c.tat_hrs) filter (where c.close_week = w.hw and c.final_status = 'Completed' and c.reason = '')::numeric, 1) as recovery_tat_hrs,
    min(c.agent_name) filter (where c.close_week = w.hw and c.final_status = 'Completed' and c.reason = '') as recovery_agent
  from rcase c
  join wk w on c.week_start <= w.hw and c.close_week >= w.hw
  group by 1, 2
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
                 range between interval '14 days' preceding and interval '1 day' preceding) as not_paid_prev_2w
  from analytics.collections_bad_debt_mv
  where for_collections = 1
    and hissab_week >= (select min(hw) from wk) - 14
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
  m.total_collected_100_pct,
  least(coalesce(m.collection_till_wed, 0), abs(coalesce(m.total_os, 0)))                    as till_wed_100pct,  -- capped at OS (Sheet col O)
  m.os_to_deposit,
  -- collection split (mv_daily_recovery), Sheet waterfall: each mode capped at OS still unpaid,
  -- order razorpay -> other -> phonepe -> adjustment -> deposit-to-rent (Sheet cols P..T)
  sp.razorpay_100pct, sp.other_100pct, sp.phonepe_100pct, sp.adjustment_100pct, sp.deposit_to_rent_100pct,
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
  case when m.bad_debt_amount < 0
       then least(coalesce(bdn.next_week_paid, 0), abs(m.bad_debt_amount)) else 0 end      as bad_debt_collected_funnel, -- next-week payment, capped at bad debt
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
  rc.recovery_tat_hrs, rc.recovery_agent,
  m.last_updated                                                                             as mv_last_updated,
  -- asset-risk inputs (kept for audit)
  y.risk_score, x.payment_habit_week, coalesce(np.not_paid_prev_2w, 0) as not_paid_prev_2w,
  coalesce(m.current_week_nd_count, 0) as nd_count_hw,
  y.gps_inactive, coalesce(ml.conn_total, 0) as connects,
  -- advance collection (old advance_payment_data tab): paid above the week OS, excluding deposit-to-OS
  greatest(coalesce(m.total_collected_amount_in_week, 0) - abs(coalesce(m.total_os, 0)), 0) as advance_amount,  -- paid above OS (Sheet col AU)
  -- WBR CarryForward (OS bifurcation) counts only OS carried forward (negative), not credits
  least(coalesce(m.prev_carryforward_os, 0), 0) as carry_forward_os_neg,
  null::date as rec_week, 'MV' as row_type, null::bigint as recovery_id
from m
left join rec r       on r.employee_id    = m.partner_etm and r.hw          = m.hissab_week
left join ml          on ml.partner_et_id = m.partner_etm and ml.week       = m.hissab_week
left join dep_alloc da on da.partner_etm  = m.partner_etm and da.hissab_week = m.hissab_week
left join rc          on rc.employee_id   = m.partner_etm and rc.hw         = m.hissab_week
left join bdn         on bdn.employee_id  = m.partner_etm and bdn.hw = m.hissab_week
left join np          on np.partner_etm   = m.partner_etm and np.hissab_week = m.hissab_week
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

-- ---- PART 2: car recovery cases (1 row per case per hisaab week it is active) -------------------
--   Same logic as Central Car Recovery Dash (RawData + Weekly_Summary). hissab_week (A) is left blank so
--   these rows never enter MV metrics; Summary recovery rows filter on rec_week (BH) instead.
--   Team = Completed with no reason (before 07-Sep: all Completed, as Recovery Dash); TAT only for team cases.
union all
select
  null as hissab_week,
  c.employee_id as partner_etm,
  null as lead_id,
  c.city as city,
  null as location,
  c.product_type as product_type,
  null as revenue_type,
  c.fuel_type as fuel_type,
  null as eip_filter,
  null as elc_filter,
  null as active_inactive_flag,
  null as in_car_recovery,
  null as total_os,
  null as weekly_os,
  null as prev_carryforward_os,
  null as total_collected_amount_in_week,
  null as total_collected_100_pct,
  null as till_wed_100pct,
  null as os_to_deposit,
  null as razorpay_100pct,
  null as other_100pct,
  null as phonepe_100pct,
  null as adjustment_100pct,
  null as deposit_to_rent_100pct,
  null as partners_not_paid_2_weeks,
  null as last_week_payment_habit,
  null as total_allocated_days,
  null as entire_week_active,
  null as last_payment_date_till_hissab_week,
  null as last_jama_date,
  null as tenure_days,
  null as week_start_deposit,
  null as week_end_deposit,
  null as alloc_date,
  null as dep_at_alloc,
  null as os_surpass_deposit_amt,
  null as bad_debt_amount,
  null as bad_debt_collected_nonfunnel,
  null as bad_debt_collected_funnel,
  null as asset_risk,
  null as recovery_recommended,
  null as cars_under_recovery_hissab_week,
  null as recovery_tat,
  (c.week_start = w.hw)::int as recovery_initiated,
  (c.week_start < w.hw)::int as recovery_brought_fwd,
  (c.close_week = w.hw and c.final_status = 'Completed' and (c.reason = '' or w.hw < date '2026-09-07'))::int as recovered_team,
  (c.close_week = w.hw and c.final_status = 'Cancelled' and ((c.reason = 'Driver Dropped Vehicle' and not c.has_checkin) or (c.reason = '' and c.has_checkin)))::int as recovered_organic,
  (c.close_week > w.hw)::int as recovery_pending,
  case when c.close_week = w.hw and c.final_status = 'Completed' and c.reason = '' then round(c.tat_hrs::numeric, 1) end as recovery_tat_hrs,
  case when c.close_week = w.hw and c.final_status = 'Completed' and c.reason = '' then c.agent_name end as recovery_agent,
  null as mv_last_updated,
  null as risk_score,
  null as payment_habit_week,
  null as not_paid_prev_2w,
  null as nd_count_hw,
  null as gps_inactive,
  null as connects,
  null as advance_amount,
  null as carry_forward_os_neg,
  w.hw as rec_week,
  'Recovery case' as row_type,
  c.id as recovery_id
from rcase c
join wk w on c.week_start <= w.hw and c.close_week >= w.hw
order by 1, 4, 2;

