import json,time
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS=open('../dash/dash_sid.txt').read().strip()
REF='1wkebsPPLwXnRYAuvRV_fhMGQLRxv6JwH-cYlaIEBjRw'
NS=open('../w14/new_sid.txt').read().strip()
out={}
# 1 Summary Delhi/Own Now
call('POST',f'{API}/{DS}/values:batchUpdate',json={'valueInputOption':'RAW','data':[{'range':"'Summary'!B2",'values':[['Delhi NCR']]},{'range':"'Summary'!B5",'values':[['Own Now']]}]})
time.sleep(20)
out['sum_new']=call('GET',f"{API}/{DS}/values/'Summary'!A1:J86")['values']
call('POST',f'{API}/{DS}/values:batchUpdate',json={'valueInputOption':'RAW','data':[{'range':"'Summary'!B2",'values':[['*']]},{'range':"'Summary'!B5",'values':[['*']]}]})
# 2 WBR ours vs ref
out['wbr_new']=call('GET',f"{API}/{DS}/values/'WBR'!A1:H486")['values']
out['wbr_ref']=call('GET',f"{API}/{REF}/values/'WBR View'!A1:H486")['values']
# 3 field-level match % 14-Sep
hdr=call('GET',f"{API}/{NS}/values/'MV_Raw_Data_Manual_Check'!A5:ZZ5")['values'][0]
r2=call('GET',f"{API}/{NS}/values/'MV_Raw_Data_Manual_Check'!A2:ZZ3")['values']
g=lambda r,j: r[j] if j<len(r) else ''
out['field_match']={h[:-9]:(g(r2[0],j),g(r2[1],j)) for j,h in enumerate(hdr) if h.endswith(' Matched?')}
out['n14']=len(call('GET',f"{API}/{NS}/values/'MV_Raw_Data_Manual_Check'!C6:C20000")['values'])
json.dump(out,open('../dash/doc_data.json','w'))
print(out['wbr_ref'][0:6]); print(out['wbr_new'][0:6]); print(out['n14'])
