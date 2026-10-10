import json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
exec(open('doc_catalog.py').read())
DS=open('../dash/dash_sid.txt').read().strip()
rows=json.load(open('../dash/doc_rows.json'))
TAB='Metric_Summary'
cnt={}
for r in rows:
    if r[0]: cnt[r[3]]=cnt.get(r[3],0)+1
H1=['ID','Metric','Required For','MV Status','Available in MV?','What it represents','Raw_Data column','Source table.column','Calculation logic','Filters & date range','Joins (key + condition)',
    'Sheet value','MV value','Difference (MV - Sheet)','Difference %','Weeks matched','Compared on','Incorrect % (record level, 14-Sep MV vs source)','Mismatch reason (detail) + Correction required','Example (partner / week: Sheet vs MV)']
TOP=[['METRIC SUMMARY - every metric used in Summary + WBR: source, MV availability, logic, Sheet vs MV difference, correction'],
 ['How to read: col D = status. GREEN = MV correct | RED = available in MV but data incorrect (see Section 2) | ORANGE = MV logic / definition to confirm | BLUE = missing in MV, added in final query by join (see Section 3) | GREY = derived / business input.'],
 ['Sheet value = old reference dashboard; MV value = this dashboard (built only from final SQL). Summary metrics compared for Delhi NCR / Own Now, Aug-17..Sep-28 (7 weeks, total; average for %). WBR metrics compared all India, Sep-14..Oct-05.'],
 ['Metric groups by status:  '+'  |  '.join(f'{k}: {v}' for k,v in sorted(cnt.items()))],
 [],['SECTION 1 - METRIC CATALOG (all Summary + WBR metrics)'],H1]
body=[r[:20] for r in rows]
S2H=['MV column','Metrics affected','Required For','MV value','Sheet value','Amount / Count difference','Incorrect % (records)','Mismatch reason','Correction required (in MV)']
S2=[['SECTION 2 - AVAILABLE IN MV BUT DATA INCORRECT (fix in MV, not in sheet)'],S2H,
 ['partners_not_paid_2_weeks','Not paid > 2 weeks (S14)','Summary','450 partners (Delhi NCR / Own Now, 7 weeks)','238','+212 (+89%)','11.2% (1,272 of 11,375)','MV previous_week_collection is 0 for every partner, so the flag checks only 1 week (unpaid in 31Aug-06Sep counts even if paid in 07-13Sep)','Fill previous_week_collection = positive payments 2 weeks back; flag = 1 only if BOTH previous weeks unpaid'],
 ['previous_week_collection','(helper for partners_not_paid_2_weeks)','Summary','0 for all rows','payments of week 2 back','100% rows = 0','100%','Helper column never filled','Populate from mv_daily_recovery (razorpay/phonepe/other) for hissab_week-14 .. hissab_week-8'],
 ['bad_debt_collected','Bad debt collected (Non Funnel) S23 / W10, Net Bad Debt % (Non Funnel)','Both','65.8M (all India, 4 weeks)','1.37M','+64.4M','23.9% (2,718 of 11,375)','Running total of deposit-to-OS after the partner left (e.g. ETB02477 week 14-Sep = 6,000 = 4,765 on 08-Sep + 1,235 on 15-Sep); own deposit, not cash; repeated in every week','Only real payments (razorpay/phonepe/other) between leave (jama) date and next join date, for that week only; 0 if no rejoin'],
 ['total_allocated_days','Active driver DP to OS amount/count/% (S17), Active Convert to Rent % / partners (W12) via entire_week_active','Both','967.2K / 48 partners (Delhi Own Now, 7 wks)','34.2K / 4','+933K / +44','3.5% (401 of 11,375)','Car-swap day counted twice (8 instead of 7); ~131 rows = driven + hisaab week (14)','COUNT(DISTINCT allocated date) within hisaab week only. Also confirm "active full week" = allocated 7 days vs Uber-active 7 days (Sheet)'],
 ['collection_till_wed','Till Wed Collections % (S15)','Summary','31.3% avg','30.4% avg','+0.9 pp','0.4% (45 of 11,375)','MV sums all recovery types Mon-Wed; Sheet used razorpay only','Decide rule; if razorpay-only, filter recovery_type in MV'],
 [],['Other MV columns with data issues (NOT used in Summary / WBR - for MV team): tenure_days 94.5% (MV ~9-10 days lower), last_jama_date / next_join_date 94.8% (blank when partner rejoined in same weeks), location 76.8% (hub names vs SSOT allocation location), last_car_number 87.8% (only 1 car when 2+ used). Performance: add index on collections_bad_debt_mv (hissab_week, partner_etm) - MV queries time out without it.']]
