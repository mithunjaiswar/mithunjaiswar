import json, requests, time, pickle, math
import pandas as pd, numpy as np
TOKEN='/home/user/mithunjaiswar/google-workspace-access/token.json'
SID='1Vn58kq_-i8ywbaT_zBx8P7fgahqxKeoNX_RD6o8Vjfo'; TAB='MV_Raw_Data_Manual_Check'
API='https://sheets.googleapis.com/v4/spreadsheets'
tok=json.load(open(TOKEN))
r=requests.post(tok['token_uri'],data=dict(client_id=tok['client_id'],client_secret=tok['client_secret'],refresh_token=tok['refresh_token'],grant_type='refresh_token'),timeout=60)
H={'Authorization':'Bearer '+r.json()['access_token']}
def call(method,url,**kw):
    for i in range(6):
        x=requests.request(method,url,headers=H,timeout=300,**kw)
        if x.status_code in (429,500,502,503): time.sleep(2**i*2); continue
        if not x.ok: raise SystemExit(f'{x.status_code}: {x.text[:400]}')
        return x.json()
def col(i):
    s='';i+=1
    while i: i,rr=divmod(i-1,26); s=chr(65+rr)+s
    return s
MAN,REM=pickle.load(open('manual_out.pkl','rb'))
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
sid=[s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title']==TAB][0]
hdr=call('GET',f"{API}/{SID}/values/'{TAB}'!A4:ZZ4")['values'][0]
# 1) insert one Remark column after each '<field> Matched?' (only if not already present)
idx=[(hdr.index(f'{f} Matched?'),f) for f in MAN if f'{f} Remark' not in hdr]
reqs=[{'insertDimension':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':i+1,'endIndex':i+2},'inheritFromBefore':False}} for i,f in sorted(idx,reverse=True)]
if reqs: call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs}); print('inserted',len(reqs))
hdr=call('GET',f"{API}/{SID}/values/'{TAB}'!A4:ZZ4")['values'][0]
nrows=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
emp=call('GET',f"{API}/{SID}/values/'{TAB}'!C5:C20000")['values']
emp=[e[0] if e else '' for e in emp]; n=len(emp); print('rows',n)
# 2) clear any formatting the new Remark columns inherited (new columns only)
fmt=[]
for f in MAN:
    j=hdr.index(f'{f} Matched?')+1
    assert hdr[j] in ('',f'{f} Remark'), (f,hdr[j])
    fmt.append({'repeatCell':{'range':{'sheetId':sid,'startRowIndex':0,'endRowIndex':4+n,'startColumnIndex':j,'endColumnIndex':j+1},'cell':{'userEnteredFormat':{}},'fields':'userEnteredFormat'}})
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':fmt})
def cell(v):
    if v is None: return ''
    if isinstance(v,(float,np.floating)):
        if math.isnan(v): return ''
        return int(v) if float(v).is_integer() else round(float(v),2)
    if isinstance(v,(np.integer,)): return int(v)
    return str(v)
data=[]
for f in MAN:
    jm=hdr.index(f'{f} (Manual)'); jr=hdr.index(f'{f} Matched?')+1
    man=MAN[f]; rem=REM[f]
    pass
    data.append({'range':f"'{TAB}'!{col(jr)}4:{col(jr)}{4+n}",'values':[[f'{f} Remark']]+[[str(rem.get(e,''))] for e in emp]})
for i in range(0,len(data),8):
    call('POST',f'{API}/{SID}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data[i:i+8]})
    print('written',i+8)
print('done')
