import json,re
exec(open('clean2_wbr.py').read().split('m=call(')[0])   # MAP + remap
DS=open('../dash/dash_sid.txt').read().strip()
# City_Targets formulas
C=call('GET',f"{API}/{DS}/values/'City_Targets'!A1:Q900",params={'valueRenderOption':'FORMULA'})['values']
out=[[remap(c) if isinstance(c,str) and c.startswith('=') else c for c in r] for r in C]
call('PUT',f"{API}/{DS}/values/'City_Targets'!A1",params={'valueInputOption':'USER_ENTERED'},json={'values':out})
print('City_Targets remapped', sum(1 for r in C for c in r if isinstance(c,str) and 'Raw_Data!' in c))
# Raw_Data col P (total_collected_amount_in_week): blank -> 0
D=json.load(open('../dash/raw_final.json')); hdr=D[0]; R=D[1:]
R.sort(key=lambda r:(r[0],r[3],r[1]))
j=hdr.index('total_collected_amount_in_week')
vals=[[float(r[j]) if r[j]!='' else 0] for r in R]
call('PUT',f"{API}/{DS}/values/'Raw_Data'!P2:P{len(R)+1}",params={'valueInputOption':'RAW'},json={'values':vals})
print('P zero-filled', sum(1 for r in R if r[j]==''))
