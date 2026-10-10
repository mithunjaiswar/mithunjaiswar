import json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS=open('../dash/dash_sid.txt').read().strip()
cnt=json.load(open('../dash/tab_cnt.json')); C=json.load(open('../dash/cmp_out.json'))
G=[['Raw Data Summary - what each data tab holds and why it is needed'],
['Why so much raw data? The 4 dashboards filter every number by Week x City x Product x Fuel x ELC x Active. Formulas (SUMIFS/COUNTIFS) need one row per partner per week, so 9 weeks x ~11.4k partners = ~103k rows. Pre-aggregating would lose the filters.'],
[],
['Tab','Rows','Source','What it contains','Used by','Why needed'],
['Raw_Data',cnt['Raw_Data']-1,'PG: analytics.collections_bad_debt_mv + mv_daily_recovery (split)','1 row per partner per Hissab week (10-Aug..05-Oct): OS, collections & split (Razorpay/Other/Phonepe/Adjustment/DP-to-Rent), not-paid flags, habit, risk, bad debt, deposit, recovery, tenure','WBR View, Summary, SD_Profiles, CarryForward_View','Main fact table - every dashboard number is calculated from it'],
['City_Targets',cnt['City_Targets']-1,'Copied from old sheet','Collection / bad-debt target % by city & week','Summary, WBR View','Targets are business inputs, not in PG'],
['NonFunnel_BadDebt_Collected',cnt['NonFunnel_BadDebt_Collected']-1,'Copied from old sheet','Bad debt collected from partners outside the funnel (last 15 weeks)','Summary (Bad debt collected Non Funnel)','Not part of weekly MV rows'],
['advance_payment_data',cnt['advance_payment_data']-1,'Copied from old sheet','Advance payments by partner & week','Summary (Total Collections % wt Advances)','Advances are added on top of collections'],
['OS_Surpass',cnt['OS_Surpass']-1,'Copied from old sheet','Live OS vs deposit buckets for active drivers','Summary (Live OS Tracking)','Live snapshot, not weekly history'],
['excellent_data',cnt['excellent_data'],'Copied from old sheet','Excellent payment-habit list','Summary (Payment Behaviour)','Lookup for Excellent bucket'],
['collections_data',cnt['collections_data']-1,'Copied from old sheet','Collection detail used by WBR view','WBR View','WBR week-level collection view'],
['sd_bucket',cnt['sd_bucket']-1,'PG: MV week_start_deposit (rebuilt)','Partner count per deposit bucket by week/city/fuel/product + avg deposit','Summary (Deposit Threshold, City avg deposit)','Old tab was IMPORTRANGE (#REF in copy)'],
['sd_bucket_V2',cnt['sd_bucket_V2']-1,'PG: MV week_start_deposit (rebuilt)','Same as sd_bucket - placeholder for deposit AT ALLOCATION','Summary / SD_Profiles [At Allocation]','PG has no deposit-at-allocation field yet (open item)'],
[],
['Dashboards (no raw data, only formulas): WBR View, Summary, SD_Profiles [At Allocation], CarryForward_View'],
['Comparison result: see tab Old_vs_New_Summary']]
meta=call('GET',f'{API}/{DS}',params={'fields':'sheets.properties'})
tabs={s['properties']['title']:s['properties']['sheetId'] for s in meta['sheets']}
req=[]
for i,(t,n,c) in enumerate([('Raw_Tabs_Guide',len(G),8),('Old_vs_New_Summary',len(C['out']),20)]):
    if t not in tabs: req.append({'addSheet':{'properties':{'title':t,'index':i,'gridProperties':{'rowCount':max(n+5,100),'columnCount':c}}}})
if req:
    r=call('POST',f'{API}/{DS}:batchUpdate',json={'requests':req})
    for x in r['replies']: tabs[x['addSheet']['properties']['title']]=x['addSheet']['properties']['sheetId']
for t,v in [('Raw_Tabs_Guide',G),('Old_vs_New_Summary',C['out'])]:
    call('POST',f"{API}/{DS}/values/'{t}'!A1:clear",json={})
    call('PUT',f"{API}/{DS}/values/'{t}'!A1",params={'valueInputOption':'RAW'},json={'values':v})
g,c=tabs['Raw_Tabs_Guide'],tabs['Old_vs_New_Summary']
def rng(s,r0,r1,c0,c1): return {'sheetId':s,'startRowIndex':r0,'endRowIndex':r1,'startColumnIndex':c0,'endColumnIndex':c1}
def fmt(s,r0,r1,c0,c1,bg=None,bold=False,wrap=False,fg=None,size=None):
    f={'textFormat':{'bold':bold}}
    if fg: f['textFormat']['foregroundColor']=fg
    if size: f['textFormat']['fontSize']=size
    if bg: f['backgroundColor']=bg
    if wrap: f['wrapStrategy']='WRAP'
    f['verticalAlignment']='TOP'
    return {'repeatCell':{'range':rng(s,r0,r1,c0,c1),'cell':{'userEnteredFormat':f},'fields':'userEnteredFormat'}}
DK={'red':0.2,'green':0.25,'blue':0.4}; W={'red':1,'green':1,'blue':1}
GR={'red':0.78,'green':0.92,'blue':0.79}; RD={'red':0.96,'green':0.78,'blue':0.78}; YL={'red':1,'green':0.95,'blue':0.75}
def width(s,c0,c1,px): return {'updateDimensionProperties':{'range':{'sheetId':s,'dimension':'COLUMNS','startIndex':c0,'endIndex':c1},'properties':{'pixelSize':px},'fields':'pixelSize'}}
R=[fmt(g,0,len(G),0,6,wrap=True),fmt(g,0,1,0,6,bold=True,size=13),fmt(g,1,2,0,6,bg=YL,wrap=True),
   fmt(g,3,4,0,6,bg=DK,bold=True,fg=W,wrap=True),
   {'mergeCells':{'range':rng(g,1,2,0,6),'mergeType':'MERGE_ALL'}},
   width(g,0,1,190),width(g,1,2,70),width(g,2,3,230),width(g,3,4,380),width(g,4,5,220),width(g,5,6,260),
   {'updateSheetProperties':{'properties':{'sheetId':g,'gridProperties':{'frozenRowCount':4}},'fields':'gridProperties.frozenRowCount'}}]
n=len(C['out'])
R+=[fmt(c,0,n,0,17,wrap=True),fmt(c,0,1,0,10,bold=True,size=13),fmt(c,1,4,0,6,bg=YL,bold=True,wrap=True),
    fmt(c,5,6,0,17,bg=DK,bold=True,fg=W,wrap=True),
    width(c,0,1,120),width(c,1,2,230),width(c,2,3,95),width(c,3,6,95),width(c,6,8,75),width(c,8,9,380),width(c,9,10,330),width(c,10,17,130),
    {'updateSheetProperties':{'properties':{'sheetId':c,'gridProperties':{'frozenRowCount':6,'frozenColumnCount':2}},'fields':'gridProperties.frozenRowCount,gridProperties.frozenColumnCount'}}]
for i,row in enumerate(C['out'][6:],start=6):
    bg={'MATCH':GR,'PARTIAL':YL,'MISMATCH':RD}[row[2]]
    R.append(fmt(c,i,i+1,2,3,bg=bg,bold=True))
call('POST',f'{API}/{DS}:batchUpdate',json={'requests':R})
print('done',tabs['Raw_Tabs_Guide'],tabs['Old_vs_New_Summary'])
