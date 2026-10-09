exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
import re, csv
from mv import COLS, num
NSID=open('../w14/new_sid.txt').read().strip(); TN='MV_Raw_Data_Manual_Check'
C=COLS+['collection_pct']
m=pd.DataFrame(json.load(open('../w14/mv_sample.json')),columns=C)
m=m.sort_values(['city','partner_etm']).reset_index(drop=True); E=m.partner_etm
mi=m.set_index('partner_etm')
# ---- Sheet (Raw_Data) values
SPECS={s['pg']:s for s in pickle.load(open('../run3/specs.pkl','rb'))['specs']}
SPECS['total_collected_100_pct']={'pg':'total_collected_100_pct','sheet':'till_sun_100pct','kind':'num'}
SPECS['eip_tag']={'pg':'eip_tag','sheet':'eip_filter','kind':'eip'}
SHEET={(r['hisaab_week'],r['partner_et_id'].strip().upper()):r for r in csv.DictReader(open('../run3/sheet.csv')) if r['hisaab_week']=='2026-09-14'}
hdrs=next(iter(SHEET.values()))
def sheet_value(c,e):
    sp=SPECS.get(c)
    if c=='for_collections': return 1 if ('2026-09-14',e.upper()) in SHEET else 0
    if not sp or sp['kind'] not in ('num','txt','eip','bool') or sp.get('sheet') not in hdrs: return 'N/A (not in Sheet)'
    row=SHEET.get(('2026-09-14',e.upper()))
    if row is None: return 'Not in Sheet'
    x=row[sp['sheet']]
    if sp['kind']=='eip': return {'EIP':1,'SINGLE':0}.get(x,x)
    if sp['kind']=='bool': return {'Yes':'true','No':'false'}.get(x,x)
    if sp['kind']=='num': x=x.replace(',','').replace('%','')
    return x
# ---- Manual values computable now (leasing table, driven week 07-13 Sep)
f=pd.read_pickle('../w14/flw_dw.pkl'); f['adj']=(f.rent==0)&(f.ad==0)
g=f.sort_values(['sd','id']).groupby('emp').agg(wos=('wos','sum'),rent=('rent','sum'),ad=('ad','sum'),kub=('kub','sum'))
cars=f[~f.adj].sort_values(['sd','id']).groupby('emp').car.agg(lambda x:', '.join(dict.fromkeys(c for c in x if c)))
def rt(x):
    lt=(x.lt or '').upper(); bv=int(float(x.bv or 0))
    if bv==6: return 'D2O'
    if bv==2 and lt.startswith('D2O'): return 'EV_Rent To Own'
    if bv==2: return 'EV_Leasing'
    if 'OWN' in lt: return 'Own Now'
    return 'Leasing'
top=f.sort_values(['emp','ad','sd','id'],ascending=[True,False,True,True]).groupby('emp').head(1)
rule=pd.Series({r.emp:rt(r) for r in top.itertuples()})
MAN={'weekly_os':g.wos.round(2),'total_rent_amount':g.rent.round(2),'rental_days':g.ad,'kuber_amount':g.kub.round(2),'last_car_number':cars,'revenue_type':rule}
z=lambda s: num(s)
def rem(fld,e):
    mv=mi.at[e,fld]; man=MAN[fld].get(e)
    if man is None or (isinstance(man,float) and pd.isna(man)): return 'No leasing row in driven week (Rev share / Fixed Pay) – Need to Deep Dive'
    if fld in ('last_car_number','revenue_type'):
        if str(mv or '').replace(' ','').upper()==str(man).replace(' ','').upper(): return 'Matched'
        if fld=='last_car_number': return f'Partner used {str(man).count(",")+1} cars in driven week; MV shows only "{mv}"' if ',' in str(man) else f'MV "{mv}" vs driven-week car "{man}" – Need to Deep Dive'
        return f'Driven-week product with most days = {man}; MV {mv}'
    d=float(z(pd.Series([mv])).fillna(0)[0])-float(man)
    if abs(d)<=1: return 'Matched'
    if fld=='weekly_os':
        adj=f[(f.emp==e)&f.adj].wos.sum()
        return f'MV {mv} vs sum of all leasing rows {man:,.2f} (diff {d:,.0f}); adjustment-only rows {adj:,.0f}' 
    return f'MV {mv} vs leasing table {man:,.2f} (diff {d:,.0f}) – Need to Deep Dive'
