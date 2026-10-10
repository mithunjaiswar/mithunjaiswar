import json,collections
F=json.load(open('dash/ref_raw_cols.json'))
D=json.load(open('dash/raw_final.json')); h=D[0]; ix={c:i for i,c in enumerate(h)}
TR='/root/.claude/projects/-home-user-mithunjaiswar/975ddfa8-2a6b-560b-8c6b-202af90fa71a/tool-results/mcp-Everest_Reporting_DB-run_read_only_query-1791623301163.txt'
K={}
for l in json.load(open(TR))['result'].split('\n'):
    l=l.strip()
    if l.startswith('| 2026-'):
        v=l[2:].rstrip('|').strip().split('~'); K[(v[0],v[1])]=v[2:]
LAB={6:'Critical Risk',5:'High Risk',4:'Moderate Risk',3:'Low Risk',2:'Minimal Risk'}
f=lambda v: float(v) if v not in ('',None) and not isinstance(v,str) or (isinstance(v,str) and v.replace('.','',1).replace('-','',1).isdigit()) else 0.0
def fl(v):
    try: return float(v)
    except: return 0.0
MV={(r[0],r[1].upper()):r for r in D[1:]}
WEEKS={'2026-08-17','2026-08-24','2026-08-31','2026-09-07','2026-09-14','2026-09-21','2026-09-28'}
n=len(F['A']); g=lambda c,i: F[c][i] if i<len(F[c]) else ''
CMP={
 'total_os':('E',lambda m,k: fl(m[ix['total_os']]),'num'),
 'coll100':('U',lambda m,k: fl(m[ix['total_collected_100_pct']]),'num'),
 'total_recovery':('I',lambda m,k: fl(m[ix['total_collected_amount_in_week']]),'num'),
 'razorpay':('P',lambda m,k: fl(m[ix['razorpay_100pct']]),'num'),
 'adjustment':('S',lambda m,k: fl(m[ix['adjustment_100pct']]),'num'),
 'dp_to_rent':('T',lambda m,k: fl(m[ix['deposit_to_rent_100pct']]),'num'),
 'till_wed':('O',lambda m,k: min(fl(m[ix['collection_till_wed']]),abs(fl(m[ix['total_os']]))),'num'),
 'not_paid_2w':('AA',lambda m,k: int(fl(m[ix['partners_not_paid_2_weeks']])>0),'np'),
 'entire_week_active':('AC',lambda m,k: int(fl(m[ix['entire_week_active']])),'num'),
 'habit':('AF',lambda m,k: m[ix['last_week_payment_habit']],'txt'),
 'recovery_recommended':('AH',lambda m,k: K.get(k,['']*7)[6],'txt'),
 'asset_risk':('AL',lambda m,k: LAB.get(int(K[k][0]),'No risk') if k in K else '','txt'),
 'bad_debt':('AW',lambda m,k: fl(m[ix['bad_debt_amount']]),'num'),
 'funnel':('AY',lambda m,k: fl(m[ix['bad_debt_collected_funnel']]),'num'),
 'week_start_deposit':('BB',lambda m,k: fl(m[ix['week_start_deposit']]),'num'),
 'carry_forward':('AQ',lambda m,k: min(fl(m[ix['prev_carryforward_os']]),0),'num'),
 'advance':('AU',lambda m,k: max(fl(m[ix['total_collected_amount_in_week']])-fl(m[ix['deposit_to_rent_100pct']])-abs(fl(m[ix['total_os']])),0),'num'),
}
res={}
for name,(c,fn,kind) in CMP.items():
    tot=bad=0; ex=[]
    for i in range(n):
        w=str(g('A',i))[:10]
        if w not in WEEKS: continue
        e=str(g('D',i)).strip().upper(); m=MV.get((w,e))
        if not m: continue
        s=g(c,i); v=fn(m,(w,m[1]))
        if kind=='num': ok=abs(fl(s)-v)<=1
        elif kind=='np': ok=(int(fl(s)>1)==v)
        else: ok=str(s).strip().lower()==str(v).strip().lower()
        tot+=1
        if not ok:
            bad+=1
            ex.append((w,m[1],g('F',i),g('H',i),s,v, abs(fl(s)-v) if kind=='num' else 0))
    dl=[x for x in ex if x[2]=='Delhi NCR' and x[3]=='Own Now'] or ex
    dl.sort(key=lambda x:-x[6])
    res[name]=dict(col=c,tot=tot,bad=bad,pct=round(bad/tot*100,1) if tot else 0,ex=dl[:6])
    print(f'{name:22s} {c:3s} rows {tot:6d} mismatch {bad:6d} {res[name]["pct"]:5.1f}%  ex {dl[:2]}')
json.dump(res,open('dash/ex_cmp.json','w'),default=str)
