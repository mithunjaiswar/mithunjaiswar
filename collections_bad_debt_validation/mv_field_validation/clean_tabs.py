exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
MAN,REM=pickle.load(open('manual_out.pkl','rb'))
GREEN={'red':0.80,'green':0.92,'blue':0.80}; RED={'red':0.96,'green':0.80,'blue':0.80}
GREEN_L={'red':0.89,'green':0.96,'blue':0.89}; RED_L={'red':0.99,'green':0.90,'blue':0.90}
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets(properties,conditionalFormats)'})
sh={s['properties']['title']:s for s in meta['sheets']}
tid=sh[TAB]['properties']['sheetId']; ncols=sh[TAB]['properties']['gridProperties']['columnCount']
hdr=call('GET',f"{API}/{SID}/values/'{TAB}'!A4:ZZ4")['values'][0]
n=len(call('GET',f"{API}/{SID}/values/'{TAB}'!C5:C20000")['values']); last=4+n
# ---------- 1) MV_Raw_Data_Manual_Check: clean rows 1-2 ----------
call('POST',f"{API}/{SID}/values/'{TAB}'!A1:{col(ncols-1)}2:clear",json={})
r1=['']*len(hdr); r2=['']*len(hdr)
r1[0]='Match %'; r2[0]='Not Matched rows'; r1[1]='Green = 98% or above'; r2[1]='Red = below 98%'
pct_cols={}
for j,h in enumerate(hdr):
    if h.endswith(' Matched?') or h=='Final Status':
        rng=f'{col(j)}5:{col(j)}{last}'
        r1[j]=f'=IFERROR(COUNTIF({rng},"Matched")/(COUNTIF({rng},"Matched")+COUNTIF({rng},"Not Matched")),"")'
        r2[j]=f'=COUNTIF({rng},"Not Matched")'
        pct_cols[h.replace(' Matched?','')]=col(j)