S3H=['Raw_Data column','Source table','Exact source column(s)','Logic','Join keys + conditions','Used in metrics']
S3=[['SECTION 3 - COLUMNS MISSING FROM MV (added in final SQL by join / derivation)'],S3H,
 ['T razorpay_100pct, U other_100pct, V phonepe_100pct, W adjustment_100pct, X deposit_to_rent_100pct','mv_daily_recovery','amount, recovery_type (razorpay_recovery, other_positive_recovery, phonepe_recovery, positive_adjustment, deposit_to_os), date','SUM(amount) per type in hisaab week; razorpay = total_collected_100_pct - other parts (so split = total)',JR,'S05-S11, S16, S17, W05, W06, W12'],
 ['J elc_filter','mv_collections_calling_masterlist','elc_filter','Last snapshot of the hisaab week; default Non_ELC',JML,'Summary ELC filter (B6)'],
 ['AN asset_risk (+ AZ risk_score, BA payment_habit_week, BB not_paid_prev_2w, BC nd_count_hw, BD gps_inactive, BE connects)','collections_bad_debt_mv (history) + mv_collections_calling_masterlist','total_collected_amount_in_week, total_os, collection_till_wed, total_collected_100_pct, week_end_deposit, current_week_nd_count, active_inactive_flag; masterlist conn_total, current_week_gps_kms, current_week_uber_kms','Score = 6 signals (see S36). 6 Critical, 5 High, 4 Moderate, 3 Low, 2 Minimal, 0-1 No risk',JNP+'; '+JML,'S36, W13'],
 ['AH alloc_date, AI dep_at_alloc','ssot_alloc_dealloc_base + mv_deposits_raw','allocation_date; amount, deposit_type, date','Latest allocation_date <= hisaab week end; deposit = SUM(amount) with date <= alloc_date excl. SD_TO_OWNNOW / OWNNOW_TO_OWNNOW',JAL,'S39 Deposit [At Allocation]'],
 ['AR recovery_initiated, AS recovery_brought_fwd, AT recovered_team, AU recovered_organic, AV recovery_pending, AW recovery_tat_hrs, AX recovery_agent_id','recovery_cars + fleet_driver','created_at, updated_at, recovery_status, recovery_agent_id, driver_id; fleet_driver.employee_id','Counts per hisaab week: initiated = created in week; brought fwd = created before week, still open / closed in week; team = complete in week; organic = cancelled in week; pending = pending/active; TAT = updated_at - created_at (complete)',JRC,'S28-S35'],
 ['AM bad_debt_collected_funnel','collections_bad_debt_mv (full history)','bad_debt_amount, hissab_week, total_collected_100_pct, active_inactive_flag','total_collected_100_pct if partner first went to bad debt in an earlier week AND is Inactive','bd CTE: MIN(hissab_week) where bad_debt_amount < 0 GROUP BY partner_etm; LEFT JOIN on partner_etm','S24, S25, W09'],
 ['BF advance_amount','Derived (MV + mv_daily_recovery)','total_collected_amount_in_week, total_os, deposit_to_os','MAX(total_collected_amount_in_week - deposit_to_os - ABS(total_os), 0)',JR,'W14'],
 ['BG carry_forward_os_neg','Derived (MV)','prev_carryforward_os','LEAST(prev_carryforward_os, 0)','None','W11'],
 ['AB entire_week_active, AJ os_surpass_deposit_amt, AO recovery_recommended, I eip_filter','Derived (MV)','total_allocated_days, total_os, week_end_deposit, total_collected_100_pct, eip_tag','entire_week = allocated >= 7; surpass = MAX(-total_os - week_end_deposit, 0) for Active; recommended = Sheet col AH rule; eip = EIP/SINGLE','None','S17-S19, S27, W12'],
 ['Asset-risk buckets in old Sheet inputs (ND / GPS / connects)','(old Sheet IMPORTRANGE)','-','Old Sheet pulled these by row position (misaligned); query uses partner-keyed PG data','-','S36']]
sql=open('/home/user/mithunjaiswar/collections_bad_debt_validation/dashboard_pg/final_raw_data.sql').read().split('\n')
S4=[['SECTION 4 - FINAL SQL (populates Raw_Data; repo: collections_bad_debt_validation/dashboard_pg/final_raw_data.sql)'],
    ['Automation: run weekly after the MV refresh and overwrite Raw_Data!A:BG (Airflow / Connected Sheets / Apps Script JDBC). Summary, WBR and City_Targets recalculate automatically.']]+[[l] for l in sql]
