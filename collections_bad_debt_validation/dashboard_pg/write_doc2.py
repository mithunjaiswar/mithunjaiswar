import json,re,time,requests,os
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
exec(open('doc_catalog.py').read()); exec(open('doc_detail.py').read()); exec(open('doc_logic.py').read())
DS=open('../dash/dash_sid.txt').read().strip()
REF='1wkebsPPLwXnRYAuvRV_fhMGQLRxv6JwH-cYlaIEBjRw'
SR=call('GET',f"{API}/{REF}/values/'Summary'!A1:J86")['values']
call('POST',f'{API}/{DS}/values:batchUpdate',json={'valueInputOption':'RAW','data':[{'range':"'Summary'!B2",'values':[['Delhi NCR']]},{'range':"'Summary'!B5",'values':[['*']]}]})
time.sleep(20)
SN=call('GET',f"{API}/{DS}/values/'Summary'!A1:J86")['values']
call('POST',f'{API}/{DS}/values:batchUpdate',json={'valueInputOption':'RAW','data':[{'range':"'Summary'!B2",'values':[['*']]}]})
WR=call('GET',f"{API}/{REF}/values/'WBR View'!A1:H486")['values']
WN=call('GET',f"{API}/{DS}/values/'WBR'!A1:H486")['values']
print('weeks', SR[7][6:10], SN[7][6:10], WR[5][2:6], WN[5][2:6])
DD=json.load(open('../dash/doc_data.json')); FM=DD['field_match']; N14=DD['n14']
def num(s):
    s=str(s).replace(',','').replace(' hrs','').replace(' ','')
    m_=re.fullmatch(r'(-?[\d.]+)(K|%)?',s)
    if not m_: return None
    v=float(m_.group(1)); return v*1000 if m_.group(2)=='K' else (v/100 if m_.group(2)=='%' else v)
g=lambda R,i,j: (R[i][j] if i<len(R) and j<len(R[i]) else '')
def cmp(src,row):
    A,B,cols=(SR,SN,range(6,10)) if src=='S' else (WR,WN,range(2,6))
    i=row-1; pc=any('%' in g(A,i,j) for j in cols)
    so=sm=0; ok=c=0; seen=False
    for j in cols:
        a,b=g(A,i,j),g(B,i,j); x,y=num(a),num(b); c+=1
        if x is None or y is None: ok+=(str(a).strip()==str(b).strip()); continue
        seen=True; so+=x; sm+=y
        tol=max(abs(x)*0.02,0.0015 if pc else (1 if abs(x)>=20 else 0)); ok+=abs(y-x)<=tol+1e-9
    if not seen: return ('','','','',f'{ok}/{c}',pc,ok<c)
    if pc: so/=c; sm/=c
    d=sm-so; dp=(d/abs(so)) if so else ('' if d==0 else 'n/a (Sheet 0)')
    return (so,sm,d,dp,f'{ok}/{c}',pc,ok<c)
EXP={'S11':[19,20,21,22,23],'S17':[29,30,31],'S19':[33,34,35,36,37,38,39],'S21':[41,42],'S22':[43,44,45],'S24':[47,48],'S25':[49,50],
     'S33':[58,59,60,61],'S36':[64,65,66,67,68,69],'S37':[70,71,72,73,74],'S38':[75,76,77,78,79,80],'S39':[81,82,83,84,85,86],
     'W07':[86,97,108],'W08':[121,132,154],'W09':[165,187],'W10':[176,198],'W11':[211,222],'W12':[235,246],'W13':[259,270],'W14':[283,294,305],
     'W16':[329,340,352,363,375,386,398,409,421,432,444,455,467,478]}
FIELD={'S02':'total_collected_100_pct','S03':'total_os','S04':'total_collected_100_pct','S10':'total_collected_amount_in_week','S12':'total_os','S13':'total_collected_amount_in_week',
 'S14':'partners_not_paid_2_weeks','S15':'collection_till_wed','S17':'total_allocated_days','S21':'bad_debt_amount','S22':'bad_debt_amount','S23':'bad_debt_collected',
 'S26':'week_start_deposit','S37':'last_week_payment_habit','S38':'week_start_deposit','W02':'total_os','W03':'total_collected_100_pct','W04':'total_collected_100_pct',
 'W08':'bad_debt_amount','W10':'bad_debt_collected','W11':'prev_carryforward_os','W12':'total_allocated_days','W15':'total_os','W16':'total_os'}
