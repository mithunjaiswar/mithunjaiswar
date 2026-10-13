# Deposit_Raw tab: 1 row per pilot active (car held at any time) in the hisaab week, with week-end deposit and
# deposit at the end of the week of their last allocation; Summary rows 75-86 count from it.
import json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip(); TAB = 'Deposit_Raw'
P = json.load(open('../dash/deposit_pilots.json'))
N = json.load(open('../dash/raw_refresh.json')); h = N[0]; ix = {c: i for i, c in enumerate(h)}
mv = {(r[0], r[1]): (r[ix['city']], r[ix['fuel_type']], r[ix['product_type']]) for r in N[1:] if r[60] == 'MV'}
def prod(p, fuel):
    p = (p or '').strip()
    if p == 'leasing': return 'EV' if fuel == 'EV' else 'SINGLE'
    return {'DTO': 'D2O', 'Own Now': 'Own Now', 'Rev_share': 'Revenue Share', 'Fixed Pay': 'Fixed Pay', 'New_team': 'SINGLE'}.get(p, p)
HDR = ['hissab_week', 'partner_etm', 'city', 'fuel_type', 'product_type', 'last_alloc_date', 'deposit_week_end', 'deposit_at_alloc_week_end', 'in_mv']
rows = []
for w, e, city, fuel, pt, ad, dwe, dal in P:
    m = mv.get((w, e))
    c, f, p = m if m else (city, fuel, prod(pt, fuel))
    rows.append([w, e, c, f, p, ad, round(float(dwe)), round(float(dal)), 'Yes' if m else 'No'])
rows.sort(key=lambda r: (r[0], r[2], r[1]))
meta = call('GET', f'{API}/{DS}', params={'fields': 'sheets.properties'})
Pp = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
if TAB not in Pp:
    call('POST', f'{API}/{DS}:batchUpdate', json={'requests': [{'addSheet': {'properties': {'title': TAB, 'gridProperties': {'rowCount': len(rows) + 1000, 'columnCount': len(HDR), 'frozenRowCount': 1}}}}]})
else:
    call('POST', f"{API}/{DS}/values/'{TAB}'!A:I:clear", json={})
call('PUT', f"{API}/{DS}/values/'{TAB}'!A1", params={'valueInputOption': 'RAW'}, json={'values': [HDR]})
for i in range(0, len(rows), 20000):
    call('PUT', f"{API}/{DS}/values/'{TAB}'!A{i + 2}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': rows[i:i + 20000]})
# Summary rows 75-80 (week-end deposit) and 81-86 (deposit at last allocation's week end)
B = [('"<=0"',), ('">0"', '"<=2000"'), ('">2000"', '"<=5000"'), ('">5000"', '"<=10000"'), ('">10000"', '"<=20000"'), ('">20000"',)]
def f(colv, c, b):
    crit = ''.join(f',Deposit_Raw!${colv}:${colv},{x}' for x in b)
    return f'=IFERROR(COUNTIFS(Deposit_Raw!$A:$A,TEXT({c}$8,"yyyy-mm-dd"),Deposit_Raw!$C:$C,$B$2,Deposit_Raw!$E:$E,$B$5,Deposit_Raw!$D:$D,$B$4{crit}), "-")'
cols = [chr(ord('C') + j) for j in range(8)]
V = [[f('G', c, b) for c in cols] for b in B] + [[f('H', c, b) for c in cols] for b in B]
call('PUT', f"{API}/{DS}/values/'Summary'!C75:J86", params={'valueInputOption': 'USER_ENTERED'}, json={'values': V})
print('Deposit_Raw rows', len(rows))
