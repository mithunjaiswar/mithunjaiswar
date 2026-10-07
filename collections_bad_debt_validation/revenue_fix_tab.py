"""Add / replace 'Revenue_Type_Script_Fix' tab: why revenue_type differs + one global script rule + tested impact.
Usage: python3 revenue_fix_tab.py <D> <token.json>"""
import sys, json, time
import requests

D, TOKEN = sys.argv[1], sys.argv[2]
API = 'https://sheets.googleapis.com/v4/spreadsheets'
TAB = 'Revenue_Type_Script_Fix'

RULE_SQL = """-- Put this in the PG script that builds analytics.collections_bad_debt_mv
-- (replace the current revenue_type logic). One rule for ALL partners:
-- revenue type = product of the hisaab row of the DRIVEN week with the most active days.
revenue_type_fix as (
  select distinct on (m.hissab_week, m.partner_etm)
         m.hissab_week, m.partner_etm,
         case when f.business_vertical_id = 6 then 'D2O'
              when f.business_vertical_id = 2 and f.leasing_type ilike 'D2O%' then 'EV_Rent To Own'
              when f.business_vertical_id = 2 then 'EV_Leasing'
              when f.leasing_type ilike '%OWN%' then 'Own Now'
              else 'Leasing' end as revenue_type
  from <mv base rows> m
  join fleet_leasing_weeklydata f
    on f.partner_etm = m.partner_etm
   and f.start_date >= m.driven_week and f.start_date < m.hissab_week
   and coalesce(f.is_deleted, 0) = 0
  order by m.hissab_week, m.partner_etm,
           f.active_days desc nulls last,   -- product used most days in the week
           f.start_date, f.id)              -- tie: first row of the week
-- then: final revenue_type = coalesce(revenue_type_fix.revenue_type, <current value>)
--       (current value kept only for partners with no leasing hisaab row, e.g. Rev share / Fixed Pay)"""

PREVIEW_SQL = """-- PREVIEW before deploying (read only): how many partners would change per week
with new_rule as (
  select distinct on (m.hissab_week, m.partner_etm)
         m.hissab_week, m.partner_etm, m.revenue_type as current_revenue_type,
         case when f.business_vertical_id = 6 then 'D2O'
              when f.business_vertical_id = 2 and f.leasing_type ilike 'D2O%' then 'EV_Rent To Own'
              when f.business_vertical_id = 2 then 'EV_Leasing'
              when f.leasing_type ilike '%OWN%' then 'Own Now'
              else 'Leasing' end as new_revenue_type
  from analytics.collections_bad_debt_mv m
  join fleet_leasing_weeklydata f
    on f.partner_etm = m.partner_etm
   and f.start_date >= m.driven_week and f.start_date < m.hissab_week
   and coalesce(f.is_deleted, 0) = 0
  where m.hissab_week in ('2026-09-21','2026-09-28','2026-10-05') and m.for_collections = 1
  order by m.hissab_week, m.partner_etm, f.active_days desc nulls last, f.start_date, f.id)
select hissab_week, count(*) as partners,
       count(*) filter (where current_revenue_type is distinct from new_revenue_type) as would_change,
       count(*) filter (where current_revenue_type is null) as blank_today
from new_rule group by 1 order by 1;
-- To see the partner list: replace the last select with
-- select * from new_rule where current_revenue_type is distinct from new_revenue_type order by 1,2;"""

