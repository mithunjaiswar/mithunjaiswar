exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
V2='MV_Raw_Data_Manual_Check_v2'
MAN,REM=pickle.load(open('manual_out_v2.pkl','rb'))
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
P={s['properties']['title']:s['properties'] for s in meta['sheets']}
if V2 not in P:
    r=call('POST',f'{API}/{SID}:batchUpdate',json={'requests':[{'duplicateSheet':{'sourceSheetId':P[TAB]['sheetId'],'insertSheetIndex':P[TAB]['index']+1,'newSheetName':V2}}]})
    print('duplicated')
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
tid=[s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title']==V2][0]
hdr=call('GET',f"{API}/{SID}/values/'{V2}'!A5:ZZ5")['values'][0]
emp=[e[0] if e else '' for e in call('GET',f"{API}/{SID}/values/'{V2}'!C6:C20000")['values']]; n=len(emp); last=5+n
CHANGED=['prev_carryforward_os','week_start_deposit','week_end_deposit','last_week_payment_habit','tenure_days','last_week_nd_count','current_week_nd_count','hissab_week_active_days','next_join_date','bad_debt_collected','active_fleet_cash_blocked','previous_week_collection']
def cell(v):
    if v is None: return ''
    if isinstance(v,(float,np.floating)):
        if math.isnan(v): return ''
        return int(v) if float(v).is_integer() else round(float(v),2)
    if isinstance(v,np.integer): return int(v)
    return str(v)
data=[]
for f in CHANGED:
    jm=hdr.index(f+' (Manual)'); jr=hdr.index(f+' Remark')
    data.append({'range':f"'{V2}'!{col(jm)}6:{col(jm)}{last}",'values':[[cell(MAN[f].get(e))] for e in emp]})
    data.append({'range':f"'{V2}'!{col(jr)}6:{col(jr)}{last}",'values':[[str(REM[f].get(e,''))] for e in emp]})
# tenure: accept MV - Manual between 0 and 7 days
j=hdr.index('tenure_days Matched?'); mv_,sh,mn=col(j-3),col(j-2),col(j-1)
fm=[]
for k in range(n):
    rn=6+k; ref=f'IF({mn}{rn}<>"",{mn}{rn},{sh}{rn})'
    fm.append([f'=IF({ref}="","",IF(AND(ISNUMBER({ref}),N({mv_}{rn})-{ref}>=-1,N({mv_}{rn})-{ref}<=7),"Matched","Not Matched"))'])
data.append({'range':f"'{V2}'!{col(j)}6:{col(j)}{last}",'values':fm})
for i in range(0,len(data),6):
    call('POST',f'{API}/{SID}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data[i:i+6]}); print('w',i)
print('v2 written', n)
