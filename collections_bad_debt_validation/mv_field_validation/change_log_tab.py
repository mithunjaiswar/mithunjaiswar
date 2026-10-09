exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
MAN,REM=pickle.load(open('manual_out.pkl','rb'))
EMP="'ETB00839'"  # change to any Employee ID
DW="'2026-09-21' and '2026-09-27'"; HW="'2026-09-28' and '2026-10-04'"
FD=f"join fleet_driver fd on fd.id = x.driver_id where fd.employee_id = {EMP}"
Q={
'revshare_days_working':f"select x.week_start_date, x.days_working from fleet_weeklydata x {FD} and x.week_start_date='2026-09-21';",
'weekly_os':f"select start_date, car_number, weekly_os, total_rent, active_days from fleet_leasing_weeklydata where partner_etm={EMP} and start_date between {DW} and coalesce(is_deleted,0)=0;  -- Manual = sum of ALL rows",
'prev_carryforward_os':f"select total_os from analytics.collections_bad_debt_mv where partner_etm={EMP} and hissab_week='2026-09-21';  -- + collections 21–27 Sep (see collection_till_wed query, change dates)",
'os_to_deposit':f"select date, deposit_type, amount from mv_deposits_raw where employee_id={EMP} and deposit_type='OS_TO_DEPOSIT' and date between {DW};  -- Manual = -sum",
'total_allocated_days':f"select allocation_datetime, jama_datetime, car_number from analytics.ssot_alloc_dealloc_base where employee_id={EMP} order by allocation_datetime desc limit 5;  -- count days inside 28 Sep–4 Oct",
'uber_active_days':f"select x.date, x.trips from fleet_dailytrip x {FD} and x.date between {DW} and x.trips>0;",
'rental_days':f"select start_date, active_days from fleet_leasing_weeklydata where partner_etm={EMP} and start_date between {DW} and coalesce(is_deleted,0)=0;",
'total_rent_amount':f"select start_date, total_rent from fleet_leasing_weeklydata where partner_etm={EMP} and start_date between {DW} and coalesce(is_deleted,0)=0;",
'last_payment_date_till_hissab_week':f"select max(date) from mv_daily_recovery where employee_id={EMP} and date<='2026-10-04' and amount>0 and recovery_type in ('razorpay_recovery','phonepe_recovery','other_positive_recovery');",
'last_jama_date':f"select allocation_datetime, jama_datetime from analytics.ssot_alloc_dealloc_base where employee_id={EMP} and jama_datetime<='2026-10-04 23:59:59' order by jama_datetime desc limit 1;",
'last_car_number':f"select string_agg(distinct car_number, ', ') from fleet_leasing_weeklydata where partner_etm={EMP} and start_date between {DW} and coalesce(is_deleted,0)=0 and (total_rent<>0 or active_days<>0);",
'week_start_deposit':f"select sum(amount) from mv_deposits_raw where employee_id={EMP} and date<'2026-09-28';",
'week_end_deposit':f"select sum(amount) from mv_deposits_raw where employee_id={EMP} and date<='2026-10-04';",
'last_week_payment_habit':f"select x.week_start_date, x.payment_habit from driver_repayment_habit x {FD} and x.week_start_date<'2026-09-28' order by x.week_start_date desc limit 1;",
'last_week_nd_count':"= total allocated days in 21–27 Sep (allocation query) - uber_active_days",
'current_week_nd_count':"= allocated days in 28 Sep–4 Oct - days with trips>0 in 28 Sep–4 Oct",
'hissab_week_active_days':f"select count(distinct x.date) from fleet_dailytrip x {FD} and x.date between {HW} and x.trips>0;",
'tenure_days':f"select sum(least(coalesce(dp.end_date::date,'2026-09-27'),'2026-09-27') - dp.start_date::date + 1) from driver_profile dp join fleet_driver fd on fd.id=dp.driver_id where fd.employee_id={EMP} and dp.start_date::date<='2026-09-27';",
'd2o_leave_days':f"select x.start_date, x.end_date, x.days, x.reason from driver_d2o_leaves_log x {FD} and coalesce(x.reason,'')<>'add' and x.end_date>='2026-09-21' and x.start_date<='2026-09-27';",
'active_inactive_flag':f"select allocation_datetime, jama_datetime from analytics.ssot_alloc_dealloc_base where employee_id={EMP} and allocation_datetime<'2026-10-05' and (jama_datetime is null or jama_datetime>='2026-10-04');  -- row = Active on 4 Oct",
'next_weekly_os':f"select weekly_os, total_os, week_end_deposit from analytics.collections_bad_debt_mv where partner_etm={EMP} and hissab_week='2026-10-05';",
'next_total_os':"same as next_weekly_os query",
'next_week_end_deposit':"same as next_weekly_os query",
'next_join_date':f"select allocation_datetime from analytics.ssot_alloc_dealloc_base where employee_id={EMP} order by allocation_datetime desc limit 3;  -- first allocation after last jama",
'in_car_recovery_driven_week':f"select x.created_at, x.updated_at, x.recovery_status, x.car_id from recovery_cars x {FD} order by x.created_at desc limit 5;  -- open between 21–27 Sep",
'in_car_recovery_hissab_week':"same recovery query, window 28 Sep–4 Oct",
'collection_till_wed':f"select recovery_type, sum(amount) from mv_daily_recovery where employee_id={EMP} and date between '2026-09-28' and '2026-09-30' group by 1;  -- Manual = total",
'bad_debt_collected':"Partner never left (no jama) → should be 0; partner left → sum collections between jama date and next join date",
'last_week_collection':f"select recovery_type, sum(amount) from mv_daily_recovery where employee_id={EMP} and date between '2026-09-14' and '2026-09-20' and recovery_type in ('razorpay_recovery','phonepe_recovery','other_positive_recovery','deposit_to_os','positive_adjustment') group by 1;",
'previous_week_collection':"same as last_week_collection, dates 2026-09-07 to 2026-09-13",
'partners_not_paid_2_weeks':"= 1 when last_week_collection = 0 AND previous_week_collection = 0",
'cars_under_recovery_driven_week':"same recovery query – count cars open 21–27 Sep",
'cars_under_recovery_hissab_week':"same recovery query – count cars open 28 Sep–4 Oct",
'recovery_tat':"TAT should be filled only when cars_under_recovery_hissab_week > 0",
'active_fleet_cash_blocked':f"select x.status, x.reason, x.updated_at from driver_cashblock x {FD};  -- current status only",
'location':f"select allocation_datetime, location from analytics.ssot_alloc_dealloc_base where employee_id={EMP} order by allocation_datetime desc limit 3;",
'revenue_type':f"select start_date, business_vertical_id, leasing_type, active_days from fleet_leasing_weeklydata where partner_etm={EMP} and start_date between {DW} and coalesce(is_deleted,0)=0;  -- row with most active days",
}
rows=[['WHAT I CHANGED – read this first'],
 ['Important','I did NOT change the MV table or any source data (DB is read-only). "Corrected" = the expected value I recomputed from the source tables, written in the (Manual) columns, with the reason in the Remark columns.'],
 [''],
 ['#','Where','What was changed','How to check'],
 [1,'MV_Raw_Data_Manual_Check','Filled the "(Manual)" column for the 37 fields in your doc, for all 10,812 partners (hisaab week 2026-09-28).','Filter "<field> Matched?" = Not Matched → compare MV vs Manual on that row.'],
 [2,'MV_Raw_Data_Manual_Check','Inserted 37 new columns "<field> Remark" right after each "<field> Matched?". Text = "Matched", the mismatch reason, or "Need to Deep Dive – Manual Validation Required".','Filter the Remark column to see each reason.'],
 [3,'MV_Raw_Data_Manual_Check','Your 37 instruction notes in rows 5–6 (Manual cells) were replaced by values; the notes are kept in MV_Field_Validation → "Rule given".','Rows 5–6 now hold values like every other row.'],
 [4,'MV_Raw_Data_Manual_Check','Matched? formula changed to EXACT match (was ±1) only for: active_fleet_cash_blocked, partners_not_paid_2_weeks, cars_under_recovery_driven_week, cars_under_recovery_hissab_week – with ±1 every 0/1 flag showed Matched.','Those 4 Matched? columns now compare exact.'],
 [5,'MV_Raw_Data_Manual_Check','NOT changed: your header colours, other formatting, other columns, rows 1–2 count formulas (they shifted automatically with the new columns).','—'],
 [6,'MV_Field_Validation (new tab)','One row per field: rule given, source table, existing DAG logic (inferred), logic used for Manual, MV match %, mismatch rows, reason, correction.','Read top to bottom.'],
 [7,'Change_Log (this tab)','This list + one SQL per field to check any partner yourself.','Change the Employee ID in the query (ETB00839) and run in PG Admin.'],
 [8,'Other tabs','Not touched: Filter wise employee view, Sheet2, Employee_Level, Summary, RCA / fix tabs.','—'],
 [''],
 ['FIELD','MV match %','Manual value = (logic used)','Check query (read only – replace ETB00839 with any Employee ID)']]
