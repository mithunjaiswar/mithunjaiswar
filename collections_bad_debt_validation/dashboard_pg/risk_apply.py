import json,re
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS=open('../dash/dash_sid.txt').read().strip()
TR='/root/.claude/projects/-home-user-mithunjaiswar/975ddfa8-2a6b-560b-8c6b-202af90fa71a/tool-results/mcp-Everest_Reporting_DB-run_read_only_query-1791623301163.txt'
K={}
for l in json.load(open(TR))['result'].split('\n'):
    l=l.strip()
    if l.startswith('| 2026-'):
        v=l[2:].rstrip('|').strip().split('~'); K[(v[0],v[1])]=v[2:]
LAB={6:'Critical Risk',5:'High Risk',4:'Moderate Risk',3:'Low Risk',2:'Minimal Risk'}
D=json.load(open('../dash/raw_final.json')); hdr=D[0]; R=D[1:]
R.sort(key=lambda r:(r[0],r[3],r[1]))
miss=0; AN=[];AO=[];EXT=[]
for r in R:
    v=K.get((r[0],r[1]))
    if not v: miss+=1; v=['0','','0','0','0','0','No']
    sc=int(v[0]); AN.append([LAB.get(sc,'No risk')]); AO.append([v[6]])
    EXT.append([sc,v[1],int(v[2]),float(v[3]),int(v[4]),float(v[5])])
print('rows',len(R),'missing',miss)
m=call('GET',f'{API}/{DS}',params={'fields':'sheets.properties'})
sid=[s['properties']['sheetId'] for s in m['sheets'] if s['properties']['title']=='Raw_Data'][0]
call('POST',f'{API}/{DS}:batchUpdate',json={'requests':[{'updateSheetProperties':{'properties':{'sheetId':sid,'gridProperties':{'columnCount':57}},'fields':'gridProperties.columnCount'}}]})
n=len(R)+1
call('POST',f'{API}/{DS}/values:batchUpdate',json={'valueInputOption':'RAW','data':[
  {'range':"'Raw_Data'!AN1:AO1",'values':[['asset_risk','recovery_recommended']]},
  {'range':"'Raw_Data'!AZ1:BE1",'values':[['risk_score','payment_habit_week','not_paid_prev_2w','nd_count_hw','gps_inactive','connects']]}]})
for c,vals in [('AN',AN),('AO',AO)]:
    call('PUT',f"{API}/{DS}/values/'Raw_Data'!{c}2:{c}{n}",params={'valueInputOption':'RAW'},json={'values':vals})
for i in range(0,len(EXT),25000):
    call('PUT',f"{API}/{DS}/values/'Raw_Data'!AZ{i+2}",params={'valueInputOption':'RAW'},json={'values':EXT[i:i+25000]})
# Summary rows 64-69 -> asset_risk buckets
F=lambda c: f'Raw_Data!$D:$D,$B$2,Raw_Data!$A:$A,{c}$8,Raw_Data!$F:$F,$B$5,Raw_Data!$J:$J,$B$6,Raw_Data!$H:$H,$B$4,Raw_Data!$K:$K,$B$7'
rows=[[f'=IFERROR(COUNTIFS({F(col(j))},Raw_Data!$AN:$AN,$B{r}), "-")' for j in range(2,10)] for r in range(64,70)]
call('PUT',f"{API}/{DS}/values/'Summary'!C64:J69",params={'valueInputOption':'USER_ENTERED'},json={'values':rows})
# WBR: restore Moderate-to-Critical chain
W=call('GET',f"{API}/{DS}/values/'WBR View'!A1:BA486",params={'valueRenderOption':'FORMULA'})['values']
ch=0; out=[]
for r in W:
    row=[]
    for c in r:
        if isinstance(c,str) and 'Raw_Data!$AN:$AN,"Critical_Risk"' in c:
            c=c.replace('Raw_Data!$AN:$AN,"Critical_Risk"','Raw_Data!$AN:$AN,"<>No Risk",Raw_Data!$AN:$AN,"<>Minimal Risk",Raw_Data!$AN:$AN,"<>Low Risk"'); ch+=1
        row.append(c)
    out.append(row)
for i in range(0,len(out),100):
    call('PUT',f"{API}/{DS}/values/'WBR View'!A{i+1}",params={'valueInputOption':'USER_ENTERED'},json={'values':out[i:i+100]})
print('WBR formulas restored',ch)
