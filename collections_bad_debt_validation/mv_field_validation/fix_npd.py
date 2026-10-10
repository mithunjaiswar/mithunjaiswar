exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
from load import rows
rec={x[0].strip():[c.strip() for c in x] for x in rows([1791613882897]) if x[0].strip().startswith('ET')}
NS=open('../w14/new_sid.txt').read().strip(); TN='MV_Raw_Data_Manual_Check'
def C(c):
  v=call('GET',f"{API}/{NS}/values/'{TN}'!{c}6:{c}12000",params={'valueRenderOption':'UNFORMATTED_VALUE'}).get('values',[]); return [r[0] if r else '' for r in v]
E=C('C'); n=len(E); M=C('GM')+['']*n; PC=C(col(188))+['']*n
f=lambda x: float(x) if x not in ('',None) else 0
rem=[];bad=0
for i,e in enumerate(E):
    r=rec.get(e,['','','0','0','0','0']); lw,pv=f(r[3]),f(r[4]); man=int(lw<=0 and pv<=0); mv=int(f(M[i]))
    if man==mv: rem.append('Matched'); continue
    bad+=1
    if mv==1: rem.append(f'MV flags not-paid but partner paid {lw:,.0f} in 07-13 Sep (paid {pv:,.0f} in 31 Aug-06 Sep). MV previous_week_collection is always 0, so MV checks only 1 week')
    else: rem.append(f'No payment in 07-13 Sep and 31 Aug-06 Sep → should be 1; MV 0')
call('PUT',f"{API}/{NS}/values/'{TN}'!GQ6:GQ{5+n}",params={'valueInputOption':'RAW'},json={'values':[[x] for x in rem]})
pz=sum(1 for x in PC[:n] if f(x)!=0)
j=call('GET',f"{API}/{NS}/values/'{TN}'!A5:ZZ5")['values'][0].index('partners_not_paid_2_weeks (MV)')
call('PUT',f"{API}/{NS}/values/'{TN}'!{col(j)}1:{col(j)}2",params={'valueInputOption':'RAW'},json={'values':[[f'Checked: 1 if no payment in BOTH previous weeks (07-13 Sep and 31 Aug-06 Sep). {bad} rows differ: MV previous_week_collection is 0 for all {n - pz} partners, so MV flag uses only one week.'],['DAG: fill previous_week_collection (payments 2 weeks back) and flag = 1 only if both weeks unpaid.']]})
print(bad,pz)
