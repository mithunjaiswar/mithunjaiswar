exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
from load import rows
from mv import COLS
C=COLS+['collection_pct']
r=[x[:54] for x in rows([1791561294506,1791561339733,1791561345971,1791561349049,1791561358477]) if len(x)>=54]
m=pd.DataFrame(r,columns=C).set_index('partner_etm',drop=False); print('fresh rows',len(m))
m.reset_index(drop=True).to_json('../run4/mv_0928_new.json')
V2='MV_Raw_Data_Manual_Check_v2'
hdr=call('GET',f"{API}/{SID}/values/'{V2}'!A5:ZZ5")['values'][0]
before=call('GET',f"{API}/{SID}/values/'{V2}'!A2:ZZ2")['values'][0]
emp=[e[0] if e else '' for e in call('GET',f"{API}/{SID}/values/'{V2}'!C6:C20000")['values']]; n=len(emp)
print('sheet rows',n,'missing in fresh MV',sum(e not in m.index for e in emp))
data=[]
for j,h in enumerate(hdr):
    if ' (MV)' not in h: continue
    f=h.split(' (MV)')[0]
    if f not in m.columns: continue
    vals=[[m.at[e,f] if e in m.index else ''] for e in emp]
    data.append({'range':f"'{V2}'!{col(j)}6:{col(j)}{5+n}",'values':vals})
for i in range(0,len(data),8):
    call('POST',f'{API}/{SID}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data[i:i+8]})
after=call('GET',f"{API}/{SID}/values/'{V2}'!A2:ZZ3")['values']
res=[]
for j,h in enumerate(hdr):
    if h.endswith(' Matched?'):
        res.append((h[:-9], before[j] if j<len(before) else '', after[0][j] if j<len(after[0]) else '', after[1][j] if j<len(after[1]) else ''))
json.dump(res,open('../run4/refresh28_res.json','w'))
for x in res: print(x)
