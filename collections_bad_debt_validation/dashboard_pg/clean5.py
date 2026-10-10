import json,re
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS=open('../dash/dash_sid.txt').read().strip()
D=json.load(open('../dash/raw_final.json')); hdr=D[0]; R=D[1:]
R.sort(key=lambda r:(r[0],r[3],r[1]))
f=lambda v: float(v) if v not in ('',None) else 0.0
iP,iX,iM=hdr.index('total_collected_amount_in_week'),hdr.index('deposit_to_rent_100pct'),hdr.index('total_os')
BF=[[round(max(f(r[iP])-f(r[iX])-abs(f(r[iM])),0),2)] for r in R]
m=call('GET',f'{API}/{DS}',params={'fields':'sheets.properties'})
P={s['properties']['title']:s['properties']['sheetId'] for s in m['sheets']}
call('POST',f'{API}/{DS}:batchUpdate',json={'requests':[{'updateSheetProperties':{'properties':{'sheetId':P['Raw_Data'],'gridProperties':{'columnCount':58}},'fields':'gridProperties.columnCount'}}]})
call('PUT',f"{API}/{DS}/values/'Raw_Data'!BF1",params={'valueInputOption':'RAW'},json={'values':[['advance_amount']]})
call('PUT',f"{API}/{DS}/values/'Raw_Data'!BF2:BF{len(R)+1}",params={'valueInputOption':'RAW'},json={'values':BF})
print('advance rows >0:',sum(1 for x in BF if x[0]>0))
W=call('GET',f"{API}/{DS}/values/'WBR View'!A1:BA486",params={'valueRenderOption':'FORMULA'})['values']
A='advance_payment_data!'
out=[];ch=0
for r in W:
    row=[]
    for c in r:
        if isinstance(c,str) and A in c:
            c=re.sub(r'COUNTUNIQUEIFS\(advance_payment_data!\$C:\$C,advance_payment_data!\$B:\$B,([^,]+),advance_payment_data!\$G:\$G,([^,]+),advance_payment_data!\$H:\$H,([^,\)]+)\)',
                     r'COUNTUNIQUEIFS(Raw_Data!$B:$B,Raw_Data!$A:$A,\1,Raw_Data!$D:$D,\2,Raw_Data!$F:$F,\3,Raw_Data!$BF:$BF,">0")',c)
            c=re.sub(r'(?i)sumifs\(advance_payment_data!\$F:\$F,advance_payment_data!\$B:\$B,([^,]+),advance_payment_data!\$G:\$G,([^,]+),advance_payment_data!\$H:\$H,([^,\)]+)\)',
                     r'SUMIFS(Raw_Data!$BF:$BF,Raw_Data!$A:$A,\1,Raw_Data!$D:$D,\2,Raw_Data!$F:$F,\3)',c)
            if A in c: raise Exception('left: '+c[:200])
            ch+=1
        row.append(c)
    out.append(row)
for i in range(0,len(out),100):
    call('PUT',f"{API}/{DS}/values/'WBR View'!A{i+1}",params={'valueInputOption':'USER_ENTERED'},json={'values':out[i:i+100]})
print('WBR advance formulas repointed',ch)
