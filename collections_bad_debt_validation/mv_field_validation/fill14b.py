import json,sys
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
from load import rows
NS=open('../w14/new_sid.txt').read().strip(); TN='MV_Raw_Data_Manual_Check'
cl=lambda x:[c.strip() for c in x]
def P(ids,n): 
    out={}
    for x in rows(ids):
        p=cl(x) if len(x)==1 else None
        if p and len(p)>=n and p[0] not in ('r',''): out[p[0] if n<99 else p[1]]=p
    return out
def F(v):
    try: return float(v)
    except: return None
pw={};nw={}
for x in rows([1791613780738]):
    p=cl(x)
    if len(p)>5: pw[p[1]]=p
for x in rows([1791613786994]):
    p=cl(x)
    if len(p)>5: nw[p[1]]=p
dep={}
for x in rows([1791613822098,1791613847731]):
    p=cl(x)
    if len(p)==4 and p[0].startswith('ET'): dep[p[0]]=p
rec={}
for x in rows([1791613882897]):
    p=cl(x)
    if len(p)==6 and p[0].startswith('ET'): rec[p[0]]=p
LP={x[0].strip():[c.strip() for c in x] for x in rows([1791614198216]) if x[0].strip().startswith('ET')}
print(len(pw),len(nw),len(dep),len(rec))
hdr=call('GET',f"{API}/{NS}/values/'{TN}'!A5:ZZ5")['values'][0]
emp=[e[0] if e else '' for e in call('GET',f"{API}/{NS}/values/'{TN}'!C6:C20000")['values']]; n=len(emp)
HX={h:j for j,h in enumerate(hdr)}
mvv={}
for f in ['prev_carryforward_os','os_to_deposit','week_start_deposit','week_end_deposit','last_payment_date_till_hissab_week','collection_till_wed','last_week_collection','partners_not_paid_2_weeks','next_weekly_os','next_total_os','next_week_end_deposit']:
    j=HX[f+' (MV)']; v=call('GET',f"{API}/{NS}/values/'{TN}'!{col(j)}6:{col(j)}{5+n}",params={'valueRenderOption':'FORMATTED_VALUE'}).get('values',[])
    mvv[f]=[(r[0] if r else '') for r in v]+['']*(n-len(v))
def nm(s):
    try: return float(str(s).replace(',',''))
    except: return 0.0
MAN={};REM={}
def put(f,vals,rems): MAN[f]=vals; REM[f]=rems
# compute
res={k:([],[]) for k in mvv}
for i,e in enumerate(emp):
    p=pw.get(e); q=nw.get(e); d=dep.get(e); r=rec.get(e)
    def add(f,man,why):
        mv=mvv[f][i]
        if man is None: res[f][0].append(''); res[f][1].append(why); return
        ok = (str(mv)==str(man)) if isinstance(man,str) else abs(nm(mv)-man)<=1
        res[f][0].append(man); res[f][1].append('Matched' if ok else why)
    if p: man=F(p[2] or 0)+F(p[3] or 0)
    else: man=None
    add('prev_carryforward_os',man,(f'Prev hisaab week 07-Sep: total_os {p[2]} + collected {p[3]} = {man:,.0f}; MV {mvv["prev_carryforward_os"][i]}' if p else 'No MV row for previous hisaab week 07-Sep (new partner) – cannot compute'))
    o2d=-F(d[3]) if d else 0.0
    add('os_to_deposit',o2d,f'OS_TO_DEPOSIT in driven week 07-13 Sep (mv_deposits_raw) = {o2d:,.0f}; MV {mvv["os_to_deposit"][i] or "blank"}')
    ws=F(d[1]) if d else 0.0; we=F(d[2]) if d else 0.0
    add('week_start_deposit',ws,f'mv_deposits_raw before 14-Sep (excl. Own Now transfers) = {ws:,.0f}; MV {mvv["week_start_deposit"][i]} – Need to Deep Dive')
    add('week_end_deposit',we,f'mv_deposits_raw till 20-Sep (excl. Own Now transfers) = {we:,.0f}; MV {mvv["week_end_deposit"][i]} – Need to Deep Dive')
    lp=LP.get(e,['','',''])[2]; lpall=r[1] if r else ''
    mvd=mvv['last_payment_date_till_hissab_week'][i]
    res['last_payment_date_till_hissab_week'][0].append(lp)
    res['last_payment_date_till_hissab_week'][1].append('Matched' if mvd==lp else f'Last real payment (razorpay/phonepe/other) till 20-Sep = {lp or "none"}; MV {mvd or "blank"}' + (f' (incl. adjustment/deposit-to-OS: {lpall})' if lpall and lpall!=lp else '') + ' – Need to Deep Dive')
    tw=F(r[2]) if r else 0.0
    add('collection_till_wed',tw,f'Net mv_daily_recovery 14-16 Sep = {tw:,.0f}; MV {mvv["collection_till_wed"][i]} – MV uses a different payment set')
    lw=F(r[3]) if r else 0.0; pv=F(r[4]) if r else 0.0
    add('last_week_collection',pv,f'Positive payments 31 Aug-06 Sep (week before driven week) = {pv:,.0f}; driven week 07-13 Sep = {lw:,.0f}; MV {mvv["last_week_collection"][i]} – helper field')
    npd=1.0 if (lw<=0 and pv<=0) else 0.0
    add('partners_not_paid_2_weeks',npd,f'Paid 07-13 Sep {lw:,.0f}, 31 Aug-06 Sep {pv:,.0f} → {int(npd)}; MV {mvv["partners_not_paid_2_weeks"][i]}')
    for f,k in [('next_weekly_os',4),('next_total_os',2),('next_week_end_deposit',5)]:
        add(f, F(q[k] or 0) if q else None, (f'MV row 21-Sep has {q[k]}; MV {mvv[f][i]} – next week changed after this row was built (snapshot timing)' if q else 'Partner has no 21-Sep MV row (left / not for collections) – Lookahead field'))
data=[]
for f,(vals,rems) in res.items():
    jm=HX[f+' (Manual)']; jr=HX[f+' Remark']
    data.append({'range':f"'{TN}'!{col(jm)}6:{col(jm)}{5+n}",'values':[[v] for v in vals]})
    data.append({'range':f"'{TN}'!{col(jr)}6:{col(jr)}{5+n}",'values':[[v] for v in rems]})
    ok=sum(1 for x in rems if x=='Matched'); print(f'{f:36s} {ok/n*100:6.2f}%  not matched {n-ok}')
for i in range(0,len(data),4):
    call('POST',f'{API}/{NS}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data[i:i+4]})
json.dump({f:sum(1 for x in r if x=='Matched')/n for f,(v,r) in res.items()},open('../w14/fill14b_res.json','w'))
