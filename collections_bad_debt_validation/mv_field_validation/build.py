from alloc import *   # a, grp, dayset, mv, num, pd, pickle
import numpy as np
m=mv(); E=m.index
z=lambda s: num(pd.Series(s)).reindex(E).fillna(0) if not isinstance(s,(int,float)) else pd.Series(s,index=E)
f=pickle.load(open('flw_dw.pkl','rb')); f['adj']=(f.rent==0)&(f.ad==0)
rec=pickle.load(open('rec_agg.pkl','rb')).reindex(E); dep=pickle.load(open('dep_agg.pkl','rb')).reindex(E)
hab=pickle.load(open('habit_agg.pkl','rb')).reindex(E); trip=pickle.load(open('trip_agg.pkl','rb')).reindex(E).fillna(0)
adjw=pickle.load(open('adjweeks.pkl','rb')).reindex(E); aw=pickle.load(open('alloc_wk.pkl','rb')).reindex(E)
recov=pickle.load(open('recov.pkl','rb')); cash=pickle.load(open('cash.pkl','rb')); d2o=pickle.load(open('d2olog.pkl','rb'))
rev=pickle.load(open('rev_rule.pkl','rb')).reindex(E)
ten=pd.read_pickle('../run2/ten_logic.pkl'); ten=ten[ten.week=='2026-09-28'].set_index('emp').logic.reindex(E)
R=lambda c: rec[c].fillna(0)
MAN={}; REM={}
def numrem(field, man, reason_fn, tol=1):
    mvv=num(m[field]).fillna(0); man=pd.Series(man,index=E)
    ok=(mvv-num(man).fillna(0)).abs()<=tol
    MAN[field]=man; REM[field]=pd.Series(np.where(ok,'Matched',[reason_fn(e) for e in E]),index=E)
def txtrem(field, man, reason_fn, norm=lambda s: s.fillna('').astype(str).str.strip().str.lower()):
    man=pd.Series(man,index=E); ok=norm(m[field])==norm(man)
    MAN[field]=man; REM[field]=pd.Series(np.where(ok,'Matched',[reason_fn(e) for e in E]),index=E)
DD='Need to Deep Dive – Manual Validation Required'
# 1 revshare
fw={'ETN23357':3,'ETK17093':3}
numrem('revshare_days_working', pd.Series(fw).reindex(E).fillna(0), lambda e: DD, tol=0)
# 2 weekly_os (all FLW rows of driven week, incl. adjustment-only rows)
g_all=f.groupby('emp').wos.sum().reindex(E); g_adj=f[f.adj].groupby('emp').wos.sum().reindex(E)
adj_cars=f[f.adj].groupby('emp').car.agg(lambda x:', '.join(dict.fromkeys(x)))
man=g_all.copy(); man[g_all.isna()]=np.nan
def r_wos(e):
    if pd.isna(g_all.get(e)): return 'No fleet_leasing_weeklydata row in driven week (Rev share / Fixed Pay partner – OS comes from fleet_weeklydata). '+DD
    if pd.notna(g_adj.get(e)): return f'MV skips adjustment-only hisaab row(s) (0 rent, 0 active days) of {g_adj[e]:.0f} on car {adj_cars.get(e,"")}; source total incl. that row = {g_all[e]:.0f}'
    return DD
numrem('weekly_os', man.round(2), r_wos)
# 3 prev_carryforward_os
coll_dw=R('dw_rzp')+R('dw_oth')+R('dw_dto')+R('pa_0921')
man=(adjw.p_tos+coll_dw); 
numrem('prev_carryforward_os', man.round(0), lambda e: ('Partner not in previous hisaab week (2026-09-21) MV – no previous total_os. '+DD) if pd.isna(adjw.p_tos.get(e)) else f'Prev week total_os {adjw.p_tos[e]:.0f} + driven-week collections {coll_dw[e]:.0f} = {man[e]:.0f}; MV {m.prev_carryforward_os[e]} (diff {num(pd.Series([m.prev_carryforward_os[e]]))[0]-man[e]:.0f}). '+DD)
# 4 os_to_deposit
numrem('os_to_deposit', -dep.o2d_dw.fillna(0), lambda e: f'OS_TO_DEPOSIT in driven week (mv_deposits_raw) = {dep.o2d_dw.fillna(0)[e]:.0f}; MV {m.os_to_deposit[e]}. '+DD)
# 5 total_allocated_days (allocation-days in hisaab week)
def asum(e,s0,e0):
    t=0; s0=pd.Timestamp(s0); e0=pd.Timestamp(e0)
    for al,ja in grp.get(e,[]):
        st=al.normalize(); en=(ja if pd.notna(ja) else pd.Timestamp('2026-10-08')).normalize()
        a_=max(st,s0); b_=min(en,e0)
        if b_>=a_: t+=(b_-a_).days+1
    return t
