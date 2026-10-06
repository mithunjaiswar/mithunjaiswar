# Collections Bad Debt – PG vs Sheet validation

Compares every column of `analytics.collections_bad_debt_mv` (PG) with the `Raw_Data` tab of the
Collections Bad Debt Google Sheet, joined on `hisaab_week + partner ET ID`, for the last 3 hisaab weeks
(21-Sep, 28-Sep, 05-Oct-2026 in the first run).

`public.collections_bad_debt_mv` exists but is empty; the populated table is `analytics.collections_bad_debt_mv`.

## Inputs (kept out of git – they contain partner-level data)

Put these in one working directory `<D>`:

| File | How it was produced |
|---|---|
| `sheet.csv` | `Raw_Data` rows of the 3 weeks (first column `sheet_row`, then the 74 sheet columns) |
| `pg.csv` | all 53 columns of `analytics.collections_bad_debt_mv` for the same weeks (NULL -> empty) |
| `habit.pkl` | `{employee_id: {week_start_date: payment_habit}}` from `driver_repayment_habit` |
| `crm_lead.json` | optional, `{employee_id: lead_id}` from `crm.lead_driver` for the lead_id mismatches |

## Run

```
python3 validate.py <D>          # agent-level comparison + reasons  -> <D>/out/*.pkl
python3 build_outputs.py <D>     # column x week, week x city, reason summary
python3 export_xlsx.py <D> out/Collections_BadDebt_PG_vs_Sheet_Validation.xlsx
python3 sheet_payloads.py <D>    # compact tables written to the PG_Validation_* tabs of the Sheet
```

## Matching rules

* Amounts: Matched when |PG - Sheet| <= 1 (rounding). IDs, counts, days, flags: exact.
* Text: trimmed, case-insensitive. Dates: exact (Sheet date serials converted to ISO dates).
* Every PG column is listed in `validate.py` (`specs`); the script asserts none is missing. Columns with
  no Sheet equivalent are reported as "Not in Sheet" with the PG total.
* Each mismatch gets a reason from column-specific rules (definition difference, PG issue, Sheet issue,
  timing of the in-progress week). Anything not explained by a rule is "Need to Deep Dive".
