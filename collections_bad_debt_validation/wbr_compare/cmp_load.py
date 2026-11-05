import json,collections
def load(sh):
    d=json.load(open(f'{sh}_raw.json')); C=d['cols']; R={}
    for r in d['rows']:
        x=dict(zip(C,r))
        if x['A'] in ('hisaab_week',''): continue
        R[(x['A'],x['D'])]=x
    return R
V=load('ver'); O=load('orig')
def f(s):
    s=str(s).replace(',','').replace('%','').strip()
    try: return float(s)
    except: return 0.0
W=['2026-10-12','2026-10-19','2026-10-26','2026-11-02']