tad=pd.Series({e:asum(e,'2026-09-28','2026-10-04') for e in E})
numrem('total_allocated_days', tad, lambda e: f'SSOT shows {tad[e]} allocation days in hisaab week, MV {m.total_allocated_days[e]}. '+DD, tol=0)
# 6 uber_active_days
numrem('uber_active_days', trip.dw_trip, lambda e: DD, tol=0)
# 7 rental_days, 8 total_rent
g=f.groupby('emp').agg(ad=('ad','sum'),rent=('rent','sum')).reindex(E)
numrem('rental_days', g.ad, lambda e: f'Source active_days = {g.ad[e]} (half-day); MV rounds to {m.rental_days[e]}' if pd.notna(g.ad[e]) and g.ad[e]%1 else DD, tol=0.01)
numrem('total_rent_amount', g.rent, lambda e: DD)
# 9 last payment date
txtrem('last_payment_date_till_hissab_week', rec.last_pos.fillna(''), lambda e: f'Last positive payment in mv_daily_recovery till 04-Oct = {rec.last_pos.get(e) or "none"}. '+DD)
# 10 last_jama_date
lj={}
for e in E:
    js=[ja for al,ja in grp.get(e,[]) if pd.notna(ja) and ja<=pd.Timestamp('2026-10-04 23:59:59')]
    lj[e]=max(js).strftime('%Y-%m-%d') if js else 'No jama till hisaab week end (car still allocated)'
lj=pd.Series(lj)
txtrem('last_jama_date', lj, lambda e: 'MV puts placeholder future date '+str(m.last_jama_date[e])+' for partner whose car is still allocated (no real jama)' if str(m.last_jama_date[e])>'2026-10-08' else f'SSOT last jama till 04-Oct = {lj[e]}; MV {m.last_jama_date[e]}. '+DD)
# 11 last_car_number: all cars used in driven week (rows with active days)
cars=f[~f.adj].sort_values(['sd','id']).groupby('emp').car.agg(lambda x:', '.join(dict.fromkeys(c for c in x if c))).reindex(E).fillna('')
ncar=cars.str.count(',')+1
txtrem('last_car_number', cars, lambda e: f'Partner used {ncar[e]} cars in driven week; MV keeps only one car' if ncar[e]>1 else DD, norm=lambda s: s.fillna('').astype(str).str.replace(' ','').str.upper())
# 12/13 deposits
def r_dep(col,src):
    return lambda e: (f'MV {m[col][e]} vs mv_deposits_raw {dep[src].fillna(0)[e]:.0f}: MV higher by {num(pd.Series([m[col][e]]))[0]-dep[src].fillna(0)[e]:.0f} – opening/legacy deposit not in mv_deposits_raw (MV takes it from another deposit table)') if num(pd.Series([m[col][e]]))[0]>dep[src].fillna(0)[e] else DD
