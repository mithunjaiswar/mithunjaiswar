# 7 city Agent Tracking sheets: automation queries (2 tabs per city)

Add 14 rows in **SQL query Automation > collections_queries** (2 per city). Copy each query from the `.sql` file, **not** from a sheet cell (a copied cell doubles the `"` and the query fails).

| City | Sheet ID |
|---|---|
| Bangalore | `1cqtYRXzgrfT9C32oPo50JY0jUDbd0j2LGIHgXAaDv3g` |
| Chennai | `192b4gADIm3KfvshyjeuEvP0DGgVgIPzGehe_uChnE4I` |
| Delhi NCR | `1EgvSmWCBriuIhZWg3XNI5_Smz-U3YwIS4xZ5ohtZIDc` |
| Hyderabad | `1GLzLpDT8enQgXEjmxkuRAypxbToBY8UYiMxnocERGjE` |
| Kolkata | `1vPodl3Ds77tyFT7FAk4F7fYAu9A5RSdC8NRF5Y2MmZI` |
| Mumbai | `1sGaKUCpf1JCqgvoBulZ21oZ8mKWnKbHpJwRGvyfeQGw` |
| Pune | `1YLqE7H-itBtb76LRTOKCAmR28ttQwzu_pNkplAweiso` |

## Row settings

| Tab (E) | Query file (B) | C Clear | F Start | H Clear range | G Run | M (schedule formula) |
|---|---|---|---|---|---|---|
| `Agent_Action` | `agent_action_<city>.sql` | Yes | `A1` | `BP` | TRUE | `=AND(HOUR(NOW())>=8, HOUR(NOW())<=20, MINUTE(NOW())>=15)` (hourly 8-20) |
| `Calling_Masterlist` | `calling_masterlist_<city>.sql` | Yes | `A3` | `BX` | TRUE | `=AND(HOUR(NOW())=7, MINUTE(NOW())>=15)` (**once a day, 7:15 AM**) |

## What each query gives

**Agent_Action** (68 columns, A:BP, same header as the tab today)
- India Collections Raw_Data logic, last 5 hisaab weeks (current week on top), sorted worst to best (asset_risk, then OS).
- Day-wise attempts / connects (Mon-Sun), till Tue / till Wed, last attempt / connect time, last 3 dispositions.
- `hawkeye_username` = the agent this sheet had for the pilot that week (from `mv_collections_calling_masterlist`, the 23:00 snapshot of the sheet).
- `ameyo_username` = the Ameyo id that most often called that agent's pilots in the last 28 days. `NA` when not known.
- Kolkata test: 3,394 rows, 5 weeks (19-Oct to 16-Nov), ~1 min.

**Calling_Masterlist** (64 data columns, A:BL; data from row 3 - keep the header in row 2, the automation writes no header when the start cell is not A1)
- Same MasterTab logic as the zero sheet `Agent_action` (fast version, ~1.5 min), filtered to the city.
- `agent_username` and `actioning_type` = latest value from the 23:00 snapshot (last 14 days). New pilots with no snapshot yet stay blank until the city fills `Agent_Mapping`.
- Clear range `BX` also clears yesterday's agent captures (BM:BX). The 23:00 snapshot has already saved them to the DB, and they show up again as "Yesterday Remarks".

## Why Calling_Masterlist runs only once a day
Agents type Call Status / Disposition / Remarks into BM:BX during the day. An hourly refresh re-orders the rows (new allocations, OS changes), so the typed captures would end up next to the wrong pilot or be wiped. Run it at 7:15 AM, after the 23:00 snapshot and before calling starts. Agent_Action has no input columns, so it is safe to run hourly.

## After the first run
- `Calling_Masterlist!A1` has a fixed "Updated: …" formula from the old script. Change it to `="Updated: "&TEXT(B3,"dd-mmm hh:mm")` so it shows the real load time.
- Check one city first (Kolkata is the smallest), then add the other 6.

Rebuild all 14 files: `python3 build_city_queries.py` (reads `../zero_deposit_dash/agent_action_masterlist.sql`).
