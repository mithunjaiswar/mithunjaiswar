import json
F=json.load(open('dash/ref_raw_cols.json'))
D=json.load(open('dash/raw_final.json')); h=D[0]; ix={c:i for i,c in enumerate(h)}
S=[[c.strip() for c in x] for x in json.load(open('dash/split_rows.json')) if x[0].strip()!='wk']
def fl(v):
    try: return float(v)
    except: return 0.0
RZ={(x[0],x[1]):fl(x[2]) for x in S}
def wf(m):
    k=(m[0],m[1]); OS=abs(fl(m[ix['total_os']]))
    rz=RZ.get(k,0.0); ot=fl(m[ix['other_100pct']]); pp=fl(m[ix['phonepe_100pct']]); ad=fl(m[ix['adjustment_100pct']]); dt=fl(m[ix['deposit_to_rent_100pct']])
    r1=min(rz,OS); r2=max(0,min(ot,OS-rz)); r3=max(0,min(pp,OS-rz-ot)); r4=max(0,min(ad,OS-rz-ot-pp)); r5=max(0,min(dt,OS-rz-ot-pp-ad))
    tw=min(fl(m[ix['collection_till_wed']]),OS); adv=max(fl(m[ix['total_collected_amount_in_week']])-OS,0)
    return r1,r2,r3,r4,r5,tw,adv
MV={(r[0],r[1].upper()):r for r in D[1:]}
W={'2026-08-17','2026-08-24','2026-08-31','2026-09-07','2026-09-14','2026-09-21','2026-09-28'}
cnt={k:[0,0] for k in ['razorpay','other','phonepe','adjustment','dp_to_rent','advance']}
exs={k:[] for k in cnt}
for i in range(len(F['A'])):
    w=str(F['A'][i])[:10]
    if w not in W: continue
    m=MV.get((w,str(F['D'][i]).strip().upper()))
    if not m: continue
    r=wf(m)
    for k,c,v in [('razorpay','P',r[0]),('other','Q' if 'Q' in F else None,r[1]),('adjustment','S',r[3]),('dp_to_rent','T',r[4]),('advance','AU',r[6])]:
        if c is None: continue
        cnt[k][0]+=1
        if abs(fl(F[c][i])-v)>1:
            cnt[k][1]+=1
            if F['F'][i]=='Delhi NCR' and F['H'][i]=='Own Now' and len(exs[k])<3: exs[k].append((w,m[1],F[c][i],v))
for k,(t,b) in cnt.items():
    if t: print(k,t,b,f'{b/t*100:.1f}%',exs[k])