rows = [
 ['REVENUE TYPE - WHY IT DIFFERS AND HOW TO FIX IT FOR EVERYONE (one script change, no row-by-row edits)'],
 [''],
 ['1. WHY THE DIFFERENCE IS COMING'],
 ['Reason A - PG blank (05-Oct, 353 partners)', 'PG takes revenue_type through the hub / location lookup. When the hub is not mapped (location blank) revenue_type stays blank. 21-Sep and 28-Sep were already fixed in the 07-Oct 08:23 refresh; 05-Oct is still blank.'],
 ['Reason B - partner had 2 products in the same week (~1,755 partner-weeks)', 'A partner can have two hisaab rows in one driven week (car / plan change, e.g. D2O then Leasing). The current script does not say which one to pick, so it picks differently from the Sheet.'],
 ['Reason C - EV car on D2O plan (~200 partners)', 'Business vertical = EV but plan = D2O. PG labels it D2O. The Sheet labelled it EV_Leasing for 21-Sep / 28-Sep and EV_Rent To Own for 05-Oct - the Sheet itself changed the label.'],
 ['Reason D - single product but PG different (32 / 54 / 147 rows today)', 'PG takes the product from outside the driven week (allocation / later row) instead of the hisaab row that is being settled.'],
 [''],
 ['2. THE ONE RULE TO PUT IN THE SCRIPT (applies to all partners)'],
 ['Rule', 'revenue_type = product of the hisaab row (fleet_leasing_weeklydata) of the DRIVEN week (driven_week to hissab_week - 1). If there are 2+ rows, take the one with the most active_days; tie = first row. Mapping: vertical 6 = D2O, vertical 2 + D2O plan = EV_Rent To Own, vertical 2 = EV_Leasing, OWN NOW plan = Own Now, else Leasing. If no leasing hisaab row (Rev share / Fixed Pay) keep the current value.'],
 ['Why this rule', 'It is the rule closest to the Sheet among the rules tested (last row, first row, latest allocation, most active days). It does not depend on hub mapping, so blanks disappear.'],
 ['SQL snippet for the script', RULE_SQL],
 [''],
 ['3. TESTED IMPACT (all 32,706 Sheet partners, PG refresh 07-Oct)'],
 ['Week', 'Match with Sheet - PG today', 'Match with Sheet - after new rule', 'Partners whose value changes'],
 ['2026-09-21', '98.46% (10,826)', '98.54% (10,834)', '144'],
 ['2026-09-28', '98.27% (10,595)', '98.77% (10,648)', '182'],
 ['2026-10-05', '94.15% (10,291)', '99.54% (10,880)', '628'],
 ['Total', 'Fixed: 728 rows', 'Newly different: 78 rows', 'Still different: 266 rows'],
 [''],
 ['4. WHAT WILL STILL BE DIFFERENT AND WHY (no script can fix these alone)'],
 ['EV on D2O plan in 21-Sep / 28-Sep (~138 rows)', 'The Sheet used EV_Leasing in September and EV_Rent To Own in October for the same kind of partner. Decide one label; if the Sheet keeps EV_Rent To Own going forward these go away.'],
 ['Some 2-product weeks (~130 rows)', 'The Sheet did not follow one fixed rule for these partners (it matches "most active days" for ~89%). Sheet query should use the same rule as PG.'],
 [''],
 ['5. STEPS'],
 ['Step 1', 'Business: confirm the rule (most active days in the driven week) and the EV label (EV_Rent To Own).'],
 ['Step 2', 'Run the PREVIEW query below in PG Admin - it changes nothing, it shows how many partners will change.'],
 ['Step 3', 'Data team: replace the revenue_type logic in the MV script with the SQL snippet above and refresh the MV.'],
 ['Step 4', 'Use the same rule in the Sheet query (Raw_Data) so both sides always agree.'],
 ['Step 5', 'Re-run query #1 and #2 in Issues_and_Fix_Steps - expected 0 rows.'],
 ['Preview query (read only)', PREVIEW_SQL],
]

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
idx = next((s['properties']['index'] for s in meta['sheets'] if s['properties']['title'] == 'Revenue_Type_RCA'), 1)
reqs = [{'deleteSheet': {'sheetId': s['properties']['sheetId']}} for s in meta['sheets'] if s['properties']['title'] == TAB]
reqs.append({'addSheet': {'properties': {'title': TAB, 'index': idx, 'gridProperties': {'rowCount': len(rows) + 3, 'columnCount': 4}}}})
tid = call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT', f"{API}/{sid}/values/'{TAB}'!A1", params={'valueInputOption': 'RAW'}, json={'values': rows})

bold_rows = [i for i, r in enumerate(rows) if r and r[0] and (r[0][0].isdigit() and r[0][1] == '.' or r[0].startswith('REVENUE') or r[0] == 'Week')]
code_rows = [i for i, r in enumerate(rows) if len(r) > 1 and r[1] in (RULE_SQL, PREVIEW_SQL)]
blue = {'red': 0.85, 'green': 0.9, 'blue': 0.97}
reqs = [{'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': len(rows)},
                        'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP', 'verticalAlignment': 'TOP'}},
                        'fields': 'userEnteredFormat(wrapStrategy,verticalAlignment)'}}]
reqs += [{'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': i, 'endRowIndex': i + 1, 'startColumnIndex': 0, 'endColumnIndex': 4},
                         'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': blue}},
                         'fields': 'userEnteredFormat(textFormat,backgroundColor)'}} for i in bold_rows]
reqs += [{'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': i, 'endRowIndex': i + 1, 'startColumnIndex': 1, 'endColumnIndex': 2},
                         'cell': {'userEnteredFormat': {'textFormat': {'fontFamily': 'Roboto Mono', 'fontSize': 9}}},
                         'fields': 'userEnteredFormat.textFormat'}} for i in code_rows]
reqs += [{'updateDimensionProperties': {'range': {'sheetId': tid, 'dimension': 'COLUMNS', 'startIndex': i, 'endIndex': i + 1},
                                        'properties': {'pixelSize': w}, 'fields': 'pixelSize'}} for i, w in enumerate([330, 640, 230, 200])]
call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})
print('done')
