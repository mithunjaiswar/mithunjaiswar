import json,sys,datetime as D
sys.path.insert(0,'.'); from load import rows
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
f=lambda v: float(v) if v.strip() not in ('','None','NULL') else 0.0
S=[[c.strip() for c in x] for x in json.load(open('../dash/split_rows.json')) if x[0].strip()!='wk']
M={(x[0],x[1]):[f(v) for v in x[2:]] for x in S}
P={(x[0].strip(),x[1].strip()):[f(x[2]),f(x[3])] for x in rows([1791605251285]) if x[0].strip()!='wk'}
A03={x[0].strip() for x in rows([1791605331382]) if x[0].strip()!='partner_etm'}
r=json.load(open('../dash/raw_data_pg.json'));R=r[1:]
ix=lambda c: (ord(c[0])-64)*26+ord(c[1])-65 if len(c)==2 else ord(c)-65
U={(x[0],x[3]):float(x[ix('U')] or 0) for x in R}
d7=lambda w,n: (D.date.fromisoformat(w)-D.timedelta(n)).isoformat()
for x in R:
    w,e=x[0],x[3]; u=float(x[ix('U')] or 0)
    m=M.get((w,e),[0]*5); pa,op=P.get((w,e),[0,0])
    q,rr,s,t=op,m[2],pa,m[4]
    if u==0: q=rr=s=t=0
    x[ix('Q')],x[ix('R')],x[ix('S')],x[ix('T')]=q,rr,s,t
    x[ix('P')]=round(u-q-rr-s-t,2)
    x[ix('N')]=t
    w7,w14=d7(w,7),d7(w,14)
    if w14=='2026-08-03': aa=2 if e in A03 else int(U.get((w7,e),0)<=0)
    elif (w14,e) in U: aa=int(U.get((w7,e),0)<=0)+int(U[(w14,e)]<=0)
    else: aa=int(U.get((w7,e),0)<=0)
    x[ix('AA')]=aa
    x[ix('AY')]=0
json.dump(r,open('../dash/raw_data_pg.json','w'))
DS=open('../dash/dash_sid.txt').read().strip()
data=[]
for c in ['N','P','Q','R','S','T','AA','AY']:
    data.append({'range':f"'Raw_Data'!{c}2:{c}{len(R)+1}",'values':[[x[ix(c)]] for x in R]})
for d in data:
    call('POST',f'{API}/{DS}/values:batchUpdate',json={'valueInputOption':'RAW','data':[d]}); print('wrote',d['range'])
