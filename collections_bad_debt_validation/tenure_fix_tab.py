"""Add / replace 'Tenure_Script_Fix' tab: tenure_days = tenure till the DRIVEN week end (hissab_week - 1).
Usage: python3 tenure_fix_tab.py <D> <token.json>"""
import sys, json, time
import requests

D, TOKEN = sys.argv[1], sys.argv[2]
API = 'https://sheets.googleapis.com/v4/spreadsheets'
TAB = 'Tenure_Script_Fix'

RULE_SQL = """-- Put this in the PG script that builds analytics.collections_bad_debt_mv
-- (replace the current tenure_days logic). One rule for ALL partners:
-- tenure = all days the partner was with us (every driver_profile stint), counted till the DRIVEN week end.
tenure_fix as (
  select m.hissab_week, m.partner_etm,
         coalesce(sum(least(coalesce(dp.end_date::date, m.hissab_week - 1), m.hissab_week - 1)
                      - dp.start_date::date + 1)
                  filter (where dp.start_date::date <= m.hissab_week - 1), 0) as tenure_days
  from <mv base rows> m
  left join fleet_driver fd on fd.employee_id = m.partner_etm
  left join driver_profile dp on dp.driver_id = fd.id
  group by m.hissab_week, m.partner_etm)
-- driven week end = hissab_week - 1 (Sunday of the driven week). Stints that ended earlier count fully,
-- the running stint is cut at the driven week end, stints that start later are not counted."""

PREVIEW_SQL = """-- PREVIEW before deploying (read only, run one week at a time): how many partners would change
with t as (
  select m.hissab_week, m.partner_etm, m.tenure_days as current_tenure,
         coalesce(sum(least(coalesce(dp.end_date::date, m.hissab_week - 1), m.hissab_week - 1) - dp.start_date::date + 1)
                  filter (where dp.start_date::date <= m.hissab_week - 1), 0) as tenure_till_driven_week_end
  from analytics.collections_bad_debt_mv m
  left join fleet_driver fd on fd.employee_id = m.partner_etm
  left join driver_profile dp on dp.driver_id = fd.id
  where m.hissab_week = '2026-09-28' and m.for_collections = 1
  group by 1,2,3)
select hissab_week, count(*) partners,
       count(*) filter (where current_tenure is distinct from tenure_till_driven_week_end) would_change,
       round(avg(current_tenure - tenure_till_driven_week_end),1) avg_drop_days
from t group by 1;
-- Partner list: replace the last select with  select * from t order by partner_etm;"""

STATS = [  # week, partners, MV today = driven-week-end %, MV rows that change, Sheet exact %, Sheet within +-1 %, date Sheet counted till
 ('2026-08-10', 12119, 11.0, 10787, 13.9, 16.1, '2026-08-12'),
 ('2026-08-17', 11886, 10.3, 10661, 12.9, 99.8, '2026-08-17'),
 ('2026-08-24', 11701, 10.9, 10431, 14.0, 16.5, '2026-08-31'),
 ('2026-08-31', 11396, 10.3, 10218, 13.3, 99.8, '2026-08-31'),
 ('2026-09-07', 11490, 10.8, 10247, 12.9, 99.8, '2026-09-07'),
 ('2026-09-14', 11361, 12.1,  9990,  4.0,  5.3, '2026-09-15 (only 57% of rows)'),
 ('2026-09-21', 10988, 11.7,  9706,  3.4, 52.0, '2026-09-21 (only 54% of rows)'),
 ('2026-09-28', 10778, 11.6,  9533, 13.8, 15.8, '2026-09-29'),
 ('2026-10-05', 10926, 12.9,  9515,  4.5, 58.8, '2026-10-05 (only 61% of rows, week in progress)'),
]
import datetime as _dt
rows = [
 ['TENURE DAYS - ONE RULE: TENURE TILL THE DRIVEN WEEK END (hissab_week - 1)'],
 [''],
 ['1. WHY TENURE DOES NOT MATCH TODAY'],
 ['PG / MV', 'Counts tenure till the Sunday of the HISAAB week (hissab_week + 6) - 6 days after the driven week ends.'],
 ['Sheet', 'Counts tenure till the day the data was pasted / refreshed - a different date every week (1 to 8 days after the driven week end, sometimes mixed within one week).'],
 ['Tables', 'public.driver_profile (one row per stint: start_date, end_date), public.fleet_driver (employee_id -> driver id), analytics.collections_bad_debt_mv'],
 [''],
 ['2. THE ONE RULE (applies to all partners)'],
 ['Rule', 'tenure_days = sum of all driver_profile stints (end_date - start_date + 1), counted only till the driven week end = hissab_week - 1. Running stint is cut at that date; stints starting after it are not counted.'],
 ['Why this rule', 'Fixed date for every week (does not depend on when the MV or Sheet is refreshed), so the value never changes after the week closes and both sides can match 100%.'],
 ['SQL snippet for the MV script', RULE_SQL],
 ['Same rule in the Sheet query', 'Use the same date (hissab_week - 1) in the Raw_Data query instead of today / paste date.'],
 [''],
 ['3. MATCH NUMBERS WEEK ON WEEK (tenure till driven week end, exact match)'],
 ['Hisaab week', 'Driven week (end)', 'Partners', 'MV today = rule', 'MV rows that will change', 'Sheet today = rule', 'Sheet within +-1 day', 'Date the Sheet actually counted till'],
]
for w, n, mv, ch, sh, sh1, sd in STATS:
    dw = _dt.date.fromisoformat(w) - _dt.timedelta(days=7)
    rows.append([w, f'{dw} to {dw + _dt.timedelta(days=6)}', n, f'{mv}%', ch, f'{sh}%', f'{sh1}%', sd])
