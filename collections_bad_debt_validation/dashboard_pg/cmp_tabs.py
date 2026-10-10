import json,re
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS=open('../dash/dash_sid.txt').read().strip()
d=json.load(open('../dash/summary_cmp.json'))
O,N1,N2=d['old'],d['new'],d['new2']
WK=O[7][2:10]
def num(s):
    s=str(s).replace(',','').replace(' ','')
    m=re.fullmatch(r'(-?[\d.]+)(K|%)?',s)
    if not m: return None
    v=float(m.group(1)); return v*1000 if m.group(2)=='K' else v
def g(R,i,j):
    r=R[i] if i<len(R) else []
    return r[j] if j<len(r) else ''
def diff(i,R,cols):
    so=sn=0;same=True;cnt=0;okc=0
    for j in cols:
        a,b=g(O,i,j),g(R,i,j); x,y=num(a),num(b)
        if x is None or y is None:
            cnt+=1; okc+=(a.strip()==b.strip()); continue
        so+=abs(x); sn+=abs(y-x); cnt+=1
        pc='%' in a; tol=max(abs(x)*0.02,0.15 if pc else (1 if abs(x)>=20 else 0))
        okc+= abs(y-x)<=tol+1e-9
    pct=0 if so==0 and sn==0 else (100.0 if so==0 else sn/so*100)
    return round(pct,1),okc,cnt
W7=list(range(2,9)); W8=list(range(2,10))
# reason, action per row (1-based)
RA={}
def ra(rows,reason,action):
    for r in rows: RA[r]=(reason,action)
ra([9],'Same City_Targets tab copied','None')
ra([10,11,12,18,24],'Aug-Sep same (small gap = admin DAG fix of weekly_os/carry-forward). Oct-05 = 0 in New: PG MV week 05-Oct collections not loaded yet','Admin: run MV refresh for 05-Oct, then refresh Raw_Data')
ra([13,19],'Old Razorpay = Total - Adjustments - DP to Rent. Adjustments differ (see Adjustments), so Razorpay 2-3% lower','Fix Adjustments rule; Razorpay corrects itself')
ra([14,15,20,21],'Split now from mv_daily_recovery (other_positive / phonepe)','None (fixed)')
ra([16,22],'New = positive_adjustment from mv_daily_recovery. Old uses a smaller adjustment amount (approx 50-60% of it; old rule not documented)','Get old sheet adjustment logic from owner; apply same filter in Raw_Data S')
ra([17,23],'Fixed: deposit_to_os from mv_daily_recovery. Aug-31 / Sep-07 higher: deposit_to_os entries posted after old sheet snapshot','None (late postings) - accept New')
ra([25],'Same Aug-Sep (Sep-21: 92 vs 95 after DAG fix). Oct-05 high because 05-Oct collections not loaded','Admin: refresh MV for 05-Oct')
ra([26],'Fixed: old counts 2 PREVIOUS weeks unpaid (w-7, w-14); MV flag was 0/1. Aug-17: Aug-03 week missing in MV, used daily recovery','None (fixed)')
ra([27],'MV collection_till_wed includes all Mon-Wed recovery types; old used razorpay-only till Wed (+1-2 pp)','Accept MV rule or filter till-Wed to razorpay only')
ra([28],'Fixed after DP-to-Rent split','None (fixed)')
ra([29,30,31],'Active definition differs: old AC = entire week Uber active; New AC = allocated 7 days (wider)','Change Raw_Data AC to uber_active_days >= 7 (add field to Raw_Data)')
ra(range(32,40),'Both 0 (OS_Surpass tab same)','None')
ra([40,46],'Same source tab','None')
ra([41,42,43,44,45,49,50],'Sep-21 / Sep-28: admin DAG fix moved bad debt dates (Old -32.7K in Sep-28 now split Sep-21 -18.3K / Sep-28 -5.7K)','None - New is corrected logic; confirm with admin')
ra([47,48],'Fixed: MV bad_debt_collected is Non-Funnel (rejoin) amount, removed from Funnel column','None (fixed)')
ra([51],'Deposit source: New = MV week_start_deposit (validated); old = older sd_week_start snapshot (+1-3%)','Accept MV deposit (validated) or use same deposit snapshot')
ra([52],'Aug-Sep +-2 cars (OS changed after DAG fix). Oct-05: week incomplete (old mid-week snapshot 172, New no collections)','Recheck after 05-Oct MV refresh')
ra(range(53,64),'Both 0 / blank','None')
ra(range(64,70),'Aug-Sep same (+-2). Oct-05 differs: no 05-Oct collections, so OS/risk bucket shifts','Recheck after 05-Oct MV refresh')
ra(range(70,75),'Old = week snapshot of payment habit; MV = last habit entry before Hissab week (agreed rule #14)','Accept MV rule (agreed) - or confirm with owner')
ra(range(75,81),'sd_bucket rebuilt from MV week_start_deposit, only MV partners (20000+: ~620 vs ~660); old from deposit raw incl. more partners','Rebuild sd_bucket from deposit raw table with same partner list as old')
ra(range(81,87),'No "deposit at allocation" field in PG MV; sd_bucket_V2 filled with week-start deposit','Add deposit_at_allocation field to MV (deposit raw on allocation start date), then rebuild sd_bucket_V2')
rows=[]; tot_ok=tot_c=0; tot_ok1=0; tot_c7=tot_ok7=0
sec=''
for i in range(8,86):
    if not O[i] or len(O[i])<2 or not O[i][1].strip(): continue
    if O[i][0].strip(): sec=O[i][0].strip()
    p1,ok1,c1=diff(i,N1,W7); p2,ok2,c2=diff(i,N2,W7); p8,ok8,c8=diff(i,N2,W8)
    tot_ok+=ok8; tot_c+=c8; tot_ok1+=diff(i,N1,W8)[1]; tot_c7+=c2; tot_ok7+=ok2
    st='MATCH' if ok2==c2 else ('PARTIAL' if ok2>=c2*0.5 else 'MISMATCH')
    o5,n5=g(O,i,9),g(N2,i,9)
    reason,act=RA.get(i+1,('',''))
    rows.append([sec,O[i][1].strip(),st,f'{p1}%',f'{p2}%',f'{ok2}/{c2}',o5,n5,reason,act]+[f'{g(O,i,j)} | {g(N2,i,j)}' for j in W7])
