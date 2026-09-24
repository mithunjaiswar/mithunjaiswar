# Lakshya 15,000 — weekly supply plan

`build_weekly_supply_plan.py` writes the workbook behind the Google Sheet
"Lakshya 15,000 - Weekly Supply Plan (21 Sep - 27 Dec 2026)".

- 10 tabs: `Lakshya vs Plan` (comparison for sharing), `Inputs`, one tab per city (Mumbai, Delhi NCR, Bangalore,
  Hyderabad, Chennai, Kolkata, Pune) and `raw_performance` (output of the SSOT query).
- Each city tab shows the last 4 actual weeks (read from `raw_performance`) and then the 14 plan weeks to w/e 27 Dec.
- Targets come from `Lakshya_15000_Model_v4.xlsx` (the CEO's AOP does not match it, so it is reference only).
- Opening position: `raw_performance` (SSOT query on `analytics.ssot_scorecard_agg`), CNG, Sun 20 Sep 2026.
- City tabs follow the column layout of the existing Weekly Supply Plan sheet (A–Z); the Lakshya
  build-up (EIP / Own Now / Leasing+DTO) sits to the right in AC–AW. Every city cell is a formula
  that reads the `Inputs` tab.

```
python3 build_weekly_supply_plan.py out.xlsx raw.json   # raw.json = {"hdr": [...], "data": [[...]]} from the SSOT query
```
