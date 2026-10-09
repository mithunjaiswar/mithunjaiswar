exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
GREEN={'red':0.80,'green':0.92,'blue':0.80}; RED={'red':0.96,'green':0.80,'blue':0.80}
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets(properties,conditionalFormats,merges)'})
sh=[s for s in meta['sheets'] if s['properties']['title']==TAB][0]; tid=sh['properties']['sheetId']; ncols=sh['properties']['gridProperties']['columnCount']
A=[r[0] if r else '' for r in call('GET',f"{API}/{SID}/values/'{TAB}'!A1:A7")['values']]
assert A[2]=='Match Status' and A[6]=='Week', A
hdr=call('GET',f"{API}/{SID}/values/'{TAB}'!A7:ZZ7")['values'][0]
nrow=len(call('GET',f"{API}/{SID}/values/'{TAB}'!C8:C20000")['values']); last=7+nrow
starts=[i for i,h in enumerate(hdr) if h.endswith(' (MV)')]
mcols=[i for i,h in enumerate(hdr) if h.endswith(' Matched?') or h=='Final Status']
# 1) unmerge rows 1-2, write status/%/count into rows 1-3 of each Matched? column
reqs=[{'unmergeCells':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':2,'startColumnIndex':0,'endColumnIndex':ncols}}}]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
data=[{'range':f"'{TAB}'!A1:B3",'values':[['Issue  |  Match Status →','Green = 98%+ | Red = below 98%'],['Action Required  |  Match % →',''],['Not Matched rows →','']]}]
for j in mcols:
    c=col(j); rng=f'{c}8:{c}{last}'
    data.append({'range':f"'{TAB}'!{c}1:{c}3",'values':[[f'=IF({c}2="","",IF({c}2>=0.98,"Matched","Mismatched"))'],
        [f'=IFERROR(COUNTIF({rng},"Matched")/(COUNTIF({rng},"Matched")+COUNTIF({rng},"Not Matched")),"")'],[f'=COUNTIF({rng},"Not Matched")']]})
call('POST',f'{API}/{SID}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data})
# 2) delete old rows 4-5 (old % / count)
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':[{'deleteDimension':{'range':{'sheetId':tid,'dimension':'ROWS','startIndex':3,'endIndex':5}}}]})
# 3) merge Issue / Action text across MV..Manual columns of each field, formats, colours
reqs=[]
for s in starts:
    f=hdr[s][:-5]; e=hdr.index(f+' Matched?')
    for r in (0,1): reqs.append({'mergeCells':{'range':{'sheetId':tid,'startRowIndex':r,'endRowIndex':r+1,'startColumnIndex':s,'endColumnIndex':e},'mergeType':'MERGE_ALL'}})
for j in mcols:
    reqs.append({'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':3,'startColumnIndex':j,'endColumnIndex':j+1},'cell':{'userEnteredFormat':{'horizontalAlignment':'CENTER','verticalAlignment':'MIDDLE','textFormat':{'bold':True},'wrapStrategy':'CLIP'}},'fields':'userEnteredFormat(horizontalAlignment,verticalAlignment,textFormat,wrapStrategy)'}})
    reqs.append({'repeatCell':{'range':{'sheetId':tid,'startRowIndex':1,'endRowIndex':2,'startColumnIndex':j,'endColumnIndex':j+1},'cell':{'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.0%'}}},'fields':'userEnteredFormat.numberFormat'}})
    reqs.append({'repeatCell':{'range':{'sheetId':tid,'startRowIndex':2,'endRowIndex':3,'startColumnIndex':j,'endColumnIndex':j+1},'cell':{'userEnteredFormat':{'numberFormat':{'type':'NUMBER','pattern':'#,##0'}}},'fields':'userEnteredFormat.numberFormat'}})
reqs.append({'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':3,'startColumnIndex':0,'endColumnIndex':1},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'wrapStrategy':'WRAP','verticalAlignment':'MIDDLE'}},'fields':'userEnteredFormat(textFormat,wrapStrategy,verticalAlignment)'}})
reqs.append({'updateSheetProperties':{'properties':{'sheetId':tid,'gridProperties':{'frozenRowCount':5}},'fields':'gridProperties.frozenRowCount'}})
cfs=call('GET',f'{API}/{SID}',params={'fields':'sheets(properties.title,conditionalFormats)'})['sheets']
cfs=[s for s in cfs if s['properties']['title']==TAB][0].get('conditionalFormats',[])
mine=[i for i,r in enumerate(cfs) if r['ranges'][0]['startRowIndex']<=4 and r['ranges'][0]['endRowIndex']-r['ranges'][0]['startRowIndex']==1]
reqs=[{'deleteConditionalFormatRule':{'sheetId':tid,'index':i}} for i in sorted(mine,reverse=True)]+reqs
def rule(r,f,c): return {'addConditionalFormatRule':{'index':0,'rule':{'ranges':[{'sheetId':tid,'startRowIndex':r,'endRowIndex':r+1,'startColumnIndex':2,'endColumnIndex':ncols}],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':f}]},'format':{'backgroundColor':c}}}}}
reqs+=[rule(0,'=C1="Matched"',GREEN),rule(0,'=C1="Mismatched"',RED),rule(1,'=AND(ISNUMBER(C2),C2>=0.98)',GREEN),rule(1,'=AND(ISNUMBER(C2),C2<0.98)',RED)]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
# 4) point MV_Field_Validation Match % to new row 2
fv=call('GET',f"{API}/{SID}/values/'MV_Field_Validation'!B5:B41")['values']
hdr2=call('GET',f"{API}/{SID}/values/'{TAB}'!A5:ZZ5")['values'][0]
call('PUT',f"{API}/{SID}/values/'MV_Field_Validation'!D5",params={'valueInputOption':'USER_ENTERED'},json={'values':[[f"='{TAB}'!{col(hdr2.index(r[0]+' Matched?'))}2"] for r in fv]})
for r in call('GET',f"{API}/{SID}/values/'{TAB}'!A1:H5")['values']: print([x[:45] for x in r])
print(call('GET',f"{API}/{SID}/values/'MV_Field_Validation'!B2:E7")['values'])
print(call('GET',f"{API}/{SID}/values/'{TAB}'!G6",params={'valueRenderOption':'FORMULA'})['values'][0][0][:80])
