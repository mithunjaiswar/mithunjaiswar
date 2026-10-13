-- Car recovery cases, same logic as the Central Car Recovery Dash "RawData" query
-- (rec_tags_id 111 = Completed, 112/113 = Cancelled, else Pending; close date = last
-- complete/failed/cancelled status log). Only the columns the Collections dashboard needs.
SELECT
    a.id                                                        AS recovery_id,
    DATE_TRUNC('week', a.activation_date)::date                 AS week_start,
    CASE WHEN a.rec_tags_id IN (111, 112, 113)
         THEN DATE_TRUNC('week', COALESCE(ls.close_date, a.updated_at AT TIME ZONE 'Asia/Kolkata'))::date
         ELSE DATE '2099-12-28' END                             AS close_week,
    CASE WHEN a.rec_tags_id = 111 THEN 'Completed'
         WHEN a.rec_tags_id IN (112, 113) THEN 'Cancelled'
         ELSE 'Pending' END                                     AS final_status,
    COALESCE(a.cancel_reason, '')                               AS cancel_reason,
    CASE WHEN cc.activation_date IS NOT NULL THEN 1 ELSE 0 END  AS has_checkin,
    ROUND((EXTRACT(EPOCH FROM (COALESCE(ls.close_date, NOW()) - a.activation_date)) / 3600.0)::numeric, 1) AS tat_hrs,
    COALESCE(fd.employee_id, fd2.employee_id)                   AS partner_etid,
    a.recovery_agent_id
FROM recovery_cars a
LEFT JOIN LATERAL (
    SELECT b.datetime AS close_date
    FROM recovery_status_logs b
    WHERE b.recovery_id = a.id AND b.recovery_status IN ('complete', 'failed', 'cancelled')
    ORDER BY b.id DESC LIMIT 1
) ls ON TRUE
LEFT JOIN fleet_driver fd ON fd.id = a.driver_id
LEFT JOIN car_checkin cc ON cc.id = a.checkin_id
LEFT JOIN LATERAL (
    SELECT ca.driver_id
    FROM car_allocation ca
    WHERE ca.deactivation_date IS NULL AND ca.driver_id IS NOT NULL
      AND ca.car_id = a.car_id AND ca.allocation_date <= a.activation_date
    ORDER BY ca.id DESC LIMIT 1
) alloc ON a.driver_id IS NULL
LEFT JOIN fleet_driver fd2 ON fd2.id = alloc.driver_id
WHERE a.activation_date < :week_to + 7
  AND (ls.close_date >= :week_from OR ls.close_date IS NULL OR a.rec_tags_id NOT IN (111, 112, 113));

-- Weekly metrics per partner (W = hisaab week), matching the Recovery Dash Weekly_Summary:
--   recovery_initiated   : week_start = W                                   (Current Week Recovery Cases)
--   recovery_brought_fwd : week_start < W and close_week >= W               (Carryforward Recovery Cases)
--   recovered_team       : final_status = Completed and close_week = W      (Completed Car Recovery)
--   recovered_organic    : final_status = Cancelled and close_week = W and
--                          (cancel_reason = 'Driver Dropped Vehicle' or checkin exists)
--   recovery_pending     : week_start <= W and close_week > W               (Overall Pending Recovery)
--   recovery_tat_hrs     : AVG(tat_hrs) of Completed cases closed in W      (Completed Avg. TAT)
