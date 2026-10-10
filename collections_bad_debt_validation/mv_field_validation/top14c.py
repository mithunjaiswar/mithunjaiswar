import time
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
NS=open('../w14/new_sid.txt').read().strip(); TN='MV_Raw_Data_Manual_Check'
hdr=call('GET',f"{API}/{NS}/values/'{TN}'!A5:ZZ5")['values'][0]; HX={h:j for j,h in enumerate(hdr)}
T={
'last_week_payment_habit':('Checked: last driver_repayment_habit entry before 14-Sep (agreed rule #14). Admin fix worked.','None – check few rows.'),
'tenure_days':('Checked vs driver_profile stints till driven week end 13-Sep. Mismatch rows: MV LOWER by ~9-10 days (MV skips a stint/gap).','DAG: use sum of all driver_profile stints till hissab_week-1.'),
'uber_active_days':('Checked: fleet_dailytrip days with trips in driven week 07-13 Sep. 100% after admin fix.','None.'),
'hissab_week_active_days':('Checked: fleet_dailytrip days with trips in hisaab week 14-20 Sep. 100% after admin fix.','None.'),
'total_allocated_days':('Checked: unique SSOT allocation days in hisaab week. ~506 rows: MV counts car-swap day twice; ~131 rows: MV adds driven + hisaab week (e.g. 14).','DAG: count DISTINCT allocated dates in hisaab week only.'),
'last_week_nd_count':('Checked: allocated days - trip days (driven week).','None – check few rows.'),
'current_week_nd_count':('Checked: allocated days - trip days (hisaab week).','None – check few rows.'),
'active_inactive_flag':('Checked: car allocated on hisaab week last day (20-Sep). 100% after admin fix.','None.'),
'last_jama_date':('Checked: last REAL jama till 20-Sep (car swap = jama+new car same day is ignored). Mismatch: partner left & rejoined inside the weeks – MV keeps it blank.','Decide: show jama date even if partner rejoined before week end?'),
'next_join_date':('Checked: next allocation after last real jama. Mismatch: rejoin before 20-Sep – MV blank.','Same decision as last_jama_date.'),
'location':('Checked vs SSOT allocation location (driven week). MV uses parent hub names (Delhi-Sukhrali, Thane, Chennai Vanagram) – different location master.','Decide master: SSOT allocation location vs hub. Map hub -> location.'),
'd2o_leave_days':('Checked: driver_d2o_leaves_log days in driven week 07-13 Sep.','Check Not Matched rows.'),
'in_car_recovery_driven_week':('Checked vs recovery_cars open in driven week.','Check Not Matched rows.'),
'in_car_recovery_hissab_week':('Checked vs recovery_cars open in hisaab week.','Check Not Matched rows.'),
'cars_under_recovery_driven_week':('Checked: count of cars open in recovery_cars (driven week).','Check Not Matched rows.'),
'cars_under_recovery_hissab_week':('Checked: count of cars open in recovery_cars (hisaab week).','Check Not Matched rows.'),
'recovery_tat':('Checked: TAT filled only when car under recovery in hisaab week.','Check Not Matched rows.'),
'active_fleet_cash_blocked':('Checked: BLOCK entry in driver_cashblock_details_logs on 20-Sep (agreed rule #13). Admin fix worked.','None.'),
}
time.sleep(8)
r2=call('GET',f"{API}/{NS}/values/'{TN}'!A2:ZZ3")['values']
g=lambda r,j: r[j] if j<len(r) else ''
data=[]
for f,(i,a) in T.items():
    j=HX[f+' (MV)']; jm=HX[f+' Matched?']; pc,nm=g(r2[0],jm),g(r2[1],jm)
    data.append({'range':f"'{TN}'!{col(j)}1:{col(j)}3",'values':[[f'{i} Match {pc}, {nm} not matched.'],[a],['Filter Matched? = Not Matched and read Remark.']]})
call('POST',f'{API}/{NS}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data})
time.sleep(3)
r2=call('GET',f"{API}/{NS}/values/'{TN}'!A2:ZZ3")['values']
for j,h in enumerate(hdr):
    if h.endswith(' Matched?'): print(f'{h[:-9]:36s} {g(r2[0],j):>7s} {g(r2[1],j):>6s}')
