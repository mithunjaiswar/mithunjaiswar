-- Zero & Low Deposit Monitoring Dashboard > Current_BadDebt (automation, output at A1 incl. header, 10 columns A:J).
-- Same logic as Calling Masterlist V2.0 > Current_BadDebt (Raja's Monday query) + 0 deposit flag + last join.
-- Pilots     = this hisaab week of collections_bad_debt_mv, for_collections = 1 (one row per pilot, latest mv row).
-- net_os     = total_os + total_collected_100_pct (negative = pilot owes).
-- deposit    = week_end_deposit.
-- bad_debt   = net_os + deposit when that is below 0 (owes more than the deposit), else 0.
--              Own Now who LEFT (no car today): full net_os (deposit not adjusted, same rule as collections_bad_debt_mv / weekly_bad_debt).
--              24-Nov fix: Raja's rule took the full net_os of every Own Now pilot -> 100% bad debt for Own Now (active pilots' EMI OS counted).
-- attrition  = returned the car (jama) last week and has no car allocated today.
-- joined_at_0_deposit = latest New Join / Rejoin / Resurrection in the last 8 weeks had deposit 0 at the end of the join day
--              (same rule as 0dp_raw: deposit now - deposits dated after the join day, at least the amount paid on allocation).
-- Guard: fails (no write) if this week's mv has < 5000 pilots.
WITH current_data AS MATERIALIZED (
  SELECT DISTINCT ON (a.partner_etm)
    a.partner_etm AS partner_et_id, a.city, a.product_type,
    COALESCE(a.total_os, 0) + COALESCE(a.total_collected_100_pct, 0) AS net_os,
    COALESCE(a.week_end_deposit, 0) AS deposit
  FROM analytics.collections_bad_debt_mv a
  WHERE a.hissab_week::date = DATE_TRUNC('week', CURRENT_DATE)::date AND a.for_collections = 1
  ORDER BY a.partner_etm, a.id DESC
),
alloc AS MATERIALIZED (   -- has a car today
  SELECT DISTINCT s.employee_id AS etm FROM analytics.ssot_alloc_dealloc_full s
  WHERE s.allocation_date::date <= CURRENT_DATE AND COALESCE(s.jama_date::date, DATE '9999-12-31') >= CURRENT_DATE
),
attrition AS MATERIALIZED (
  SELECT DISTINCT s.employee_id AS partner_et_id
  FROM analytics.ssot_alloc_dealloc_full s
  WHERE s.jama_date::date >= DATE_TRUNC('week', CURRENT_DATE)::date - 7
    AND s.jama_date::date < DATE_TRUNC('week', CURRENT_DATE)::date
    AND NOT EXISTS (SELECT 1 FROM alloc al2 WHERE al2.etm = s.employee_id)
),
lj AS MATERIALIZED (   -- latest join in the last 8 weeks
  SELECT DISTINCT ON (s.employee_id)
    s.employee_id AS etm, s.allocation_date::date AS jd, s.category AS jtype, COALESCE(s.sd_amount, 0) AS sd_amount
  FROM analytics.ssot_alloc_dealloc_full s
  WHERE s.category IN ('New Join', 'Rejoin', 'Resurrection')
    AND s.allocation_date >= DATE_TRUNC('week', CURRENT_DATE)::date - 49 AND s.allocation_date <= CURRENT_DATE
  ORDER BY s.employee_id, s.allocation_date::date DESC, s.allocation_datetime DESC
),
dep AS MATERIALIZED (
  SELECT d.employee_id AS etm,
         SUM(d.amount) AS dep_now,
         SUM(d.amount) FILTER (WHERE d.date::date > j.jd) AS dep_after
  FROM mv_deposits_raw d
  JOIN lj j ON j.etm = d.employee_id
  WHERE d.deposit_type::text <> ALL (ARRAY['OWNNOW_TO_OWNNOW','SD_TO_OWNNOW']::text[])
  GROUP BY 1
),
zdp AS MATERIALIZED (
  SELECT j.etm, j.jd, j.jtype,
         GREATEST(COALESCE(x.dep_now, 0) - COALESCE(x.dep_after, 0), j.sd_amount) AS dep_at_join
  FROM lj j LEFT JOIN dep x ON x.etm = j.etm
)
SELECT
  c.partner_et_id,
  c.city,
  c.product_type,
  c.net_os,
  c.deposit,
  CASE WHEN c.product_type = 'Own Now' AND al.etm IS NULL THEN LEAST(c.net_os, 0) WHEN c.net_os + c.deposit < 0 THEN c.net_os + c.deposit ELSE 0 END AS bad_debt,
  CASE WHEN a.partner_et_id IS NOT NULL THEN 'Yes' ELSE 'No' END AS attrition,
  CASE WHEN z.dep_at_join = 0 THEN 'Yes' ELSE 'No' END AS joined_at_0_deposit,
  COALESCE(to_char(z.jd, 'YYYY-MM-DD'), '-') AS last_join_date,
  to_char(NOW() AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS last_updated_at
FROM current_data c
LEFT JOIN attrition a ON a.partner_et_id = c.partner_et_id
LEFT JOIN alloc al ON al.etm = c.partner_et_id
LEFT JOIN zdp z ON z.etm = c.partner_et_id
WHERE (SELECT 1 / (count(*) / 5000) FROM current_data) IS NOT NULL
ORDER BY c.city, c.product_type, c.partner_et_id
