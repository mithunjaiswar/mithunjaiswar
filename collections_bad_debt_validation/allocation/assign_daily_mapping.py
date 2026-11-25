import json,sys,re
sys.path.insert(0,'.')
from collections import Counter,defaultdict
from parse import table
BAD={'','-','NA','NaN','#N/A','Agent_Missing','Agent Missing','Unassigned','#REF!'}
CITY={'chennai':'Chennai','delhi':'Delhi NCR','hyd':'Hyderabad','kolkata':'Kolkata','mumbai':'Mumbai','pune':'Pune'}
PM={'Leasing - Single':'SINGLE','SINGLE':'SINGLE','Leasing - EIP':'EIP','EIP':'EIP','EV_Leasing':'EV','EV':'EV','EV_D2O':'EV_D2O','D2O':'D2O','Own Now':'Own Now','Revenue Share':'Revenue Share','Fixed Pay':'Fixed Pay','EV_Revenue Share':'Revenue Share'}
allocs=table('allocs.json'); hist=table('hist.json')
alloc_by=defaultdict(dict)
for r in allocs: alloc_by[r['city']][r['employee_id']]=r
hist_by={(r['city'],r['etm']):r['ag'] for r in hist}
res={}
for key,city in CITY.items():
    A=json.load(open(f'am_{key}.json')); start=int(re.search(r'A(\d+):',A['range']).group(1))
    am=[(r+['']*5)[:5] for r in A['values']]
    old=[(r+['']*5)[:5] for r in json.load(open(f'am_prev_{key}.json'))['values']]
    ame={}
    for r in old+am:
        if r[3].strip() not in BAD and r[4].strip() not in BAD: ame[r[3].strip()]=r[4].strip()
    for r in old:
        if r[3].strip() not in BAD: hist_by.setdefault((city,r[1]),r[3].strip())
    cur={r[1]:(start+i,r) for i,r in enumerate(am) if r[0]=='2026-11-23'}
    last=start+len(am)-1
    cm=[(r+['']*8)[:8] for r in json.load(open(f'cm_{key}.json'))['values'] if r and r[0]]
    loads=Counter(); tot=Counter(); cmag={}; cmprod={}
    for r in cm:
        ag=r[2].strip(); cmag[r[3].strip()]=ag; cmprod[r[3].strip()]=PM.get(r[7],r[7])
        if ag not in BAD: loads[(PM.get(r[7],r[7]),ag)]+=1; tot[ag]+=1
    active=set(tot)
    # who needs an agent: 23-24 allocations + CM rows with no agent; skip if mapping already has an agent
    need={}
    for et,a in alloc_by[city].items(): need[et]=a['prod']
    for et,ag in cmag.items():
        if ag in BAD: need.setdefault(et,cmprod[et])
    out=[]; queue=[]
    for et,prod in need.items():
        m=cur.get(et)
        if m and m[1][3].strip() not in BAD: continue
        a=alloc_by[city].get(et)
        if m and m[1][2]: prod=m[1][2]
        sa=cmag.get(et,'')
        if sa not in BAD and sa in active: out.append([et,prod,sa,'sheet agent']); continue
        if city=='Hyderabad' and a and a['username'] in active: out.append([et,prod,a['username'],'hyd join user']); continue
        if not a:
            h=hist_by.get((city,et))
            if h and h in active: out.append([et,prod,h,'carry forward']); continue
        queue.append((a['adt'] if a else '9999',et,prod))
    queue.sort()
    for adt,et,prod in queue:
        pool=[g for (p,g),n in loads.items() if p==prod and n>=10]; basis='prod'
        if not pool: pool=[g for g,n in tot.items() if n>=10]; basis='city'
        if not pool: out.append([et,prod,'','no agent']); continue
        cnt=(lambda g: loads[(prod,g)]) if basis=='prod' else (lambda g: tot[g])
        best=min(pool,key=lambda g:(cnt(g),g)); loads[(prod,best)]+=1; tot[best]+=1
        out.append([et,prod,best,'level-up '+basis+(' >165' if tot[best]>165 else '')])
    fills=[]; apps=[]
    for et,prod,ag,how in out:
        e=ame.get(ag,ag) if ag else ''
        if et in cur: fills.append((cur[et][0],ag,e))
        else: apps.append(['2026-11-23',et,prod,ag,e])
    res[key]={'fills':fills,'apps':apps,'last':last,'out':out}
    print(city,'fill',len(fills),'append',len(apps),Counter(o[3] for o in out),'| top',Counter(o[2] for o in out).most_common(3))
json.dump(res,open('res.json','w'))