INMV={OK:'Yes',BAD:'Yes - data incorrect',LOGIC:'Yes - logic to confirm',ADD:'No - added via join',DER:'Derived from MV columns',BIZ:'N/A (business input)',NOSRC:'No'}
def name_w(r):
    t=r-1
    while t>0 and not (g(WR,t,2)=='*' and g(WR,t,1) not in ('*','')): t-=1
    return g(WR,t,1)
sec={'S':[],'W':[]}
for (iid,met,req,what,rc,src,st,calc,flt,jn,corr,ref) in C:
    subs=EXP.get(iid,[ref[1]])
    fm=FM.get(FIELD.get(iid,''),('',''))
    rec=f"{100-float(fm[0][:-1]):.1f}% ({fm[1]} of {N14:,} rows)" if fm[0].endswith('%') else ''
    reason,ex=DET.get(iid,(corr,''))
    mlog=ML.get(iid,calc); j=JO.get(iid,jn); s_=SRC.get(iid,src)
    for k,r in enumerate(subs):
        so,sm,d,dp,wm,pc,bad=cmp(ref[0],r)
        name=(g(SR,r-1,1).strip() if ref[0]=='S' else name_w(r)) if len(subs)>1 else met
        first=k==0
        sec[ref[0]].append([name,st,INMV[st],rc,s_,SL.get(iid,'') if first else '',mlog if first else '',j if first else '',
                            so,sm,d,dp,wm,'Delhi NCR / all products, Sep-14..Oct-05' if ref[0]=='S' else 'All India, Sep-14..Oct-05',
                            rec,reason if first else '',ex if first else '',pc,first,bad])
sql=open('/home/user/mithunjaiswar/collections_bad_debt_validation/dashboard_pg/final_raw_data.sql').read()
docf='../dash/sql_doc_id.txt'
if os.path.exists(docf):
    did=open(docf).read().strip()
    x=requests.patch(f'https://www.googleapis.com/upload/drive/v3/files/{did}?uploadType=media',headers={**H,'Content-Type':'text/plain'},data=sql.encode(),timeout=120)
else:
    bd='xxBOUNDARYxx'; meta={'name':'Collections Dashboard - Final Raw_Data SQL (Summary + WBR)','mimeType':'application/vnd.google-apps.document'}
    body=(f'--{bd}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n--{bd}\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n{sql}\r\n--{bd}--').encode()
    x=requests.post('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',headers={**H,'Content-Type':f'multipart/related; boundary={bd}'},data=body,timeout=120)
    if x.ok: open(docf,'w').write(x.json()['id'])
if not x.ok: raise SystemExit(x.text[:300])
did=open(docf).read().strip(); DOC=f'https://docs.google.com/document/d/{did}/edit'
print('doc',DOC)
HDR=['Metric','MV Status','Available in MV?','Raw_Data column','Source table.column','Logic (Sheet)','Logic (MV / final query)','Joins (key + condition)',
     'Sheet value','MV value','Difference (MV - Sheet)','Difference %','Weeks matched','Compared on','Incorrect % (record level, 14-Sep MV vs source)',
     'Mismatch reason (detail) + Correction required','Example (partner / week: Sheet vs MV)']
V=[['SECTION 1 - SUMMARY  (metrics of the Summary tab)'],HDR]+[r[:17] for r in sec['S']]+[[],
   ['SECTION 2 - WBR  (metrics of the WBR tab)'],HDR]+[r[:17] for r in sec['W']]+[[],
   ['SECTION 3 - FINAL QUERY'],['Google Doc (full SQL that populates Raw_Data):',DOC],
   ['Repo file:','collections_bad_debt_validation/dashboard_pg/final_raw_data.sql'],
   ['Automation:','Run weekly after MV refresh and overwrite Raw_Data!A:BG (Airflow / Connected Sheets / Apps Script). Summary, WBR and City_Targets recalculate automatically.']]
