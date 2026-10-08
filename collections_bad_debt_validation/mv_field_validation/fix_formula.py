exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
MAN,REM=pickle.load(open('manual_out.pkl','rb'))
hdr=call('GET',f"{API}/{SID}/values/'{TAB}'!A4:ZZ4")['values'][0]
emp=call('GET',f"{API}/{SID}/values/'{TAB}'!C5:C20000")['values']; n=len(emp)
data=[]
for f in ['active_fleet_cash_blocked','partners_not_paid_2_weeks','cars_under_recovery_driven_week','cars_under_recovery_hissab_week']:
    j=hdr.index(f+' Matched?'); mvc,shc,mnc,mc=col(j-3),col(j-2),col(j-1),col(j)
    vals=[]
    for k in range(n):
        rn=5+k; mv_,ref=f'{mvc}{rn}',f'IF({mnc}{rn}<>"",{mnc}{rn},{shc}{rn})'
        vals.append([f'=IF(OR({ref}="",{ref}="N/A (not in Sheet)",{ref}="Not in Sheet"),"",IF(AND(OR(ISNUMBER({mv_}),{mv_}=""),ISNUMBER({ref})),IF(N({mv_})={ref},"Matched","Not Matched"),IF(LOWER(TRIM(TO_TEXT({mv_})))=LOWER(TRIM(TO_TEXT({ref}))),"Matched","Not Matched")))'])
    data.append({'range':f"'{TAB}'!{mc}5:{mc}{4+n}",'values':vals})
    jr=j+1; data.append({'range':f"'{TAB}'!{col(jr)}5:{col(jr)}{4+n}",'values':[[str(REM[f].get(e[0] if e else '',''))] for e in emp]})
call('POST',f'{API}/{SID}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data})
print('fixed')
