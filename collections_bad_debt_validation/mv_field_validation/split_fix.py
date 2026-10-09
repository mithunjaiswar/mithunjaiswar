exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
import sys
TABX=sys.argv[1] if len(sys.argv)>1 else TAB
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
p=[s['properties'] for s in meta['sheets'] if s['properties']['title']==TABX][0]; tid=p['sheetId']; nr=p['gridProperties']['rowCount']
hdr=call('GET',f"{API}/{SID}/values/'{TABX}'!A5:ZZ5")['values'][0]
m=call('GET',f'{API}/{SID}',params={'ranges':f"'{TABX}'!A6:{col(len(hdr)-1)}6",'fields':'sheets.data.rowData.values.userEnteredFormat.borders'})
vals=m['sheets'][0]['data'][0]['rowData'][0]['values']
THICK={'style':'SOLID_THICK','width':3,'color':{'red':0,'green':0,'blue':0}}
reqs=[]; moved=[]
for j,h in enumerate(hdr):
    b=vals[j].get('userEnteredFormat',{}).get('borders',{}) if j<len(vals) else {}
    if h.endswith(' Remark') and b.get('left',{}).get('style')=='SOLID_THICK':
        reqs.append({'updateBorders':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':nr,'startColumnIndex':j,'endColumnIndex':j+1},'left':{'style':'NONE'}}})
        reqs.append({'updateBorders':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':nr,'startColumnIndex':j+1,'endColumnIndex':j+2},'left':THICK}})
        moved.append(f'{col(j)}→{col(j+1)}')
if reqs: call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
print(TABX,'moved splitter',moved)