V=TOP+body+[[],[]]+S2+[[],[]]+S3+[[],[]]+S4
m=call('GET',f'{API}/{DS}',params={'fields':'sheets.properties'})
P={s['properties']['title']:s['properties']['sheetId'] for s in m['sheets']}
req=[]
if TAB in P: req.append({'deleteSheet':{'sheetId':P[TAB]}})
req.append({'addSheet':{'properties':{'title':TAB,'index':0,'gridProperties':{'rowCount':len(V)+10,'columnCount':20,'frozenRowCount':7,'frozenColumnCount':2}}}})
sid=call('POST',f'{API}/{DS}:batchUpdate',json={'requests':req})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT',f"{API}/{DS}/values/'{TAB}'!A1",params={'valueInputOption':'RAW'},json={'values':[[('' if x is None else x) for x in r] for r in V]})
def rng(r0,r1,c0,c1): return {'sheetId':sid,'startRowIndex':r0,'endRowIndex':r1,'startColumnIndex':c0,'endColumnIndex':c1}
def fmt(r0,r1,c0,c1,f,fields): return {'repeatCell':{'range':rng(r0,r1,c0,c1),'cell':{'userEnteredFormat':f},'fields':fields}}
DK={'red':0.2,'green':0.25,'blue':0.4}; WH={'red':1,'green':1,'blue':1}
CL={OK:{'red':0.78,'green':0.92,'blue':0.79},BAD:{'red':0.96,'green':0.74,'blue':0.74},LOGIC:{'red':1,'green':0.85,'blue':0.6},ADD:{'red':0.8,'green':0.87,'blue':0.98},DER:{'red':0.9,'green':0.9,'blue':0.9},BIZ:{'red':0.9,'green':0.9,'blue':0.9},NOSRC:{'red':0.9,'green':0.9,'blue':0.9}}
YL={'red':1,'green':0.95,'blue':0.75}
b0=len(TOP); b1=b0+len(body)
R=[fmt(0,len(V),0,20,{'wrapStrategy':'WRAP','verticalAlignment':'TOP','textFormat':{'fontSize':9}},'userEnteredFormat(wrapStrategy,verticalAlignment,textFormat)'),
   fmt(0,1,0,19,{'textFormat':{'bold':True,'fontSize':13}},'userEnteredFormat.textFormat'),
   fmt(1,4,0,19,{'backgroundColor':YL},'userEnteredFormat.backgroundColor')]
R.append(fmt(0,6,0,1,{'wrapStrategy':'OVERFLOW_CELL'},'userEnteredFormat.wrapStrategy'))
def sec(r,n):
    return [fmt(r,r+1,0,n,{'backgroundColor':YL,'textFormat':{'bold':True,'fontSize':11}},'userEnteredFormat(backgroundColor,textFormat)'),
            fmt(r+1,r+2,0,n,{'backgroundColor':DK,'textFormat':{'bold':True,'foregroundColor':WH,'fontSize':9},'wrapStrategy':'WRAP'},'userEnteredFormat(backgroundColor,textFormat,wrapStrategy)')]
R+=sec(b0-2,20)
s2=b1+2; R+=sec(s2,9); s3=s2+len(S2)+2; R+=sec(s3,6); s4=s3+len(S3)+2
R.append(fmt(s4,s4+1,0,19,{'backgroundColor':YL,'textFormat':{'bold':True,'fontSize':11}},'userEnteredFormat(backgroundColor,textFormat)'))
R.append(fmt(s4+2,s4+len(S4),0,1,{'textFormat':{'fontFamily':'Roboto Mono','fontSize':9},'wrapStrategy':'OVERFLOW_CELL'},'userEnteredFormat(textFormat,wrapStrategy)'))
for k,r in enumerate(rows):
    rr=b0+k; pc=r[20]
    R.append(fmt(rr,rr+1,3,4,{'backgroundColor':CL.get(r[3],WH),'textFormat':{'bold':True,'fontSize':9}},'userEnteredFormat(backgroundColor,textFormat)'))
    R.append(fmt(rr,rr+1,11,14,{'numberFormat':{'type':'NUMBER','pattern':'0.0%' if pc else '#,##0'}},'userEnteredFormat.numberFormat'))
    R.append(fmt(rr,rr+1,14,15,{'numberFormat':{'type':'NUMBER','pattern':'0.0%'}},'userEnteredFormat.numberFormat'))
    if r[0]: R.append({'updateBorders':{'range':rng(rr,rr+1,0,20),'top':{'style':'SOLID','color':{'red':0.5,'green':0.5,'blue':0.5}}}})
R.append(fmt(s2+2,s2+7,0,1,{'backgroundColor':CL[BAD],'textFormat':{'bold':True,'fontSize':9}},'userEnteredFormat(backgroundColor,textFormat)'))
R.append(fmt(s3+2,s3+len(S3),0,1,{'backgroundColor':CL[ADD],'textFormat':{'bold':True,'fontSize':9}},'userEnteredFormat(backgroundColor,textFormat)'))
for c0,c1,px in [(0,1,45),(1,2,200),(2,3,70),(3,4,130),(4,5,110),(5,6,170),(6,7,150),(7,8,190),(8,9,280),(9,10,200),(10,11,220),(11,14,95),(14,15,70),(15,16,60),(16,17,110),(17,18,110),(18,19,380),(19,20,330)]:
    R.append({'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':c0,'endIndex':c1},'properties':{'pixelSize':px},'fields':'pixelSize'}})
call('POST',f'{API}/{DS}:batchUpdate',json={'requests':R})
m=call('GET',f'{API}/{DS}',params={'fields':'sheets.properties'})
print([s['properties']['title'] for s in m['sheets']], 'rows',len(V), cnt)
