exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
from mv import COLS, num
C=COLS+['collection_pct']
m=pd.DataFrame(json.load(open('../w14/mv_sample.json')),columns=C).set_index('partner_etm',drop=False)
f=pd.read_pickle('../w14/flw_dw.pkl'); f['adj']=(f.rent==0)&(f.ad==0)
g=f.sort_values(['sd','id']).groupby('emp').agg(wos=('wos','sum'),rent=('rent','sum'),ad=('ad','sum'),kub=('kub','sum'),cars=('car',lambda x:', '.join(dict.fromkeys(c for c in x if c))))
gm=f[~f.adj].sort_values(['sd','id']).groupby('emp').car.agg(lambda x:', '.join(dict.fromkeys(c for c in x if c)))
def rt(x):
    lt=(x.lt or '').upper(); bv=int(float(x.bv or 0))
    if bv==6: return 'D2O'
    if bv==2 and lt.startswith('D2O'): return 'EV_Rent To Own'
    if bv==2: return 'EV_Leasing'
    if 'OWN' in lt: return 'Own Now'
    return 'Leasing'
top=f.sort_values(['emp','ad','sd','id'],ascending=[True,False,True,True]).groupby('emp').head(1)
rule=pd.Series({r.emp:rt(r) for r in top.itertuples()})
j=m.join(g).join(gm.rename('cars_main')); z=lambda s: num(s).fillna(0)
n=len(j)
def pct(ok): return f'{ok.mean()*100:.1f}%', int((~ok).sum())
checks=[
 ('weekly_os','Sum of ALL leasing rows of driven week (agreed rule)',*pct((z(j.weekly_os)-j.wos.fillna(0)).abs()<=1)),
 ('total_rent_amount','Sum of total_rent (leasing)',*pct((z(j.total_rent_amount)-j.rent.fillna(0)).abs()<=1)),
 ('rental_days','Sum of active_days (leasing), ±1',*pct((z(j.rental_days)-j.ad.fillna(0)).abs()<=1)),
 ('kuber_amount','Sum of kuber_amount (leasing)',*pct((z(j.kuber_amount)-j.kub.fillna(0)).abs()<=1)),
 ('last_car_number','All cars used in driven week',*pct(j.last_car_number.fillna('').str.replace(' ','')==j.cars_main.fillna('').str.replace(' ',''))),
 ('revenue_type','Product with most active days in driven week',*pct(j.revenue_type.fillna('')==rule.reindex(j.index).fillna(''))),
 ('total_os','= weekly_os + prev_carryforward_os',*pct((z(j.total_os)-z(j.weekly_os)-z(j.prev_carryforward_os)).abs()<=1)),
 ('last_jama_date','No future placeholder date',*pct(~(j.last_jama_date.fillna('')>'2026-10-09'))),
 ('next_join_date','No future placeholder date',*pct(~(j.next_join_date.fillna('')>'2026-10-09'))),
 ('hissab_week_active_days','Between 0 and 7 days',*pct(z(j.hissab_week_active_days)<=7)),
 ('collection_pct','Filled',*pct(j.collection_pct.fillna('')!='')),
]
TN='MV_Check_2026-09-14'
summ=[['MV check – hisaab week 14-Sep-2026 (driven week 07–13 Sep) – MV refreshed by admin on 09-Oct, '+str(n)+' partners (for_collections = 1)'],
      ['Checks below use data already pulled (leasing table + MV itself). Allocation / payments / deposits / cash-block checks will be added when the database responds.'],[],
      ['Field','Rule checked','Match %','Not matched rows','Status']]
summ+=[[a,b,c,d,'OK' if float(c[:-1])>=98 else 'Fix'] for a,b,c,d in checks]
summ+=[[],['RAW MV DATA (14-Sep) – all columns'],C]
data=[[('' if v is None else v) for v in r] for r in m.reset_index(drop=True).sort_values(['city','partner_etm'])[C].values.tolist()]
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
P={s['properties']['title']:s['properties'] for s in meta['sheets']}
reqs=([{'deleteSheet':{'sheetId':P[TN]['sheetId']}}] if TN in P else [])+[{'addSheet':{'properties':{'title':TN,'index':0,'gridProperties':{'rowCount':len(summ)+len(data)+5,'columnCount':len(C),'frozenColumnCount':0}}}}]
tid=call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT',f"{API}/{SID}/values/'{TN}'!A1",params={'valueInputOption':'RAW'},json={'values':summ})
start=len(summ)+1
for i in range(0,len(data),3000):
    call('PUT',f"{API}/{SID}/values/'{TN}'!A{start+i}",params={'valueInputOption':'USER_ENTERED'},json={'values':data[i:i+3000]})
G={'red':0.80,'green':0.92,'blue':0.80}; R={'red':0.96,'green':0.80,'blue':0.80}; HB={'red':0.85,'green':0.9,'blue':0.97}
L=4+len(checks)
reqs=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':1},'cell':{'userEnteredFormat':{'textFormat':{'bold':True,'fontSize':12}}},'fields':'userEnteredFormat.textFormat'}},
 {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':3,'endRowIndex':4,'startColumnIndex':0,'endColumnIndex':5},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'backgroundColor':HB}},'fields':'userEnteredFormat(textFormat,backgroundColor)'}},
 {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':start-2,'endRowIndex':start-1},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'backgroundColor':HB}},'fields':'userEnteredFormat(textFormat,backgroundColor)'}},
 {'addConditionalFormatRule':{'index':0,'rule':{'ranges':[{'sheetId':tid,'startRowIndex':4,'endRowIndex':L,'startColumnIndex':0,'endColumnIndex':5}],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':'=$E5="OK"'}]},'format':{'backgroundColor':G}}}}},
 {'addConditionalFormatRule':{'index':0,'rule':{'ranges':[{'sheetId':tid,'startRowIndex':4,'endRowIndex':L,'startColumnIndex':0,'endColumnIndex':5}],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':'=$E5="Fix"'}]},'format':{'backgroundColor':R}}}}},
 {'setBasicFilter':{'filter':{'range':{'sheetId':tid,'startRowIndex':start-2,'endRowIndex':start-1+len(data),'startColumnIndex':0,'endColumnIndex':len(C)}}}}]
reqs+=[{'updateDimensionProperties':{'range':{'sheetId':tid,'dimension':'COLUMNS','startIndex':i,'endIndex':i+1},'properties':{'pixelSize':w},'fields':'pixelSize'}} for i,w in enumerate([190,330,90,120,70])]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
for c in checks: print(c)