numrem('week_start_deposit', dep.d_lt0928.fillna(0), r_dep('week_start_deposit','d_lt0928'))
numrem('week_end_deposit', dep.d_le1004.fillna(0), r_dep('week_end_deposit','d_le1004'))
# 14 habit
txtrem('last_week_payment_habit', hab.h_before_hw.fillna(''), lambda e: 'No driver_repayment_habit entry before hisaab week but MV has a value. '+DD)
# 15/16 ND counts
lnd=(aw.al_dw_u-trip.dw_trip).clip(lower=0); cnd=(aw.al_hw_u-trip.hw_trip).clip(lower=0)
numrem('last_week_nd_count', lnd, lambda e: f'Allocation days {aw.al_dw_u[e]} - Uber active days {trip.dw_trip[e]:.0f} = {lnd[e]:.0f} (driven week); MV {m.last_week_nd_count[e]}. '+DD, tol=0)
numrem('current_week_nd_count', cnd, lambda e: f'Allocation days {aw.al_hw_u[e]} - Uber active days {trip.hw_trip[e]:.0f} = {cnd[e]:.0f} (hisaab week); MV {m.current_week_nd_count[e]}. '+DD, tol=0)
# 17 hissab_week_active_days
numrem('hissab_week_active_days', trip.hw_trip, lambda e: f'MV holds allocated days across driven+hisaab week ({m.hissab_week_active_days[e]}), not trip-active days; fleet_dailytrip active days in hisaab week = {trip.hw_trip[e]:.0f}', tol=0)
# 18 tenure
numrem('tenure_days', ten, lambda e: f'MV counts tenure till hisaab week Sunday (04-Oct); till driven week end (27-Sep) = {ten[e]:.0f} (diff {num(pd.Series([m.tenure_days[e]]))[0]-ten[e]:.0f})', tol=0)
# 19 d2o
def ov(s,e_):
    s=pd.Timestamp(s); e_=pd.Timestamp(e_)
    o=((d2o.ed.clip(upper=e_)-d2o.sd.clip(lower=s)).dt.days+1).clip(lower=0)
    return o.groupby(d2o.emp).sum().reindex(E).fillna(0)
dl=ov('2026-09-21','2026-09-27'); d28=ov('2026-09-28','2026-09-28')
numrem('d2o_leave_days', dl, lambda e: f'Leave days in driven week = {dl[e]:.0f}; MV {m.d2o_leave_days[e]} also counts leave dated 28-Sep (hisaab Monday)' if d28[e]>0 else DD, tol=0)
# 20 active flag (allocated on last day of hisaab week)
ds={e:dayset(e) for e in E}
act=pd.Series({e:('Active' if pd.Timestamp('2026-10-04') in ds[e] else 'Inactive') for e in E})
txtrem('active_inactive_flag', act, lambda e: f'Car returned (jama) on {lj[e]} before hisaab week last day; MV marks Active if allocated on any day of hisaab week' if act[e]=='Inactive' else DD)
# 21-24 next_*
P='Lookahead field (next hisaab week 2026-10-05 row of the same partner)'
numrem('next_weekly_os', adjw.n_wos, lambda e: ('Partner has no 2026-10-05 row (left / not for collections next week)' if pd.isna(adjw.n_wos[e]) else 'Next-week MV row changed after this snapshot. '+DD))
numrem('next_total_os', adjw.n_tos, lambda e: ('Partner has no 2026-10-05 row' if pd.isna(adjw.n_tos[e]) else 'Next week (in-progress) total_os changed after this row was built – snapshot timing'))
numrem('next_week_end_deposit', adjw.n_wed, lambda e: ('Partner has no 2026-10-05 row' if pd.isna(adjw.n_wed[e]) else 'Next week (in-progress) deposit changed after this row was built – snapshot timing'))
nj={}
for e in E:
    real=[ja for al,ja in grp.get(e,[]) if pd.notna(ja) and ja<=pd.Timestamp('2026-10-04 23:59:59')]
    if not real: nj[e]='Not left (car still allocated)'; continue
    lastj=max(real); nxt=[al for al,ja in grp.get(e,[]) if al>lastj]
    nj[e]=min(nxt).strftime('%Y-%m-%d') if nxt else ''
nj=pd.Series(nj)
txtrem('next_join_date', nj, lambda e: 'MV puts placeholder future date '+str(m.next_join_date[e])+' for partner who never left' if str(m.next_join_date[e])>'2026-10-08' else (f'Rejoined on {nj[e]} after MV refresh (06/07-Oct) – MV not updated' if nj[e]>'2026-10-06' else DD))
# 25/26/32/33 recovery (record open during the week)
def rc(s,e_):
    s=pd.Timestamp(s); e_=pd.Timestamp(e_)
    closed=recov.st.isin(['complete','cancelled'])
    x=recov[(recov.cr<=e_)&(~closed|(recov.upd>=s))]
    return x.groupby('emp').car.nunique().reindex(E).fillna(0)
