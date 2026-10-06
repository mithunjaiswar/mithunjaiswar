"""Create a NEW Google Spreadsheet with the validation outputs (employee level included).

Uses the OAuth token from google-workspace-access/token.json via plain REST calls.
Usage: python3 upload_gsheet.py <D> <token.json>
"""
import sys, json, time
import numpy as np
import pandas as pd
import requests

D, TOKEN = sys.argv[1], sys.argv[2]
OUT = f'{D}/out'
API = 'https://sheets.googleapis.com/v4/spreadsheets'

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

def clean(df):
    df = df.astype(object).where(pd.notna(df), '')
    rows = [list(df.columns)]
    for r in df.itertuples(index=False):
        rows.append([(int(v) if isinstance(v, (float, np.floating)) and float(v).is_integer()
                      else float(v) if isinstance(v, (float, np.floating))
                      else int(v) if isinstance(v, np.integer) else v) for v in r])
    return rows

# ---------- build tables ----------
col = pd.read_pickle(f'{OUT}/col_summary.pkl')
wk = pd.read_pickle(f'{OUT}/week_level.pkl'); city = pd.read_pickle(f'{OUT}/city_level.pkl')
rs = pd.read_pickle(f'{OUT}/reason_summary.pkl')
ag = pd.read_pickle(f'{OUT}/agent.pkl'); pres = pd.read_pickle(f'{OUT}/presence.pkl')

lv = pd.concat([wk.rename(columns={'week': 'Week'}).assign(City='ALL CITIES'), city.rename(columns={'week': 'Week', 'city': 'City'})])
lv = lv[['Week', 'City', 'Overall Status'] + [c for c in lv.columns if c not in ('Week', 'City', 'Overall Status', 'Mismatched Columns')] + ['Mismatched Columns']]
ag = ag.rename(columns={'week': 'Week', 'city': 'City', 'employee': 'Employee/Agent'})
lead = ['Week', 'City', 'Employee/Agent', 'Overall Status', 'Mismatched Columns']
ag = ag[lead + [c for c in ag.columns if c not in lead]].sort_values(['Week', 'City', 'Employee/Agent'])
dd = []
for c in [c for c in ag.columns if c.endswith('| Reason')]:
    pc = c.split(' |')[0]
    x = ag[ag[c].str.startswith('Need to Deep Dive')]
    dd.append(pd.DataFrame({'Week': x.Week, 'City': x.City, 'Employee/Agent': x['Employee/Agent'], 'PG Column': pc,
                            'Sheet Value': x[f'{pc} | Sheet'], 'PG Value': x[f'{pc} | PG'], 'Status': 'Mismatched', 'Reason': x[c]}))
p = pres[pres.Status == 'Mismatched']
dd.append(pd.DataFrame({'Week': p.week, 'City': p.city, 'Employee/Agent': p.employee, 'PG Column': 'for_collections (row presence)',
                        'Sheet Value': p.presence.map({'Both': 'present', 'PG only': 'missing', 'Sheet only': 'present'}),
                        'PG Value': p.pg_for_collections.fillna('row missing'), 'Status': 'Mismatched', 'Reason': p.Reason}))
dd = pd.concat(dd).sort_values(['Week', 'City', 'Employee/Agent', 'PG Column'])
pr = pres.rename(columns={'week': 'Week', 'city': 'City', 'employee': 'Employee/Agent', 'presence': 'Row Presence',
                          'pg_for_collections': 'PG for_collections'})

notes = pd.DataFrame({'Collections Bad Debt - PG (analytics.collections_bad_debt_mv) vs Sheet (Raw_Data) validation': [
    'Hisaab weeks 21-Sep, 28-Sep, 05-Oct-2026 (05-Oct = in-progress week). Join = hisaab_week + partner ET ID. Run on 06-Oct-2026.',
    'All 53 PG columns compared. Amounts matched within +/-1 (rounding); IDs / counts / days exact; text case-insensitive; dates exact.',
    'Employee_Level: Week -> City -> Employee/Agent, every compared column shown as Sheet | PG | Status | Reason (32,706 rows).',
    'Column_Summary: column x week match counts, sums and main reason. Week_City: Week -> City Sheet vs PG per column.',
    'Reasons: every mismatch reason with row counts. Deep_Dive_Items: employee-level items whose reason could not be identified (Need to Deep Dive).',
    'Row_Presence: PG rows vs Sheet rows (Sheet = PG for_collections = 1; for_collections = 0 rows are expected to be absent).',
]})

TABS = [('Readme', notes), ('Column_Summary', col), ('Week_City', lv), ('Reasons', rs),
        ('Employee_Level', ag), ('Deep_Dive_Items', dd), ('Row_Presence', pr)]
data = {name: clean(df) for name, df in TABS}

# ---------- create spreadsheet ----------
sheets = [{'properties': {'title': n, 'gridProperties': {'rowCount': len(v) + 5, 'columnCount': max(len(v[0]), 5),
                                                         'frozenRowCount': 1}}} for n, v in data.items()]
ss = call('POST', API, json={'properties': {'title': 'Collections Bad Debt - PG vs Sheet Validation (Employee Level)'},
                             'sheets': sheets})
sid = ss['spreadsheetId']
print('created', ss['spreadsheetUrl'], flush=True)

CHUNK_CELLS = 150_000
for name, rows in data.items():
    step = max(1, CHUNK_CELLS // len(rows[0]))
    for i in range(0, len(rows), step):
        call('PUT', f"{API}/{sid}/values/'{name}'!A{i + 1}", params={'valueInputOption': 'RAW'},
             json={'values': rows[i:i + step]})
    print(f'{name}: {len(rows) - 1} rows x {len(rows[0])} cols', flush=True)

# header formatting + filters
meta = call('GET', f'{API}/{sid}', params={'fields': 'sheets.properties'})
reqs = []
for s in meta['sheets']:
    p = s['properties']; n = len(data[p['title']][0])
    reqs.append({'repeatCell': {'range': {'sheetId': p['sheetId'], 'startRowIndex': 0, 'endRowIndex': 1},
                                'cell': {'userEnteredFormat': {'textFormat': {'bold': True},
                                                               'backgroundColor': {'red': 0.85, 'green': 0.9, 'blue': 0.97}}},
                                'fields': 'userEnteredFormat(textFormat,backgroundColor)'}})
    if p['title'] != 'Readme':
        reqs.append({'setBasicFilter': {'filter': {'range': {'sheetId': p['sheetId'], 'startRowIndex': 0,
                                                             'endRowIndex': len(data[p['title']]), 'startColumnIndex': 0, 'endColumnIndex': n}}}})
call('POST', f'{API}/{sid}:batchUpdate', json={'requests': reqs})
json.dump({'spreadsheetId': sid, 'url': ss['spreadsheetUrl']}, open(f'{OUT}/new_gsheet.json', 'w'))
print('done', ss['spreadsheetUrl'])
