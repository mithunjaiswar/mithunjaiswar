"""ADD (never replace/delete) a tab with an MV sample for manual checking.

Layout: Week | City | Employee/Agent | then for every MV column (except id, driven_week):
        <col> (MV) | <col> (Sheet) | <col> (Manual) | <col> Matched? (formula) | ... | Final Status (formula).
Matched? compares MV with Manual when Manual is filled, otherwise MV with Sheet.
Row 2 = match % per column.
Usage: python3 mv_manual_check_tab.py <D> <token.json> <tab title> [--replace]
<D>/mv_sample.json = rows in MV column order (53 columns); <D>/sheet.csv = Raw_Data rows; <D>/specs.pkl = column map.
--replace only replaces THIS tab (refuses if any Manual cell is already filled)."""
import sys, json, time, csv, pickle
import requests

D, TOKEN, TAB = sys.argv[1], sys.argv[2], sys.argv[3]
REPLACE = '--replace' in sys.argv
SID = '1Vn58kq_-i8ywbaT_zBx8P7fgahqxKeoNX_RD6o8Vjfo'
API = 'https://sheets.googleapis.com/v4/spreadsheets'
COLS = ('id, driven_week, hissab_week, partner_etm, lead_id, city, eip_tag, fuel_type, product_type, revshare_days_working, '
        'total_os, weekly_os, prev_carryforward_os, os_to_deposit, kuber_amount, total_allocated_days, uber_active_days, '
        'rental_days, total_rent_amount, total_collected_amount_in_week, last_payment_date_till_hissab_week, last_jama_date, '
        'last_car_number, week_start_deposit, week_end_deposit, last_week_payment_habit, last_week_nd_count, '
        'current_week_nd_count, hissab_week_active_days, tenure_days, d2o_leave_days, active_inactive_flag, bad_debt_amount, '
        'next_weekly_os, next_total_os, next_week_end_deposit, next_join_date, in_car_recovery_driven_week, '
        'in_car_recovery_hissab_week, for_collections, last_updated, collection_till_wed, bad_debt_collected, '
        'last_week_collection, previous_week_collection, partners_not_paid_2_weeks, cars_under_recovery_driven_week, '
        'cars_under_recovery_hissab_week, recovery_tat, active_fleet_cash_blocked, location, revenue_type, '
        'total_collected_100_pct').split(', ')
KEYS = ['hissab_week', 'city', 'partner_etm']
REST = [c for c in COLS if c not in KEYS + ['id', 'driven_week']]
SPECS = {s['pg']: s for s in pickle.load(open(f'{D}/specs.pkl', 'rb'))['specs']}
SPECS['total_collected_100_pct'] = {'pg': 'total_collected_100_pct', 'sheet': 'till_sun_100pct', 'kind': 'num'}
SPECS['eip_tag'] = {'pg': 'eip_tag', 'sheet': 'eip_filter', 'kind': 'eip'}
SHEET = {}
for r in csv.DictReader(open(f'{D}/sheet.csv')):
    SHEET[(r['hisaab_week'], r['partner_et_id'].strip().upper())] = r

def sheet_value(c, v):
    sp = SPECS.get(c)
    if c == 'for_collections':
        return 1 if (v['hissab_week'], v['partner_etm'].upper()) in SHEET else 0
    if not sp or sp['kind'] not in ('num', 'txt', 'eip', 'bool') or sp.get('sheet') not in next(iter(SHEET.values())):
        return 'N/A (not in Sheet)'
    row = SHEET.get((v['hissab_week'], v['partner_etm'].upper()))
    if row is None:
        return 'Not in Sheet'
    x = row[sp['sheet']]
    if sp['kind'] == 'eip':
        return {'EIP': 1, 'SINGLE': 0}.get(x, x)
    if sp['kind'] == 'bool':
        return {'Yes': 'true', 'No': 'false'}.get(x, x)
    if sp['kind'] == 'num':
        x = x.replace(',', '').replace('%', '')
    return x

def col_letter(i):  # 0-based -> A1 letters
    s = ''
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s

rows = json.load(open(f'{D}/mv_sample.json'))
rows.sort(key=lambda r: (r[COLS.index('hissab_week')], r[COLS.index('city')], r[COLS.index('partner_etm')]))
FIRST = 5  # rows 1-2 = Matched / Not Matched counts, row 3 blank, row 4 header
n = len(rows)
last = FIRST + n - 1

hdr = ['Week', 'City', 'Employee/Agent']
for c in REST:
    hdr += [f'{c} (MV)', f'{c} (Sheet)', f'{c} (Manual)', f'{c} Matched?']
hdr.append('Final Status')
ncol = len(hdr)
fin = col_letter(ncol - 1)
first_m, last_m = col_letter(3), col_letter(ncol - 2)

WEEK = rows[0][COLS.index('hissab_week')] if rows else ''
top = [['', '', 'Matched? = MV vs Manual if Manual filled, else MV vs Sheet'], [WEEK, '', f'{len(rows)} employees']]
for j, c in enumerate(list(REST) + ['__final__']):
    m = fin if c == '__final__' else col_letter(3 + 4 * j + 3)
    rng = f'{m}{FIRST}:{m}{last}'
    for k, lab in enumerate(('Matched', 'Not Matched')):
        cnt = f'COUNTIF({rng},"{lab}")'
        cell = [lab, f'={cnt}', f'=IFERROR({cnt}/(COUNTIF({rng},"Matched")+COUNTIF({rng},"Not Matched")),"")']
        if c == '__final__':
            top[k] += cell
        else:
            top[k] += cell + ['']

