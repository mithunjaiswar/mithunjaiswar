import json, collections
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
from load import rows
def TS(s):
    t=pd.Timestamp(s)
    return t.tz_convert("Asia/Kolkata").tz_localize(None) if t.tzinfo else t
def R(i,n): return [[c.strip() for c in x] for x in rows([i]) if len(x)>=n and x[0].strip() not in ('r','')]
hab={x[0]:x for x in R(1791614402180,3)}
ten={x[0]:float(x[1]) for x in R(1791614418349,2)}
dmap={x[0]:x[1] for x in R(1791614432004,2)}
trip={dmap[x[0]]:(int(x[1]),int(x[2])) for x in R(1791614423594,3) if x[0] in dmap}
AL=collections.defaultdict(list)
for x in R(1791614437594,5):
    try: AL[x[0]].append((TS(x[1]), TS(x[2]) if x[2] else None, x[3], x[4]))
    except Exception: pass
D2O=collections.defaultdict(list)
for x in R(1791614450021,3):
    try: D2O[x[0]].append((TS(x[1]),TS(x[2])))
    except Exception: pass
CB={x[0]:int(x[2]) for x in R(1791614489068,3)}
RC=collections.defaultdict(list)
for x in R(1791614499221,6):
    try: RC[x[0]].append((x[2],x[3],TS(x[4]),TS(x[5]) if x[5] else None))
    except Exception: pass
print(len(hab),len(ten),len(trip),len(AL),len(D2O),len(CB),len(RC))
NS=open('../w14/new_sid.txt').read().strip(); TN='MV_Raw_Data_Manual_Check'
hdr=call('GET',f"{API}/{NS}/values/'{TN}'!A5:ZZ5")['values'][0]; HX={h:j for j,h in enumerate(hdr)}
E=[r[0] if r else '' for r in call('GET',f"{API}/{NS}/values/'{TN}'!C6:C12000")['values']]; n=len(E)
FL=['last_week_payment_habit','tenure_days','uber_active_days','hissab_week_active_days','total_allocated_days','last_week_nd_count','current_week_nd_count','active_inactive_flag','last_jama_date','next_join_date','location','d2o_leave_days','in_car_recovery_driven_week','in_car_recovery_hissab_week','cars_under_recovery_driven_week','cars_under_recovery_hissab_week','recovery_tat','active_fleet_cash_blocked']
MV={}
for f in FL:
    j=HX[f+' (MV)']; v=call('GET',f"{API}/{NS}/values/'{TN}'!{col(j)}6:{col(j)}{5+n}").get('values',[])
    MV[f]=[(r[0] if r else '') for r in v]+['']*n
DW0,DW1,HW0,HW1=TS('2026-09-07'),TS('2026-09-13'),TS('2026-09-14'),TS('2026-09-20')
NOW=TS('2026-10-10')
def days(e,a,b):
    S=set()
    for al,ja,_,_ in AL.get(e,[]):
        st=al.normalize(); en=(ja if ja is not None else NOW).normalize()
        for d in pd.date_range(max(st,a),min(en,b)): S.add(d)
    return S
def num(s):
    try: return float(str(s).replace(',',''))
    except: return None
out={f:([],[]) for f in FL}
def put(f,i,man,ok,why):
    out[f][0].append(man); out[f][1].append('Matched' if ok else why)
