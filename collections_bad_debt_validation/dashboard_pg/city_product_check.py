# Compare Summary (old Sheet copy vs our dashboard) for several City / Product filters -> tab Summary_City_Product
import json, re, time
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip(); CP = open('../dash/ref_copy_sid.txt').read().strip()
TAB = 'Summary_City_Product'
USER = call('GET', f"{API}/{DS}/values/'Summary'!B2:B7")['values']
CITIES = ['Bangalore', 'Chennai', 'Delhi NCR', 'Hyderabad', 'Kolkata', 'Mumbai', 'Pune']
PRODS = ['SINGLE', 'D2O', 'Own Now', 'EV', 'EIP']
COMBOS = [('*', '*')] + [(c, '*') for c in CITIES] + [('*', p) for p in PRODS]
WEEKS = ['Sep-14', 'Sep-21', 'Sep-28', 'Oct-05']
def num(s):
    s = str(s).replace(',', '').replace(' hrs', '').replace(' ', '')
    m = re.fullmatch(r'(-?[\d.]+)(K|%)?', s)
    if not m: return None
    v = float(m.group(1)); return v * 1000 if m.group(2) == 'K' else (v / 100 if m.group(2) == '%' else v)
g = lambda R, i, j: R[i][j] if i < len(R) and j < len(R[i]) else ''
def setf(sid, city, prod):
    call('POST', f'{API}/{sid}/values:batchUpdate', json={'valueInputOption': 'RAW', 'data': [
        {'range': "'Summary'!B2:B7", 'values': [[city], ['*'], ['*'], [prod], ['*'], ['*']]}]})
RES = []
try:
    for city, prod in COMBOS:
        setf(DS, city, prod); setf(CP, city, prod); time.sleep(25)
        A = call('GET', f"{API}/{CP}/values/'Summary'!A8:J86")['values']
        B = call('GET', f"{API}/{DS}/values/'Summary'!A8:J86")['values']
        ca = {g(A, 0, j): j for j in range(2, 10)}; cb = {g(B, 0, j): j for j in range(2, 10)}
        sec = ''
        for i in range(1, len(B)):
            sec = g(B, i, 0) or sec
            name = g(B, i, 1).strip()
            if not name: continue
            cells, bad, seen = [], 0, 0
            for w in WEEKS:
                a, b = g(A, i, ca.get(w, 99)), g(B, i, cb.get(w, 99)); x, y = num(a), num(b)
                if x is None or y is None:
                    cells += [a, b, '', '']; continue
                pc = '%' in a; d = y - x; seen += 1
                tol = max(abs(x) * 0.02, 0.0015 if pc else (1 if abs(x) >= 20 else 0))
                bad += abs(d) > tol + 1e-9
                cells += [a, b, round(d, 4) if pc else round(d), (round(d / abs(x), 4) if x else ('' if d == 0 else 'n/a'))]
            if seen: RES.append([f'{city} | {prod}', sec, name] + cells + [f'{seen - bad}/{seen}'])
        print(city, prod, 'rows', sum(1 for r in RES if r[0] == f'{city} | {prod}'), flush=True)
finally:
    call('POST', f'{API}/{DS}/values:batchUpdate', json={'valueInputOption': 'RAW', 'data': [{'range': "'Summary'!B2:B7", 'values': USER}]})
json.dump(RES, open('../dash/city_product.json', 'w'))
# ---- write tab
summ = [['Filter (City | Product)', 'Metrics compared', 'Matched (all 4 weeks within 2%)', 'Not matched', 'Match %']]
for city, prod in COMBOS:
    rs = [r for r in RES if r[0] == f'{city} | {prod}']
    ok = sum(1 for r in rs if r[-1].split('/')[0] == r[-1].split('/')[1])
    summ.append([f'{city} | {prod}', len(rs), ok, len(rs) - ok, round(ok / len(rs), 4) if rs else ''])
hdr = ['Filter (City | Product)', 'Section', 'Metric'] + sum([[f'{w} Sheet', f'{w} MV', f'{w} Diff (MV-Sheet)', f'{w} Diff %'] for w in WEEKS], []) + ['Weeks matched']
title = [[f'Summary check by City / Product – old Sheet vs our dashboard (MV), weeks {WEEKS[0]} to {WEEKS[-1]}. '
          'Old Sheet values come from an editable copy with the same filter. "*" = all. SINGLE = Leasing. Matched = within 2%.']]
