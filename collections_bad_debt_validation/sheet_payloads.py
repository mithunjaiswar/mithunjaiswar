"""Compact tables written into the Google Sheet (summary level + small deep-dive list)."""
import sys, json
import numpy as np
import pandas as pd

D = sys.argv[1]; OUT = f'{D}/out'
col = pd.read_pickle(f'{OUT}/col_summary.pkl')
wk = pd.read_pickle(f'{OUT}/week_level.pkl'); city = pd.read_pickle(f'{OUT}/city_level.pkl')
rs = pd.read_pickle(f'{OUT}/reason_summary.pkl')

def clean(df):
    df = df.replace({np.nan: ''})
    def cv(v):
        if isinstance(v, (float, np.floating)):
            return int(v) if float(v).is_integer() else round(float(v), 2)
        if isinstance(v, np.integer):
            return int(v)
        return v
    return [list(df.columns)] + [[cv(v) for v in r] for r in df.itertuples(index=False)]

c = col.copy()
c['Main Reason'] = c['Reasons (rows)'].fillna('').str.split(' \\|\\| ').str[0]
c['Distinct Reasons'] = c['Reasons (rows)'].fillna('').apply(lambda s: len(s.split(' || ')) if s else 0)
c.loc[c.PG_Column.isin(['lead_id']), ['Sheet_Sum', 'PG_Sum', 'Sum_Diff']] = np.nan
c = c[~(c.Status.eq('Not in Sheet') & c.Week.ne('All 3 weeks'))]
c['Main Reason'] = c['Main Reason'].str.replace('; Column not present in Sheet Raw_Data - cannot be matched; PG total shown for reference', ' - not in Sheet; PG total for reference', regex=False) \
    .str.replace('Column not present in Sheet Raw_Data - cannot be matched; PG total shown for reference', 'Not in Sheet Raw_Data; PG total for reference', regex=False)
c = c.drop(columns=['Reasons (rows)', 'Comparison'])
wo = {'All 3 weeks': 0}
c['_o'] = c.Week.map(lambda w: wo.get(w, 1)); c['_p'] = c.PG_Column.map({k: i for i, k in enumerate(col.PG_Column.unique())})
c = c.sort_values(['_p', '_o', 'Week']).drop(columns=['_o', '_p'])
lv = pd.concat([wk.rename(columns={'week': 'Week'}).assign(City='ALL CITIES'), city.rename(columns={'week': 'Week', 'city': 'City'})])
lv = lv[['Week', 'City', 'Overall Status'] + [x for x in lv.columns if x not in ('Week', 'City', 'Overall Status', 'Mismatched Columns')]]
json.dump(dict(summary=clean(c), level=clean(lv), reasons=clean(rs[['Week', 'PG_Column', 'Sheet_Column', 'Category', 'Reason', 'Rows']])),
          open(f'{OUT}/payloads.json', 'w'))
for k, v in json.load(open(f'{OUT}/payloads.json')).items():
    print(k, len(v), len(v[0]), len(json.dumps(v)))
