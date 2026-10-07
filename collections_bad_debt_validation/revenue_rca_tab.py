"""Add / replace the 'Revenue_Type_RCA' tab: per employee-week, revenue type at hisaab vs Sheet vs PG with reason.
Input: <D>/out/rev_rca.pkl (built from fleet_leasing_weeklydata of the driven week). Usage: python3 revenue_rca_tab.py <D> <token.json>"""
import sys, json, time
import pandas as pd
import requests

D, TOKEN = sys.argv[1], sys.argv[2]
API = 'https://sheets.googleapis.com/v4/spreadsheets'
TAB = 'Revenue_Type_RCA'
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

x = pd.read_pickle(f'{D}/out/rev_rca.pkl')
def dw(w): d = pd.Timestamp(w); return f"{(d - pd.Timedelta(days=7)):%d-%b} to {(d - pd.Timedelta(days=1)):%d-%b}"
det = pd.DataFrame({'Week': x.week, 'City': x.city, 'Employee/Agent': x.employee, 'Driven week (hisaab period)': x.week.map(dw),
                    'Revenue type at hisaab (fleet_leasing_weeklydata)': x.hisaab, 'Sheet revenue_type': x.sheet,
                    'PG revenue_type': x.pg.replace('', '(blank)'), 'PG location': x.pg_location.replace('', '(blank)'),
                    'Sheet hub (allocation_location)': x.sh_allocation_location.replace('', '(blank)'),
                    'Sheet = Hisaab?': x.sheet_ok, 'PG = Hisaab?': x.pg_ok, 'Category': x.category, 'Reason': x.reason})
ACT = {'PG mapping gap': ('PG / data team', 'Fill PG revenue_type from the hisaab row of the driven week (not from hub lookup). Set it to: {h}'),
       'PG wrong': ('PG / data team', 'Change PG to the hisaab product of the driven week. Set it to: {h}'),
       'Product changed during week': ('Business - decide rule', 'Partner had 2 products in the week ({h}). Agree one rule (use LAST product of the week) and apply it in Sheet and PG.'),
       'Labelling rule (EV on D2O plan)': ('Business - decide label', 'Same partner, different name. Pick one label for EV car on D2O plan (e.g. EV_Rent To Own) and use it in Sheet and PG.'),
       'Sheet wrong': ('Sheet owner', 'Change Sheet value to the hisaab product: {h}'),
       'Need to Deep Dive': ('Data team', 'Check hisaab rows manually for this partner.')}
def correct(cat, h):
    if cat in ('PG mapping gap', 'PG wrong', 'Sheet wrong') and '+' not in h: return h
    if cat == 'Labelling rule (EV on D2O plan)': return 'EV on D2O plan (label to be agreed)'
    return 'Rule to be agreed'
det['Action needed by'] = [ACT[c][0] for c in x.category]
det['Solution'] = [ACT[c][1].format(h=h) for c, h in zip(x.category, x.hisaab)]
det['Correct revenue_type'] = [correct(c, h) for c, h in zip(x.category, x.hisaab)]
detail = [list(det.columns)] + det.astype(str).values.tolist()

piv = pd.crosstab(x.category, x.week, margins=True, margins_name='Total')
summ = [['Revenue type mismatch - summary', '', '', '', ''], ['Category'] + [str(c) for c in piv.columns]]
summ += [[str(i)] + [int(v) for v in row] for i, row in zip(piv.index, piv.values)]
summ += [[''], ['ACTION PLAN (short)'],
         ['1. PG mapping gap', 'Who: PG / data team. Fix: take revenue_type from fleet_leasing_weeklydata of the driven week; add missing hubs. Note: 21-Sep and 28-Sep already fixed in the 07-Oct PG refresh, 05-Oct still open (353).'],
         ['2. PG wrong', 'Who: PG / data team. Fix: use the driven-week hisaab product, not the latest allocation. Sheet is already correct - no Sheet change.'],
         ['3. Product changed during week', 'Who: Business. Decide: use the LAST product of the driven week. Then data team applies the same rule in Sheet and PG.'],
         ['4. Labelling rule (EV on D2O plan)', 'Who: Business. Decide one name (e.g. EV_Rent To Own). Then use it in Sheet and PG.'],
         ['5. Sheet wrong', 'Who: Sheet owner. Fix the 1 row to the hisaab product.'],
         ['Check after fix', 'Run query #1-#4 in tab Issues_and_Fix_Steps - result should be 0 rows.']]
