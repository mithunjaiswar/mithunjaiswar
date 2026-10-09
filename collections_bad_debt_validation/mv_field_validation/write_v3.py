exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
V2='MV_Raw_Data_Manual_Check_v2'
MAN,REM=pickle.load(open('manual_out_v3.pkl','rb'))
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
tid=[s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title']==V2][0]
hdr=call('GET',f"{API}/{SID}/values/'{V2}'!A5:ZZ5")['values'][0]
emp=[e[0] if e else '' for e in call('GET',f"{API}/{SID}/values/'{V2}'!C6:C20000")['values']]; n=len(emp); last=5+n
def cell(v):
    if v is None: return ''
    if isinstance(v,(float,np.floating)):
        if math.isnan(v): return ''
        return int(v) if float(v).is_integer() else round(float(v),2)
    if isinstance(v,np.integer): return int(v)
    return str(v)
data=[]
for f in ['weekly_os','prev_carryforward_os','last_jama_date','week_start_deposit','week_end_deposit','active_fleet_cash_blocked','previous_week_collection']:
    jm=hdr.index(f+' (Manual)'); jr=hdr.index(f+' Remark')
    if f!='previous_week_collection': data.append({'range':f"'{V2}'!{col(jm)}6:{col(jm)}{last}",'values':[[cell(MAN[f].get(e))] for e in emp]})
    data.append({'range':f"'{V2}'!{col(jr)}6:{col(jr)}{last}",'values':[[str(REM[f].get(e,''))] for e in emp]})
# last_jama_date: "(blank)" means expected empty
j=hdr.index('last_jama_date Matched?'); mvc,sh,mn=col(j-3),col(j-2),col(j-1)
data.append({'range':f"'{V2}'!{col(j)}6:{col(j)}{last}",'values':[[f'=IF({mn}{r}="(blank)",IF({mvc}{r}="","Matched","Not Matched"),IF(LOWER(TRIM(TO_TEXT({mvc}{r})))=LOWER(TRIM(TO_TEXT({mn}{r}))),"Matched","Not Matched"))'] for r in range(6,last+1)]})
# previous_week_collection: mark not required, clear its Matched? so it is not counted
j=hdr.index('previous_week_collection Matched?')
data.append({'range':f"'{V2}'!{col(j)}6:{col(j)}{last}",'values':[['Not required']]*n})
data.append({'range':f"'{V2}'!{col(hdr.index('previous_week_collection (MV)'))}5",'values':[['previous_week_collection (MV) – NOT REQUIRED']]})
for i in range(0,len(data),5):
    call('POST',f'{API}/{SID}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data[i:i+5]}); print('w',i)
# add collection_pct column right after previous_week_collection Remark (only once)
hdr=call('GET',f"{API}/{SID}/values/'{V2}'!A5:ZZ5")['values'][0]
if 'collection_pct (new)' not in hdr:
    jr=hdr.index('previous_week_collection Remark')
    call('POST',f'{API}/{SID}:batchUpdate',json={'requests':[{'insertDimension':{'range':{'sheetId':tid,'dimension':'COLUMNS','startIndex':jr+1,'endIndex':jr+2},'inheritFromBefore':True}}]})
    hdr=call('GET',f"{API}/{SID}/values/'{V2}'!A5:ZZ5")['values'][0]
jc=hdr.index('previous_week_collection Remark')+1
tos=col(hdr.index('total_os (MV)')); tc=col(hdr.index('total_collected_amount_in_week (MV)'))
vals=[['Collection % = total_collected_amount_in_week ÷ amount due (−total_os). NEW column replacing previous_week_collection'],['Formula column – no MV field yet'],[f'=IFERROR(COUNTIF({col(jc)}6:{col(jc)}{last},">=1")/COUNTA({col(jc)}6:{col(jc)}{last}),"")'],[''],['collection_pct (new)']]
vals+=[[f'=IF(N({tos}{r})<0,N({tc}{r})/-N({tos}{r}),"")'] for r in range(6,last+1)]
call('PUT',f"{API}/{SID}/values/'{V2}'!{col(jc)}1",params={'valueInputOption':'USER_ENTERED'},json={'values':vals})
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':[
 {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':5,'endRowIndex':last,'startColumnIndex':jc,'endColumnIndex':jc+1},'cell':{'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.0%'},'backgroundColor':{'red':1,'green':1,'blue':1}}},'fields':'userEnteredFormat(numberFormat,backgroundColor)'}},
 {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':5,'startColumnIndex':jc,'endColumnIndex':jc+1},'cell':{'userEnteredFormat':{'wrapStrategy':'WRAP','textFormat':{'bold':True},'backgroundColor':{'red':1,'green':0.95,'blue':0.8}}},'fields':'userEnteredFormat(wrapStrategy,textFormat,backgroundColor)'}},
 {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':2,'endRowIndex':3,'startColumnIndex':jc,'endColumnIndex':jc+1},'cell':{'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.0%'}}},'fields':'userEnteredFormat.numberFormat'}},
 {'updateDimensionProperties':{'range':{'sheetId':tid,'dimension':'COLUMNS','startIndex':jc,'endIndex':jc+1},'properties':{'pixelSize':140},'fields':'pixelSize'}}]})
print('collection_pct at', col(jc))