import pandas as pd
fv=call('GET',f"{API}/{SID}/values/'MV_Field_Validation'!B5:F45")['values']
logic={r[0]:r[4] if len(r)>4 else '' for r in fv}
for f in MAN:
    ok=REM[f].str.startswith('Matched')
    rows.append([f,f'{ok.mean()*100:.2f}%',logic.get(f,''),Q[f]])
TABN='Change_Log'
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
old=[s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title']==TABN]
reqs=[{'deleteSheet':{'sheetId':i}} for i in old]+[{'addSheet':{'properties':{'title':TABN,'index':0,'gridProperties':{'rowCount':len(rows)+3,'columnCount':4,'frozenRowCount':1}}}}]
tid=call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT',f"{API}/{SID}/values/'{TABN}'!A1",params={'valueInputOption':'RAW'},json={'values':rows})
blue={'red':0.85,'green':0.9,'blue':0.97}
hdr_rows=[0,3,13]
reqs=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':len(rows)},'cell':{'userEnteredFormat':{'wrapStrategy':'WRAP','verticalAlignment':'TOP'}},'fields':'userEnteredFormat(wrapStrategy,verticalAlignment)'}}]
reqs+=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':i,'endRowIndex':i+1,'startColumnIndex':0,'endColumnIndex':4},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'backgroundColor':blue}},'fields':'userEnteredFormat(textFormat,backgroundColor)'}} for i in hdr_rows]
reqs+=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':14,'endRowIndex':len(rows),'startColumnIndex':3,'endColumnIndex':4},'cell':{'userEnteredFormat':{'textFormat':{'fontFamily':'Roboto Mono','fontSize':9}}},'fields':'userEnteredFormat.textFormat'}}]
reqs+=[{'updateDimensionProperties':{'range':{'sheetId':tid,'dimension':'COLUMNS','startIndex':i,'endIndex':i+1},'properties':{'pixelSize':w},'fields':'pixelSize'}} for i,w in enumerate([230,170,420,620])]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
print('ok', len(rows))
