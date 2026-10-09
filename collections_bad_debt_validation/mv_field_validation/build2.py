from alloc import *
import numpy as np
MAN,REM=pickle.load(open('manual_out.pkl','rb')); MAN=dict(MAN); REM=dict(REM)
m=mv(); E=m.index; z=lambda s: num(s).reindex(E).fillna(0)
def setf(f, man, reason_fn, tol=1, text=False):
    man=pd.Series(man,index=E)
    if text: ok=m[f].fillna('').astype(str).str.strip().str.lower()==man.fillna('').astype(str).str.strip().str.lower()
    else: ok=(z(m[f])-num(man).fillna(0)).abs()<=tol
    MAN[f]=man; REM[f]=pd.Series(np.where(ok,'Matched',[reason_fn(e) for e in E]),index=E)
# 2) prev_carryforward_os = last week net OS (MV total_os + total_collected of 21-Sep week)
pn=pickle.load(open('prevnet.pkl','rb')).reindex(E); cat=pickle.load(open('prevcf_cat.pkl','rb')).reindex(E)
setf('prev_carryforward_os', pn.net.round(2), lambda e: {'A':'No MV row last week (21-Sep) – cannot take last week net OS','B':f'Last week overpaid: net {pn.net[e]:,.0f} (credit) but MV carries 0','C':'Gap = negative adjustment of the week','D':f'Gap {z(m.prev_carryforward_os)[e]-pn.net[e]:,.0f} = fixed fine/charge added by MV','E':f'MV {m.prev_carryforward_os[e]} vs last week net {pn.net[e]:,.0f} – Need to Deep Dive'}.get(str(cat[e])[:1],'Need to Deep Dive'))
# 4/5) deposits per user rule (<= hisaab week start / <= hisaab week end) from mv_deposits_raw
dep=pickle.load(open('dep_agg.pkl','rb')).reindex(E).fillna(0); dx=pd.read_pickle('depx.pkl').reindex(E).fillna(0)
own=dx.sd2own+dx.own2own; ws=dep.d_lt0928+dx.d0928; we=dep.d_le1004
def r_dep(col,v):
    def f(e):
        if own[e]!=0 and abs(z(m[col])[e]-(v[e]-own[e]))<=1: return f'MV ignores Own Now transfer (SD_TO_OWNNOW / OWNNOW_TO_OWNNOW = {own[e]:,.0f}); raw total {v[e]:,.0f}, MV {m[col][e]}'
        if dx.d0928[e]!=0 and col=='week_start_deposit': return f'Deposit entry on 28-Sep itself ({dx.d0928[e]:,.0f}) – MV uses < hisaab week start, rule uses <='
        return 'Need to Deep Dive'
    return f
setf('week_start_deposit', ws, r_dep('week_start_deposit',ws)); setf('week_end_deposit', we, r_dep('week_end_deposit',we))
# 6) habit – new partners
txt=MAN['last_week_payment_habit']
setf('last_week_payment_habit', txt, lambda e: 'New partner – first habit entry is for 28-Sep week itself; MV puts default "Excellent"', text=True)
# 7) tenure – delta 7 accepted (handled by formula); remark
ten=MAN['tenure_days']; dlt=z(m.tenure_days)-num(ten).fillna(0)
REM['tenure_days']=pd.Series(np.where(dlt.abs()<=1,'Matched',np.where((dlt-7).abs()<=1,'Matched (7-day delta: MV counts till hisaab Sunday – accepted)',[f'Delta {d:,.0f} days (not 0/7) – Need to Deep Dive' for d in dlt])),index=E)
# 8) ND (allocated day without trip, day level) and hissab_week_active_days (trip days)
td,z0,res=pickle.load(open('nd_day.pkl','rb'))
for f in ['last_week_nd_count','current_week_nd_count']:
    a,t,nd,_=res[f]
    setf(f, nd, lambda e,a=a,t=t,nd=nd,f=f: f'Allocated {a[e]} days, drove {t[e]} days → ND {nd[e]}; MV {m[f][e]} (MV ND not from allocation/dailytrip – Need to Deep Dive)', tol=0)
setf('hissab_week_active_days', res['current_week_nd_count'][1], lambda e: f'MV {m.hissab_week_active_days[e]} = allocated days of driven+hisaab week; car ran {res["current_week_nd_count"][1][e]} days in hisaab week (fleet_dailytrip)', tol=0)
# 10) next_join_date
nj,why=pickle.load(open('nj.pkl','rb')); nj=nj.reindex(E); why=why.reindex(E)
setf('next_join_date', nj, lambda e: ('Not attrited in driven/hisaab week – should be blank; MV placeholder '+str(m.next_join_date[e])) if why[e]=='not attrited in DW/HW' else (f'Attrited and rejoined on {nj[e]} (after MV refresh) – MV blank' if why[e]=='attrited, rejoined later' else 'Need to Deep Dive'), text=True)
# 11) bad_debt_collected
x=pickle.load(open('bdc.pkl','rb'))
bd=pd.Series(0.0,index=E); bd[x.index]=x.expected
setf('bad_debt_collected', bd, lambda e: ('Never left – MV fills whole week collection '+str(m.bad_debt_collected[e])+' (should be 0)') if e in x.index and x.cat[e].startswith('Never') else (f'Left – collection between leave and rejoin = {bd[e]:,.0f}; MV took whole week collection {m.bad_debt_collected[e]}' if e in x.index and x.mv_eq_week[e] else 'Need to Deep Dive'))
# 13) cash block: last admin entry (driver_cashblock_details) on or before hisaab week end
cbd=pd.DataFrame([r[:5] for r in pickle.load(open('cbdet1004.pkl','rb'))],columns=['emp','st','cr','deact','exp']).set_index('emp').st.reindex(E)
cb=(cbd=='BLOCK').astype(int)
setf('active_fleet_cash_blocked', cb, lambda e: f'Cash-block entry on 04-Oct = {cbd[e] if isinstance(cbd[e],str) else "none"}; MV {m.active_fleet_cash_blocked[e]} (MV flag ≈ "partner has a cash-block record", not BLOCK status)', tol=0)
# 12) previous_week_collection – helper only
REM['previous_week_collection']=REM['previous_week_collection'].str.replace('Need to Deep Dive – Manual Validation Required','Helper for partners_not_paid_2_weeks only')
pickle.dump((MAN,REM),open('manual_out_v2.pkl','wb'))
for f in ['prev_carryforward_os','week_start_deposit','week_end_deposit','last_week_payment_habit','tenure_days','last_week_nd_count','current_week_nd_count','hissab_week_active_days','next_join_date','bad_debt_collected','active_fleet_cash_blocked','active_inactive_flag','last_jama_date','weekly_os']:
    ok=REM[f].str.startswith('Matched'); print(f'{f:30s} {ok.mean()*100:6.2f}%  mism {(~ok).sum()}')
