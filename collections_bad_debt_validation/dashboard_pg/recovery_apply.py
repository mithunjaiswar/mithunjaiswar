# Rebuild Raw_Data AR..AX (car recovery metrics) from the Central Car Recovery Dash case data,
# using the same rules as its Weekly_Summary tab, and write them to the dashboard sheet.
import json, collections, datetime as dt
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
v = json.load(open('../cr/rawdata.json')); HD = v[0]
D = lambda s: dt.date.fromisoformat(str(s)[:10])
cases = collections.defaultdict(list)
for r in v[1:]:
    if not r or r[0] == '': continue
    c = dict(zip(HD, r)); c['b'], c['c'] = D(c['week_start']), D(c['close_week'])
    cases[c['partner_etid']].append(c)

def metrics(pid, W):
    E = W + dt.timedelta(6)
    cs = cases.get(pid, [])
    closed = [c for c in cs if c['b'] <= E and W <= c['c'] <= E]
    team = [c for c in closed if c['final_status'] == 'Completed' and c['finalstatus_reason'] == '']
    organic = [c for c in closed if c['final_status'] == 'Cancelled' and
               (c['finalstatus_reason'] == 'Driver Dropped Vehicle' or (c['finalstatus_reason'] == '' and c['checkin_dt'] != ''))]
    tat = [float(c['tat_seconds']) / 3600 for c in team]
    return [sum(1 for c in cs if W <= c['b'] <= E and c['c'] >= W),          # recovery_initiated
            sum(1 for c in cs if c['b'] < W and c['c'] >= W),                # recovery_brought_fwd
            len(team), len(organic),                                         # recovered_team, recovered_organic
            sum(1 for c in cs if c['b'] <= E and c['c'] > E),                # recovery_pending
            round(sum(tat) / len(tat), 1) if tat else '',                    # recovery_tat_hrs
            ', '.join(sorted({c['agent_name'] for c in team if c['agent_name']}))]  # recovery agent

N = json.load(open('../dash/raw_refresh.json')); h = N[0]
i0 = h.index('recovery_initiated'); assert h[i0:i0 + 7][-1] == 'recovery_agent_id'
out = []
for row in N[1:]:
    m = metrics(row[1], D(row[0])); row[i0:i0 + 7] = [str(x) for x in m]; out.append(m)
h[i0 + 6] = 'recovery_agent'
json.dump(N, open('../dash/raw_refresh.json', 'w'))
call('PUT', f"{API}/{DS}/values/'Raw_Data'!AX1", params={'valueInputOption': 'RAW'}, json={'values': [['recovery_agent']]})
for s in range(0, len(out), 20000):
    call('PUT', f"{API}/{DS}/values/'Raw_Data'!AR{s + 2}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': out[s:s + 20000]})
tot = collections.defaultdict(lambda: [0] * 5)
for row, m in zip(N[1:], out):
    for k in range(5): tot[row[0]][k] += m[k]
for w in sorted(tot): print(w, dict(zip(['initiated', 'brought_fwd', 'team', 'organic', 'pending'], tot[w])))
