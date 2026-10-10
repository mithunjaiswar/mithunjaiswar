import json,re
exec(open('cmp_tabs.py').read().split('rows=[]; tot_ok')[0])   # O, N2, WK, RA, num, g
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS=open('../dash/dash_sid.txt').read().strip()
ST={}
def st(rows,s):
    for r in rows: ST[r]=s
FIX='Fixed in MV data'; ADM='Pending - MV correction (Admin)'; SHT='Sheet to correct (MV correct)'; DEC='Need your decision'; OK='Matched - no action'
st([14,15,17,20,21,23,26,28,47,48],FIX)
st([10,11,12,18,24,25,52]+list(range(64,70))+list(range(81,87)),ADM)
st([41,42,43,44,45,49,50,51]+list(range(70,75)),SHT)
st([13,16,19,22,27,29,30,31]+list(range(75,81)),DEC)
WKS=list(range(2,10))
def val(s,pc):
    x=num(s)
    if x is None: return None
    return x/100 if pc else x
out=[]; meta=[]
sec=''
for i in range(8,86):
    if not O[i] or len(O[i])<2 or not O[i][1].strip(): continue
    if O[i][0].strip(): sec=O[i][0].strip()
    pc=any('%' in g(O,i,j) for j in WKS) or '%' in O[i][1]
    wk=[];ok=c=0;S=[];M=[]
    for j in WKS:
        a,b=g(O,i,j),g(N2,i,j); x,y=val(a,pc),val(b,pc)
        if x is None or y is None:
            wk+=[a,b,'',''];
            if j<9: c+=1; ok+=a.strip()==b.strip()
            continue
        d=y-x; dp=(d/abs(x)) if x else (0 if d==0 else '')
        wk+=[x,y,d,dp]
        if j<9:
            S.append(x);M.append(y);c+=1
            tol=max(abs(x)*0.02,0.0015 if pc else (1 if abs(x)>=20 else 0)); ok+=abs(d)<=tol+1e-9
    if S:
        ts=sum(S)/len(S) if pc else sum(S); tm=sum(M)/len(M) if pc else sum(M); td=tm-ts; tdp=(td/abs(ts)) if ts else (0 if td==0 else '')
    else: ts=tm=td=tdp=''
    status='MATCH' if ok==c else ('PARTIAL' if ok>=c*0.5 else 'MISMATCH')
    cs=ST.get(i+1,OK) if status!='MATCH' or (i+1) in ST and ST[i+1]==FIX else OK
    if status=='MATCH' and ST.get(i+1)==ADM: cs=ADM   # Oct-05 still pending
    rec,reason=RA.get(i+1,('',''))
    if cs==OK: rec,reason=('No change',reason or 'Sheet and MV same')
    dflt='MV Correct' if cs in (FIX,SHT) else ('Both Same' if cs==OK else 'Pending')
    out.append([sec,O[i][1].strip(),status,f'{ok}/{c}',ts,tm,td,tdp,cs,rec,reason,dflt,'']+wk)
    meta.append(pc)
n0=6
for k,r in enumerate(out):
    rr=n0+1+k
    r[12]=f'=IF(L{rr}="MV Correct","MV",IF(L{rr}="Sheet Correct","Sheet",IF(L{rr}="Both Same","Sheet = MV","Decide")))'
tc=len(out); nm=sum(r[2]=='MATCH' for r in out); npa=sum(r[2]=='PARTIAL' for r in out); nmi=sum(r[2]=='MISMATCH' for r in out)
cells=sum(int(r[3].split('/')[1]) for r in out); okc=sum(int(r[3].split('/')[0]) for r in out)
from collections import Counter; cc=Counter(r[8] for r in out)
top=[['Sheet vs MV - Summary tab  |  Sheet = reference dashboard (our check)  |  MV = same dashboard built from PG MV  |  Delhi NCR / Own Now / *'],
 ['Result (Aug-17..Sep-28, 2% tolerance)',f'Match {nm} | Partial {npa} | Mismatch {nmi} of {tc} metrics',f'Week values matched: {okc}/{cells} ({okc/cells:.1%})',f'Final difference: {1-okc/cells:.1%}'],
 ['Correction status',f'Fixed in MV data: {cc[FIX]}',f'Pending MV (Admin): {cc[ADM]}',f'Sheet to correct: {cc[SHT]}',f'Need your decision: {cc[DEC]}',f'Matched: {cc[OK]}'],
 ['How to use','Col L = YOUR final decision (dropdown). "MV Correct" -> Col M shows MV as final source of truth for that metric.'],
 [],
 ['Section','Metric','Match Status','Weeks matched','Sheet (Aug17-Sep28 total; avg for %)','MV (total; avg for %)','Difference (MV - Sheet)','Difference %','Correction Status','Your Recommendation','Reason','Final Decision (you)','Final Source of Truth']
 +sum([[f'{w} Sheet',f'{w} MV',f'{w} Diff',f'{w} Diff %'] for w in WK],[])]
