# Collections Dashboard (PG) — Context File

Last updated: 2026-10-14. Branch: `claude/eager-brahmagupta-iwbp63`.
This file is the hand-over: read it first before continuing work.

---

## 1. Goal

- Rebuild the old **Collections Sheet** as a new dashboard fed only by SQL queries on the
  Everest Reporting DB (Postgres, read-only), mainly the MV `analytics.collections_bad_debt_mv`.
- When the user refreshes the queries and pastes the output into the data tabs, every tab must show the right numbers.
- Raw_Data must use the **same columns as the old sheet** (names and order), so the old sheet's tabs work unchanged.

## 2. Google files

| What | ID / link |
|---|---|
| Old Collections Sheet (reference, **read-only — never edit**) | `1wkebsPPLwXnRYAuvRV_fhMGQLRxv6JwH-cYlaIEBjRw` |
| New dashboard (the one we build) | `1fi21Yi8l1bw33VMxqUpxCDkHYA_QV1_P26ghaYIn-GY` |
| Copy of old sheet (used for filter tests) | `1DdTEVKrCMyKZPqdoEm5FDFb6s1LAdo570KuKmjClpm4` |
| Central Car Recovery Dash (source of recovery logic) | `1m5QN8rFwnQLl7mmmLNGNqvjQHxGzWyLhcItPzJBq9a4` |
| SD Bucket sheet (old source of sd_bucket / sd_bucket_V2) | `1p79ci0sBLcCkE8hOCLOeWI8lUG41SVKZp2WYeoEuLMM` |
| 28-Sep validation sheet | `111cJwcbWhg5Rxj6BxdfX9nvr8iWIHUZOPBOPB0SY868` |
| Doc — Query 1 Raw_Data | `174FcWeD4sx-1bXYw2jnsfRUM0OL_vYxdSJUqzTcleTk` |
| Doc — Query 2 Deposit_Raw | `1iVBIDBUSsxPDxzRkHjiTF3GT-XVBBFVVQPgs6FzuFsY` |
| Doc — Query 3 Recovery_Raw | `1ofNMx52vc7cgm0yd9c1_JuES1sjRMZvmxc9DFZd2nUY` |
| Old single SQL doc (outdated, not maintained) | `1SaerOv47v1qfmTnN9gK03Nez_h1KoQzZiuCncmPuWZw` |

## 3. Dashboard tabs

| Tab | Type | Fed by |
|---|---|---|
| Metric_Summary | comparison old Sheet vs MV | script `write_doc3.py` |
| Summary_City_Product | city/product comparison + Logic, Example, Difference reason, Employee example | `city_product_check.py`, `city_product_tab.py`, `metric_notes.py` |
| Summary | formulas | Raw_Data, Deposit_Raw, Recovery_Raw, City_Targets |
| WBR | formulas | Raw_Data |
| Ownership_Dash | copied from old sheet (formulas) | Raw_Data + Ownership_CR_Import |
| OwnNow Analysis | copied from old sheet | Raw_Data |
| SD_Profiles | copied from old sheet | sd_bucket |
| SD_Profiles [At Allocation] | copied from old sheet | sd_bucket_V2 |
| Raw_Data | data | **Query 1** |
| City_Targets | targets + formulas | Raw_Data |
| Deposit_Raw | data | **Query 2** |
| Recovery_Raw | data | **Query 3** |
| sd_bucket | data | **Query 4** (not loaded yet) |
| sd_bucket_V2 | data | **Query 5** (not loaded yet) |
| Ownership_CR_Import | data | **Query 6** (not loaded yet) |
| Query | user's own layout: 3 names, each hyperlinked to its doc | **do not rebuild this tab**; only add links |

## 4. Queries (`final_raw_data.sql` holds all 6)

| # | Tab | Grain | Notes |
|---|---|---|---|
| 1 | Raw_Data | pilot × hisaab week (MV, `for_collections = 1`) | Columns A..BS = old sheet Raw_Data, same names/order; + BT `os_surpass_deposit_amt`, BU `bad_debt_collected_nonfunnel`, BV `mv_last_updated` (74 cols) |
| 2 | Deposit_Raw | pilot who held a car in the week (allocation table) | cols: week, partner, city, fuel, product (old SD rule), last_alloc_date, G `deposit_week_end`, H `deposit_at_alloc_week_end` (`in_mv` dropped) |
| 3 | Recovery_Raw | recovery case × week it is open | Same rules as Central Car Recovery Dash; matches it exactly |
| 4 | sd_bucket | week × city × fuel × payment_model | deposit buckets by `deposit_week_end` |
| 5 | sd_bucket_V2 | same | buckets by `deposit_at_alloc_week_end` |
| 6 | Ownership_CR_Import | week × product × city (last 8 weeks) | same as Recovery Dash `Ownership_CR_Aggregate_City`; negative OS = pilot's MV total_os that week |

Window: last 10 hisaab weeks (`63 days` in the `wk` CTE). Hisaab week = Monday–Sunday.

