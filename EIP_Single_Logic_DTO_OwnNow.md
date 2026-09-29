# EIP / Single split for DTO and Own Now

**Status:** Proposal, awaiting approval
**Table:** `analytics.ssot_alloc_dealloc_full` (Airflow DAG `ssot_alloc_dealloc_full`)

## Context
- Today EIP is identified only from the team's payment model ("Drive To Earn - EIP" / "Drive To Own - EIP").
- EIP teams are set up under **leasing**, so **DTO** and **Own Now** show almost no EIP, even though some of their drivers run several cars.

## Proposed logic
1. **Rule:** Every day, count the cars each DTO and Own Now driver holds at the end of the day (allocated and not yet returned).
   **2 or more cars of the same revenue type = EIP**, **1 car = Single**.
2. **Scope:** DTO and Own Now only. **Leasing is not changed** and keeps using the EIP team / payment model.

## Validation (live data)
EIP + Single adds up to the total, and the total cars match the scorecard (`dto_cars_eod`, `own_now_cars_eod`) exactly.

| Date | Type | EIP drivers | Single drivers | Total drivers | EIP cars | Single cars | Total cars | Scorecard cars | Match |
|---|---|---|---|---|---|---|---|---|---|
| 27-Sep-2026 | DTO | 103 | 3,278 | 3,381 | 521 | 3,278 | 3,799 | 3,799 | ✅ |
| 27-Sep-2026 | Own Now | 65 | 2,908 | 2,973 | 180 | 2,908 | 3,088 | 3,088 | ✅ |
| 21-Sep-2026 | DTO | 105 | 3,398 | 3,503 | 508 | 3,398 | 3,906 | 3,906 | ✅ |
| 21-Sep-2026 | Own Now | 62 | 2,868 | 2,930 | 172 | 2,868 | 3,040 | 3,040 | ✅ |

## Change needed
- Add one column, `eip_single`, in the `ssot_alloc_dealloc_full` Airflow DAG, filled only for DTO and Own Now.
- The columns that existing reports and downstream DAGs read today are unchanged.

## SQL (daily summary)
```sql
WITH days AS (
    SELECT d::date AS dt
    FROM generate_series(CURRENT_DATE - INTERVAL '60 days', CURRENT_DATE, INTERVAL '1 day') d
),
held AS (   -- cars held at the end of each day (DTO and Own Now only)
    SELECT dy.dt, a.city, a.fuel_type, a.revenue_type, a.employee_id, a.allocation_id
    FROM days dy
    JOIN analytics.ssot_alloc_dealloc_full a
      ON a.allocation_date <= dy.dt
     AND (a.jama_id IS NULL OR a.jama_date > dy.dt)
    WHERE a.revenue_type IN ('DTO', 'Own Now')
),
drv AS (    -- cars per driver per day, within the same revenue type
    SELECT dt, city, fuel_type, revenue_type, employee_id,
           COUNT(DISTINCT allocation_id) AS total_cars
    FROM held
    GROUP BY 1, 2, 3, 4, 5
)
SELECT
    dt AS date, city, fuel_type, revenue_type,
    COUNT(*) FILTER (WHERE total_cars > 1)                     AS eip_drivers,
    COUNT(*) FILTER (WHERE total_cars = 1)                     AS single_drivers,
    COUNT(*)                                                   AS total_drivers,
    COALESCE(SUM(total_cars) FILTER (WHERE total_cars > 1), 0) AS eip_cars,
    COALESCE(SUM(total_cars) FILTER (WHERE total_cars = 1), 0) AS single_cars,
    SUM(total_cars)                                            AS total_cars
FROM drv
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 4, 2, 3;
```
