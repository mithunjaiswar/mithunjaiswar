"""Build summary / city / agent level comparison tables from validate.py outputs."""
import sys, pickle
import numpy as np
import pandas as pd

D = sys.argv[1]
OUT = f'{D}/out'
agent = pd.read_pickle(f'{OUT}/agent.pkl')
pres = pd.read_pickle(f'{OUT}/presence.pkl')
j = pd.read_pickle(f'{OUT}/joined.pkl')
m = pd.read_pickle(f'{OUT}/merged.pkl')
specs = pickle.load(open(f'{OUT}/specs.pkl', 'rb'))['specs']
DD = 'Need to Deep Dive'
WEEKS = sorted(agent.week.unique())

def num(x):
    return pd.to_numeric(pd.Series(x).astype(str).str.replace(',', '').str.replace('%', ''), errors='coerce').fillna(0)

compared = [sp for sp in specs if f"{sp['pg']} | Status" in agent.columns]
NUMK = {sp['pg'] for sp in specs if sp['kind'] == 'num'}

# ---------------- 1. column x week summary ----------------
rows = []
for sp in specs:
    pc = sp['pg']
    for w in WEEKS + ['All 3 weeks']:
        sel = agent if w == 'All 3 weeks' else agent[agent.week == w]
        r = dict(Week=w, PG_Column=pc, Sheet_Column=sp['sheet'] or 'Not available in Sheet Raw_Data',
                 Comparison=sp['kind'])
        if f'{pc} | Status' in agent.columns:
            st = sel[f'{pc} | Status']; rs = sel[f'{pc} | Reason']
            mm = st.eq('Mismatched')
            r.update(Rows_Compared=len(sel), Matched=int((~mm).sum()), Mismatched=int(mm.sum()),
                     Match_Pct=round(100 * (~mm).mean(), 2) if len(sel) else None,
                     Need_Deep_Dive=int(rs.str.startswith(DD).sum()))
            if pc in NUMK:
                r.update(Sheet_Sum=round(num(sel[f'{pc} | Sheet']).sum(), 2), PG_Sum=round(num(sel[f'{pc} | PG']).sum(), 2))
                r['Sum_Diff'] = round(r['PG_Sum'] - r['Sheet_Sum'], 2)
            r['Status'] = 'Matched' if mm.sum() == 0 else 'Mismatched'
            top = rs[mm].value_counts()
            r['Reasons (rows)'] = ' || '.join(f'{k} [{v}]' for k, v in top.items())
        elif sp['kind'] == 'key':
            r.update(Status='Matched', Rows_Compared=len(sel), Matched=len(sel), Mismatched=0, Match_Pct=100.0,
                     **{'Reasons (rows)': 'Join key (week + partner): every Sheet row joined to exactly one PG row'})
        elif sp['kind'] == 'presence':
            ps = pres if w == 'All 3 weeks' else pres[pres.week == w]
            mm = ps.Status.eq('Mismatched')
            r.update(Rows_Compared=len(ps), Matched=int((~mm).sum()), Mismatched=int(mm.sum()),
                     Match_Pct=round(100 * (~mm).mean(), 2), Need_Deep_Dive=int(mm.sum()),
                     Status='Matched' if mm.sum() == 0 else 'Mismatched',
                     **{'Reasons (rows)': ' || '.join(f'{k} [{v}]' for k, v in ps.Reason[ps.Reason != ''].value_counts().items())})
        elif sp['kind'] == 'agg':
            pw = m[(m.pg_for_collections == '1') & ((m.week == w) if w != 'All 3 weeks' else True)]
            sw = j if w == 'All 3 weeks' else j[j.week == w]
            pgv = int(num(pw.pg_cars_under_recovery_hissab_week).sum()); shv = int(sw.sh_in_car_recovery.eq('Yes').sum())
            r.update(Sheet_Sum=shv, PG_Sum=pgv, Sum_Diff=pgv - shv, Status='Matched' if pgv == shv else 'Mismatched',
                     **{'Reasons (rows)': 'Aggregate check (for_collections = 1): PG SUM(cars_under_recovery_hissab_week) vs Sheet COUNT(in_car_recovery = Yes). '
                        'PG counts cars (a partner can have >1 car under recovery); differences follow the in_car_recovery_hissab_week row reasons'})
        else:
            pw = m[m.pg_for_collections.notna() & ((m.week == w) if w != 'All 3 weeks' else True)]
            pw = pw[pw._merge != 'right_only']
            r.update(Status='Not in Sheet', **{'Reasons (rows)': (sp.get('note') or '') + ('; ' if sp.get('note') else '') +
                     'Column not present in Sheet Raw_Data - cannot be matched; PG total shown for reference'})
            if pc not in ('id', 'last_updated', 'next_join_date'):
                v = num(pw['pg_' + pc].replace({'true': 1, 'false': 0}))
                r['PG_Sum'] = round(v.sum(), 2)
        rows.append(r)