### Key rules inside the queries
- Collections split (P..T) = waterfall razorpay → other → phonepe → adjustment → deposit-to-rent, each capped at OS still unpaid.
- `recovery_pct` (V) = U / |E|, 1 when OS ≥ 0, capped at 1.
- `entire_week_active` (AC) = car allocated on all 7 days (swap cases counted).
- `not_paid_last_2_weeks` (AA) = count of previous 2 weeks with 0 collection. The MV column `partners_not_paid_2_weeks` was **dropped from the MV**.
- Funnel: AX `bad_debt_rec` = next-week payments; AY = min(AX, |bad debt|); AZ = AY + AW.
- OS bifurcation: AQ = min(prev CF, 0), AR = E − AQ, AS = min(U, −AQ), AT = U − AS, AV = E + U, AP = min(AV, 0).
- Buckets BE (by AP), BG (by BH = week-start deposit), BI (by tenure).
- BK `uber_tenure_tag`, BL `source_channel` from `mv_elc_upload_data` (latest non-blank), blank when not in ELC (~50%).
- BM/BN car recovery start / end (end = today if still pending); BO = MV `recovery_tat`.
- BP first day tagged `Critical_Risk` in the calling masterlist that week.
- BS `allocation_location` = hub of latest allocation (`ssot_alloc_dealloc_base.location`).
- AJ attempts, AM et_rank from calling masterlist (old source unknown — low match).
- B `location` = city (not used by any formula).
- Recovery cases: `rec_tags_id` 111 Completed, 112/113 Cancelled, NULL/else Pending (use `coalesce(rec_tags_id,0)`);
  reason = `payment_reason` for Completed, `cancel_reason` otherwise; team = Completed with blank reason (before 07-Sep all Completed);
  product from team at activation, skipping bad team rows (end_date < start_date).
- Deposit product rule (old SD sheet): Fixed Pay (pm 3) > EIP (7/8) > D2O (6) > Own Now (9) > EV (model ids) > Revenue Share (1) > SINGLE, by car's current team.

## 5. Raw_Data column move (done 14-Oct)
Summary / WBR / City_Targets formulas were moved from the old 59-col layout to the new one with `remap_raw_cols.py`
(map: A→A, B→D, D→F, F→H, H→AO, J→AN, K→AD, L→BC, M→E, P→I, Q→U, R→O, T→P, U→Q, V→R, W→S, X→T,
Z→AF, AB→AC, AF→BB, AJ→BT, AK→AW, AL→BU, AM→AY, AN→AL, AO→AH, AY→BV, BB→AA, BF→AU, BG→AQ;
old AV>0 "recovery pending" → BN > week end and BM ≤ week end). Backups of old formulas: `dash/formulas_before_remap_*.json` (scratchpad).
Payment Behaviour rows now use AF `payment_habit` (old sheet logic) instead of MV `last_week_payment_habit`.

## 6. Status (14-Oct)

Done:
- Queries 1–3 run and match the sheet; Raw_Data (113,933 rows × 74 cols), Deposit_Raw, Recovery_Raw loaded from query output.
- Summary / WBR / City_Targets formulas moved to new layout; numbers unchanged (e.g. DP to OS 14-Sep = 2,633.3K).
- 4 tabs copied from old sheet; 3 empty source tabs created with headers.
- Queries 4–6 written (in `final_raw_data.sql`), **not run yet**.

Next steps:
1. Run Queries 4, 5, 6 (one at a time) and load into sd_bucket, sd_bucket_V2, Ownership_CR_Import (`load_query_tab.py`).
   Cross-check sd_bucket against a recount from Deposit_Raw.
2. Check the 4 tabs show numbers (Ownership_Dash, OwnNow Analysis, SD_Profiles x2).
3. Update the 3 docs (`query_docs.py`) with the new Query 1 and add docs + links for Queries 4–6
   (Query tab: keep user layout — names hyperlinked; add 3 new rows the same way).
4. Commit + push.

Known gaps to tell the user:
- 07-Sep asset risk: calling masterlist has no connects for most pilots → "No risk" low (source data gap).
- Columns from masterlist / ELC (attempts, et_rank, uber tag, source channel) do not fully match the old sheet.
- Old sheet columns BT..BW not kept (10M cell limit). Cell budget is tight (~9.8M): don't add Raw_Data columns.

## 7. How to work (gotchas)

- Sheets API helper: `exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])` → `call`, `API`, headers `H`.
  **Never name a variable `H`** (clashes with auth headers). Auth token file is local to the session (not in repo).
- DB MCP: read-only, 60 s timeout. Big results are saved to a tool-results file; parse lines starting `| ` split on `~`.
  Query 1 must run **one week at a time** (replace `wk` with `select date 'YYYY-MM-DD' as hw`); ~60 s per week.
  The DB crashed once under repeated heavy queries — run one query at a time with pauses.
- Google Sheets cell limit 10M per file.
- Scratchpad (`/tmp/claude-0/.../scratchpad`) is temporary; scripts that matter are copied into this folder.
- User style: short, simple sentences; bullet points; don't change header colours; don't delete user tabs;
  never edit the old reference sheet; don't create PRs unless asked.
