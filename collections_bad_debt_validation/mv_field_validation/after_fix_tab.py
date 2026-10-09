exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
import sys
D=json.load(open(sys.argv[1]))
TN='MV_After_DAG_Fix'
hdr=['Hisaab week','MV refreshed','DAG version','Partners (for_collections)','last_jama_date future placeholder (should be 0)','next_join_date future placeholder (should be 0)','Active partners','hissab_week_active_days max (should be ≤ 7)','bad_debt_collected non-zero','…of which = whole week collection (should be low)','Cash blocked = 1','collection_pct filled','Avg collection_pct','total_os ≠ weekly_os + prev_cf (should be 0)','prev_carryforward_os positive (credit carried)']
rows=[['MV after admin DAG change – available weeks (for_collections = 1)'],['Green = admin fix visible, Red = still wrong. 21-Sep and 28-Sep are not rebuilt yet – sheet will be refreshed when they are back.'],[],hdr]
for r in D:
    new=r[1]>='2026-10-09'
    rows.append([r[0],r[1],'NEW DAG' if new else 'OLD DAG',*[int(x) if x not in ('NULL',None,'') and str(x).replace('.','',1).isdigit() and '.' not in str(x) else (float(x) if x not in ('NULL',None,'') else '') for x in r[2:]]])
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
P={s['properties']['title']:s['properties'] for s in meta['sheets']}
reqs=([{'deleteSheet':{'sheetId':P[TN]['sheetId']}}] if TN in P else [])+[{'addSheet':{'properties':{'title':TN,'index':0,'gridProperties':{'rowCount':len(rows)+15,'columnCount':len(hdr),'frozenRowCount':4,'frozenColumnCount':1}}}}]
tid=call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT',f"{API}/{SID}/values/'{TN}'!A1",params={'valueInputOption':'USER_ENTERED'},json={'values':rows})
G={'red':0.80,'green':0.92,'blue':0.80}; R={'red':0.96,'green':0.80,'blue':0.80}; HB={'red':0.85,'green':0.9,'blue':0.97}
L=len(rows)
def cf(c,formula,colr): return {'addConditionalFormatRule':{'index':0,'rule':{'ranges':[{'sheetId':tid,'startRowIndex':4,'endRowIndex':L,'startColumnIndex':c,'endColumnIndex':c+1}],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':formula}]},'format':{'backgroundColor':colr}}}}}
reqs=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':1},'cell':{'userEnteredFormat':{'textFormat':{'bold':True,'fontSize':13}}},'fields':'userEnteredFormat.textFormat'}},
 {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':3,'endRowIndex':4},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'wrapStrategy':'WRAP','backgroundColor':HB,'verticalAlignment':'MIDDLE','horizontalAlignment':'CENTER'}},'fields':'userEnteredFormat(textFormat,wrapStrategy,backgroundColor,verticalAlignment,horizontalAlignment)'}},
 {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':4,'endRowIndex':L,'startColumnIndex':1},'cell':{'userEnteredFormat':{'horizontalAlignment':'CENTER'}},'fields':'userEnteredFormat.horizontalAlignment'}},
 {'updateDimensionProperties':{'range':{'sheetId':tid,'dimension':'ROWS','startIndex':3,'endIndex':4},'properties':{'pixelSize':80},'fields':'pixelSize'}},
 {'updateDimensionProperties':{'range':{'sheetId':tid,'dimension':'COLUMNS','startIndex':0,'endIndex':len(hdr)},'properties':{'pixelSize':125},'fields':'pixelSize'}},
 cf(2,'=$C5="NEW DAG"',G),cf(2,'=$C5="OLD DAG"',R),
 cf(4,'=E5=0',G),cf(4,'=E5>0',R),cf(5,'=F5=0',G),cf(5,'=F5>0',R),
 cf(7,'=H5<=7',G),cf(7,'=H5>7',R),cf(9,'=J5<I5*0.5',G),cf(9,'=J5>=I5*0.5',R),
 cf(11,'=L5=D5',G),cf(11,'=L5<D5',R),cf(13,'=M5=0',G),cf(13,'=M5>0',R),cf(14,'=O5>0',G),cf(14,'=O5=0',R)]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
print('ok',L-4)
