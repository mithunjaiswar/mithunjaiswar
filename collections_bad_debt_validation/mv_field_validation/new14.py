exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
import os
V2='MV_Raw_Data_Manual_Check_v2'
if os.path.exists('../w14/new_sid.txt'):
    NSID=open('../w14/new_sid.txt').read().strip()
else:
    r=call('POST',API,json={'properties':{'title':'MV Validation – Hisaab week 14-Sep-2026'}})
    NSID=r['spreadsheetId']; open('../w14/new_sid.txt','w').write(NSID)
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
v2id=[s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title']==V2][0]
nm=call('GET',f'{API}/{NSID}',params={'fields':'sheets.properties'})
titles={s['properties']['title']:s['properties']['sheetId'] for s in nm['sheets']}
TN='MV_Raw_Data_Manual_Check'
if TN not in titles:
    c=call('POST',f'{API}/{SID}/sheets/{v2id}:copyTo',json={'destinationSpreadsheetId':NSID})
    reqs=[{'updateSheetProperties':{'properties':{'sheetId':c['sheetId'],'title':TN,'index':0},'fields':'title,index'}}]
    reqs+=[{'deleteSheet':{'sheetId':i}} for t,i in titles.items()]
    call('POST',f'{API}/{NSID}:batchUpdate',json={'requests':reqs})
print('https://docs.google.com/spreadsheets/d/'+NSID)
