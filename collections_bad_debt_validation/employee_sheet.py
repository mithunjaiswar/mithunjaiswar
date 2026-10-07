"""Rebuild the validation spreadsheet as ONE tab: Employee_Level.

Layout: Week | City | Employee/Agent, then for every Sheet header that has a PG column:
  <sheet col> (Sheet) | <pg col> (PG) | <sheet col> Difference | <sheet col> Matched?
and a final 'Final Status' column (Matched only when every column matched).

Difference: numbers = PG - Sheet; dates = PG - Sheet in days; text = blank when equal, 'Different' otherwise.
Usage: python3 employee_sheet.py <D> <token.json>
"""
import sys, json, time, csv, pickle
import numpy as np
import pandas as pd
import requests

D, TOKEN = sys.argv[1], sys.argv[2]
OUT = f'{D}/out'
API = 'https://sheets.googleapis.com/v4/spreadsheets'
TAB = 'Employee_Level'

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
    raise SystemExit('too many retries')

# ---------- build the table ----------
ag = pd.read_pickle(f'{OUT}/agent.pkl').sort_values(['week', 'city', 'employee']).reset_index(drop=True)
specs = pickle.load(open(f'{OUT}/specs.pkl', 'rb'))['specs']
sheet_order = next(csv.reader(open(f'{D}/sheet.csv')))
pairs = [s for s in specs if s['kind'] in ('num', 'txt', 'eip', 'bool') ]
pairs.sort(key=lambda s: sheet_order.index(s['sheet']))

def num(x):
    return pd.to_numeric(pd.Series(x).astype(str).str.replace(',', ''), errors='coerce')

out = pd.DataFrame({'Week': ag.week, 'City': ag.city, 'Employee/Agent': ag.employee})
status_cols = []
for s in pairs:
    pc, sc = s['pg'], s['sheet']
    sv, pv = ag[f'{pc} | Sheet'], ag[f'{pc} | PG']
    ok = ag[f'{pc} | Status'].eq('Matched')
    if s['kind'] == 'num':
        diff = (num(pv).fillna(0) - num(sv).fillna(0)).round(2)
    elif pc in ('last_payment_date_till_hissab_week', 'last_jama_date'):
        diff = (pd.to_datetime(pv, errors='coerce') - pd.to_datetime(sv, errors='coerce')).dt.days
        diff = diff.astype(object).where(diff.notna(), np.where(ok, '', 'Different'))
    else:
        diff = pd.Series(np.where(ok, '', 'Different'), index=ag.index)
    out[f'{sc} (Sheet)'] = sv
    out[f'{pc} (PG)'] = pv
    out[f'{sc} Difference'] = diff
    out[f'{sc} Matched?'] = np.where(ok, 'Matched', 'Not Matched')
    status_cols.append(f'{sc} Matched?')
out['Final Status'] = np.where((out[status_cols] == 'Matched').all(axis=1), 'Matched', 'Not Matched')

def cell(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ''
    if isinstance(v, (float, np.floating)):
        return int(v) if float(v).is_integer() else float(v)
    if isinstance(v, np.integer):
        return int(v)
    return v

rows = [list(out.columns)] + [[cell(v) for v in r] for r in out.itertuples(index=False)]
print('table', len(rows) - 1, 'rows x', len(rows[0]), 'cols', flush=True)

# ---------- replace all tabs of the spreadsheet with one Employee_Level tab ----------
sid = json.load(open(f'{OUT}/new_gsheet.json'))['spreadsheetId']
meta = call('GET', f'{API}/{sid}', params={'fields': 'sheets.properties'})
reqs = [{'addSheet': {'properties': {'title': TAB + '_tmp', 'gridProperties': {
    'rowCount': len(rows) + 5, 'columnCount': len(rows[0]), 'frozenRowCount': 1, 'frozenColumnCount': 3}}}}]
reqs += [{'deleteSheet': {'sheetId': s['properties']['sheetId']}} for s in meta['sheets'] if s['properties']['title'] in (TAB, TAB + '_tmp')]
resp = call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})
new_id = resp['replies'][0]['addSheet']['properties']['sheetId']
call('POST', f'{API}/{sid}:batchUpdate', json={'requests': [
    {'updateSheetProperties': {'properties': {'sheetId': new_id, 'title': TAB}, 'fields': 'title'}}]})

step = 150_000 // len(rows[0])
for i in range(0, len(rows), step):
    call('PUT', f"{API}/{sid}/values/'{TAB}'!A{i + 1}", params={'valueInputOption': 'RAW'}, json={'values': rows[i:i + step]})
print('written', flush=True)

ncol = len(rows[0])
green = {'red': 0.85, 'green': 0.94, 'blue': 0.85}
red = {'red': 0.98, 'green': 0.85, 'blue': 0.85}
match_cols = [j for j, c in enumerate(rows[0]) if c.endswith('Matched?') or c == 'Final Status']
reqs = [{'repeatCell': {'range': {'sheetId': new_id, 'startRowIndex': 0, 'endRowIndex': 1},
                        'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'wrapStrategy': 'WRAP',
                                                       'backgroundColor': {'red': 0.85, 'green': 0.9, 'blue': 0.97}}},
                        'fields': 'userEnteredFormat(textFormat,wrapStrategy,backgroundColor)'}},
        {'setBasicFilter': {'filter': {'range': {'sheetId': new_id, 'startRowIndex': 0, 'endRowIndex': len(rows),
                                                 'startColumnIndex': 0, 'endColumnIndex': ncol}}}}]
for j in match_cols:
    rng = {'sheetId': new_id, 'startRowIndex': 1, 'endRowIndex': len(rows), 'startColumnIndex': j, 'endColumnIndex': j + 1}
    for txt, colr in (('Not Matched', red), ('Matched', green)):
        reqs.append({'addConditionalFormatRule': {'index': 0, 'rule': {'ranges': [rng], 'booleanRule': {
            'condition': {'type': 'TEXT_EQ', 'values': [{'userEnteredValue': txt}]},
            'format': {'backgroundColor': colr}}}}})
call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})
print('done', json.load(open(f'{OUT}/new_gsheet.json'))['url'])
print('Final Status counts:', out['Final Status'].value_counts().to_dict())
