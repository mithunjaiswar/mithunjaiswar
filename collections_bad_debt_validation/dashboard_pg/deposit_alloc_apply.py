# Write alloc_date (AH) and dep_at_alloc (AI) for MV rows of Raw_Data:
# Active pilots only = deposit balance on the day of the last allocation BEFORE the hisaab week.
# usage: python3 deposit_alloc_apply.py <tool-result files with "partner~alloc_date~deposit" lines>
import json, sys
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
AL = json.load(open('../dash/alloc_before_week.json'))           # "week|partner" -> alloc date
DEP = {}
for f in sys.argv[1:]:
    for l in json.load(open(f))['result'].split('\n'):
        l = l.strip()
        if l.startswith('| ') and '~' in l:
            p, a, d = l[2:].rstrip('|').strip().split('~')
            DEP[(p, a)] = d
N = json.load(open('../dash/raw_refresh.json')); h = N[0]
ia, idp = h.index('alloc_date'), h.index('dep_at_alloc')
out, miss = [], 0
for r in N[1:]:
    if r[60] != 'MV': break
    a = AL.get(f'{r[0]}|{r[1]}', '') if r[10] == 'Active' else ''
    d = DEP.get((r[1], a), '') if a else ''
    if a and d == '': miss += 1
    r[ia], r[idp] = a, d
    out.append([a, d])
print('MV rows', len(out), 'active with alloc', sum(1 for x in out if x[0]), 'missing deposit', miss)
json.dump(N, open('../dash/raw_refresh.json', 'w'))
for i in range(0, len(out), 20000):
    call('PUT', f"{API}/{DS}/values/'Raw_Data'!AH{i + 2}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': out[i:i + 20000]})
print('written')
