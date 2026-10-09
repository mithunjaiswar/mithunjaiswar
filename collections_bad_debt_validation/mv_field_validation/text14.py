exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
NSID=open('../w14/new_sid.txt').read().strip(); TN='MV_Raw_Data_Manual_Check'
hdr=call('GET',f"{API}/{NSID}/values/'{TN}'!A5:ZZ5")['values'][0]
r2=call('GET',f"{API}/{NSID}/values/'{TN}'!A2:ZZ3")['values']
P={h[:-9]:(r2[0][j] if j<len(r2[0]) else '', r2[1][j] if j<len(r2[1]) else '') for j,h in enumerate(hdr) if h.endswith(' Matched?')}
CHK={
'weekly_os':('Checked vs leasing table (ALL driven-week rows, agreed rule). Admin fix worked – only a few rows differ.','None – check the few Not Matched rows.'),
'total_rent_amount':('Checked vs leasing table total_rent.','None.'),
'rental_days':('Checked vs leasing table active_days (±1).','None.'),
'kuber_amount':('Checked vs leasing table kuber_amount.','Check Not Matched rows (Remark).'),
'last_car_number':('Checked: all cars used in driven week. Partners with 2+ cars still show only 1 car in MV.','DAG: list all driven-week cars "Car1, Car2".'),
'revenue_type':('Checked: product with most active days in driven week.','Check Not Matched rows (Remark).'),
}
data=[{'range':f"'{TN}'!A4",'values':[['Hisaab week 14-Sep-2026 (driven 07–13 Sep) – MV after admin DAG change (refreshed 09-Oct). Manual filled only for fields checked so far; other fields compare MV vs Raw_Data sheet.']]}]
for j,h in enumerate(hdr):
    if not h.endswith(' (MV)') and not h.startswith('previous_week_collection (MV)'): continue
    f=h.split(' (MV)')[0]
    pc,nm=P.get(f,('',''))
    if f in CHK:
        i,a=CHK[f]; i=f'{i} Match {pc}, {nm} rows not matched.'; s='Filter Matched? = Not Matched and read Remark.'
    else:
        i=f'Not checked against source tables for 14-Sep yet (DB timing out). Matched? = MV vs Raw_Data sheet: {pc}.'; a='Pending source-table check.'; s='—'
    data.append({'range':f"'{TN}'!{col(j)}1:{col(j)}3",'values':[[i],[a],[s]]})
call('POST',f'{API}/{NSID}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data})
for f in CHK: print(f, P.get(f))
