# Raw_Data AB entire_week_active = 1 when the pilot held a car on ALL 7 days of the hisaab week (allocation table);
# Summary rows 29-31 (Active Drivers Deposit To OS) = pilots with DP to OS in the week AND entire_week_active = 1.
import json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
FW = json.load(open('../dash/full_week.json'))
N = json.load(open('../dash/raw_refresh.json')); h = N[0]; ia = h.index('entire_week_active'); assert ia == 27
out = []
for r in N[1:]:
    if r[60] != 'MV': break
    v = FW.get(f'{r[0]}|{r[1]}', 0); r[ia] = str(v); out.append([v])
json.dump(N, open('../dash/raw_refresh.json', 'w'))
call('PUT', f"{API}/{DS}/values/'Raw_Data'!AB2:AB{len(out) + 1}", params={'valueInputOption': 'RAW'}, json={'values': out})
f = call('GET', f"{API}/{DS}/values/'Summary'!C29:J30", params={'valueRenderOption': 'FORMULA'})['values']
new = [[c.replace('Raw_Data!$K:$K,"Active"', 'Raw_Data!$AB:$AB,1') for c in r] for r in f]
assert all('$AB:$AB,1' in c for r in new for c in r)
call('PUT', f"{API}/{DS}/values/'Summary'!C29:J30", params={'valueInputOption': 'USER_ENTERED'}, json={'values': new})
print('AB written', len(out), 'full-week', sum(x[0] for x in out)); print(new[0][0])