col_summary = pd.DataFrame(rows)
order = ['Week', 'PG_Column', 'Sheet_Column', 'Comparison', 'Rows_Compared', 'Matched', 'Mismatched', 'Match_Pct',
         'Need_Deep_Dive', 'Sheet_Sum', 'PG_Sum', 'Sum_Diff', 'Status', 'Reasons (rows)']
col_summary = col_summary.reindex(columns=order)

# ---------------- 2. week / city level (sum & count per column) ----------------
def level_table(keys):
    out = []
    jj = j.copy(); jj['All'] = 'All'
    ag = agent.copy(); ag['All'] = 'All'
    pr = pres.copy(); pr['All'] = 'All'
    for k, g in ag.groupby(keys):
        k = k if isinstance(k, tuple) else (k,)
        r = dict(zip(keys, k))
        pg_rows = pr
        for kk, vv in zip(keys, k):
            pg_rows = pg_rows[pg_rows[kk] == vv]
        r['Partner Count - Sheet'] = int(pg_rows.presence.isin(['Both', 'Sheet only']).sum())
        r['Partner Count - PG (for_collections=1)'] = int((pg_rows.pg_for_collections == '1').sum())
        r['Partner Count - Status'] = 'Matched' if r['Partner Count - Sheet'] == r['Partner Count - PG (for_collections=1)'] else 'Mismatched'
        r['Partner Count - PG all rows'] = int(pg_rows.presence.isin(['Both', 'PG only']).sum())
        for sp in compared:
            pc = sp['pg']
            if pc in NUMK and pc != 'lead_id':
                sv, pv = num(g[f'{pc} | Sheet']).sum(), num(g[f'{pc} | PG']).sum()
                r[f'{pc} - Sheet (sum)'] = round(sv, 2); r[f'{pc} - PG (sum)'] = round(pv, 2)
                # status follows the row-level result (each row within tolerance); sums can drift by paise rounding
                r[f'{pc} - Status'] = 'Matched' if g[f'{pc} | Status'].eq('Matched').all() else 'Mismatched'
            else:
                r[f'{pc} - Matched rows'] = int(g[f'{pc} | Status'].eq('Matched').sum())
                r[f'{pc} - Mismatched rows'] = int(g[f'{pc} | Status'].eq('Mismatched').sum())
                r[f'{pc} - Status'] = 'Matched' if r[f'{pc} - Mismatched rows'] == 0 else 'Mismatched'
        out.append(r)
    t = pd.DataFrame(out)
    st = [c for c in t.columns if c.endswith('Status')]
    t['Overall Status'] = np.where((t[st] == 'Matched').all(axis=1), 'Matched', 'Mismatched')
    t['Mismatched Columns'] = t[st].apply(lambda r: ', '.join(c.replace(' - Status', '') for c, v in r.items() if v != 'Matched'), axis=1)
    return t

week_level = level_table(['week'])
city_level = level_table(['week', 'city'])

# ---------------- 3. reason summary ----------------
rr = []
for sp in compared:
    pc = sp['pg']
    x = agent[agent[f'{pc} | Status'] == 'Mismatched']
    for (w, reason), n in x.groupby(['week', f'{pc} | Reason']).size().items():
        rr.append(dict(Week=w, PG_Column=pc, Sheet_Column=sp['sheet'], Reason=reason, Rows=n,
                       Category='Need to Deep Dive' if DD in reason else
                       ('Sheet issue' if reason.startswith('Sheet') else
                        ('PG issue' if reason.startswith('PG') else
                         ('Timing / refresh' if reason.startswith('Timing') else 'Definition / logic difference')))))
for (w, reason), n in pres[pres.Reason != ''].groupby(['week', 'Reason']).size().items():
    rr.append(dict(Week=w, PG_Column='for_collections (row presence)', Sheet_Column='row present in Raw_Data', Reason=reason, Rows=n,
                   Category='Expected' if reason.startswith('Expected') else 'Need to Deep Dive'))
reason_summary = pd.DataFrame(rr).sort_values(['PG_Column', 'Week', 'Rows'], ascending=[True, True, False])

col_summary.to_pickle(f'{OUT}/col_summary.pkl'); week_level.to_pickle(f'{OUT}/week_level.pkl')
city_level.to_pickle(f'{OUT}/city_level.pkl'); reason_summary.to_pickle(f'{OUT}/reason_summary.pkl')
print(col_summary[col_summary.Week == 'All 3 weeks'][['PG_Column', 'Sheet_Column', 'Rows_Compared', 'Mismatched', 'Match_Pct', 'Need_Deep_Dive', 'Status']].to_string())
print(week_level[['week', 'Partner Count - Sheet', 'Partner Count - PG (for_collections=1)', 'Partner Count - PG all rows', 'Overall Status']])
print(city_level.shape, reason_summary.shape)