fin_before=round(100-tot_ok1/tot_c*100,1); fin_after=round(100-tot_ok/tot_c*100,1); fin7=round(100-tot_ok7/tot_c7*100,1)
nm=sum(r[2]=='MATCH' for r in rows); npart=sum(r[2]=='PARTIAL' for r in rows); nmis=sum(r[2]=='MISMATCH' for r in rows)
top=[['Old vs New Summary - Delhi NCR / Own Now / all filters *  |  Old = reference sheet, New = PG raw'],
 ['Final difference (cells not matching, 2% tolerance)', f'Before fix: {fin_before}%', f'After fix: {fin_after}%', f'After fix, excl. Oct-05: {fin7}%'],
 ['Metrics', f'MATCH: {nm}', f'PARTIAL: {npart}', f'MISMATCH: {nmis}', f'Total: {len(rows)}'],
 ['Main open items','1) Admin: refresh MV for 05-Oct week','2) Adjustments rule from old owner','3) AC = Uber active 7 days','4) Deposit at allocation field + sd_bucket from deposit raw'],
 [],
 ['Section','Metric','Status (after fix)','Diff % before fix (Aug17-Sep28)','Diff % after fix (Aug17-Sep28)','Weeks matched (of 7)','Oct-05 Old','Oct-05 New','Reason','Correction step']+[f'{w} Old | New' for w in WK[:7]]]
out=top+rows
json.dump({'out':out,'fin':[fin_before,fin_after,fin7],'cnt':[nm,npart,nmis]},open('../dash/cmp_out.json','w'))
for r in rows: print(r[2],r[1],r[3],r[4],r[5])
print(fin_before,fin_after,fin7,nm,npart,nmis)
