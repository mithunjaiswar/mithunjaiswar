import json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS=open('../dash/dash_sid.txt').read().strip()
D=json.load(open('../dash/raw_final.json')); hdr=D[0]; R=D[1:]
TEXT={'partner_etm','city','location','product_type','revenue_type','fuel_type','eip_filter','elc_filter','active_inactive_flag','in_car_recovery','last_week_payment_habit','critical_risk_tag','recovery_recommended','mv_last_updated','hissab_week','last_payment_date_till_hissab_week','last_jama_date','alloc_date'}
def cv(h,v):
    if v=='' : return ''
    if h in TEXT: return v
    try:
        f=float(v); return int(f) if f.is_integer() else round(f,2)
    except: return v
R.sort(key=lambda r:(r[0],r[3],r[1]))
rows=[[cv(h,v) for h,v in zip(hdr,r)] for r in R]
m=call('GET',f'{API}/{DS}',params={'fields':'sheets.properties'})
P={s['properties']['title']:s['properties'] for s in m['sheets']}
print({t:p['sheetId'] for t,p in P.items()})
sid=P['Raw_Data']['sheetId']
n=len(rows)+1
call('POST',f'{API}/{DS}:batchUpdate',json={'requests':[
  {'updateCells':{'range':{'sheetId':sid},'fields':'userEnteredValue'}},
  {'updateSheetProperties':{'properties':{'sheetId':sid,'gridProperties':{'rowCount':n+10,'columnCount':len(hdr),'frozenRowCount':1}},'fields':'gridProperties(rowCount,columnCount,frozenRowCount)'}}]})
call('PUT',f"{API}/{DS}/values/'Raw_Data'!A1",params={'valueInputOption':'RAW'},json={'values':[hdr]})
B=5000
for i in range(0,len(rows),B):
    call('PUT',f"{API}/{DS}/values/'Raw_Data'!A{i+2}",params={'valueInputOption':'USER_ENTERED'},json={'values':rows[i:i+B]})
    print('rows',i+B, flush=True)
