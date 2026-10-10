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
def ra(rows,rec,reason):
    for r in rows: RA[r]=(rec,reason)
ra([9],'No change','Same City_Targets tab in both sheets')
ra([10,12,18],'Admin: rerun MV for 05-Oct, then refresh Raw_Data','Aug-Sep within 0.2%. Oct-05 New = 0: MV week 05-Oct has total_collected_100_pct empty (old DAG run)')
ra([11],'Admin: rerun MV for 05-Oct, then refresh Raw_Data','Aug-Sep within 0.2%. Oct-05 -5792K vs -5992K: 05-Oct collections missing in MV, so OS not netted')
ra([24],'Admin: rerun MV for 05-Oct','Aug-Sep diff 1-4 pilots (DAG fix on weekly_os). Oct-05 645 vs 668: no 05-Oct collections in MV')
ra([13,19],'Fix Adjustments first - Razorpay will auto-correct','Old Razorpay = Total - Adjustments - DP to Rent. New Adjustments ~45K/week higher, so Razorpay ~2% lower (Sep-14: 2947.9K vs 3002.7K)')
ra([14,15,20,21],'No change (fixed)','Now split from mv_daily_recovery other_positive_recovery / phonepe_recovery - matches old (Sep-28 Other 18.0K both)')
ra([16,22],'Ask old sheet owner which adjustment types count; apply same filter on Raw_Data col S','New = all positive_adjustment in mv_daily_recovery (Sep-14: 128.9K). Old = 84.0K, about 55-65% of it - old rule not documented')
ra([17,23],'No change - accept New','Fixed from mv_daily_recovery deposit_to_os. Only Aug-31 (653.7K vs 590.0K) and Sep-07 (364.4K vs 358.4K) higher: entries synced after old snapshot')
ra([25],'Admin: rerun MV for 05-Oct','Aug-Sep match (Sep-21 92 vs 95 after DAG fix). Oct-05 464 vs 176: MV 05-Oct has no collections so all show unpaid')
ra([26],'No change (fixed)','Old counts unpaid in 2 PREVIOUS weeks (w-7, w-14). MV partners_not_paid_2_weeks is 0/1 flag. Recomputed - now 37/47/36/30/32 same as old. Aug-17 21 vs 18: week 03-Aug not in MV')
ra([27],'Decide rule: keep MV (all types) or filter Till-Wed to razorpay only','MV collection_till_wed sums all Mon-Wed recovery types; old used razorpay only. New 1-2 pp higher every week')
ra([28],'No change (fixed)','Matches after DP to Rent split (T column)')
ra([29,30,31],'Add uber_active_days to Raw_Data; set AC = 1 only if uber_active_days >= 7','Old AC = Uber active full week. New AC = allocated 7 days (wider) - so 4-14 drivers/week counted vs old 0-3')
ra(range(32,40),'No change','Both 0 - OS_Surpass tab same')
ra([40,46],'No change','Same source tab')
ra([41,42,43,44,45,49,50],'No change - New is corrected DAG logic; confirm with admin','Only Sep-21 / Sep-28 differ: DAG fix moved bad debt dates. Old Sep-28 -32.7K (7 partners) is now Sep-21 -18.3K (4) + Sep-28 -5.7K (1)')
ra([47,48],'No change (fixed)','MV bad_debt_collected = Non-Funnel rejoin amount; was wrongly in Funnel column (702K vs 0). Removed - now 0 same as old')
ra([51],'Accept MV deposit (validated) or use same deposit snapshot as old','New = MV week_start_deposit; old = older sd_week_start snapshot. New 1-3% higher (Sep-14 59.8K vs 57.5K)')
ra([52],'Recheck after 05-Oct MV rerun','Aug-Sep diff 0-2 cars (OS change from DAG fix). Oct-05 7 vs 172: old was mid-week snapshot, New has no 05-Oct collections')
ra(range(53,64),'No change','Both 0 / blank')
ra(range(64,70),'Recheck after 05-Oct MV rerun','Aug-Sep match (diff 0-2). Oct-05 differs: no 05-Oct collections in MV so risk buckets shift')
ra(range(70,75),'Accept MV rule (agreed rule #14) or confirm with owner','Old = payment habit snapshot of that week. MV last_week_payment_habit = last entry before Hissab week. Diff 8-34% per bucket')
ra(range(75,81),'Rebuild sd_bucket from deposit raw table with same partner list as old','New sd_bucket counts only MV partners with week_start_deposit (20000+: 615-658). Old has more partners (650-694)')
ra(range(81,87),'Admin: add deposit_at_allocation to MV (deposit on allocation start date); rebuild sd_bucket_V2','PG MV has no deposit-at-allocation field. sd_bucket_V2 currently = week-start deposit, so ~99% in 20000+ vs old 29%')
rows=[]; tot_ok=tot_c=0; tot_ok1=0; tot_c7=tot_ok7=0
sec=''
for i in range(8,86):
    if not O[i] or len(O[i])<2 or not O[i][1].strip(): continue
    if O[i][0].strip(): sec=O[i][0].strip()
    p1,ok1,c1=diff(i,N1,W7); p2,ok2,c2=diff(i,N2,W7); p8,ok8,c8=diff(i,N2,W8)
    tot_ok+=ok8; tot_c+=c8; tot_ok1+=diff(i,N1,W8)[1]; tot_c7+=c2; tot_ok7+=ok2
    st='MATCH' if ok2==c2 else ('PARTIAL' if ok2>=c2*0.5 else 'MISMATCH')
    o5,n5=g(O,i,9),g(N2,i,9)
    rec,reason=RA.get(i+1,('',''))
    rows.append([sec,O[i][1].strip(),st,f'{p1}%',f'{p2}%',f'{ok2}/{c2}',o5,n5,rec,reason]+[f'{g(O,i,j)} | {g(N2,i,j)}' for j in W7])
fin_before=round(100-tot_ok1/tot_c*100,1); fin_after=round(100-tot_ok/tot_c*100,1); fin7=round(100-tot_ok7/tot_c7*100,1)
nm=sum(r[2]=='MATCH' for r in rows); npart=sum(r[2]=='PARTIAL' for r in rows); nmis=sum(r[2]=='MISMATCH' for r in rows)
top=[['Old vs New Summary - Delhi NCR / Own Now / all filters *  |  Old = reference sheet, New = PG raw'],
 ['Final difference (cells not matching, 2% tolerance)', f'Before fix: {fin_before}%', f'After fix: {fin_after}%', f'After fix, excl. Oct-05: {fin7}%'],
 ['Metrics', f'MATCH: {nm}', f'PARTIAL: {npart}', f'MISMATCH: {nmis}', f'Total: {len(rows)}'],
 ['Main open items','1) Admin: refresh MV for 05-Oct week','2) Adjustments rule from old owner','3) AC = Uber active 7 days','4) Deposit at allocation field + sd_bucket from deposit raw'],
 [],
 ['Section','Metric','Status (after fix)','Diff % before fix (Aug17-Sep28)','Diff % after fix (Aug17-Sep28)','Weeks matched (of 7)','Oct-05 Old','Oct-05 New','Your Recommendation','Reason']+[f'{w} Old | New' for w in WK[:7]]]
out=top+rows
json.dump({'out':out,'fin':[fin_before,fin_after,fin7],'cnt':[nm,npart,nmis]},open('../dash/cmp_out.json','w'))
for r in rows: print(r[2],r[1],r[3],r[4],r[5])
print(fin_before,fin_after,fin7,nm,npart,nmis)
