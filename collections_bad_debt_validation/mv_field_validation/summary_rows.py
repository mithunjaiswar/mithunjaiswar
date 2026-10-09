exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
GREEN={'red':0.80,'green':0.92,'blue':0.80}; RED={'red':0.96,'green':0.80,'blue':0.80}
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets(properties,conditionalFormats)'})
sh=[s for s in meta['sheets'] if s['properties']['title']==TAB][0]; tid=sh['properties']['sheetId']; ncols=sh['properties']['gridProperties']['columnCount']
top=call('GET',f"{API}/{SID}/values/'{TAB}'!A1:A4")['values']
assert top[0][0]=='Match %' and top[3][0]=='Week', top   # run once only
# insert: 1 row on top (Status), 2 rows after 'Not Matched rows' (Issue, Action) -> borders copied from neighbours
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':[
 {'insertDimension':{'range':{'sheetId':tid,'dimension':'ROWS','startIndex':2,'endIndex':4},'inheritFromBefore':True}},
 {'insertDimension':{'range':{'sheetId':tid,'dimension':'ROWS','startIndex':0,'endIndex':1},'inheritFromBefore':False}}]})
hdr=call('GET',f"{API}/{SID}/values/'{TAB}'!A7:ZZ7")['values'][0]
fv=call('GET',f"{API}/{SID}/values/'MV_Field_Validation'!B5:G41")['values']
info={r[0]:(r[4] if len(r)>4 else '', r[5] if len(r)>5 else '') for r in fv}
r1=['']*len(hdr); r4=['']*len(hdr); r5=['']*len(hdr)
r1[0]='Match Status'; r1[1]='Green = 98%+ | Red = below 98%'; r4[0]='Issue'; r5[0]='Action Required'
fields=[h[:-len(' Matched?')] for h in hdr if h.endswith(' Matched?')]
for f in fields:
    j=hdr.index(f+' Matched?'); c=col(j); first=hdr.index(f+' (MV)')
    r1[j]=f'=IF({c}2="","",IF({c}2>=0.98,"Matched","Mismatched"))'
    why,fix=info.get(f,('Compared MV with Sheet only (not in validation doc)','—'))
    r4[first]=why if why!='—' else 'No issue'; r5[first]=fix if fix!='—' else 'No action'
jf=hdr.index('Final Status'); r1[jf]=f'=IF({col(jf)}2="","",IF({col(jf)}2>=0.98,"Matched","Mismatched"))'
call('POST',f'{API}/{SID}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':[
 {'range':f"'{TAB}'!A1",'values':[r1]},{'range':f"'{TAB}'!A4",'values':[r4,r5]}]})
reqs=[]
# replace my old Match % colour rules (now on row 2) – only rules whose formula I wrote
for i,r in sorted(enumerate(call('GET',f'{API}/{SID}',params={'fields':'sheets(properties.title,conditionalFormats)'})['sheets']),key=lambda x:0):
    pass
cfs=[s for s in call('GET',f'{API}/{SID}',params={'fields':'sheets(properties.title,conditionalFormats)'})['sheets'] if s['properties']['title']==TAB][0].get('conditionalFormats',[])
mine=[i for i,r in enumerate(cfs) if r['ranges'][0]['startRowIndex']<=1 and r['ranges'][0]['endRowIndex']<=2 and 'ISNUMBER' in str(r)]
reqs+=[{'deleteConditionalFormatRule':{'sheetId':tid,'index':i}} for i in sorted(mine,reverse=True)]
pr={'sheetId':tid,'startRowIndex':1,'endRowIndex':2,'startColumnIndex':2,'endColumnIndex':ncols}
sr={'sheetId':tid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':2,'endColumnIndex':ncols}
def rule(rg,f,colr): return {'addConditionalFormatRule':{'index':0,'rule':{'ranges':[rg],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':f}]},'format':{'backgroundColor':colr}}}}}
reqs+=[rule(pr,'=AND(ISNUMBER(C2),C2>=0.98)',GREEN),rule(pr,'=AND(ISNUMBER(C2),C2<0.98)',RED),
       rule(sr,'=C1="Matched"',GREEN),rule(sr,'=C1="Mismatched"',RED)]
# formats for my summary rows only (no border changes)
reqs+=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':1},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'horizontalAlignment':'CENTER','numberFormat':{'type':'TEXT'}}},'fields':'userEnteredFormat(textFormat,horizontalAlignment,numberFormat,backgroundColor)'}},
       {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':3,'endRowIndex':5},'cell':{'userEnteredFormat':{'textFormat':{'bold':False},'horizontalAlignment':'LEFT','numberFormat':{'type':'TEXT'},'wrapStrategy':'OVERFLOW_CELL','textFormat':{'italic':False}}},'fields':'userEnteredFormat(textFormat,horizontalAlignment,numberFormat,wrapStrategy,backgroundColor)'}},
       {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':5,'startColumnIndex':0,'endColumnIndex':1},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'horizontalAlignment':'LEFT'}},'fields':'userEnteredFormat(textFormat,horizontalAlignment)'}},
       {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':1,'endColumnIndex':2},'cell':{'userEnteredFormat':{'textFormat':{'bold':False},'horizontalAlignment':'LEFT','wrapStrategy':'OVERFLOW_CELL'}},'fields':'userEnteredFormat(textFormat,horizontalAlignment,wrapStrategy)'}},
       {'updateSheetProperties':{'properties':{'sheetId':tid,'gridProperties':{'frozenRowCount':7}},'fields':'gridProperties.frozenRowCount'}}]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
print(call('GET',f"{API}/{SID}/values/'{TAB}'!A1:Q7")['values'])
