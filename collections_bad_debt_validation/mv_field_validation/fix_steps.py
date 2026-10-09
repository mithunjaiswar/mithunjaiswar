exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
SMALL='1) Filter "{f} Matched?" = Not Matched ({n} rows). 2) Check each row in source table (query in Change_Log tab). 3) Correct the Manual value or note the reason in Remark. Gap is very small – no DAG change needed.'
STEPS={
'weekly_os':'1) Filter Remark = "MV skips adjustment-only…" (471 rows). 2) Confirm with business: should fines/adjustments (e.g. -1000 on old car) be in weekly_os? 3) If yes → DAG: remove the filter "rent > 0 or active_days > 0" on fleet_leasing_weeklydata. Expected: 95.6% → 100%.',
'prev_carryforward_os':'1) Ask DAG owner for the carry-forward formula. 2) Take 5 partners with gap -1000 / -175 (e.g. ETB00839: gap 175) and check which charge makes the gap (fine, toll, penalty). 3) Add that charge to the Manual rule, re-check. Expected: 72.3% → 95%+ once formula is known.',
'os_to_deposit':SMALL,'total_allocated_days':SMALL,'last_payment_date_till_hissab_week':SMALL,'last_week_payment_habit':SMALL,
'in_car_recovery_driven_week':SMALL,'in_car_recovery_hissab_week':SMALL,'cars_under_recovery_driven_week':SMALL,'cars_under_recovery_hissab_week':SMALL,'collection_till_wed':SMALL,'rental_days':SMALL,
'last_jama_date':'1) DAG: when car is still allocated (jama_date is NULL) keep last_jama_date blank – do not put a future date (21-Oct). 2) Re-run MV for 28-Sep. 3) Check the 232 "Need to Deep Dive" rows manually. Expected: 23.5% → 97.9%.',
'last_car_number':'1) DAG: replace single car with string_agg(distinct car_number, \', \') of all driven-week hisaab rows that have rent or active days. 2) Re-run MV. 3) Check the 820 Deep Dive rows (same car twice / order). Expected: 84.8% → 92%+.',
'week_start_deposit':'1) Filter Remark "opening/legacy deposit not in mv_deposits_raw" (830 rows, e.g. ETB00839 MV 30,000 / raw 0). 2) Send the list to Data team to load opening deposits into mv_deposits_raw. 3) Re-check. Expected: 92.3% → 100%.',
'week_end_deposit':'Same as week_start_deposit – one data fix (load opening deposits into mv_deposits_raw) fixes both fields. Expected: 92.3% → 100%.',
'last_week_nd_count':'1) Ask DAG owner how ND count is calculated (source table + rule). 2) Test 5 partners, e.g. ETB01547: allocated 7 days, 0 trips → ND should be 7, MV shows 0. 3) Agree one rule (allocated days − trip days) and update DAG. Expected: 86% → 100% after rule agreed.',
'current_week_nd_count':'Same as last_week_nd_count but for hisaab week (e.g. ETB01547: allocated 5, 0 trips → 5, MV 1). Fix together with last_week_nd_count. Expected: 87.5% → 100%.',
'hissab_week_active_days':'1) DAG: change logic to count distinct dates in fleet_dailytrip with trips > 0 between hissab_week and hissab_week + 6. 2) Today it counts allocated days of 2 weeks (14). 3) Re-run MV. Expected: 2% → 100%.',
'tenure_days':'1) DAG: count driver_profile stints only till hissab_week − 1 (driven week end) – SQL already sent to Suraj (Tenure_Script_Fix tab). 2) Re-run MV via Airflow. 3) Re-check this column. Expected: 13.5% → 100%.',
'd2o_leave_days':'1) DAG: count leave rows only where leave date is inside the driven week (do not include 28-Sep). 2) Check the 34 Deep Dive rows manually. Expected: 99.5% → 99.7%.',
'active_inactive_flag':'1) DAG: Active = car allocated on the LAST day of hisaab week (Sunday); current week = allocated today. 2) Today MV says Active if allocated any day (1,116 partners returned car mid-week). Expected: 89.6% → 99.9%.',
'next_total_os':'1) Confirm with DAG owner what next_total_os means for partners who left (no next-week row). 2) If it is final OS → rename/document; else set blank. 3) Refresh this week and next week together. Expected: 95.9% → 100%.',
'next_week_end_deposit':'1) Refresh this week and next week together (177 rows changed after refresh). 2) Same decision as next_total_os for partners with no next-week row (575 rows). Expected: 93% → 100%.',
'next_join_date':'1) DAG: keep blank when partner never left (no placeholder 21-Oct). 2) Re-run MV after the week closes so late rejoins are captured. 3) Check 1,368 Deep Dive rows. Expected: 22.6% → 87%+.',
'recovery_tat':'1) DAG: fill TAT only when cars_under_recovery_hissab_week > 0; blank otherwise. 2) Check 45 rows. Expected: 99.6% → 100%.',
'bad_debt_collected':'1) DAG: set 0 when partner never left (3,100 rows, e.g. ETB00514 MV 2,999 → 0). 2) For partners who left: sum mv_daily_recovery between jama date and next join date. 3) Manually check 3,305 left partners. Expected: 40.8% → 69% (step 1), → 95%+ (step 2).',
'previous_week_collection':'1) Filter Not Matched (242 rows, e.g. ETB02171 MV 1,860, no payment 7–13 Sep). 2) Check which source MV uses (fleet_leasing_recovery?) for these partners. 3) Align source. Expected: 97.8% → 100%.',
'partners_not_paid_2_weeks':'Will fix automatically when previous_week_collection is fixed (56 rows). Expected: 99.5% → 100%.',
'active_fleet_cash_blocked':'1) Ask data team for cash-block HISTORY (Airflow / Cash Block API table with date). 2) Load it to reporting DB. 3) Then compare status on hisaab week last day. Today DB has only current status (84 blocked vs MV 7,304). Expected: 32.9% → 98%+ after history available.',
'location':'1) Business decision: use main hub (e.g. Thane) or exact location (e.g. Kopar Khairane)? 2) If exact location → DAG: take location from ssot_alloc_dealloc_base allocation. 3) Re-run MV. Expected: 75.9% → 100%.',
'revenue_type':'1) DAG: revenue_type = product of driven-week hisaab row with most active days (SQL in Revenue_Type_Script_Fix tab). 2) Re-run MV. Expected: 98.3% → 100%.',
}
hdr=call('GET',f"{API}/{SID}/values/'{TAB}'!A5:ZZ5")['values'][0]
cnt=call('GET',f"{API}/{SID}/values/'{TAB}'!A3:ZZ3")['values'][0]
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets(properties)'})
tid=[s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title']==TAB][0]
data=[{'range':f"'{TAB}'!A3",'values':[['How to fix (steps)  |  Not Matched rows →']]}]; reqs=[]
for i,h in enumerate(hdr):
    if not h.endswith(' (MV)'): continue
    f=h[:-5]; jm=hdr.index(f+' Matched?'); st=col(jm)
    n=cnt[jm] if jm<len(cnt) else '0'
    if f in STEPS: txt=STEPS[f].format(f=f,n=n)
    elif f in ('revshare_days_working','uber_active_days','total_rent_amount','last_week_collection','next_weekly_os'): txt='—'
    else: txt=f'=IF({st}3=0,"—","1) Filter {f} Matched? = Not Matched. 2) Compare MV vs Sheet value on those rows. 3) Note the pattern in Remark – field not in validation doc.")'
    data.append({'range':f"'{TAB}'!{col(i)}3",'values':[[txt]]})
    reqs.append({'mergeCells':{'range':{'sheetId':tid,'startRowIndex':2,'endRowIndex':3,'startColumnIndex':i,'endColumnIndex':jm},'mergeType':'MERGE_ALL'}})
reqs+=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':2,'endRowIndex':3,'startColumnIndex':3},'cell':{'userEnteredFormat':{'wrapStrategy':'WRAP','verticalAlignment':'TOP'}},'fields':'userEnteredFormat(wrapStrategy,verticalAlignment)'}},
       {'updateDimensionProperties':{'range':{'sheetId':tid,'dimension':'ROWS','startIndex':2,'endIndex':3},'properties':{'pixelSize':120},'fields':'pixelSize'}}]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
# merged cells keep alignment of the first cell: make text left aligned, Matched? count stays centred
reqs=[]
for i,h in enumerate(hdr):
    if h.endswith(' (MV)'):
        reqs.append({'repeatCell':{'range':{'sheetId':tid,'startRowIndex':2,'endRowIndex':3,'startColumnIndex':i,'endColumnIndex':i+1},'cell':{'userEnteredFormat':{'horizontalAlignment':'LEFT','textFormat':{'bold':False},'numberFormat':{'type':'TEXT'}}},'fields':'userEnteredFormat(horizontalAlignment,textFormat,numberFormat)'}})
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
call('POST',f'{API}/{SID}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data})
v=call('GET',f"{API}/{SID}/values/'{TAB}'!A3:AJ3")['values'][0]
print([x[:70] for x in v if x])
