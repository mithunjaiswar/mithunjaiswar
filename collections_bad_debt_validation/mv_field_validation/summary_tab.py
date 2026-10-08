exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
MAN,REM=pickle.load(open('manual_out.pkl','rb'))
notes={x[2].replace(' (Manual)',''):x[5] for x in json.load(open('../run4/user_manual.json'))}
DD='Need to Deep Dive – Manual Validation Required'
S={ # field: (source, existing logic (inferred from data), logic used for Manual, mismatch reason, correction)
'revshare_days_working':('fleet_weeklydata.days_working (driven week)','= fleet_weeklydata days_working of driven week; 0 for leasing partners','Same','—','None'),
'weekly_os':('fleet_leasing_weeklydata (driven week rows) + fleet_weeklydata','Sum of weekly_os of driven-week hisaab rows EXCLUDING adjustment-only rows (0 rent, 0 active days)','Sum of ALL driven-week rows (as per rule)','473 partners have an extra adjustment-only row (e.g. -1000 / -500 fine, +685 credit on old car) that MV leaves out','Confirm business rule: include adjustment-only rows in weekly_os, or keep them in carry-forward'),
'prev_carryforward_os':('MV previous hisaab week total_os + mv_daily_recovery (driven week)','Not fully reproducible without DAG; ~72% = prev total_os + collections','Prev week total_os + driven-week collections (razorpay+phonepe+other_positive+deposit_to_os+positive_adjustment)','Differences in round amounts (-1000, -175, -500 …) – likely fines/adjustments the DAG adds; 506 partners not in previous week','Need DAG script to confirm components. '+DD),
'os_to_deposit':('mv_deposits_raw OS_TO_DEPOSIT','= -(OS_TO_DEPOSIT amount in driven week)','Same','23 rows differ – '+DD,'None (99.8% match)'),
'total_allocated_days':('analytics.ssot_alloc_dealloc_base','Sum of allocation days (each allocation counted, inclusive) in HISAAB week','Same','5 rows: MV 2 vs SSOT 7 – '+DD,'None'),
'uber_active_days':('fleet_dailytrip','Days with trips > 0 in driven week','Same','—','None'),
'rental_days':('fleet_leasing_weeklydata.active_days','Sum of active_days rounded to whole days','Exact sum of active_days','Half-day active_days (x.5 / x.25) rounded by MV – within ±1','Optional: keep decimals or document rounding'),
'total_rent_amount':('fleet_leasing_weeklydata.total_rent','Sum of total_rent of driven-week rows','Same','—','None'),
'last_payment_date_till_hissab_week':('mv_daily_recovery','Max date of positive payment (razorpay/phonepe/other_positive) till hisaab week end','Same','11 rows – '+DD,'None'),
'last_jama_date':('analytics.ssot_alloc_dealloc_base.jama_date','Placeholder future date (2026-10-21) when car still allocated','Last real jama date till hisaab week end; text if never returned','8,268 rows carry the placeholder future date','Set NULL (or "No jama") instead of a future placeholder date'),
'last_car_number':('fleet_leasing_weeklydata.car_number (driven week)','Only one car (main hisaab row)','All cars used in driven week, "Car1, Car2" format','1,642 partners used 2+ cars in driven week','Change DAG to string_agg all driven-week cars'),
'week_start_deposit':('mv_deposits_raw (cumulative till 27-Sep)','Cumulative deposit before hisaab week start incl. opening balance from another table','Cumulative mv_deposits_raw till 27-Sep','830 older partners: opening/legacy deposit (mostly 30,000+) not present in mv_deposits_raw','Load legacy/opening deposits into mv_deposits_raw (gap in raw table)'),
'week_end_deposit':('mv_deposits_raw (cumulative till 04-Oct)','Cumulative deposit till hisaab week end','Cumulative mv_deposits_raw till 04-Oct','Same 830 legacy-deposit gap','Same as above'),
'last_week_payment_habit':('driver_repayment_habit','Last entry before hisaab week','Same','3 rows: MV value with no prior entry – '+DD,'None'),
'last_week_nd_count':('ssot allocation + fleet_dailytrip','Not = allocation days - active days (source unknown)','Allocation days - Uber active days (driven week)','~21% differ in both directions; MV ND not derivable from allocation/trip data','Need DAG logic. '+DD),
'current_week_nd_count':('ssot allocation + fleet_dailytrip','Same as above for hisaab week','Allocation days - Uber active days (hisaab week)','~18% differ','Need DAG logic. '+DD),
'hissab_week_active_days':('fleet_dailytrip','Allocation days across driven + hisaab week (14 = full 2 weeks) – not trip days','Days with trips > 0 in hisaab week','Field holds allocated days of 2 weeks, not active days','Rename or change DAG to count fleet_dailytrip active days in hisaab week'),
'tenure_days':('driver_profile + fleet_driver','Tenure till hisaab week Sunday (hissab_week + 6)','Tenure till driven week end (hissab_week - 1)','MV is ~7 days higher for active partners','DAG fix shared (Tenure_Script_Fix tab / mail to Suraj)'),
'd2o_leave_days':('driver_d2o_leaves_log (leave rows)','Leave days overlapping driven week','Same','51 rows: MV also counts leave rows dated 28-Sep (hisaab Monday, auto-created)','Restrict window to driven week (start <= hissab_week - 1)'),
'active_inactive_flag':('analytics.ssot_alloc_dealloc_base','Active if allocated on ANY day of hisaab week','Active if allocated on LAST day of hisaab week (current week: allocated today)','1,116 partners returned car mid-week but MV says Active','Change DAG to check allocation on hisaab week last day'),
'next_weekly_os':('MV row of next hisaab week (2026-10-05)','Copy of next week weekly_os – lookahead used for bad-debt / rejoin logic (inferred; DAG not accessible)','Next week MV weekly_os','—','Document purpose in DAG'),
'next_total_os':('MV row of next hisaab week','Copy of next week total_os (lookahead)','Next week MV total_os','448 rows: next week still in progress, value changed after snapshot','Document purpose; refresh together'),
'next_week_end_deposit':('MV row of next hisaab week','Copy of next week week_end_deposit (lookahead)','Next week MV week_end_deposit','752 rows: snapshot timing','Document purpose; refresh together'),
'next_join_date':('analytics.ssot_alloc_dealloc_base','Placeholder 2026-10-21 for partners who never left; next allocation after jama otherwise','Next allocation after last real jama; text if never left','Placeholder future date for 6,595 partners; rejoins after MV refresh missing','Set NULL for never-left partners; refresh after rejoin'),
'in_car_recovery_driven_week':('recovery_cars','Recovery record open during driven week','Same','26 rows – '+DD,'None'),
'in_car_recovery_hissab_week':('recovery_cars','Recovery record open during hisaab week','Same','45 rows – '+DD,'None'),
'collection_till_wed':('mv_daily_recovery','Net of all recovery types Mon–Wed of hisaab week','Same','95 rows – '+DD,'None'),
'bad_debt_collected':('mv_daily_recovery + ssot (jama → next join)','Filled with week collection even for partners who never left','0 for partners who never left; left partners need manual check','6,405 rows filled for partners with no leave/rejoin','DAG should only sum collections between jama date and next join date'),
'last_week_collection':('mv_daily_recovery (14–20 Sep)','Payments + deposit_to_os + positive_adjustment in the week 2 weeks before hisaab week – HELPER for partners_not_paid_2_weeks','Same','—','Confirm week window (it is driven week - 1, not driven week)'),
'previous_week_collection':('mv_daily_recovery (07–13 Sep)','Same for the week before – HELPER for partners_not_paid_2_weeks','Same','242 rows: MV value but no payment rows that week – '+DD,'None'),
'partners_not_paid_2_weeks':('Derived','1 when last_week_collection and previous_week_collection are both 0','Same','Follows the two helper fields','None'),
'cars_under_recovery_driven_week':('recovery_cars','Count of cars with recovery open during driven week','Same','28 rows – '+DD,'None'),
'cars_under_recovery_hissab_week':('recovery_cars','Count of cars with recovery open during hisaab week','Same','48 rows – '+DD,'None'),
'recovery_tat':('recovery_cars','Filled only when car under recovery in hisaab week','Consistency check vs cars_under_recovery_hissab_week','45 rows inconsistent','None'),
'active_fleet_cash_blocked':('Cash Block API (Airflow) – not in reporting DB; driver_cashblock = current status only','7,304 partners flagged 1','driver_cashblock current status (only 84 blocked)','Cannot validate hisaab-week-end status from DB','Need Cash Block API history table. '+DD),
'location':('analytics.ssot_alloc_dealloc_base.location','Parent / hisaab hub (e.g. Delhi-Sukhrali, Thane)','Allocation location in SSOT','Different location master: hub vs allocation sub-location (Honda Sector 35 Office, Kopar Khairane, Vasai …)','Decide one location master for collections'),
'revenue_type':('fleet_leasing_weeklydata (driven week)','Hub/location lookup','Product of driven-week hisaab row with most active days','184 rows: 2 products in week / EV on D2O plan label','See Revenue_Type_Script_Fix tab'),
}
rows=[['MV FIELD VALIDATION – hisaab week 2026-09-28 (driven week 2026-09-21), 10,812 partners (for_collections = 1). Row-level values: MV_Raw_Data_Manual_Check → "(Manual)" + "Remark" columns.'],
      ['Note: DAG script repo is not accessible, so "Existing logic" is inferred from the data (rule that reproduces the MV values).'],[''],
      ['#','Field','Rule given (your note)','Source / Table','Existing DAG logic (inferred)','Logic used for Manual value','MV match %','Mismatch rows','Mismatch reason','Correction required']]
