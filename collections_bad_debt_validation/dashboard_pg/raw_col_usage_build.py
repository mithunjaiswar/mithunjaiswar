import json,re
H=["hisaab_week","location","revenue_type","partner_et_id","negative_os","city","eip_filter","product_type","total_recovery","razorpay_recovery","other_recovery","phonepe_recovery","adjustments","dp_to_os","till_wed_100pct","razorpay_recovery_100pct","other_recovery_100pct","phonepe_100pct","adjustments_100pct","dp_to_os_100pct","till_sun_100pct","recovery_pct","last_paid_date","last_jama_date","last_car_number","active_today?","not_paid_last_2_weeks","week_end_deposit","entire_week_active","1d_active","os_gt_deposit_pct","payment_habit","not_driven_count","recovery_recommended_vehicle","gps_inactive","attempts","connects","asset_risk","et_rank","elc_filter","fuel_type","carry_forward_os","prev_carry_forward","current_week_os","prev_recovery","current_recovery","advance_recovery","net_os","bad_debt","bad_debt_rec","bad_debt_rec_100pct","net_bad_debt","lead_id","sd_week_start","in_car_recovery","bad_debt_product_type","carry_forward_os_Bu","sd_Surpass %","Deposit_Bucket","sd_week_start Filter","Tenure_Buckets","tenure_days","uber_tenure_tag","source_channel","car_recovery_startdate","car_recovery_enddate","car_recovery_pending_tat","firstdate_critical_risk","<60_L2w","bad_debt","allocation_location","allocation_location","OWN NOW SWASTIK"," ","bad_debt_attrition","exception_status","potential_bad_debt (calling rule: Inactive, OS+deposit; Own Now deposit nahi)","","OWN NOW SWASTIK","OWN NOW SWASTIK Bad Debt"]
R={
1:"Hisaab week (Monday) - har tab ka week filter",2:"Hub / location name",3:"Revenue type (D2O, Own Now, Leasing...) - product grouping",4:"Pilot ETM ID - pilot count / lookup / exclusions match",
5:"Weekly OS (negative = owes) - Total OS / collection % ka base",6:"City - city filter in all views",7:"EIP / SINGLE split",8:"Product type - product filter in all views",
9:"Week me total collection (cap nahi)",10:"Razorpay se collection",11:"Other positive recovery",12:"PhonePe recovery",13:"Positive adjustments",14:"Deposit to OS (deposit se OS adjust)",
15:"Wed tak collection (OS tak capped) - till Wed %",16:"Razorpay collection (OS tak capped)",17:"Other recovery (capped)",18:"PhonePe (capped)",19:"Adjustments (capped)",20:"DP to OS (capped)",
21:"Sunday tak collection (OS tak capped) - main Collected / Collection %",22:"Recovery % (collected / OS, max 100%)",23:"Last payment date",24:"Last jama (car return) date",25:"Last car number",
26:"Active today flag (active / inactive)",27:"Pichhle 2 hafte koi payment nahi (count)",28:"Week end deposit - surpass / bad debt calc",29:"Pura week active tha (1/0)",30:"Active / Inactive status (pilot base filter)",
31:"OS / deposit %",32:"Payment habit (Excellent / Good / Defaulter...)",33:"Not driven days count",34:"Car recovery recommended (Yes/No)",35:"GPS inactive flag",36:"Calling attempts",37:"Calling connects",
38:"Asset risk bucket",39:"ET rank",40:"ELC / Non ELC filter",41:"Fuel type (CNG / EV) filter",42:"Carry forward OS (pichhle hafton ka bacha OS)",43:"Previous carry forward",44:"Current week OS (sirf is hafte ka)",
45:"Previous OS ki recovery",46:"Current week OS ki recovery",47:"Advance recovery (OS se zyada payment)",48:"Net OS (OS + collection)",49:"Bad debt amount (weekly)",50:"Bad debt recovered (next week paid)",
51:"Bad debt recovered (funnel, capped)",52:"Net bad debt",53:"Lead ID",54:"Week start deposit",55:"In car recovery (Yes/No)",56:"Bad debt ka product type",57:"Carry forward OS bucket",58:"SD surpass % (OS / deposit)",
59:"Deposit bucket (0, 1K-5K, ... 30K+) - SD / deposit views",60:"Week start deposit (filter copy)",61:"Tenure bucket (0-30 ... 120+) - tenure views",62:"Tenure days",63:"Uber tenure tag (New / Old in Uber)",
64:"Source channel (join channel)",65:"Car recovery start date",66:"Car recovery end date",67:"Car recovery pending TAT (days)",68:"First critical risk date",69:"<60 payment in last 2 weeks (count)",
70:"Attrition bad debt flag (header bad_debt - duplicate naam AW jaisa)",71:"Allocation location",72:"Allocation location (duplicate column)",73:"OWN NOW SWASTIK (purana column, values 0/NaN)",74:"Khaali header",
75:"Bad debt attrition",76:"HELPER: Include / Exclude (Exclusions tab se) - har view ka main filter",77:"HELPER: potential bad debt (Inactive + OS beyond deposit; Own Now me deposit nahi)",78:"Khaali header",
79:"MANUAL: Swastik ka OWN NOW bad debt input (Swastik sheet se)",80:"HELPER: CA + AW = Own Now Swastik bad debt"}
UNK={53,73,74,75,78,72,70,35,39}
helper={76:"Formula (ARRAYFORMULA)",77:"Formula (ARRAYFORMULA)",80:"Formula (har row)",79:"Manual input"}
internal={1:["BX helper"],4:["BX helper"],30:["BY helper"],5:["BY helper"],48:["BY helper"],8:["BY helper"],28:["BY helper"],79:["CB helper"],49:["CB helper"]}
u=json.load(open('usage_5.json'))
def col(n):
    s=''
    while n: n,r=divmod(n-1,26); s=chr(65+r)+s
    return s
rows=[["Col","Header","Type","Used? (Yes/No)","# formula refs","Used in tabs","Kyu use hota hai / kya hai","Pata hai? (Known / Not sure)"]]
cnt={'Yes':0,'No':0}
for n in range(1,81):
    t=u.get(str(n),{})
    tabs=sorted(t, key=lambda k:-t[k])+internal.get(n,[])
    used='Yes' if tabs else 'No'; cnt[used]+=1
    typ=helper.get(n,"Query data (paste)")
    know='Not sure' if (n in UNK or not tabs and n not in helper) else 'Known'
    if n in UNK: know='Not sure'
    rows.append([col(n),H[n-1],typ,used,sum(t.values()),", ".join(tabs) if tabs else "-",R[n],know])
json.dump(rows,open('rows.json','w'))
print(cnt, len(rows))
for r in rows: 
    if r[3]=='No': print(r[0],r[1],r[7])
