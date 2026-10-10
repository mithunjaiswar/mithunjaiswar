import json
exec(open('val/write_tab.py').read().split('MAN,REM=pickle.load')[0])
exec(open('val/waterfall.py').read().split('MV={(r[0]')[0])
DS=open('dash/dash_sid.txt').read().strip()
R=D[1:]; R.sort(key=lambda r:(r[0],r[3],r[1]))
TW=[];SP=[];AD=[]
for m in R:
    r=wf(m); SP.append([round(x,2) for x in r[:5]]); TW.append([round(r[5],2)]); AD.append([round(r[6],2)])
n=len(R)+1
call('POST',f'{API}/{DS}/values:batchUpdate',json={'valueInputOption':'RAW','data':[{'range':"'Raw_Data'!R1",'values':[['till_wed_100pct']]}]})
for c,v in [('R',TW),('BF',AD)]:
    call('PUT',f"{API}/{DS}/values/'Raw_Data'!{c}2:{c}{n}",params={'valueInputOption':'RAW'},json={'values':v})
for i in range(0,len(SP),25000):
    call('PUT',f"{API}/{DS}/values/'Raw_Data'!T{i+2}",params={'valueInputOption':'RAW'},json={'values':SP[i:i+25000]})
print('Raw_Data R, T:X, BF updated', len(R))