def eqn(mv,man,tol=0): x=num(mv); return (x if x is not None else 0)==man if tol==0 else abs((x or 0)-man)<=tol
for i,e in enumerate(E):
    g=lambda f: MV[f][i]
    h=hab.get(e); hv=h[1] if h else '(blank)'
    put('last_week_payment_habit',i,hv,(g('last_week_payment_habit') or '(blank)').lower()==hv.lower(),
        f'Last driver_repayment_habit entry before 14-Sep = {h[1]} (week {h[2]}); MV {g("last_week_payment_habit") or "blank"}' if h else f'No habit entry before 14-Sep (new partner); MV puts "{g("last_week_payment_habit")}"')
    t=ten.get(e)
    if t is None: put('tenure_days',i,'',True,'')
    else:
        d=(num(g('tenure_days')) or 0)-t
        put('tenure_days',i,t,-1<=d<=7, (f'MV {g("tenure_days")} is {-d:.0f} days LOWER than driver_profile tenure till 13-Sep ({t:.0f}) – MV likely skips a profile stint / gap – Need to Deep Dive' if d<0 else f'MV {g("tenure_days")} is {d:.0f} days higher than driver_profile tenure till 13-Sep ({t:.0f}) – Need to Deep Dive'))
    dw,hw=trip.get(e,(0,0))
    put('uber_active_days',i,dw,eqn(g('uber_active_days'),dw),f'fleet_dailytrip days with trips 07-13 Sep = {dw}; MV {g("uber_active_days")}')
    put('hissab_week_active_days',i,hw,eqn(g('hissab_week_active_days'),hw),f'fleet_dailytrip days with trips 14-20 Sep = {hw}; MV {g("hissab_week_active_days")} (MV counts allocated days, not trip days)')
    ad=days(e,DW0,DW1); ah=days(e,HW0,HW1)
    raw=sum(max((min((ja if ja is not None else NOW).normalize(),HW1)-max(al.normalize(),HW0)).days+1,0) for al,ja,_,_ in AL.get(e,[]))
    mva=num(g('total_allocated_days')) or 0
    why=(f'MV {mva:.0f} = allocated days of driven + hisaab week together ({len(ad)}+{len(ah)}); hisaab week only = {len(ah)}' if mva==len(ad)+len(ah) else (f'MV {mva:.0f} counts each car allocation separately (car swap day counted twice = {raw}); unique days in 14-20 Sep = {len(ah)}' if mva==raw else f'SSOT unique allocation days 14-20 Sep = {len(ah)} (driven week {len(ad)}); MV {g("total_allocated_days")} – Need to Deep Dive'))
    put('total_allocated_days',i,len(ah),eqn(g('total_allocated_days'),len(ah)),why)
    lnd=max(len(ad)-dw,0); cnd=max(len(ah)-hw,0)
    put('last_week_nd_count',i,lnd,eqn(g('last_week_nd_count'),lnd),f'Allocated {len(ad)} - drove {dw} = {lnd} (07-13 Sep); MV {g("last_week_nd_count")}')
    put('current_week_nd_count',i,cnd,eqn(g('current_week_nd_count'),cnd),f'Allocated {len(ah)} - drove {hw} = {cnd} (14-20 Sep); MV {g("current_week_nd_count")}')
    act='Active' if HW1 in ah else 'Inactive'
    AE=AL.get(e,[])
    def isleft(ja): return not any(al2<=ja+pd.Timedelta(days=1) and (ja2 is None or ja2>ja) for al2,ja2,_,_ in AE if al2>=ja-pd.Timedelta(days=1) or (al2<ja and (ja2 is None or ja2>ja)))
    js=[ja for al,ja,_,_ in AE if ja is not None and ja<=TS('2026-09-20 23:59:59') and isleft(ja)]
    swaps=[ja for al,ja,_,_ in AE if ja is not None and DW0<=ja<=TS('2026-09-20 23:59:59') and not isleft(ja)]
    lj=max(js).strftime('%Y-%m-%d') if js else None
    put('active_inactive_flag',i,act,g('active_inactive_flag').lower()==act.lower(),f'Car {"allocated" if act=="Active" else "not allocated"} on 20-Sep (last jama {lj or "none"}); MV {g("active_inactive_flag")}')
    ljm=lj or '(blank)'
    mvj=g('last_jama_date')
    put('last_jama_date',i,ljm,(mvj=='' if lj is None else mvj==lj),(f'MV placeholder future date {mvj} – car still allocated, no jama till 20-Sep' if (mvj>'2026-10-10') else f'SSOT last real jama (car returned, no new car within 1 day) till 20-Sep = {lj or "none"}; MV {mvj or "blank"}'))
    if lj:
        nxt=[al for al,ja,_,_ in AL.get(e,[]) if al>max(js)]
        nj=min(nxt).strftime('%Y-%m-%d') if nxt else '(blank)'
    else: nj='(blank)'
    mvn=g('next_join_date')
    rej=(nj!='(blank)' and nj<='2026-09-20')
    if rej and not mvj:
        out['last_jama_date'][1][-1]=f'Left on {lj}, rejoined on {nj} (before 20-Sep). MV blank – MV ignores a jama if partner is back by hisaab week end' if out['last_jama_date'][1][-1]!='Matched' else 'Matched'
    put('next_join_date',i,nj,(mvn=='' if nj=='(blank)' else mvn==nj),(f'Never left till 20-Sep – should be blank; MV placeholder {mvn}' if not lj and mvn else (f'Left on {lj}, rejoined on {nj} (before 20-Sep). MV blank – MV ignores rejoin inside the same weeks' if rej and not mvn else f'Last real jama {lj or "none"}, next allocation {nj}; MV {mvn or "blank"}')))
    rows_=sorted(AL.get(e,[]),key=lambda x:x[0])
    pk=[x for x in rows_ if x[0]<=TS('2026-09-13 23:59') and (x[1] is None or x[1]>=DW0)] or [x for x in rows_ if x[0]<=TS('2026-09-20 23:59')]
    loc=pk[0][3] if pk else ''
    put('location',i,loc,g('location').strip().lower()==loc.strip().lower(),f'MV "{g("location")}" vs SSOT allocation location (driven week) "{loc}" – different location master')
    dl=sum(max((min(b,DW1)-max(a,DW0)).days+1,0) for a,b in D2O.get(e,[]))
    put('d2o_leave_days',i,dl,eqn(g('d2o_leave_days'),dl),f'D2O leave days in driven week 07-13 Sep = {dl}; MV {g("d2o_leave_days")}')
    def rc(s,t):
        c=set()
        for car,st,cr,up in RC.get(e,[]):
            closed=st in ('complete','cancelled')
            if cr<=t and (not closed or (up is not None and up>=s)): c.add(car)
        return len(c)
    cdw=rc(DW0,TS('2026-09-13 23:59:59')); chw=rc(HW0,TS('2026-09-20 23:59:59'))
    tf=lambda x:'TRUE' if x>0 else 'FALSE'
    put('in_car_recovery_driven_week',i,tf(cdw),str(g('in_car_recovery_driven_week')).upper()==tf(cdw),f'recovery_cars open in 07-13 Sep: {cdw} car(s); MV {g("in_car_recovery_driven_week")}')
    put('in_car_recovery_hissab_week',i,tf(chw),str(g('in_car_recovery_hissab_week')).upper()==tf(chw),f'recovery_cars open in 14-20 Sep: {chw} car(s); MV {g("in_car_recovery_hissab_week")}')
    put('cars_under_recovery_driven_week',i,cdw,eqn(g('cars_under_recovery_driven_week'),cdw),f'recovery_cars open in 07-13 Sep = {cdw}; MV {g("cars_under_recovery_driven_week")}')
    put('cars_under_recovery_hissab_week',i,chw,eqn(g('cars_under_recovery_hissab_week'),chw),f'recovery_cars open in 14-20 Sep = {chw}; MV {g("cars_under_recovery_hissab_week")}')
    tat=num(g('recovery_tat'))
    if chw>0: put('recovery_tat',i,tat if tat is not None else '(blank)',tat is not None,'Car under recovery in hisaab week but MV TAT blank')
    else: put('recovery_tat',i,0 if tat is None else 0,tat in (None,0.0),f'No car under recovery in 14-20 Sep but MV TAT = {g("recovery_tat")}')
    cb=1 if CB.get(e,0)>0 else 0
    put('active_fleet_cash_blocked',i,cb,eqn(g('active_fleet_cash_blocked'),cb),(f'BLOCK entry in driver_cashblock_details_logs on 20-Sep → 1; MV {g("active_fleet_cash_blocked")}' if cb else f'No BLOCK entry on 20-Sep ({"some log entries" if e in CB else "no log entry"}) → 0; MV {g("active_fleet_cash_blocked")}'))
data=[]
for f,(vals,rems) in out.items():
    jm=HX[f+' (Manual)']; jr=HX[f+' Remark']
    data.append({'range':f"'{TN}'!{col(jm)}6:{col(jm)}{5+n}",'values':[[v] for v in vals]})
    data.append({'range':f"'{TN}'!{col(jr)}6:{col(jr)}{5+n}",'values':[[v] for v in rems]})
    ok=sum(1 for x in rems if x=='Matched'); print(f'{f:34s} {ok/n*100:6.2f}%  not matched {n-ok}')
for i in range(0,len(data),4):
    call('POST',f'{API}/{NS}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data[i:i+4]})