cdw=rc('2026-09-21','2026-09-27 23:59:59'); chw=rc('2026-09-28','2026-10-04 23:59:59')
tf=lambda s:(s>0).map({True:'TRUE',False:'FALSE'})
txtrem('in_car_recovery_driven_week', tf(cdw), lambda e: DD)
txtrem('in_car_recovery_hissab_week', tf(chw), lambda e: DD)
numrem('cars_under_recovery_driven_week', cdw, lambda e: DD, tol=0)
numrem('cars_under_recovery_hissab_week', chw, lambda e: DD, tol=0)
# 34 recovery_tat: must be present only when car under recovery in hisaab week
tat=num(m.recovery_tat)
man=pd.Series(np.where(chw>0, tat.fillna(-1), 0),index=E)
numrem('recovery_tat', man, lambda e: ('TAT blank although car under recovery in hisaab week' if chw[e]>0 else 'TAT filled although no car under recovery in hisaab week'), tol=0)
# 27 collection_till_wed
numrem('collection_till_wed', R('hw_wed_net'), lambda e: f'Net mv_daily_recovery Mon–Wed of hisaab week = {R("hw_wed_net")[e]:.0f}. '+DD)
# 28 bad_debt_collected: should be >0 only for partners who left and rejoined
left=lj.str.match(r'^\d')
man=pd.Series(np.where(~left,0,np.nan),index=E)
numrem('bad_debt_collected', man, lambda e: ('Partner never left (car allocated through hisaab week) – MV still fills bad_debt_collected = week collection '+str(m.bad_debt_collected[e])) if not left[e] else 'Partner left on '+lj[e]+' – collections between jama and next join need manual check. '+DD)
# 29/30/31
lw=R('pw_pos')+R('pa_0914')+R('pw_dto'); pw=R('ppw_pos')+R('ppw_dto')+R('pa_0907')
numrem('last_week_collection', lw, lambda e: DD)
numrem('previous_week_collection', pw, lambda e: 'No payment rows in mv_daily_recovery for 07–13 Sep but MV has value. '+DD)
npd=((lw<=0)&(pw<=0)).astype(int)
numrem('partners_not_paid_2_weeks', npd, lambda e: 'Follows last_week_collection / previous_week_collection difference', tol=0)
# 35 cash block
cb=cash.sort_values('upd').groupby('emp').st.last().reindex(E)
numrem('active_fleet_cash_blocked', (cb=='Cash Blocked').astype(int), lambda e: 'driver_cashblock holds only current status (84 blocked); hisaab-week-end block status comes from Cash Block API (Airflow) – not in reporting DB. '+DD, tol=0)
# 36 location
g2={k:v.sort_values('al') for k,v in a.groupby('emp')}
def pick(e):
    v=g2.get(e)
    if v is None: return ''
    ja=v.ja.fillna(pd.Timestamp('2030-01-01'))
    x=v[(v.al<=pd.Timestamp('2026-09-27 23:59'))&(ja>=pd.Timestamp('2026-09-21'))]
    if len(x)==0: x=v[v.al<=pd.Timestamp('2026-10-04 23:59')]
    return x.iloc[0]['loc'] if len(x) else ''
loc=pd.Series({e:pick(e) for e in E})
txtrem('location', loc, lambda e: f'MV uses parent/hisaab hub "{m.location[e]}"; SSOT allocation location is "{loc[e]}" (different location master)')
# 37 revenue_type
txtrem('revenue_type', rev.fillna(''), lambda e: f'Driven-week hisaab row with most active days says "{rev[e]}"; MV "{m.revenue_type[e]}" (2 products in week / EV on D2O plan label)')
pickle.dump((MAN,REM),open('manual_out.pkl','wb'))
for k in MAN: print(f'{k:40s} {(REM[k]=="Matched").mean()*100:6.2f}%  mism {(REM[k]!="Matched").sum()}')
print(len(MAN))