summ += [[''], ['What each category means'],
         ['PG mapping gap', 'PG revenue_type is blank. In 1,036 of the 1,143 rows PG location is also blank: PG could not resolve the partner hub (mostly Delhi - Honda Sector 35 Office / Sukhrali, Kolkata), so revenue_type is not filled. The other 107 are Chennai (Vanagram) partners. At hisaab these partners were D2O (most) or Own Now - Sheet is correct.'],
         ['PG wrong', 'Hisaab record of the driven week has one product; Sheet matches it, PG shows a different product (PG takes the product from outside the hisaab week).'],
         ['Product changed during week', 'Partner had two products in the same driven week (two hisaab rows). Sheet and PG picked different ones - both exist in hisaab.'],
         ['Labelling rule (EV on D2O plan)', 'EV car (business vertical 2) on a D2O plan. Sheet calls it EV_Leasing / EV_Rent To Own, PG calls it D2O. Same hisaab record, different naming rule - needs one agreed label.'],
         ['Sheet wrong', 'Hisaab matches PG, Sheet differs.']]

sid = json.load(open(f'{D}/out/new_gsheet.json'))['spreadsheetId']
meta = call('GET', f'{API}/{sid}', params={'fields': 'sheets.properties'})
reqs = [{'deleteSheet': {'sheetId': s['properties']['sheetId']}} for s in meta['sheets'] if s['properties']['title'] == TAB]
reqs.append({'addSheet': {'properties': {'title': TAB, 'index': 1, 'gridProperties': {
    'rowCount': len(detail) + 5, 'columnCount': 24, 'frozenRowCount': 1, 'frozenColumnCount': 3}}}})
tid = call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT', f"{API}/{sid}/values/'{TAB}'!A1", params={'valueInputOption': 'RAW'}, json={'values': detail})
call('PUT', f"{API}/{sid}/values/'{TAB}'!R1", params={'valueInputOption': 'RAW'}, json={'values': summ})
blue = {'red': 0.85, 'green': 0.9, 'blue': 0.97}
call('POST', f'{API}/{sid}:batchUpdate', json={'requests': [
    {'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': 16},
                    'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': blue, 'wrapStrategy': 'WRAP'}},
                    'fields': 'userEnteredFormat(textFormat,backgroundColor,wrapStrategy)'}},
    {'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': 2, 'startColumnIndex': 17, 'endColumnIndex': 22},
                    'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': blue}},
                    'fields': 'userEnteredFormat(textFormat,backgroundColor)'}},
    {'setBasicFilter': {'filter': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': len(detail),
                                             'startColumnIndex': 0, 'endColumnIndex': 16}}}},
    {'updateDimensionProperties': {'range': {'sheetId': tid, 'dimension': 'COLUMNS', 'startIndex': 12, 'endIndex': 13},
                                   'properties': {'pixelSize': 520}, 'fields': 'pixelSize'}},
    {'updateDimensionProperties': {'range': {'sheetId': tid, 'dimension': 'COLUMNS', 'startIndex': 14, 'endIndex': 15},
                                   'properties': {'pixelSize': 380}, 'fields': 'pixelSize'}},
    {'updateDimensionProperties': {'range': {'sheetId': tid, 'dimension': 'COLUMNS', 'startIndex': 17, 'endIndex': 18},
                                   'properties': {'pixelSize': 260}, 'fields': 'pixelSize'}},
    {'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 1, 'endRowIndex': len(detail), 'startColumnIndex': 13, 'endColumnIndex': 14},
                    'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': {'red': 1, 'green': 0.95, 'blue': 0.8}}},
                    'fields': 'userEnteredFormat(textFormat,backgroundColor)'}}]})
print('done', len(detail) - 1, 'rows')