for i,f in enumerate(S,1):
    rem=REM[f]; ok=rem.str.startswith('Matched')
    rows.append([i,f,notes.get(f,''),*S[f][:3],f'{ok.mean()*100:.2f}%',int((~ok).sum()),S[f][3],S[f][4]])
TABN='MV_Field_Validation'
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
if any(s['properties']['title']==TABN for s in meta['sheets']): raise SystemExit('tab exists')
tid=call('POST',f'{API}/{SID}:batchUpdate',json={'requests':[{'addSheet':{'properties':{'title':TABN,'gridProperties':{'rowCount':len(rows)+3,'columnCount':10,'frozenRowCount':4}}}}]})['replies'][0]['addSheet']['properties']['sheetId']
call('PUT',f"{API}/{SID}/values/'{TABN}'!A1",params={'valueInputOption':'RAW'},json={'values':rows})
blue={'red':0.85,'green':0.9,'blue':0.97}
reqs=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':len(rows)},'cell':{'userEnteredFormat':{'wrapStrategy':'WRAP','verticalAlignment':'TOP'}},'fields':'userEnteredFormat(wrapStrategy,verticalAlignment)'}},
      {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':3,'endRowIndex':4},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'backgroundColor':blue}},'fields':'userEnteredFormat(textFormat,backgroundColor)'}},
      {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':1},'cell':{'userEnteredFormat':{'textFormat':{'bold':True}}},'fields':'userEnteredFormat.textFormat'}}]
reqs+=[{'updateDimensionProperties':{'range':{'sheetId':tid,'dimension':'COLUMNS','startIndex':i,'endIndex':i+1},'properties':{'pixelSize':w},'fields':'pixelSize'}} for i,w in enumerate([35,210,260,230,280,250,80,80,330,280])]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
for r_ in rows[4:]: print(r_[1], r_[6], r_[7])
