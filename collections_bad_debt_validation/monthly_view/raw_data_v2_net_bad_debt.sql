-- =====================================================================================
-- Collections Monthly View > Raw_Data_V2: old vs new collection and bad debt, + NET bad debt (26-Nov-2026)
-- One row per month x product x city (no GROUPING SETS total rows: the dash adds them up, so no double count).
-- old = deposit_to_os counted as collection and deposit adjusted against next-week OS (old method)
-- new = deposit_to_os NOT counted as collection, no deposit adjustment (new method)
-- net bad debt = bad debt - bad_debt_collected (what was recovered later against it), never below 0
-- Fixes vs the earlier version:
--   1. product_type is 'Own Now' in collections_bad_debt_mv (the old 'OWN' check never matched)
--   2. inactive = no next-week row (next_weekly_os IS NULL) or next_weekly_os = 0 (only '= 0' before; almost all leavers are NULL)
-- =====================================================================================
WITH base AS MATERIALIZED (
    SELECT
        DATE_TRUNC('month', a.hissab_week)::date AS month,
        a.hissab_week,
        a.city,
        a.product_type,
        a.partner_etm,
        ABS(a.total_os)::numeric AS total_os,
        GREATEST(-COALESCE(a.next_total_os, 0), 0)::numeric AS next_total_os,
        a.next_weekly_os,
        GREATEST(COALESCE(a.week_end_deposit, 0), 0)::numeric AS week_end_deposit,
        GREATEST(COALESCE(a.bad_debt_collected, 0), 0)::numeric AS bad_debt_collected
    FROM analytics.collections_bad_debt_mv a
    WHERE a.driven_week >= DATE '2025-12-29'
      AND a.total_os < 0
      AND a.for_collections = 1
),
recovery AS MATERIALIZED (
    SELECT
        DATE_TRUNC('week', r.date)::date AS hissab_week,
        r.employee_id AS partner_etm,
        COALESCE(SUM(r.amount) FILTER (WHERE r.recovery_type IN
            ('razorpay_recovery','other_positive_recovery','phonepe_recovery','positive_adjustment')), 0)::numeric AS collected_ex_dto,
        COALESCE(SUM(r.amount) FILTER (WHERE r.recovery_type = 'deposit_to_os'), 0)::numeric AS deposit_to_os_amount
    FROM public.mv_daily_recovery r
    JOIN (SELECT DISTINCT hissab_week, partner_etm FROM base) b
      ON b.hissab_week = DATE_TRUNC('week', r.date)::date AND b.partner_etm = r.employee_id
    WHERE r.date >= DATE '2025-12-01'
      AND r.recovery_type IN ('razorpay_recovery','other_positive_recovery','phonepe_recovery','positive_adjustment','deposit_to_os')
    GROUP BY 1, 2
),
calc AS (
    SELECT
        b.*,
        CASE WHEN b.next_weekly_os IS NULL OR b.next_weekly_os = 0 THEN 1 ELSE 0 END AS is_inactive,
        LEAST(b.total_os, GREATEST(COALESCE(r.collected_ex_dto, 0), 0)) AS new_collection_amount,
        LEAST(b.total_os, GREATEST(COALESCE(r.collected_ex_dto, 0) + COALESCE(r.deposit_to_os_amount, 0), 0)) AS old_collection_amount
    FROM base b
    LEFT JOIN recovery r ON r.hissab_week = b.hissab_week AND r.partner_etm = b.partner_etm
),
bd AS (
    SELECT
        c.*,
        CASE WHEN c.product_type = 'Own Now' AND c.is_inactive = 0 THEN 0
             ELSE GREATEST(c.next_total_os - LEAST(c.next_total_os, c.week_end_deposit), 0) END AS old_bad_debt_amount,
        CASE WHEN c.product_type = 'Own Now' AND c.is_inactive = 0 THEN 0
             ELSE GREATEST(c.total_os - c.new_collection_amount, 0) END AS new_bad_debt_amount
    FROM calc c
),
fin AS (
    SELECT
        bd.*,
        bd.old_bad_debt_amount - LEAST(bd.old_bad_debt_amount, bd.bad_debt_collected) AS old_net_bad_debt_amount,
        bd.new_bad_debt_amount - LEAST(bd.new_bad_debt_amount, bd.bad_debt_collected) AS new_net_bad_debt_amount
    FROM bd
)
SELECT
    month,
    product_type AS product,
    city,
    ROUND(SUM(total_os))                                   AS total_os,
    ROUND(SUM(old_collection_amount))                      AS old_collection,
    ROUND(SUM(new_collection_amount))                      AS new_collection,
    ROUND(SUM(old_bad_debt_amount))                        AS old_bad_debt,
    ROUND(SUM(new_bad_debt_amount))                        AS new_bad_debt,
    ROUND(SUM(LEAST(old_bad_debt_amount, bad_debt_collected))) AS old_bad_debt_recovered,
    ROUND(SUM(LEAST(new_bad_debt_amount, bad_debt_collected))) AS new_bad_debt_recovered,
    ROUND(SUM(old_net_bad_debt_amount))                    AS old_net_bad_debt,
    ROUND(SUM(new_net_bad_debt_amount))                    AS new_net_bad_debt,
    COUNT(DISTINCT partner_etm)                            AS total_partners,
    COUNT(DISTINCT partner_etm) FILTER (WHERE old_bad_debt_amount > 0) AS old_bad_debt_partners,
    COUNT(DISTINCT partner_etm) FILTER (WHERE new_bad_debt_amount > 0) AS new_bad_debt_partners,
    COUNT(DISTINCT partner_etm) FILTER (WHERE old_net_bad_debt_amount > 0) AS old_net_bad_debt_partners,
    COUNT(DISTINCT partner_etm) FILTER (WHERE new_net_bad_debt_amount > 0) AS new_net_bad_debt_partners,
    TO_CHAR(NOW() AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS last_updated
FROM fin
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