data = []
for k, r in enumerate(rows):
    rn = FIRST + k
    v = dict(zip(COLS, r))
    line = [v['hissab_week'], v['city'], v['partner_etm']]
    for j, c in enumerate(REST):
        mv, sh, man = (col_letter(3 + 4 * j + o) + str(rn) for o in range(3))
        ref = f'IF({man}<>"",{man},{sh})'
        line += [v[c], sheet_value(c, v), '',
                 f'=IF(OR({ref}="",{ref}="N/A (not in Sheet)",{ref}="Not in Sheet"),"",'
                 f'IF(AND(OR(ISNUMBER({mv}),{mv}=""),ISNUMBER({ref})),IF(ABS(N({mv})-{ref})<=1,"Matched","Not Matched"),'
                 f'IF(LOWER(TRIM(TO_TEXT({mv})))=LOWER(TRIM(TO_TEXT({ref}))),"Matched","Not Matched")))']
    line.append(f'=IF(COUNTIF({first_m}{rn}:{last_m}{rn},"Not Matched")>0,"Not Matched",'
                f'IF(COUNTIF({first_m}{rn}:{last_m}{rn},"Matched")>0,"Matched","Pending"))')
    data.append(line)

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

meta = call('GET', f'{API}/{SID}', params={'fields': 'sheets.properties'})
old = [s['properties'] for s in meta['sheets'] if s['properties']['title'] == TAB]
pre = []
if old:
    if not REPLACE:
        raise SystemExit(f'Tab "{TAB}" already exists - not touching it. Use --replace or another name.')
    cur = call('GET', f"{API}/{SID}/values/'{TAB}'!1:{old[0]['gridProperties']['rowCount']}").get('values', [])
    hi = next((k for k, r in enumerate(cur) if any(str(h).endswith('(Manual)') for h in r)), 0)
    mi = [i for i, h in enumerate(cur[hi]) if str(h).endswith('(Manual)')] if cur else []
    if any(i < len(r) and r[i] != '' for r in cur[hi + 1:] for i in mi):
        raise SystemExit('Manual values already entered in this tab - not replacing it.')
    pre = [{'deleteSheet': {'sheetId': old[0]['sheetId']}}]
resp = call('POST', f'{API}/{SID}:batchUpdate', json={'requests': pre + [{'addSheet': {'properties': {
    'title': TAB, 'gridProperties': {'rowCount': last + 2, 'columnCount': ncol + 2, 'frozenRowCount': 4, 'frozenColumnCount': 3}}}}]})
tid = resp['replies'][-1]['addSheet']['properties']['sheetId']

call('PUT', f"{API}/{SID}/values/'{TAB}'!A1", params={'valueInputOption': 'USER_ENTERED'}, json={'values': top})
call('PUT', f"{API}/{SID}/values/'{TAB}'!A4", params={'valueInputOption': 'RAW'}, json={'values': [hdr]})
for i in range(0, n, 400):
    call('PUT', f"{API}/{SID}/values/'{TAB}'!A{FIRST + i}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': data[i:i + 400]})

blue = {'red': 0.85, 'green': 0.9, 'blue': 0.97}
yellow = {'red': 1, 'green': 0.97, 'blue': 0.8}
reqs = [{'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': 4},
                        'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': blue, 'wrapStrategy': 'WRAP'}},
                        'fields': 'userEnteredFormat(textFormat,backgroundColor,wrapStrategy)'}},

        {'setBasicFilter': {'filter': {'range': {'sheetId': tid, 'startRowIndex': FIRST - 2, 'endRowIndex': last,
                                                 'startColumnIndex': 0, 'endColumnIndex': ncol}}}}]
for j in range(len(REST) + 1):  # % cells in the top block
    cidx = 3 + 4 * j + 2 if j < len(REST) else ncol + 1
    reqs.append({'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': 2, 'startColumnIndex': cidx, 'endColumnIndex': cidx + 1},
                                'cell': {'userEnteredFormat': {'numberFormat': {'type': 'PERCENT', 'pattern': '0.00%'}}},
                                'fields': 'userEnteredFormat.numberFormat'}})
for j in range(len(REST)):  # yellow = cells to fill manually
    reqs.append({'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': FIRST - 1, 'endRowIndex': last,
                                          'startColumnIndex': 3 + 4 * j + 2, 'endColumnIndex': 3 + 4 * j + 3},
                                'cell': {'userEnteredFormat': {'backgroundColor': yellow}}, 'fields': 'userEnteredFormat.backgroundColor'}})
rng = {'sheetId': tid, 'startRowIndex': FIRST - 1, 'endRowIndex': last, 'startColumnIndex': 3, 'endColumnIndex': ncol}
for txt, colr in (('Not Matched', {'red': 0.98, 'green': 0.85, 'blue': 0.85}), ('Matched', {'red': 0.85, 'green': 0.94, 'blue': 0.85})):
    reqs.append({'addConditionalFormatRule': {'index': 0, 'rule': {'ranges': [rng], 'booleanRule': {
        'condition': {'type': 'TEXT_EQ', 'values': [{'userEnteredValue': txt}]}, 'format': {'backgroundColor': colr}}}}})
call('POST', f'{API}/{SID}:batchUpdate', json={'requests': reqs})
print('added', TAB, n, 'rows x', ncol, 'cols')
