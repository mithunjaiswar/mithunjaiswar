# Week-level check of MV car-recovery columns against the Recovery Dash case logic.
import json, collections, datetime as dt
v = json.load(open('../cr/rawdata.json')); HD = v[0]
D = lambda s: dt.date.fromisoformat(str(s)[:10])
byp = collections.defaultdict(list)
for r in v[1:]:
    if r and r[0] != '':
        c = dict(zip(HD, r)); c['b'], c['c'] = D(c['week_start']), D(c['close_week']); byp[c['partner_etid']].append(c)
N = json.load(open('../dash/raw_refresh.json')); h = N[0]; ix = {c: h.index(c) for c in h}
W = collections.defaultdict(lambda: collections.Counter()); EX = collections.defaultdict(list)
for row in N[1:]:
    w = D(row[0]); e = w + dt.timedelta(6); cs = byp.get(row[1], [])
    act = [c for c in cs if c['b'] <= e and c['c'] >= w]
    comp = [c for c in act if w <= c['c'] <= e and c['final_status'] == 'Completed']
    mv_in = row[ix['in_car_recovery']] == 'Yes'; mv_cu = int(float(row[ix['cars_under_recovery_hissab_week']] or 0))
    mv_t = row[ix['recovery_tat']] != ''
    k = W[row[0]]
    k['in_mv'] += mv_in; k['in_dash'] += bool(act); k['in_bad'] += mv_in != bool(act)
    k['cu_mv'] += mv_cu; k['cu_dash'] += len(act); k['cu_bad'] += mv_cu != len(act)
    k['t_mv'] += mv_t; k['t_dash'] += bool(comp); k['t_bad'] += mv_t != bool(comp); k['n'] += 1
    if mv_in != bool(act) and len(EX['in', mv_in]) < 2:
        cc = act or cs
        EX['in', mv_in].append(f"{row[1]}, week {row[0]}: MV in_car_recovery = {'Yes' if mv_in else 'No'}; Recovery Dash cases: " +
                               ('; '.join(f"#{c['recovery_id']} {c['start_date']} -> {c['close_date']} {c['final_status']}" for c in cc[:2]) or 'none'))
    if mv_cu > len(act) + 1 and len(EX['cu']) < 2:
        EX['cu'].append(f"{row[1]}, week {row[0]}: MV cars_under_recovery = {mv_cu}; Recovery Dash active cases = {len(act)}")
    if mv_t and comp and len(EX['t']) < 2:
        EX['t'].append(f"{row[1]}, week {row[0]}: MV recovery_tat = {row[ix['recovery_tat']]} (days); Recovery Dash TAT = {round(float(comp[0]['tat_seconds'])/3600,1)} hrs")
    if mv_t and not comp and len(EX['t0']) < 1:
        EX['t0'].append(f"{row[1]}, week {row[0]}: MV recovery_tat = {row[ix['recovery_tat']]} but no recovery completed in this week")
json.dump({'weeks': {w: dict(c) for w, c in W.items()}, 'ex': {str(k): x for k, x in EX.items()}}, open('../dash/recovery_mv_check.json', 'w'), indent=1)
for w in sorted(W): print(w, dict(W[w]))
for k, x in EX.items(): print(k, x)
