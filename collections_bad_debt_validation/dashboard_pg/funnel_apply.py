# Raw_Data AM bad_debt_collected_funnel = MIN(next-week positive payments, |bad_debt_amount|) when bad debt < 0 (old Sheet rule)
import json, datetime as dt
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
TR = '/root/.claude/projects/-home-user-mithunjaiswar/975ddfa8-2a6b-560b-8c6b-202af90fa71a/tool-results/mcp-Everest_Reporting_DB-run_read_only_query-1791867793708.txt'
rec = {}
for l in json.load(open(TR))['result'].split('\n'):
    l = l.strip()
    if l.startswith('| 2026-'):
        v = l[2:].rstrip('|').strip().split('~'); rec[(v[0], v[1])] = sum(max(float(x), 0) for x in v[2:7])
N = json.load(open('../dash/raw_refresh.json')); h = N[0]; ia, ib = h.index('bad_debt_collected_funnel'), h.index('bad_debt_amount')
f = lambda x: float(x) if x not in ('', None) else 0.0
out = []
for r in N[1:]:
    if r[60] != 'MV': break
    bd = f(r[ib]); nx = rec.get(((dt.date.fromisoformat(r[0]) + dt.timedelta(7)).isoformat(), r[1]), 0.0)
    v = round(min(nx, abs(bd)), 2) if bd < 0 else 0
    r[ia] = str(v); out.append([v])
json.dump(N, open('../dash/raw_refresh.json', 'w'))
call('PUT', f"{API}/{DS}/values/'Raw_Data'!AM2:AM{len(out) + 1}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': out})
print('written', len(out), 'non-zero', sum(1 for x in out if x[0]))
