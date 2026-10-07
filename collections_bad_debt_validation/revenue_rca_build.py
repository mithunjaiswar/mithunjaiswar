"""Classify revenue_type mismatches against the hisaab record (fleet_leasing_weeklydata of the driven week).
Usage: python3 revenue_rca_build.py <D> <query-result-21Sep> <query-result-28Sep> <query-result-05Oct>"""
import sys, os, json, pandas as pd
os.chdir(sys.argv[1])
FILES = dict(zip(['2026-09-21','2026-09-28','2026-10-05'], sys.argv[2:5]))
rows=[]
for w,f in FILES.items():
    s=json.load(open(f))['result']
    for l in s.split('\n')[3:]:
        if l.startswith('| '):
            p=l[2:].rstrip(' |').split('|')
            if len(p)==4: rows.append([w]+[x.strip() for x in p])
src=pd.DataFrame(rows,columns=['week','employee','pg_rt','flw','alloc'])
a=pd.read_pickle('out/agent.pkl'); j=pd.read_pickle('out/joined.pkl')
x=a[a['revenue_type | Status']=='Mismatched'][['week','city','employee','revenue_type | Sheet','revenue_type | PG']]
x.columns=['week','city','employee','sheet','pg']
x=x.merge(j[['week','employee','pg_location','sh_allocation_location']],on=['week','employee'],how='left').merge(src[['week','employee','flw','alloc']],on=['week','employee'],how='left').fillna('')
LBL={'6':'D2O','2':'EV','1':None}
def htypes(flw):
    out=[]
    for part in [p for p in flw.split(';') if p]:
        bv,lt=(part.split('/',1)+[''])[:2]; lt=lt.upper()
        t='D2O' if bv=='6' else ('EV_Leasing' if bv=='2' and 'D2O' not in lt else ('EV on D2O plan' if bv=='2' else ('Own Now' if 'OWN' in lt else 'Leasing')))
        if t not in out: out.append(t)
    return sorted(out)
def norm(v): return 'Leasing' if v.lower()=='leasing' else v
def dw(w): d=pd.Timestamp(w); return f"{(d-pd.Timedelta(days=7)):%d-%b} to {(d-pd.Timedelta(days=1)):%d-%b}"
def reason(r):
    h=htypes(r.flw); hs=' + '.join(h) if h else 'no hisaab row'; s=norm(r.sheet); p=norm(r.pg)
    if p=='':
        if r.pg_location=='':
            return ('PG mapping gap', f"PG revenue_type blank because PG could not resolve the partner's hub (PG location also blank; Sheet hub = {r.sh_allocation_location or 'blank'}). At hisaab the partner was {hs}.")
        return ('PG mapping gap', f"PG revenue_type blank for {r.pg_location} hub partner although at hisaab the partner was {hs}.")
    if s=='': return ('Sheet blank', f'Sheet revenue_type blank; at hisaab the partner was {hs}, PG shows {p}.')
    if h==['EV on D2O plan'] and p=='D2O':
        return ('Labelling rule (EV on D2O plan)', f'EV car (business vertical 2) on a D2O plan: Sheet labels it {s} (by vertical), PG labels it D2O (by plan). Both describe the same hisaab record.')
    if len(h)>1:
        return ('Product changed during week', f'Partner changed product during the driven week {dw(r.week)} (hisaab rows: {hs}); Sheet took {s}, PG took {p}.')
    hh=h[0] if h else ''
    if s==hh or (hh=='EV on D2O plan' and s.startswith('EV')):
        return ('PG wrong', f'At hisaab (driven week {dw(r.week)}) the partner was {hh}; Sheet = {s} (correct), PG = {p} (PG picks a product from outside the hisaab week).')
    if p==hh: return ('Sheet wrong', f'At hisaab the partner was {hh}; PG = {p} (correct), Sheet = {s}.')
    return ('Need to Deep Dive', f'Hisaab shows {hs}; Sheet = {s}; PG = {p}.')
rr=x.apply(reason,axis=1,result_type='expand'); x['category']=rr[0]; x['reason']=rr[1]
x['hisaab']=x.flw.map(lambda f:' + '.join(htypes(f)) or 'no hisaab row')
x['sheet_ok']=[('Yes' if norm(s) in h.split(' + ') or (s.startswith('EV') and 'EV' in h) else 'No') for s,h in zip(x.sheet,x.hisaab)]
x['pg_ok']=[('Yes' if norm(p) in h.split(' + ') or (p=='D2O' and h=='EV on D2O plan') else 'No') for p,h in zip(x.pg,x.hisaab)]
x=x.sort_values(['week','city','employee'])
x.to_pickle('out/rev_rca.pkl')
print(len(x)); print(pd.crosstab(x.category,x.week,margins=True))
print(x[['sheet_ok','pg_ok']].value_counts())
