"""Write the full validation workbook (all tabs, full agent-level detail)."""
import sys
import pandas as pd

D, XLSX = sys.argv[1], sys.argv[2]
OUT = f'{D}/out'
col = pd.read_pickle(f'{OUT}/col_summary.pkl')
wk = pd.read_pickle(f'{OUT}/week_level.pkl')
city = pd.read_pickle(f'{OUT}/city_level.pkl')
rs = pd.read_pickle(f'{OUT}/reason_summary.pkl')
ag = pd.read_pickle(f'{OUT}/agent.pkl')
pres = pd.read_pickle(f'{OUT}/presence.pkl')

ag = ag.rename(columns={'week': 'Week', 'city': 'City', 'employee': 'Employee/Agent'})
lead = ['Week', 'City', 'Employee/Agent', 'Overall Status', 'Mismatched Columns']
ag = ag[lead + [c for c in ag.columns if c not in lead]]
dd = []
for c in [c for c in ag.columns if c.endswith('| Reason')]:
    pc = c.split(' |')[0]
    x = ag[ag[c].str.startswith('Need to Deep Dive')]
    dd.append(pd.DataFrame({'Week': x.Week, 'City': x.City, 'Employee/Agent': x['Employee/Agent'], 'PG Column': pc,
                            'Sheet Value': x[f'{pc} | Sheet'], 'PG Value': x[f'{pc} | PG'], 'Status': 'Mismatched', 'Reason': x[c]}))
p = pres[pres.Status == 'Mismatched']
dd.append(pd.DataFrame({'Week': p.week, 'City': p.city, 'Employee/Agent': p.employee, 'PG Column': 'for_collections (row presence)',
                        'Sheet Value': p.presence.map({'Both': 'present', 'PG only': 'missing', 'Sheet only': 'present'}),
                        'PG Value': p.pg_for_collections.fillna('row missing'), 'Status': 'Mismatched', 'Reason': p.Reason}))
dd = pd.concat(dd).sort_values(['PG Column', 'Week', 'City', 'Employee/Agent'])

with pd.ExcelWriter(XLSX, engine='xlsxwriter') as w:
    col.to_excel(w, sheet_name='Column_Summary', index=False)
    pd.concat([wk.rename(columns={'week': 'Week'}).assign(City='ALL'), city.rename(columns={'week': 'Week', 'city': 'City'})]) \
        .pipe(lambda t: t[['Week', 'City'] + [c for c in t.columns if c not in ('Week', 'City')]]) \
        .to_excel(w, sheet_name='Week_City_Level', index=False)
    rs.to_excel(w, sheet_name='Reason_Summary', index=False)
    dd.to_excel(w, sheet_name='Deep_Dive_Items', index=False)
    pres.rename(columns={'week': 'Week', 'city': 'City', 'employee': 'Employee/Agent', 'presence': 'Row Presence',
                         'pg_for_collections': 'PG for_collections'}).to_excel(w, sheet_name='Row_Presence', index=False)
    ag.to_excel(w, sheet_name='Agent_Level', index=False)
    for name, ws in w.sheets.items():
        ws.freeze_panes(1, 3 if name in ('Agent_Level', 'Deep_Dive_Items', 'Row_Presence') else 2)
        ws.autofilter(0, 0, 0, 0)
print('deep dive items', len(dd))
