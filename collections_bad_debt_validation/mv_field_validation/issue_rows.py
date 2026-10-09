exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
T=pickle.load(open('issue_text.pkl','rb'))
GREEN={'red':0.80,'green':0.92,'blue':0.80}; RED={'red':0.96,'green':0.80,'blue':0.80}
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets(properties,conditionalFormats,merges)'})
sh=[s for s in meta['sheets'] if s['properties']['title']==TAB][0]; tid=sh['properties']['sheetId']; ncols=sh['properties']['gridProperties']['columnCount']
A=[r[0] if r else '' for r in call('GET',f"{API}/{SID}/values/'{TAB}'!A1:A5")['values']]
if A[0]=='Match Status':   # move Issue/Action (rows 4-5) to top
    call('POST',f'{API}/{SID}:batchUpdate',json={'requests':[{'moveDimension':{'source':{'sheetId':tid,'dimension':'ROWS','startIndex':3,'endIndex':5},'destinationIndex':0}}]})
A=[r[0] if r else '' for r in call('GET',f"{API}/{SID}/values/'{TAB}'!A1:A5",params={'valueRenderOption':'FORMULA'})['values']]
print(A); assert A[0]=='Issue' and A[2]=='Match Status' and A[3]=='Match %'
hdr=call('GET',f"{API}/{SID}/values/'{TAB}'!A7:ZZ7")['values'][0]
starts=[i for i,h in enumerate(hdr) if h.endswith(' (MV)')]+[hdr.index('Final Status')]
r1=['']*len(hdr); r2=['']*len(hdr)
r1[0]='Issue (what is wrong + example)'; r2[0]='Action Required (what to correct)'
for k,s in enumerate(starts[:-1]):
    f=hdr[s][:-5]; st=col(hdr.index(f+' Matched?'))+'3'
    if f in T: r1[s],r2[s]=T[f]
    else:
        r1[s]=f'=IF({st}="Matched","No issue – all rows match.","MV differs from the Sheet value for some rows (field not in validation doc).")'
        r2[s]=f'=IF({st}="Matched","No action needed.","Compare MV with Sheet for the Not Matched rows.")'
call('POST',f"{API}/{SID}/values/'{TAB}'!A1:{col(ncols-1)}2:clear",json={})
call('PUT',f"{API}/{SID}/values/'{TAB}'!A1",params={'valueInputOption':'USER_ENTERED'},json={'values':[r1,r2]})
reqs=[]
# merge each field group in rows 1-2 (borders on the left edge stay)
for a,b in zip(starts[:-1],starts[1:]):
    reqs.append({'mergeCells':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':a,'endColumnIndex':b},'mergeType':'MERGE_ALL'}})
    reqs.append({'mergeCells':{'range':{'sheetId':tid,'startRowIndex':1,'endRowIndex':2,'startColumnIndex':a,'endColumnIndex':b},'mergeType':'MERGE_ALL'}})
reqs+=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':2,'startColumnIndex':3},'cell':{'userEnteredFormat':{'wrapStrategy':'WRAP','horizontalAlignment':'LEFT','verticalAlignment':'TOP','textFormat':{'bold':False},'numberFormat':{'type':'TEXT'}}},'fields':'userEnteredFormat(wrapStrategy,horizontalAlignment,verticalAlignment,textFormat,numberFormat)'}},
       {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':2,'startColumnIndex':0,'endColumnIndex':3},'cell':{'userEnteredFormat':{'wrapStrategy':'WRAP','verticalAlignment':'TOP','textFormat':{'bold':True}}},'fields':'userEnteredFormat(wrapStrategy,verticalAlignment,textFormat)'}},
       {'updateDimensionProperties':{'range':{'sheetId':tid,'dimension':'ROWS','startIndex':0,'endIndex':1},'properties':{'pixelSize':95},'fields':'pixelSize'}},
       {'updateDimensionProperties':{'range':{'sheetId':tid,'dimension':'ROWS','startIndex':1,'endIndex':2},'properties':{'pixelSize':55},'fields':'pixelSize'}}]
# re-create my green/red rules for Match Status (row 3) and Match % (row 4)
cfs=sh.get('conditionalFormats',[])
mine=[i for i,r in enumerate(cfs) if r['ranges'][0]['endRowIndex']-r['ranges'][0]['startRowIndex']==1 and r['ranges'][0]['startRowIndex']<=5]
reqs=[{'deleteConditionalFormatRule':{'sheetId':tid,'index':i}} for i in sorted(mine,reverse=True)]+reqs
srow={'sheetId':tid,'startRowIndex':2,'endRowIndex':3,'startColumnIndex':2,'endColumnIndex':ncols}
prow={'sheetId':tid,'startRowIndex':3,'endRowIndex':4,'startColumnIndex':2,'endColumnIndex':ncols}
def rule(rg,f,c): return {'addConditionalFormatRule':{'index':0,'rule':{'ranges':[rg],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':f}]},'format':{'backgroundColor':c}}}}}
reqs+=[rule(srow,'=C3="Matched"',GREEN),rule(srow,'=C3="Mismatched"',RED),rule(prow,'=AND(ISNUMBER(C4),C4>=0.98)',GREEN),rule(prow,'=AND(ISNUMBER(C4),C4<0.98)',RED)]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
v=call('GET',f"{API}/{SID}/values/'{TAB}'!A1:L7")['values']
for r in v: print(r[:12])
print(call('GET',f"{API}/{SID}/values/'{TAB}'!G3:G4",params={'valueRenderOption':'FORMULA'})['values'])
print(call('GET',f"{API}/{SID}/values/'MV_Field_Validation'!D5:E6",params={'valueRenderOption':'FORMULA'})['values'], call('GET',f"{API}/{SID}/values/'MV_Field_Validation'!B2:B3")['values'])
