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
# ---- write tab (with week-on-week splitter)
exec(open('city_product_tab.py').read())