call('PUT',f"{API}/{SID}/values/'{TAB}'!A1",params={'valueInputOption':'USER_ENTERED'},json={'values':[r1,r2]})
reqs=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':2},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'horizontalAlignment':'CENTER'}},'fields':'userEnteredFormat(textFormat,horizontalAlignment,backgroundColor)'}},
      {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':2},'cell':{'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.0%'}}},'fields':'userEnteredFormat.numberFormat'}},
      {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':1,'endRowIndex':2,'startColumnIndex':2},'cell':{'userEnteredFormat':{'numberFormat':{'type':'NUMBER','pattern':'#,##0'}}},'fields':'userEnteredFormat.numberFormat'}},
      {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':1,'endColumnIndex':2},'cell':{'userEnteredFormat':{'backgroundColor':GREEN,'textFormat':{'bold':True}}},'fields':'userEnteredFormat(backgroundColor,textFormat)'}},
      {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':1,'endRowIndex':2,'startColumnIndex':1,'endColumnIndex':2},'cell':{'userEnteredFormat':{'backgroundColor':RED,'textFormat':{'bold':True}}},'fields':'userEnteredFormat(backgroundColor,textFormat)'}}]
top={'sheetId':tid,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':2,'endColumnIndex':ncols}
reqs+=[{'addConditionalFormatRule':{'index':0,'rule':{'ranges':[top],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':'=AND(ISNUMBER(C1),C1>=0.98)'}]},'format':{'backgroundColor':GREEN}}}}},
       {'addConditionalFormatRule':{'index':0,'rule':{'ranges':[top],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':'=AND(ISNUMBER(C1),C1<0.98)'}]},'format':{'backgroundColor':RED}}}}}]
# Remark columns: green when Matched, light red otherwise
for f in MAN:
    j=hdr.index(f'{f} Remark'); c=col(j)
    rg={'sheetId':tid,'startRowIndex':4,'endRowIndex':last,'startColumnIndex':j,'endColumnIndex':j+1}
    reqs+=[{'addConditionalFormatRule':{'index':0,'rule':{'ranges':[rg],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':f'=LEFT({c}5,7)="Matched"'}]},'format':{'backgroundColor':GREEN_L}}}}},
           {'addConditionalFormatRule':{'index':0,'rule':{'ranges':[rg],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':f'=AND({c}5<>"",LEFT({c}5,7)<>"Matched")'}]},'format':{'backgroundColor':RED_L}}}}}]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
print('raw tab cleaned')
# ---------- 2) MV_Field_Validation: rebuild simple ----------
S=[ # field, source table, why not matching, fix needed
('revshare_days_working','fleet_weeklydata','—','—'),
('weekly_os','fleet_leasing_weeklydata','MV skips fine/adjustment-only rows (0 rent, 0 days) e.g. -1000','DAG: include adjustment rows (confirm with business)'),
('prev_carryforward_os','MV last week + mv_daily_recovery','Difference in round amounts (-1000, -175, -500); 506 partners new this week','Deep dive – need DAG logic'),
('os_to_deposit','mv_deposits_raw','23 rows only','—'),
('total_allocated_days','ssot_alloc_dealloc_base','5 rows only','—'),
('uber_active_days','fleet_dailytrip','—','—'),
('rental_days','fleet_leasing_weeklydata','MV rounds half days (4.5 → 5) – within ±1','—'),
('total_rent_amount','fleet_leasing_weeklydata','—','—'),
('last_payment_date_till_hissab_week','mv_daily_recovery','11 rows only','—'),
('last_jama_date','ssot_alloc_dealloc_base','MV puts a future date (21-Oct) when car not returned','DAG: keep blank if no jama'),
('last_car_number','fleet_leasing_weeklydata','MV shows only 1 car; partner used 2+ cars','DAG: list all cars "Car1, Car2"'),
('week_start_deposit','mv_deposits_raw','Old partners: opening deposit (30,000+) missing in mv_deposits_raw','Data: load old deposits in raw table'),
('week_end_deposit','mv_deposits_raw','Same as week_start_deposit','Data: load old deposits in raw table'),
('last_week_payment_habit','driver_repayment_habit','3 rows only','—'),
('last_week_nd_count','ssot + fleet_dailytrip','MV ≠ allocation days − active days','Deep dive – need DAG logic'),
('current_week_nd_count','ssot + fleet_dailytrip','MV ≠ allocation days − active days','Deep dive – need DAG logic'),
('hissab_week_active_days','fleet_dailytrip','MV has allocated days of 2 weeks (14), not trip days','DAG: count trip days in hisaab week'),
('tenure_days','driver_profile','MV counts till hisaab Sunday (+7 days)','DAG fix sent to Suraj (till driven week end)'),
('d2o_leave_days','driver_d2o_leaves_log','51 rows: MV also counts leave on 28-Sep','—'),
('active_inactive_flag','ssot_alloc_dealloc_base','MV = Active if allocated any day of week (car returned mid-week)','DAG: check last day of hisaab week'),
('next_weekly_os','MV next week row','—','—'),
('next_total_os','MV next week row','Next week still running – value changed','Refresh timing only'),
('next_week_end_deposit','MV next week row','Next week still running – value changed','Refresh timing only'),
('next_join_date','ssot_alloc_dealloc_base','MV puts a future date (21-Oct) for partners who never left','DAG: keep blank if never left'),
('in_car_recovery_driven_week','recovery_cars','26 rows only','—'),
('in_car_recovery_hissab_week','recovery_cars','45 rows only','—'),
('collection_till_wed','mv_daily_recovery','95 rows only','—'),
('bad_debt_collected','mv_daily_recovery + ssot','Filled for partners who never left','DAG: only money between leave and rejoin'),
('last_week_collection','mv_daily_recovery','—','—'),
('previous_week_collection','mv_daily_recovery','242 rows: no payment found that week','Deep dive'),
('partners_not_paid_2_weeks','derived','56 rows (follows previous_week_collection)','—'),
('cars_under_recovery_driven_week','recovery_cars','28 rows only','—'),
('cars_under_recovery_hissab_week','recovery_cars','48 rows only','—'),
('recovery_tat','recovery_cars','45 rows only','—'),
('active_fleet_cash_blocked','Cash Block API (not in DB)','Cannot check – DB has only current status','Need Cash Block history table'),
('location','ssot_alloc_dealloc_base','MV uses main hub (Thane), SSOT uses sub-hub (Vasai)','Decide which location to use'),
('revenue_type','fleet_leasing_weeklydata','184 rows: 2 products in one week','See Revenue_Type_Script_Fix tab'),
]
TABN='MV_Field_Validation'
F=f"'{TAB}'"
rows=[['MV Field Validation – Hisaab week 28-Sep-2026 (10,812 partners)'],
      ['Fields OK (98%+)','=COUNTIF(E5:E41,"OK")'],
      ['Fields to fix (below 98%)','=COUNTIF(E5:E41,"Fix")'],
      ['#','Field','Source table','Match %','Status','Why not matching','Fix needed']]
for i,(f,src,why,fix) in enumerate(S,1):
    rn=4+i
    rows.append([i,f,src,f"={F}!{pct_cols[f]}1",f'=IF(D{rn}="","",IF(D{rn}>=0.98,"OK","Fix"))',why,fix])
idx=sh[TABN]['properties']['index'] if TABN in sh else 1
reqs=([{'deleteSheet':{'sheetId':sh[TABN]['properties']['sheetId']}}] if TABN in sh else [])+[{'addSheet':{'properties':{'title':TABN,'index':idx,'gridProperties':{'rowCount':len(rows)+2,'columnCount':7,'frozenRowCount':4}}}}]
t2=call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT',f"{API}/{SID}/values/'{TABN}'!A1",params={'valueInputOption':'USER_ENTERED'},json={'values':rows})
L=len(rows); HDR={'red':0.85,'green':0.9,'blue':0.97}
reqs=[{'repeatCell':{'range':{'sheetId':t2,'startRowIndex':0,'endRowIndex':L},'cell':{'userEnteredFormat':{'wrapStrategy':'WRAP','verticalAlignment':'MIDDLE'}},'fields':'userEnteredFormat(wrapStrategy,verticalAlignment)'}},
 {'repeatCell':{'range':{'sheetId':t2,'startRowIndex':0,'endRowIndex':1},'cell':{'userEnteredFormat':{'textFormat':{'bold':True,'fontSize':13}}},'fields':'userEnteredFormat.textFormat'}},
 {'repeatCell':{'range':{'sheetId':t2,'startRowIndex':1,'endRowIndex':3,'startColumnIndex':0,'endColumnIndex':2},'cell':{'userEnteredFormat':{'textFormat':{'bold':True}}},'fields':'userEnteredFormat.textFormat'}},
 {'repeatCell':{'range':{'sheetId':t2,'startRowIndex':1,'endRowIndex':2,'startColumnIndex':1,'endColumnIndex':2},'cell':{'userEnteredFormat':{'backgroundColor':GREEN,'horizontalAlignment':'CENTER'}},'fields':'userEnteredFormat(backgroundColor,horizontalAlignment)'}},
 {'repeatCell':{'range':{'sheetId':t2,'startRowIndex':2,'endRowIndex':3,'startColumnIndex':1,'endColumnIndex':2},'cell':{'userEnteredFormat':{'backgroundColor':RED,'horizontalAlignment':'CENTER'}},'fields':'userEnteredFormat(backgroundColor,horizontalAlignment)'}},
 {'repeatCell':{'range':{'sheetId':t2,'startRowIndex':3,'endRowIndex':4},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'backgroundColor':HDR}},'fields':'userEnteredFormat(textFormat,backgroundColor)'}},
 {'repeatCell':{'range':{'sheetId':t2,'startRowIndex':4,'endRowIndex':L,'startColumnIndex':3,'endColumnIndex':4},'cell':{'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.0%'},'horizontalAlignment':'CENTER'}},'fields':'userEnteredFormat(numberFormat,horizontalAlignment)'}},
 {'repeatCell':{'range':{'sheetId':t2,'startRowIndex':4,'endRowIndex':L,'startColumnIndex':4,'endColumnIndex':5},'cell':{'userEnteredFormat':{'horizontalAlignment':'CENTER','textFormat':{'bold':True}}},'fields':'userEnteredFormat(horizontalAlignment,textFormat)'}},
 {'setBasicFilter':{'filter':{'range':{'sheetId':t2,'startRowIndex':3,'endRowIndex':L,'startColumnIndex':0,'endColumnIndex':7}}}}]
rr={'sheetId':t2,'startRowIndex':4,'endRowIndex':L,'startColumnIndex':0,'endColumnIndex':7}
reqs+=[{'addConditionalFormatRule':{'index':0,'rule':{'ranges':[rr],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':'=$E5="OK"'}]},'format':{'backgroundColor':GREEN_L}}}}},
       {'addConditionalFormatRule':{'index':0,'rule':{'ranges':[rr],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':'=$E5="Fix"'}]},'format':{'backgroundColor':RED_L}}}}}]
reqs+=[{'updateDimensionProperties':{'range':{'sheetId':t2,'dimension':'COLUMNS','startIndex':i,'endIndex':i+1},'properties':{'pixelSize':w},'fields':'pixelSize'}} for i,w in enumerate([40,260,210,80,70,420,320])]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
v=call('GET',f"{API}/{SID}/values/'{TABN}'!A2:G41")['values']
print(v[0],v[1]); print([ (r[1],r[3],r[4]) for r in v[3:8]])