V=top+out
TAB='Sheet_vs_MV'
m=call('GET',f'{API}/{DS}',params={'fields':'sheets.properties'})
tabs={s['properties']['title']:s['properties']['sheetId'] for s in m['sheets']}
req=[]
if 'Old_vs_New_Summary' in tabs: req.append({'deleteSheet':{'sheetId':tabs['Old_vs_New_Summary']}})
if TAB in tabs: req.append({'deleteSheet':{'sheetId':tabs[TAB]}})
req.append({'addSheet':{'properties':{'title':TAB,'index':1,'gridProperties':{'rowCount':len(V)+5,'columnCount':len(V[5])}}}})
r=call('POST',f'{API}/{DS}:batchUpdate',json={'requests':req}); sid=r['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT',f"{API}/{DS}/values/'{TAB}'!A1",params={'valueInputOption':'USER_ENTERED'},json={'values':[[('' if v is None else v) for v in row] for row in V]})
def rng(r0,r1,c0,c1): return {'sheetId':sid,'startRowIndex':r0,'endRowIndex':r1,'startColumnIndex':c0,'endColumnIndex':c1}
def fmt(r0,r1,c0,c1,f,fields='userEnteredFormat'): return {'repeatCell':{'range':rng(r0,r1,c0,c1),'cell':{'userEnteredFormat':f},'fields':fields}}
def nf(r0,r1,c0,c1,p): return fmt(r0,r1,c0,c1,{'numberFormat':{'type':'NUMBER','pattern':p}},'userEnteredFormat.numberFormat')
DK={'red':0.2,'green':0.25,'blue':0.4}; W={'red':1,'green':1,'blue':1}
GR={'red':0.78,'green':0.92,'blue':0.79}; RD={'red':0.96,'green':0.78,'blue':0.78}; YL={'red':1,'green':0.95,'blue':0.75}; BL={'red':0.85,'green':0.9,'blue':0.98}; GY={'red':0.93,'green':0.93,'blue':0.93}
NC=len(V[5]); NR=len(V)
R=[fmt(0,NR,0,NC,{'verticalAlignment':'TOP','wrapStrategy':'WRAP'},'userEnteredFormat(verticalAlignment,wrapStrategy)'),
   fmt(0,1,0,NC,{'textFormat':{'bold':True,'fontSize':12}},'userEnteredFormat.textFormat'),
   fmt(1,4,0,6,{'backgroundColor':YL,'textFormat':{'bold':True}},'userEnteredFormat(backgroundColor,textFormat)'),
   fmt(5,6,0,NC,{'backgroundColor':DK,'textFormat':{'bold':True,'foregroundColor':W},'wrapStrategy':'WRAP','verticalAlignment':'MIDDLE'}),
   fmt(6,NR,11,12,{'backgroundColor':BL,'textFormat':{'bold':True}},'userEnteredFormat(backgroundColor,textFormat)'),
   {'setDataValidation':{'range':rng(6,NR,11,12),'rule':{'condition':{'type':'ONE_OF_LIST','values':[{'userEnteredValue':v} for v in ['MV Correct','Sheet Correct','Both Same','Pending']]},'showCustomUi':True,'strict':True}}},
   {'updateSheetProperties':{'properties':{'sheetId':sid,'gridProperties':{'frozenRowCount':6,'frozenColumnCount':2}},'fields':'gridProperties(frozenRowCount,frozenColumnCount)'}}]
for c0,c1,px in [(0,1,110),(1,2,220),(2,4,85),(4,8,105),(8,9,150),(9,10,280),(10,11,330),(11,13,115),(13,NC,85)]:
    R.append({'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':c0,'endIndex':c1},'properties':{'pixelSize':px},'fields':'pixelSize'}})
# alternate week shading
for w in range(8):
    if w%2==0: R.append(fmt(5,6,13+4*w,17+4*w,{'backgroundColor':{'red':0.3,'green':0.36,'blue':0.52}},'userEnteredFormat.backgroundColor'))
for k,pc in enumerate(meta):
    rr=6+k; p='0.0%' if pc else '#,##0'
    R.append(nf(rr,rr+1,4,7,p))
    R.append(nf(rr,rr+1,7,8,'0.0%'))
    for w in range(8):
        R.append(nf(rr,rr+1,13+4*w,16+4*w,p)); R.append(nf(rr,rr+1,16+4*w,17+4*w,'0.0%'))
    row=out[k]
    R.append(fmt(rr,rr+1,2,3,{'backgroundColor':{'MATCH':GR,'PARTIAL':YL,'MISMATCH':RD}[row[2]],'textFormat':{'bold':True}},'userEnteredFormat(backgroundColor,textFormat)'))
    R.append(fmt(rr,rr+1,8,9,{'backgroundColor':{FIX:GR,ADM:YL,SHT:BL,DEC:RD,OK:GY}[row[8]],'textFormat':{'bold':True}},'userEnteredFormat(backgroundColor,textFormat)'))
# red text on week diff% beyond 2%
for w in range(8):
    c=13+4*w+3
    R.append({'addConditionalFormatRule':{'rule':{'ranges':[rng(6,NR,c,c+1)],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':f'=AND(ISNUMBER({chr(0)}),1)'}]},'format':{}}},'index':0}}) if False else None
R=[x for x in R if x]
def cl(i):
    s='';i+=1
    while i: i,q=divmod(i-1,26); s=chr(65+q)+s
    return s
for c in [7]+[16+4*w for w in range(8)]:
    L=cl(c)
    R.append({'addConditionalFormatRule':{'rule':{'ranges':[rng(6,NR,c,c+1)],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':f'=AND(ISNUMBER({L}7),ABS({L}7)>0.02)'}]},'format':{'textFormat':{'foregroundColor':{'red':0.8,'green':0,'blue':0},'bold':True}}}},'index':0}})
R.append({'addConditionalFormatRule':{'rule':{'ranges':[rng(6,NR,12,13)],'booleanRule':{'condition':{'type':'TEXT_EQ','values':[{'userEnteredValue':'MV'}]},'format':{'backgroundColor':GR,'textFormat':{'bold':True}}}},'index':0}})
for i in range(0,len(R),200): call('POST',f'{API}/{DS}:batchUpdate',json={'requests':R[i:i+200]})
print('ok',nm,npa,nmi,okc,cells,dict(cc))