m=call('GET',f'{API}/{DS}',params={'fields':'sheets.properties'})
P={s['properties']['title']:s['properties']['sheetId'] for s in m['sheets']}
req=[]
if 'Metric_Summary' in P: req.append({'deleteSheet':{'sheetId':P['Metric_Summary']}})
req.append({'addSheet':{'properties':{'title':'Metric_Summary','index':0,'gridProperties':{'rowCount':len(V)+5,'columnCount':17,'frozenRowCount':2,'frozenColumnCount':1}}}})
sid=call('POST',f'{API}/{DS}:batchUpdate',json={'requests':req})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT',f"{API}/{DS}/values/'Metric_Summary'!A1",params={'valueInputOption':'USER_ENTERED'},json={'values':[[('' if x is None else x) for x in r] for r in V]})
def rng(r0,r1,c0,c1): return {'sheetId':sid,'startRowIndex':r0,'endRowIndex':r1,'startColumnIndex':c0,'endColumnIndex':c1}
def fmt(r0,r1,c0,c1,f,fields): return {'repeatCell':{'range':rng(r0,r1,c0,c1),'cell':{'userEnteredFormat':f},'fields':fields}}
DK={'red':0.2,'green':0.25,'blue':0.4}; WH={'red':1,'green':1,'blue':1}; YL={'red':1,'green':0.95,'blue':0.75}; RED={'red':0.85,'green':0,'blue':0}
CL={OK:{'red':0.78,'green':0.92,'blue':0.79},BAD:{'red':0.96,'green':0.74,'blue':0.74},LOGIC:{'red':1,'green':0.85,'blue':0.6},ADD:{'red':0.8,'green':0.87,'blue':0.98},DER:{'red':0.9,'green':0.9,'blue':0.9},BIZ:{'red':0.9,'green':0.9,'blue':0.9},NOSRC:{'red':0.9,'green':0.9,'blue':0.9}}
R=[fmt(0,len(V),0,17,{'wrapStrategy':'WRAP','verticalAlignment':'TOP','textFormat':{'fontSize':9}},'userEnteredFormat(wrapStrategy,verticalAlignment,textFormat)')]
s1=0; s2=2+len(sec['S'])+1; s3=s2+2+len(sec['W'])+1
nred=0
for st_,rows_ in ((s1,sec['S']),(s2,sec['W'])):
    R.append(fmt(st_,st_+1,0,17,{'backgroundColor':YL,'textFormat':{'bold':True,'fontSize':12},'wrapStrategy':'OVERFLOW_CELL'},'userEnteredFormat(backgroundColor,textFormat,wrapStrategy)'))
    R.append(fmt(st_+1,st_+2,0,17,{'backgroundColor':DK,'textFormat':{'bold':True,'foregroundColor':WH,'fontSize':9},'wrapStrategy':'WRAP','verticalAlignment':'MIDDLE'},'userEnteredFormat(backgroundColor,textFormat,wrapStrategy,verticalAlignment)'))
    for k,r in enumerate(rows_):
        rr=st_+2+k; pc=r[17]
        R.append(fmt(rr,rr+1,1,2,{'backgroundColor':CL.get(r[1],WH),'textFormat':{'bold':True,'fontSize':9}},'userEnteredFormat(backgroundColor,textFormat)'))
        R.append(fmt(rr,rr+1,8,11,{'numberFormat':{'type':'NUMBER','pattern':'0.0%' if pc else '#,##0'}},'userEnteredFormat.numberFormat'))
        R.append(fmt(rr,rr+1,11,12,{'numberFormat':{'type':'NUMBER','pattern':'0.0%'}},'userEnteredFormat.numberFormat'))
        if r[19]:
            nred+=1
            R.append(fmt(rr,rr+1,10,12,{'textFormat':{'foregroundColor':RED,'bold':True,'fontSize':9}},'userEnteredFormat.textFormat'))
        if r[18]: R.append({'updateBorders':{'range':rng(rr,rr+1,0,17),'top':{'style':'SOLID','color':{'red':0.55,'green':0.55,'blue':0.55}}}})
R.append(fmt(s3,s3+1,0,17,{'backgroundColor':YL,'textFormat':{'bold':True,'fontSize':12},'wrapStrategy':'OVERFLOW_CELL'},'userEnteredFormat(backgroundColor,textFormat,wrapStrategy)'))
R.append(fmt(s3+1,s3+4,0,1,{'textFormat':{'bold':True,'fontSize':10}},'userEnteredFormat.textFormat'))
R.append(fmt(s3+1,s3+4,1,2,{'wrapStrategy':'OVERFLOW_CELL','textFormat':{'fontSize':10}},'userEnteredFormat(wrapStrategy,textFormat)'))
for c0,c1,px in [(0,1,220),(1,2,125),(2,3,105),(3,4,150),(4,5,190),(5,6,260),(6,7,260),(7,8,220),(8,11,95),(11,12,70),(12,13,60),(13,14,120),(14,15,110),(15,16,430),(16,17,360)]:
    R.append({'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':c0,'endIndex':c1},'properties':{'pixelSize':px},'fields':'pixelSize'}})
call('POST',f'{API}/{DS}:batchUpdate',json={'requests':R})
print('rows S',len(sec['S']),'W',len(sec['W']),'red rows',nred)
