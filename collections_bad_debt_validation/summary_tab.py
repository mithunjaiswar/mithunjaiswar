"""Add / replace a 'Summary' tab: week-on-week and city-wise Sheet vs PG values and match counts.

One row per Week x City (ALL CITIES first) x column:
  Week | City | Sheet Column | PG Column | Sheet Value | PG Value | Difference (PG - Sheet) |
  Total Rows | Matched Count | Not Matched Count | Match % | Status
Value = SUM for amount / count columns; for text columns it is the count of non-blank values.
The first row of every Week x City block is the partner count (Sheet rows vs PG for_collections = 1).
Usage: python3 summary_tab.py <D> <token.json>
"""
import sys, json, time, csv, pickle
import numpy as np
import pandas as pd
import requests

D, TOKEN = sys.argv[1], sys.argv[2]
OUT = f'{D}/out'
API = 'https://sheets.googleapis.com/v4/spreadsheets'
TAB = 'Summary'

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

def num(x):
    return pd.to_numeric(pd.Series(x).astype(str).str.replace(',', ''), errors='coerce').fillna(0)

ag = pd.read_pickle(f'{OUT}/agent.pkl')
pres = pd.read_pickle(f'{OUT}/presence.pkl')
specs = pickle.load(open(f'{OUT}/specs.pkl', 'rb'))['specs']
sheet_order = next(csv.reader(open(f'{D}/sheet.csv')))
pairs = [s for s in specs if s['kind'] in ('num', 'txt', 'eip', 'bool') and s['pg'] != 'eip_tag']
pairs.sort(key=lambda s: sheet_order.index(s['sheet']))
SUMMABLE = {s['pg'] for s in pairs if s['kind'] == 'num' and s['pg'] != 'lead_id'}

ag['ALL'] = 'ALL CITIES'; pres['ALL'] = 'ALL CITIES'
rows = []
weeks = sorted(ag.week.unique())
cities = ['ALL CITIES'] + sorted(c for c in ag.city.unique())
for w in weeks:
    for c in cities:
        g = ag[(ag.week == w) & ((ag.city == c) | (c == 'ALL CITIES'))]
        p = pres[(pres.week == w) & ((pres.city == c) | (c == 'ALL CITIES'))]
        if not len(g):
            continue
        s_cnt = int(p.presence.isin(['Both', 'Sheet only']).sum())
        p_cnt = int((p.pg_for_collections == '1').sum())
        both = int(((p.presence == 'Both') & (p.pg_for_collections == '1')).sum())
        rows.append([w, c, 'Partner Count', 'Partner Count (for_collections = 1)', s_cnt, p_cnt, p_cnt - s_cnt,
                     max(s_cnt, p_cnt), both, max(s_cnt, p_cnt) - both,
                     round(100 * both / max(s_cnt, p_cnt, 1), 2), 'Matched' if s_cnt == p_cnt == both else 'Not Matched'])
        for s in pairs:
            pc, sc = s['pg'], s['sheet']
            st = g[f'{pc} | Status']
            m = int(st.eq('Matched').sum()); nm = len(g) - m
            if pc in SUMMABLE:
                sv = round(float(num(g[f'{pc} | Sheet']).sum()), 2)
                pv = round(float(num(g[f'{pc} | PG']).sum()), 2)
            else:  # text / id columns: count of non-blank values
                sv = int(g[f'{pc} | Sheet'].astype(str).str.strip().replace('nan', '').ne('').sum())
                pv = int(g[f'{pc} | PG'].astype(str).str.strip().replace('nan', '').ne('').sum())
            rows.append([w, c, sc, pc, sv, pv, round(pv - sv, 2), len(g), m, nm,
                         round(100 * m / len(g), 2), 'Matched' if nm == 0 else 'Not Matched'])

hdr = ['Week', 'City', 'Sheet Column', 'PG Column', 'Sheet Value', 'PG Value', 'Difference (PG - Sheet)',
       'Total Rows', 'Matched Count', 'Not Matched Count', 'Match %', 'Status']
data = [hdr] + rows
print('summary rows', len(rows), flush=True)

sid = json.load(open(f'{OUT}/new_gsheet.json'))['spreadsheetId']
meta = call('GET', f'{API}/{sid}', params={'fields': 'sheets.properties'})
reqs = [{'deleteSheet': {'sheetId': s['properties']['sheetId']}} for s in meta['sheets'] if s['properties']['title'] == TAB]
reqs.append({'addSheet': {'properties': {'title': TAB, 'index': 0, 'gridProperties': {
    'rowCount': len(data) + 5, 'columnCount': len(hdr), 'frozenRowCount': 1, 'frozenColumnCount': 2}}}})
resp = call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})
tid = resp['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT', f"{API}/{sid}/values/'{TAB}'!A1", params={'valueInputOption': 'RAW'}, json={'values': data})

green = {'red': 0.85, 'green': 0.94, 'blue': 0.85}
red = {'red': 0.98, 'green': 0.85, 'blue': 0.85}
grey = {'red': 0.93, 'green': 0.93, 'blue': 0.93}
n = len(data)
reqs = [{'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': 1},
                        'cell': {'userEnteredFormat': {'textFormat': {'bold': True},
                                                       'backgroundColor': {'red': 0.85, 'green': 0.9, 'blue': 0.97}}},
                        'fields': 'userEnteredFormat(textFormat,backgroundColor)'}},
        {'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 1, 'endRowIndex': n, 'startColumnIndex': 4, 'endColumnIndex': 7},
                        'cell': {'userEnteredFormat': {'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0.00;-#,##0.00;0'}}},
                        'fields': 'userEnteredFormat.numberFormat'}},
        {'setBasicFilter': {'filter': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': n,
                                                 'startColumnIndex': 0, 'endColumnIndex': len(hdr)}}}},
        {'addConditionalFormatRule': {'index': 0, 'rule': {'ranges': [{'sheetId': tid, 'startRowIndex': 1, 'endRowIndex': n,
                                                                     'startColumnIndex': 0, 'endColumnIndex': len(hdr)}],
            'booleanRule': {'condition': {'type': 'CUSTOM_FORMULA', 'values': [{'userEnteredValue': '=$C2="Partner Count"'}]},
                            'format': {'backgroundColor': grey, 'textFormat': {'bold': True}}}}}}]
for txt, colr in (('Not Matched', red), ('Matched', green)):
    reqs.append({'addConditionalFormatRule': {'index': 0, 'rule': {'ranges': [{'sheetId': tid, 'startRowIndex': 1, 'endRowIndex': n,
                                                                             'startColumnIndex': 11, 'endColumnIndex': 12}],
        'booleanRule': {'condition': {'type': 'TEXT_EQ', 'values': [{'userEnteredValue': txt}]}, 'format': {'backgroundColor': colr}}}}})
reqs.append({'autoResizeDimensions': {'dimensions': {'sheetId': tid, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': len(hdr)}}})
call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})
print('done')