V = title + [[]] + summ + [[]] + [hdr] + RES
meta = call('GET', f'{API}/{DS}', params={'fields': 'sheets.properties'})
P = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
req = [{'deleteSheet': {'sheetId': P[TAB]}}] if TAB in P else []
req.append({'addSheet': {'properties': {'title': TAB, 'index': 1, 'gridProperties': {'rowCount': len(V) + 10, 'columnCount': len(hdr), 'frozenRowCount': 0}}}})
sid = call('POST', f'{API}/{DS}:batchUpdate', json={'requests': req})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT', f"{API}/{DS}/values/'{TAB}'!A1", params={'valueInputOption': 'USER_ENTERED'}, json={'values': V})
h0 = 2 + len(summ) + 1  # header row index (0-based)
rng = lambda r0, r1, c0, c1: {'sheetId': sid, 'startRowIndex': r0, 'endRowIndex': r1, 'startColumnIndex': c0, 'endColumnIndex': c1}
B = {'red': 0.2, 'green': 0.25, 'blue': 0.4}; W = {'red': 1, 'green': 1, 'blue': 1}; RED = {'red': 0.85, 'green': 0, 'blue': 0}
R = [{'repeatCell': {'range': rng(0, 1, 0, 6), 'cell': {'userEnteredFormat': {'textFormat': {'bold': True, 'fontSize': 11}}}, 'fields': 'userEnteredFormat.textFormat'}},
     {'repeatCell': {'range': rng(2, 3, 0, 5), 'cell': {'userEnteredFormat': {'backgroundColor': B, 'textFormat': {'bold': True, 'foregroundColor': W}}}, 'fields': 'userEnteredFormat(backgroundColor,textFormat)'}},
     {'repeatCell': {'range': rng(h0, h0 + 1, 0, len(hdr)), 'cell': {'userEnteredFormat': {'backgroundColor': B, 'wrapStrategy': 'WRAP', 'textFormat': {'bold': True, 'foregroundColor': W}}}, 'fields': 'userEnteredFormat(backgroundColor,wrapStrategy,textFormat)'}},
     {'repeatCell': {'range': rng(3, 3 + len(summ) - 1, 4, 5), 'cell': {'userEnteredFormat': {'numberFormat': {'type': 'PERCENT', 'pattern': '0.0%'}}}, 'fields': 'userEnteredFormat.numberFormat'}},
     {'updateSheetProperties': {'properties': {'sheetId': sid, 'gridProperties': {'frozenRowCount': h0 + 1, 'frozenColumnCount': 3}}, 'fields': 'gridProperties(frozenRowCount,frozenColumnCount)'}},
     {'setBasicFilter': {'filter': {'range': rng(h0, h0 + 1 + len(RES), 0, len(hdr))}}}]
for k in range(4):  # red text for differences outside 2%
    dc, pcl = 3 + 4 * k + 2, 3 + 4 * k + 3
    R.append({'repeatCell': {'range': rng(h0 + 1, h0 + 1 + len(RES), pcl, pcl + 1), 'cell': {'userEnteredFormat': {'numberFormat': {'type': 'PERCENT', 'pattern': '0.0%'}}}, 'fields': 'userEnteredFormat.numberFormat'}})
    for c in (dc, pcl):
        R.append({'addConditionalFormatRule': {'index': 0, 'rule': {'ranges': [rng(h0 + 1, h0 + 1 + len(RES), c, c + 1)], 'booleanRule': {
            'condition': {'type': 'CUSTOM_FORMULA', 'values': [{'userEnteredValue': f'=AND(ISNUMBER(${chr(65 + 3 + 4 * k + 3)}{h0 + 2}),ABS(${chr(65 + 3 + 4 * k + 3)}{h0 + 2})>0.02)'}]},
            'format': {'textFormat': {'foregroundColor': RED, 'bold': True}}}}}})
R.append({'addConditionalFormatRule': {'index': 0, 'rule': {'ranges': [rng(3, 3 + len(summ) - 1, 4, 5)], 'booleanRule': {
    'condition': {'type': 'NUMBER_LESS', 'values': [{'userEnteredValue': '0.9'}]}, 'format': {'textFormat': {'foregroundColor': RED, 'bold': True}}}}}})
call('POST', f'{API}/{DS}:batchUpdate', json={'requests': R})
for r in summ: print(r)
