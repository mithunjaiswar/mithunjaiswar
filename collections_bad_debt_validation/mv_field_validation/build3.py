from alloc import *
import numpy as np
MAN,REM=pickle.load(open('manual_out_v2.pkl','rb')); MAN=dict(MAN); REM=dict(REM)
m=mv(); E=m.index; z=lambda s: num(s).reindex(E).fillna(0)
def setf(f, man, reason_fn, tol=1, text=False):
    man=pd.Series(man,index=E)
    if text: ok=m[f].fillna('').astype(str).str.strip().str.lower()==man.fillna('').astype(str).str.strip().str.lower()
    else: ok=(z(m[f])-num(man).fillna(0)).abs()<=tol
    MAN[f]=man; REM[f]=pd.Series(np.where(ok,'Matched',[reason_fn(e) for e in E]),index=E)
# 1 weekly_os: ALL rows of the driven week
f=pickle.load(open('flw_dw.pkl','rb')); f['adj']=(f.rent==0)&(f.ad==0)
allw=f.groupby('emp').wos.sum().reindex(E); adjw=f[f.adj].groupby('emp').wos.sum().reindex(E)
setf('weekly_os', allw.round(2), lambda e: (f'MV leaves out adjustment-only row(s) {adjw[e]:,.0f} (0 rent, 0 days); sum of ALL rows = {allw[e]:,.0f}' if pd.notna(adjw[e]) else ('No leasing row – Rev share/Fixed Pay partner (fleet_weeklydata). Need to Deep Dive' if pd.isna(allw[e]) else 'Need to Deep Dive')))
# 2 prev_cf: partner's LAST hisaab week net OS (credit allowed)
pc,cat=pickle.load(open('prevcf2.pkl','rb')); pc=pc.reindex(E); cat=cat.reindex(E)
setf('prev_carryforward_os', pc.net.round(2), lambda e: f'{cat[e]}. Last hisaab week {pc.pw[e]}: total_os {pc.ptos[e]:,.0f} + collected {pc.pcol[e]:,.0f} = {pc.net[e]:,.0f}; MV {m.prev_carryforward_os[e]}' if pd.notna(pc.pw[e]) else f'{cat[e]}; MV {m.prev_carryforward_os[e]}')
# 3 last_jama_date
exp,jc=pickle.load(open('jama2.pkl','rb'))
setf('last_jama_date', exp.reindex(E).replace('','(blank)'), lambda e: jc[e], text=True)
# 4/5 deposits – MV logic (exclude Own Now transfer types) – 100%
dep=pickle.load(open('dep_agg.pkl','rb')).reindex(E).fillna(0); dx=pd.read_pickle('depx.pkl').reindex(E).fillna(0); own=dx.sd2own+dx.own2own
setf('week_start_deposit', dep.d_lt0928-own, lambda e:'Need to Deep Dive')
setf('week_end_deposit', dep.d_le1004-own, lambda e:'Need to Deep Dive')
# 12 previous_week_collection – not required
REM['previous_week_collection']=pd.Series('NOT REQUIRED – calculate last/previous week collection with lag in Python; use collection_pct column instead',index=E)
# 13 cash block: any BLOCK entry in driver_cashblock_details_logs on 04-Oct
c=pickle.load(open('cb1004only.pkl','rb')).reindex(E)
blk=(c.nblock.fillna(0)>0).astype(int)
setf('active_fleet_cash_blocked', blk, lambda e: (f'{int(c.n[e])} log entries on 04-Oct, none BLOCK (last = {c["last"][e]}) → should be 0; MV 1 (MV flags "has a log entry", not BLOCK)' if pd.notna(c.n[e]) and blk[e]==0 else (f'{int(c.nblock[e])} BLOCK entries on 04-Oct → should be 1; MV 0' if blk[e]==1 else 'No log entry on 04-Oct → 0; MV 1')), tol=0)
pickle.dump((MAN,REM),open('manual_out_v3.pkl','wb'))
for k in ['weekly_os','prev_carryforward_os','last_jama_date','week_start_deposit','week_end_deposit','active_fleet_cash_blocked']:
    ok=REM[k].str.startswith('Matched'); print(f'{k:28s} {ok.mean()*100:6.2f}%  {(~ok).sum()}')
