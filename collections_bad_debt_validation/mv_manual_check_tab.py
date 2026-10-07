"""ADD (never replace/delete) a tab with an MV sample for manual checking.

Layout: Week | City | Employee/Agent | then for every other MV column: <col> (MV) | <col> (Manual) | <col> Matched? (formula)
        | Final Status (formula). Row 2 = match % per column over the rows where Manual is filled.
Usage: python3 mv_manual_check_tab.py <D> <token.json> <tab title>
<D>/mv_sample.json = list of rows in MV column order (53 columns)."""
import sys, json, time
import requests

D, TOKEN, TAB = sys.argv[1], sys.argv[2], sys.argv[3]
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
REST = [c for c in COLS if c not in KEYS]

def col_letter(i):  # 0-based -> A1 letters
    s = ''
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s

rows = json.load(open(f'{D}/mv_sample.json'))
rows.sort(key=lambda r: (r[COLS.index('hissab_week')], r[COLS.index('city')], r[COLS.index('partner_etm')]))
FIRST = 3  # first data row (row 1 header, row 2 match %)
n = len(rows)
last = FIRST + n - 1

hdr = ['Week', 'City', 'Employee/Agent']
for c in REST:
    hdr += [f'{c} (MV)', f'{c} (Manual)', f'{c} Matched?']
hdr.append('Final Status')
ncol = len(hdr)
fin = col_letter(ncol - 1)
first_m, last_m = col_letter(3), col_letter(ncol - 2)

pct = ['', '', 'Match % (rows where Manual filled) ->']
for j, c in enumerate(REST):
    m = col_letter(3 + 3 * j + 2)
    rng = f'{m}{FIRST}:{m}{last}'
    pct += ['', '', f'=IFERROR(COUNTIF({rng},"Matched")/(COUNTIF({rng},"Matched")+COUNTIF({rng},"Not Matched")),"")']
pct.append(f'=IFERROR(COUNTIF({fin}{FIRST}:{fin}{last},"Matched")/(COUNTIF({fin}{FIRST}:{fin}{last},"Matched")+COUNTIF({fin}{FIRST}:{fin}{last},"Not Matched")),"")')

data = []
for k, r in enumerate(rows):
    rn = FIRST + k
    v = dict(zip(COLS, r))
    line = [v['hissab_week'], v['city'], v['partner_etm']]
    for j, c in enumerate(REST):
        mv, man = col_letter(3 + 3 * j) + str(rn), col_letter(3 + 3 * j + 1) + str(rn)
        line += [v[c], '',
                 f'=IF({man}="","",IF(AND(ISNUMBER({mv}),ISNUMBER({man})),IF(ABS({mv}-{man})<=1,"Matched","Not Matched"),'
                 f'IF(LOWER(TRIM(TO_TEXT({mv})))=LOWER(TRIM(TO_TEXT({man}))),"Matched","Not Matched")))']
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
if any(s['properties']['title'] == TAB for s in meta['sheets']):
    raise SystemExit(f'Tab "{TAB}" already exists - not touching it. Choose another name.')
resp = call('POST', f'{API}/{SID}:batchUpdate', json={'requests': [{'addSheet': {'properties': {
    'title': TAB, 'gridProperties': {'rowCount': last + 2, 'columnCount': ncol, 'frozenRowCount': 2, 'frozenColumnCount': 3}}}}]})
tid = resp['replies'][0]['addSheet']['properties']['sheetId']

call('PUT', f"{API}/{SID}/values/'{TAB}'!A1", params={'valueInputOption': 'RAW'}, json={'values': [hdr]})
call('PUT', f"{API}/{SID}/values/'{TAB}'!A2", params={'valueInputOption': 'USER_ENTERED'}, json={'values': [pct]})
for i in range(0, n, 400):
    call('PUT', f"{API}/{SID}/values/'{TAB}'!A{FIRST + i}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': data[i:i + 400]})

blue = {'red': 0.85, 'green': 0.9, 'blue': 0.97}
yellow = {'red': 1, 'green': 0.97, 'blue': 0.8}
reqs = [{'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': 2},
                        'cell': {'userEnteredFormat': {'textFormat': {'bold': True}, 'backgroundColor': blue, 'wrapStrategy': 'WRAP'}},
                        'fields': 'userEnteredFormat(textFormat,backgroundColor,wrapStrategy)'}},
        {'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': 1, 'endRowIndex': 2, 'startColumnIndex': 3, 'endColumnIndex': ncol},
                        'cell': {'userEnteredFormat': {'numberFormat': {'type': 'PERCENT', 'pattern': '0.0%'}}},
                        'fields': 'userEnteredFormat.numberFormat'}},
        {'setBasicFilter': {'filter': {'range': {'sheetId': tid, 'startRowIndex': 0, 'endRowIndex': last,
                                                 'startColumnIndex': 0, 'endColumnIndex': ncol}}}}]
for j in range(len(REST)):  # yellow = cells to fill manually
    reqs.append({'repeatCell': {'range': {'sheetId': tid, 'startRowIndex': FIRST - 1, 'endRowIndex': last,
                                          'startColumnIndex': 3 + 3 * j + 1, 'endColumnIndex': 3 + 3 * j + 2},
                                'cell': {'userEnteredFormat': {'backgroundColor': yellow}}, 'fields': 'userEnteredFormat.backgroundColor'}})
rng = {'sheetId': tid, 'startRowIndex': FIRST - 1, 'endRowIndex': last, 'startColumnIndex': 3, 'endColumnIndex': ncol}
for txt, colr in (('Not Matched', {'red': 0.98, 'green': 0.85, 'blue': 0.85}), ('Matched', {'red': 0.85, 'green': 0.94, 'blue': 0.85})):
    reqs.append({'addConditionalFormatRule': {'index': 0, 'rule': {'ranges': [rng], 'booleanRule': {
        'condition': {'type': 'TEXT_EQ', 'values': [{'userEnteredValue': txt}]}, 'format': {'backgroundColor': colr}}}}})
call('POST', f'{API}/{SID}:batchUpdate', json={'requests': reqs})
print('added', TAB, n, 'rows x', ncol, 'cols')
