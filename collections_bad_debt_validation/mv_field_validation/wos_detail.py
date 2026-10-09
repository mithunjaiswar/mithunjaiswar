exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
from mv import mv, num
MAN,REM=pickle.load(open('manual_out_v2.pkl','rb')); m=mv()
f=pickle.load(open('flw_dw.pkl','rb')); f['adj']=(f.rent==0)&(f.ad==0)
bad=REM['weekly_os'][~REM['weekly_os'].str.startswith('Matched')].index
x=f[f.emp.isin(bad)].sort_values(['emp','adj','sd','id'])
allsum=x.groupby('emp').wos.sum(); mainsum=x[~x.adj].groupby('emp').wos.sum()
rows=[['weekly_os detail – driven week 21–27 Sep (fleet_leasing_weeklydata), 471 partners where MV ≠ sum of all rows'],
      ['weekly_os is a direct column of fleet_leasing_weeklydata. MV = sum of "Main" rows only; "Adjustment-only" rows (rent 0, active days 0) are left out.'],
      [],['Employee','City','Start date','Car number','weekly_os (table)','total_rent','active_days','Row type','MV weekly_os','Sum ALL rows','Sum MAIN rows only','MV = Main only?']]
for e,g in x.groupby('emp',sort=False):
    for r in g.itertuples():
        mvw=float(num(pd.Series([m.loc[e,'weekly_os']]))[0]); ms=mainsum.get(e,0.0)
        rows.append([e,m.loc[e,'city'],str(r.sd),r.car,float(r.wos),float(r.rent),float(r.ad),'Adjustment-only' if r.adj else 'Main',mvw,round(float(allsum[e]),2),round(float(ms),2),'Yes' if abs(mvw-ms)<=1 else 'No'])
TN='weekly_os_detail'
meta=call('GET',f'{API}/{SID}',params={'fields':'sheets.properties'})
P={s['properties']['title']:s['properties'] for s in meta['sheets']}
reqs=([{'deleteSheet':{'sheetId':P[TN]['sheetId']}}] if TN in P else [])+[{'addSheet':{'properties':{'title':TN,'index':P['MV_Raw_Data_Manual_Check_v2']['index']+1,'gridProperties':{'rowCount':len(rows)+5,'columnCount':12,'frozenRowCount':4}}}}]
tid=call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT',f"{API}/{SID}/values/'{TN}'!A1",params={'valueInputOption':'RAW'},json={'values':rows})
L=len(rows)
reqs=[{'repeatCell':{'range':{'sheetId':tid,'startRowIndex':0,'endRowIndex':1},'cell':{'userEnteredFormat':{'textFormat':{'bold':True,'fontSize':12}}},'fields':'userEnteredFormat.textFormat'}},
 {'repeatCell':{'range':{'sheetId':tid,'startRowIndex':3,'endRowIndex':4},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'backgroundColor':{'red':0.85,'green':0.9,'blue':0.97}}},'fields':'userEnteredFormat(textFormat,backgroundColor)'}},
 {'setBasicFilter':{'filter':{'range':{'sheetId':tid,'startRowIndex':3,'endRowIndex':L,'startColumnIndex':0,'endColumnIndex':12}}}},
 {'addConditionalFormatRule':{'index':0,'rule':{'ranges':[{'sheetId':tid,'startRowIndex':4,'endRowIndex':L,'startColumnIndex':0,'endColumnIndex':12}],'booleanRule':{'condition':{'type':'CUSTOM_FORMULA','values':[{'userEnteredValue':'=$H5="Adjustment-only"'}]},'format':{'backgroundColor':{'red':0.99,'green':0.9,'blue':0.9}}}}}}]
reqs+=[{'updateDimensionProperties':{'range':{'sheetId':tid,'dimension':'COLUMNS','startIndex':i,'endIndex':i+1},'properties':{'pixelSize':w},'fields':'pixelSize'}} for i,w in enumerate([100,90,90,110,110,90,90,120,100,100,120,110])]
call('POST',f'{API}/{SID}:batchUpdate',json={'requests':reqs})
print('rows',L-4, 'partners', x.emp.nunique(), 'MV=main only', sum(1 for r in rows[4:] if r[-1]=='Yes'))