# ---- read layout of the copied tab
meta=call('GET',f'{API}/{NSID}',params={'fields':'sheets.properties'})
p=[s['properties'] for s in meta['sheets'] if s['properties']['title']==TN][0]; tid=p['sheetId']
hdr=call('GET',f"{API}/{NSID}/values/'{TN}'!A5:ZZ5")['values'][0]
tmpl=call('GET',f"{API}/{NSID}/values/'{TN}'!A6:ZZ6",params={'valueRenderOption':'FORMULA'})['values'][0]
n=len(m); last=5+n
need=last+2-p['gridProperties']['rowCount']
if need>0: call('POST',f'{API}/{NSID}:batchUpdate',json={'requests':[{'appendDimension':{'sheetId':tid,'dimension':'ROWS','length':need}}]})
call('POST',f"{API}/{NSID}/values/'{TN}'!A6:{col(len(hdr)-1)}{last+10}:clear",json={})
def colname(h):
    for suf in (' (MV)',' (Sheet)',' (Manual)',' Matched?',' Remark'):
        if suf in h: return h.split(suf)[0], suf.strip()
    return h, None
def cell(v):
    if v is None: return ''
    if isinstance(v,(float,np.floating)):
        if math.isnan(v): return ''
        return int(v) if float(v).is_integer() else round(float(v),2)
    if isinstance(v,np.integer): return int(v)
    return v
cols=[]
for j,h in enumerate(hdr):
    base,kind=colname(h)
    t=tmpl[j] if j<len(tmpl) else ''
    if h=='Week': vals=['2026-09-14']*n
    elif h=='City': vals=list(m.city)
    elif h=='Employee/Agent': vals=list(E)
    elif h.startswith('collection_pct'): vals=list(m.collection_pct)
    elif kind=='(MV)': vals=list(m[base]) if base in m.columns else ['']*n
    elif kind=='(Sheet)': vals=[sheet_value(base,e) for e in E]
    elif kind=='(Manual)': vals=[cell(MAN[base].get(e)) if base in MAN else '' for e in E]
    elif kind=='Remark': vals=[rem(base,e) if base in MAN else '' for e in E]
    elif isinstance(t,str) and t.startswith('='): vals=[re.sub(r'(?<![A-Z])([A-Z]{1,3})6(?!\d)',lambda mm: mm.group(1)+str(rn),t) for rn in range(6,last+1)]
    else: vals=['']*n
    cols.append(vals)
rows=[[cell(cols[j][i]) for j in range(len(hdr))] for i in range(n)]
for i in range(0,n,1500):
    call('PUT',f"{API}/{NSID}/values/'{TN}'!A{6+i}",params={'valueInputOption':'USER_ENTERED'},json={'values':rows[i:i+1500]}); print('rows',i)
# fix header for collection_pct and fix top-row count ranges to new last row
data=[]
jc=[j for j,h in enumerate(hdr) if h.startswith('collection_pct')]
if jc: data.append({'range':f"'{TN}'!{col(jc[0])}5",'values':[['collection_pct (MV)']]})
top=call('GET',f"{API}/{NSID}/values/'{TN}'!A1:ZZ3",params={'valueRenderOption':'FORMULA'})['values']
newtop=[[re.sub(r'([A-Z]{1,3})6:([A-Z]{1,3})\d+',lambda mm: f'{mm.group(1)}6:{mm.group(2)}{last}',v) if isinstance(v,str) else v for v in r] for r in top]
data.append({'range':f"'{TN}'!A1",'values':newtop})
call('POST',f'{API}/{NSID}/values:batchUpdate',json={'valueInputOption':'USER_ENTERED','data':data})
print('filled',n)
