# Lakshya 15,000 — weekly supply plan

`build_weekly_supply_plan.py` writes the workbook behind the Google Sheet
"Lakshya 15,000 - Weekly Supply Plan (21 Sep - 31 Dec 2026)".

- 9 tabs: `Lakshya vs Plan` (comparison for sharing), `Inputs`, and one tab per city (Mumbai, Delhi NCR, Bangalore, Hyderabad, Chennai, Kolkata, Pune).
- Targets come from `Lakshya_15000_Model_v4.xlsx` (the CEO's AOP does not match it, so it is reference only).
- Opening position: reporting DB `analytics.ssot_scorecard_agg`, CNG, Sun 20 Sep 2026.
- City tabs follow the column layout of the existing Weekly Supply Plan sheet (A–Z); the Lakshya
  build-up (EIP / Own Now / Leasing+DTO) sits to the right in AC–AW. Every city cell is a formula
  that reads the `Inputs` tab.

```
python3 build_weekly_supply_plan.py out.xlsx
```
