exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
from load import rows
import os
REF='1wkebsPPLwXnRYAuvRV_fhMGQLRxv6JwH-cYlaIEBjRw'
# ---------- 1. PG rows -> Raw_Data layout
F=['wk','emp','location','revenue_type','total_os','city','eip_tag','product_type','tot_coll','os_to_dep','till_wed','coll100','np2w','alloc_days','active','habit','fuel','prev_cf','weekly_os','bad_debt','bd_coll','in_car_rec','wed','wsd','tenure','last_pay','last_jama','last_car','lead_id','nd','tat','cpct']
ids=[1791561980137,1791562050455,1791562068852,1791562072385,1791562027417,1791562034973]
p=pd.DataFrame([x[:32] for x in rows(ids) if len(x)>=32],columns=F)
print('PG rows',len(p), p.wk.value_counts().sort_index().to_dict())
ref=json.load(open('../dash/ref_raw_lookup.json')); hdr=ref['hdr']; lk=ref['lk']
def n(x):
    try: return float(x)
    except: return 0.0
R=[]
for r in p.sort_values(['wk','city','emp']).itertuples(index=False):
    row=['']*len(hdr); i=len(R)+2
    al,an=lk.get(f'{r.wk}|{r.emp.upper()}',('',''))
    E=n(r.total_os); U=n(r.coll100); AQ=n(r.prev_cf)
    AS=min(U,max(-AQ,0)); AT=U-AS
    v={'hisaab_week':r.wk,'location':r.city,'revenue_type':r.revenue_type,'partner_et_id':r.emp,'negative_os':E,'city':r.city,
       'eip_filter':'EIP' if r.eip_tag=='1' else 'SINGLE','product_type':r.product_type,'total_recovery':n(r.tot_coll),
       'dp_to_os':n(r.os_to_dep),'till_wed_100pct':n(r.till_wed),'razorpay_recovery_100pct':U,'other_recovery_100pct':0,'phonepe_100pct':0,
       'adjustments_100pct':0,'dp_to_os_100pct\n':0,'till_sun_100pct':U,'recovery_pct':n(r.cpct),'last_paid_date':r.last_pay,'last_jama_date':r.last_jama,
       'last_car_number':r.last_car,'active_today?':'active' if r.active=='Active' else 'inactive','not_paid_last_2_weeks':n(r.np2w),
       'week_end_deposit':n(r.wed),'entire_week_active':1 if n(r.alloc_days)>=7 else 0,'1d_active':r.active,'payment_habit':r.habit,
       'not_driven_count':n(r.nd),'recovery_recommended_vehicle':f'=IF(AV{i}>=0,"No",IF(ABS(AV{i})>AB{i},"Yes","No"))',
       'asset_risk':al,'elc_filter':an or 'Non_ELC','fuel_type':r.fuel,'prev_carry_forward':AQ,'current_week_os':n(r.weekly_os),
       'prev_recovery':AS,'current_recovery':AT,'net_os':E+U,'bad_debt':n(r.bad_debt),'bad_debt_rec':n(r.bd_coll),'bad_debt_rec_100pct':n(r.bd_coll),
       'net_bad_debt':f'=AY{i}+AW{i}','lead_id':r.lead_id,'sd_week_start':n(r.wsd),'in_car_recovery':'Yes' if r.in_car_rec=='true' else 'No',
       'bad_debt_product_type':r.product_type,'tenure_days':n(r.tenure),'car_recovery_pending_tat':r.tat,'allocation_location':r.location}
    seen=set()
    for j,h in enumerate(hdr):
        if h in v and h not in seen: row[j]=v[h]; seen.add(h)
    R.append(row)
json.dump([hdr]+R,open('../dash/raw_data_pg.json','w')); print('Raw_Data rows',len(R))