rows += [
 ['After fix', '', '', '100% (by definition)', '', '100% if Sheet query uses the same date', '', ''],
 [''],
 ['Note', '~13% match in every week = partners whose last stint already ended (tenure no longer grows). All active partners differ by the number of days between the driven week end and the date each side counts till (MV +7 days, Sheet +1 to +8 days).'],
 [''],
 ['4. STEPS'],
 ['Step 1', 'Business: confirm tenure = till driven week end (hissab_week - 1).'],
 ['Step 2', 'Run the PREVIEW query below (read only) - shows how many partners change per week. Tested on 28-Sep: 10,812 partners, 9,562 change, average -5.7 days.'],
 ['Step 3', 'Data team: replace tenure_days logic in the MV script with the SQL snippet above (branch + PR, test on one week first) and refresh the MV.'],
 ['Step 4', 'Change the Raw_Data (Sheet) query to the same date so it stops using the paste date.'],
 ['Step 5', 'Re-check tenure_days Matched? in Employee_Level / MV_Raw_Data_Manual_Check - expected ~100%.'],
 ['Preview query (read only)', PREVIEW_SQL],
]
NCOL = 8

tok = json.load(open(TOKEN))
r = requests.post(tok['token_uri'], data=dict(client_id=tok['client_id'], client_secret=tok['client_secret'],
                                              refresh_token=tok['refresh_token'], grant_type='refresh_token'), timeout=60)
r.raise_for_status()
H = {'Authorization': 'Bearer ' + r.json()['access_token']}
def call(method, url, **kw):
    for attempt in range(6):
        resp = requests.request(method, url, headers=H, timeout=300, **kw)
        if resp.status_code in (429, 500, 502, 503):
            time.sleep(2 ** attempt * 2); continue
        if not resp.ok:
            raise SystemExit(f'{resp.status_code}: {resp.text[:500]}')
        return resp.json()

sid = json.load(open(f'{D}/out/new_gsheet.json'))['spreadsheetId']
meta = call('GET', f'{API}/{sid}', params={'fields': 'sheets.properties'})
idx = next((s['properties']['index'] for s in meta['sheets'] if s['properties']['title'] == 'Revenue_Type_Script_Fix'), 1) + 1
reqs = [{'deleteSheet': {'sheetId': s['properties']['sheetId']}} for s in meta['sheets'] if s['properties']['title'] == TAB]
reqs.append({'addSheet': {'properties': {'title': TAB, 'index': idx, 'gridProperties': {'rowCount': len(rows) + 3, 'columnCount': NCOL}}}})
tid = call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT', f"{API}/{sid}/values/'{TAB}'!A1", params={'valueInputOption': 'RAW'}, json={'values': rows})

bold_rows = [i for i, r in enumerate(rows) if r and r[0] and (r[0][0].isdigit() and r[0][1] == '.' or r[0].startswith('TENURE') or r[0] == 'Hisaab week')]
code_rows = [i for i, r in enumerate(rows) if len(r) > 1 and r[1] in (RULE_SQL, PREVIEW_SQL)]
blue = {'red': 0.85, 'green': 0.9, 'blue': 0.97}
reqs = [{'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': len(rows)},
                        'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP', 'verticalAlignment': 'TOP'}},
                        'fields': 'userEnteredFormat(wrapStrategy,verticalAlignment)'}}]
reqs += [{'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': i, 'endRowIndex': i + 1, 'startColumnIndex': 0, 'endColumnIndex': NCOL},
                         'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': blue}},
                         'fields': 'userEnteredFormat(textFormat,backgroundColor)'}} for i in bold_rows]
reqs += [{'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': i, 'endRowIndex': i + 1, 'startColumnIndex': 1, 'endColumnIndex': 2},
                         'cell': {'userEnteredFormat': {'textFormat': {'fontFamily': 'Roboto Mono', 'fontSize': 9}}},
                         'fields': 'userEnteredFormat.textFormat'}} for i in code_rows]
reqs += [{'updateDimensionProperties': {'range': {'sheetId': tid, 'dimension': 'COLUMNS', 'startIndex': i, 'endIndex': i + 1},
                                        'properties': {'pixelSize': w}, 'fields': 'pixelSize'}} for i, w in enumerate([230, 640, 90, 130, 150, 160, 140, 260])]
call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})
print('done')
