-- Calling Masterlist V2.0 > Current_BadDebt (Raja's Monday query). F bad_debt = same logic as the old F2 formula. Guard: fails (no write) if this week's bad_debt_mv has < 5000 pilots.
WITH current_data AS (
  SELECT DISTINCT ON (a.partner_etm)
    a.partner_etm AS partner_et_id, a.city, a.product_type,
    COALESCE(a.total_os, 0) + COALESCE(a.total_collected_100_pct, 0) AS net_os,
    COALESCE(a.week_end_deposit, 0) AS deposit
  FROM analytics.collections_bad_debt_mv a
  WHERE a.hissab_week::date = DATE_TRUNC('week', CURRENT_DATE)::date AND a.for_collections = 1
  ORDER BY a.partner_etm, a.id DESC
),
attrition AS (
  SELECT DISTINCT s.employee_id AS partner_et_id
  FROM analytics.ssot_alloc_dealloc_full s
  WHERE s.jama_date::date >= DATE_TRUNC('week', CURRENT_DATE)::date - 7
    AND s.jama_date::date < DATE_TRUNC('week', CURRENT_DATE)::date
    AND NOT EXISTS (
      SELECT 1 FROM analytics.ssot_alloc_dealloc_full s2
      WHERE s2.employee_id = s.employee_id AND s2.allocation_date::date <= CURRENT_DATE
        AND COALESCE(s2.jama_date::date, DATE '9999-12-31') >= CURRENT_DATE)
)
SELECT
  c.partner_et_id,
  c.city,
  c.product_type,
  c.net_os,
  c.deposit,
  CASE WHEN c.product_type = 'Own Now' THEN c.net_os WHEN c.net_os + c.deposit < 0 THEN c.net_os + c.deposit ELSE 0 END AS bad_debt,
  CASE WHEN a.partner_et_id IS NOT NULL THEN 'Yes' ELSE 'No' END AS attrition,
  to_char(NOW() AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS last_updated_at
FROM current_data c
LEFT JOIN attrition a ON a.partner_et_id = c.partner_et_id
WHERE (SELECT 1 / (count(*) / 5000) FROM current_data) IS NOT NULL
ORDER BY c.city, c.product_type, c.partner_et_id
