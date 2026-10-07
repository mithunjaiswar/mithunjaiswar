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
detail = [list(det.columns)] + det.astype(str).values.tolist()

piv = pd.crosstab(x.category, x.week, margins=True, margins_name='Total')
summ = [['Revenue type mismatch - summary', '', '', '', ''], ['Category'] + [str(c) for c in piv.columns]]
summ += [[str(i)] + [int(v) for v in row] for i, row in zip(piv.index, piv.values)]
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
    'rowCount': len(detail) + 5, 'columnCount': 22, 'frozenRowCount': 1, 'frozenColumnCount': 3}}}})
tid = call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT', f"{API}/{sid}/values/'{TAB}'!A1", params={'valueInputOption': 'RAW'}, json={'values': detail})
call('PUT', f"{API}/{sid}/values/'{TAB}'!O1", params={'valueInputOption': 'RAW'}, json={'values': summ})
blue = {'red': 0.85, 'green': 0.9, 'blue': 0.97}
call('POST', f'{API}/{sid}:batchUpdate', json={'requests': [
    {'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': 13},
                    'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': blue, 'wrapStrategy': 'WRAP'}},
                    'fields': 'userEnteredFormat(textFormat,backgroundColor,wrapStrategy)'}},
    {'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': 2, 'startColumnIndex': 14, 'endColumnIndex': 19},
                    'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': blue}},
                    'fields': 'userEnteredFormat(textFormat,backgroundColor)'}},
    {'setBasicFilter': {'filter': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': len(detail),
                                             'startColumnIndex': 0, 'endColumnIndex': 13}}}},
    {'updateDimensionProperties': {'range': {'sheetId': tid, 'dimension': 'COLUMNS', 'startIndex': 12, 'endIndex': 13},
                                   'properties': {'pixelSize': 520}, 'fields': 'pixelSize'}},
    {'updateDimensionProperties': {'range': {'sheetId': tid, 'dimension': 'COLUMNS', 'startIndex': 14, 'endIndex': 15},
                                   'properties': {'pixelSize': 230}, 'fields': 'pixelSize'}}]})
print('done', len(detail) - 1, 'rows')
