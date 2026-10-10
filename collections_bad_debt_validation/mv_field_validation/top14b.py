exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
NS=open('../w14/new_sid.txt').read().strip(); TN='MV_Raw_Data_Manual_Check'
hdr=call('GET',f"{API}/{NS}/values/'{TN}'!A5:ZZ5")['values'][0]; HX={h:j for j,h in enumerate(hdr)}
r2=call('GET',f"{API}/{NS}/values/'{TN}'!A2:ZZ3")['values']
g=lambda r,j: r[j] if j<len(r) else ''
T={
'prev_carryforward_os':('Checked: prev hisaab week 07-Sep total_os + collected (MV rows). New partners without a 07-Sep row are compared with Raw_Data sheet.','None.'),
'os_to_deposit':('Checked vs mv_deposits_raw OS_TO_DEPOSIT in driven week 07-13 Sep. ','Check Not Matched rows (Remark).'),
'week_start_deposit':('Checked vs mv_deposits_raw before 14-Sep (excl. Own Now transfers). ','Check Not Matched rows (Remark).'),
'week_end_deposit':('Checked vs mv_deposits_raw till 20-Sep (excl. Own Now transfers). ','Check Not Matched rows (Remark).'),
'last_payment_date_till_hissab_week':('Checked vs mv_daily_recovery: last REAL payment (razorpay/phonepe/other) till 20-Sep. MV correctly ignores adjustments & deposit-to-OS.','None – MV correct (sheet allows ±1 day).'),
'collection_till_wed':('Checked vs net mv_daily_recovery 14-16 Sep. ','Check Not Matched rows (Remark).'),
'last_week_collection':('Checked: MV = positive payments of week BEFORE driven week (31 Aug-06 Sep). 100% match. Helper field.','None (helper for not-paid-2-weeks).'),
'next_weekly_os':('Checked vs MV 21-Sep row. Lookahead field. 1,069 partners have no 21-Sep row (left) – not compared.','None – lookahead (used for next-week view).'),
'next_total_os':('Checked vs MV 21-Sep row total_os. Lookahead field. Same as next_weekly_os.','None.'),
'next_week_end_deposit':('Checked vs MV 21-Sep row week_end_deposit. Lookahead field.','None.'),
}
data=[]
for f,(i,a) in T.items():
    j=HX[f+' (MV)']; jm=HX[f+' Matched?']
    pc,nm=g(r2[0],jm),g(r2[1],jm)
    data.append({'range':f"'{TN}'!{col(j)}1:{col(j)}3",'values':[[f'{i} Match {pc}, {nm} not matched.'],[a],['Filter Matched? = Not Matched and read Remark.']]})
    print(f,pc,nm)
call('POST',f'{API}/{NS}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data})
