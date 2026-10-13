# Fill old-Sheet values for Deposit Threshold / Deposit [At Allocation] rows in city_product.json from the ORIGINAL
# old Sheet's sd_bucket / sd_bucket_V2 tabs (the copy cannot run their IMPORTRANGE). Same SUMIFS as the Sheet formula.
import json, datetime as dt
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
REF = '1wkebsPPLwXnRYAuvRV_fhMGQLRxv6JwH-cYlaIEBjRw'
SD = {t: call('GET', f"{API}/{REF}/values/'{t}'!A1:K1000")['values'] for t in ('sd_bucket', 'sd_bucket_V2')}
json.dump(SD, open('../dash/sd_bucket_ref.json', 'w'))
BK = ['Deposit <= 0', 'Deposit Between 0-2000', 'Deposit Between 2000-5000', 'Deposit Between 5000-10000', 'Deposit Between 10000-20000', 'Deposit 20000+']
WEEKS = ['Sep-14', 'Sep-21', 'Sep-28', 'Oct-05']
iso = lambda w: dt.datetime.strptime(w + '-2026', '%b-%d-%Y').date().isoformat()
def sheet_val(tab, city, prod, week, bucket):
    rows = SD[tab]; h = rows[0]; j = h.index(bucket); tot = 0
    for r in rows[1:]:
        if len(r) <= j or r[0] != iso(week): continue
        if city != '*' and r[1] != city: continue
        if prod != '*' and r[3] != prod: continue
        tot += int(float(r[j] or 0))
    return tot
RES = json.load(open('../dash/city_product.json'))
for r in RES:
    tab = {'Deposit Threshold': 'sd_bucket', 'Deposit [At Allocation]': 'sd_bucket_V2'}.get(r[1])
    if not tab or r[2] not in BK: continue
    city, prod = [x.strip() for x in r[0].split('|')]
    ok = 0
    for k, w in enumerate(WEEKS):
        c = 3 + 4 * k; x = sheet_val(tab, city, prod, w, r[2])
        y = float(str(r[c + 1]).replace(',', '') or 0); d = y - x
        r[c], r[c + 2], r[c + 3] = str(x), round(d), (round(d / abs(x), 4) if x else ('' if d == 0 else 'n/a'))
        ok += abs(d) <= max(abs(x) * 0.02, 1 if abs(x) >= 20 else 0)
    r[-1] = f'{ok}/{len(WEEKS)}'
json.dump(RES, open('../dash/city_product.json', 'w'))
for r in RES:
    if r[0] == '* | *' and r[1].startswith('Deposit'): print(r[1][:16], r[2][:26].ljust(26), r[3:5], r[-1])
