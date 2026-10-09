exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
import os
REF='1wkebsPPLwXnRYAuvRV_fhMGQLRxv6JwH-cYlaIEBjRw'
data=json.load(open('../dash/raw_data_pg.json')); hdr=data[0]
fn='../dash/dash_sid.txt'
if os.path.exists(fn): DS=open(fn).read().strip()
else:
    r=call('POST',API,json={'properties':{'title':'Collections Dashboard – PG Raw (WBR, Summary, SD Profiles, CarryForward)'},
       'sheets':[{'properties':{'title':'Raw_Data','gridProperties':{'rowCount':len(data)+2,'columnCount':len(hdr),'frozenRowCount':1,'frozenColumnCount':8}}}]})
    DS=r['spreadsheetId']; open(fn,'w').write(DS)
refmeta={s['properties']['title']:s['properties']['sheetId'] for s in call('GET',f'{API}/{REF}',params={'fields':'sheets.properties'})['sheets']}
def have(): return {s['properties']['title']:s['properties']['sheetId'] for s in call('GET',f'{API}/{DS}',params={'fields':'sheets.properties'})['sheets']}
order=['City_Targets','NonFunnel_BadDebt_Collected','advance_payment_data','OS_Surpass','excellent_data','collections_data','sd_bucket','sd_bucket_V2','WBR View','Summary','SD_Profiles [At Allocation]','CarryForward_View']
for t in order:
    if t in have(): continue
    c=call('POST',f'{API}/{REF}/sheets/{refmeta[t]}:copyTo',json={'destinationSpreadsheetId':DS})
    call('POST',f'{API}/{DS}:batchUpdate',json={'requests':[{'updateSheetProperties':{'properties':{'sheetId':c['sheetId'],'title':t},'fields':'title'}}]})
    print('copied',t)
# tab order: dashboards first
HV=have(); dash=['WBR View','Summary','SD_Profiles [At Allocation]','CarryForward_View','Raw_Data']
reqs=[{'updateSheetProperties':{'properties':{'sheetId':HV[t],'index':i},'fields':'index'}} for i,t in enumerate(dash)]
call('POST',f'{API}/{DS}:batchUpdate',json={'requests':reqs})
# write Raw_Data
call('PUT',f"{API}/{DS}/values/'Raw_Data'!A1",params={'valueInputOption':'RAW'},json={'values':[hdr]})
B=4000
for i in range(1,len(data),B):
    call('PUT',f"{API}/{DS}/values/'Raw_Data'!A{i+1}",params={'valueInputOption':'USER_ENTERED'},json={'values':data[i:i+B]})
    if i%20000<B: print('rows',i)
print('https://docs.google.com/spreadsheets/d/'+DS)
