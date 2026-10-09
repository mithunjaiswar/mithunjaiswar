import pickle, pandas as pd
from mv import mv, num
MAN,REM=pickle.load(open('manual_out.pkl','rb')); m=mv()
def fmt(v):
    if v is None or (isinstance(v,float) and pd.isna(v)) or v=='': return 'blank'
    try:
        x=float(v)+0.0; x=0.0 if x==0 else x; return f'{x:,.0f}' if x==int(x) else f'{x:,.2f}'
    except: return str(v)
def ex(f, pick=None):
    bad=REM[f][~REM[f].str.startswith('Matched')]
    if pick: bad=bad[[pick(e) for e in bad.index]]
    if not len(bad): return ''
    e=bad.index[0]
    return f'Example: {e} → MV = {fmt(m.loc[e,f])}, Correct = {fmt(MAN[f][e])}.'
def nbad(f): return int((~REM[f].str.startswith('Matched')).sum())
T={}
OK=('No issue – all rows match.','No action needed.')
def small(f): return (f'Only {nbad(f)} rows differ (very small gap). {ex(f)}', 'Check these few rows manually – no DAG change needed.')
T['revshare_days_working']=OK; T['uber_active_days']=OK; T['total_rent_amount']=OK; T['last_week_collection']=OK; T['next_weekly_os']=OK
for f in ['os_to_deposit','total_allocated_days','last_payment_date_till_hissab_week','last_week_payment_habit','in_car_recovery_driven_week','in_car_recovery_hissab_week','cars_under_recovery_driven_week','cars_under_recovery_hissab_week','recovery_tat','collection_till_wed']: T[f]=small(f)
T['weekly_os']=(f'MV leaves out small fine/adjustment rows (rent 0, days 0, e.g. -1000 penalty on old car). {ex("weekly_os")}','DAG: add these fine/adjustment rows into weekly_os (confirm with business).')
T['prev_carryforward_os']=(f'MV is not equal to "last week total OS + payments made in driven week". Gap is usually a round amount (-1000, -175, -500). {ex("prev_carryforward_os")}','Share the DAG formula for carry-forward – we will check which extra charge it adds.')
T['rental_days']=('MV rounds half days. Example: car ran 4.5 days → MV shows 5. (Inside ±1, so counted as matched.)','No action – rounding only.')
T['last_jama_date']=(f'Car is NOT returned yet, but MV shows a future date (21-Oct). {ex("last_jama_date")}','DAG: keep this blank when the car is not returned.')
T['last_car_number']=(f'Partner drove 2 or more cars in the driven week, MV shows only 1 car. {ex("last_car_number", lambda e: "," in str(MAN["last_car_number"][e]))}','DAG: show all cars of the driven week as "Car1, Car2".')
T['week_start_deposit']=(f'Old partners: their first deposit (mostly 30,000) is missing in the deposit raw table, so raw total is lower than MV. {ex("week_start_deposit")}','Data team: add old/opening deposits into mv_deposits_raw.')
T['week_end_deposit']=(f'Same as week_start_deposit – old deposit missing in raw table. {ex("week_end_deposit")}','Data team: add old/opening deposits into mv_deposits_raw.')
T['last_week_nd_count']=(f'ND should be "days car allocated − days car ran" in driven week, MV gives a different number. {ex("last_week_nd_count")}','Share the DAG logic for ND count – we will compare.')
T['current_week_nd_count']=(f'Same ND rule for hisaab week – MV gives a different number. {ex("current_week_nd_count")}','Share the DAG logic for ND count – we will compare.')
T['hissab_week_active_days']=(f'MV shows days car was allocated in 2 weeks (14), not days car actually ran in hisaab week. {ex("hissab_week_active_days")}','DAG: count only days with trips in the hisaab week.')
T['tenure_days']=(f'MV counts tenure 7 days extra (till hisaab week Sunday instead of driven week end). {ex("tenure_days")}','DAG: count tenure till driven week end (fix already sent to Suraj).')
T['d2o_leave_days']=(f'Only {nbad("d2o_leave_days")} rows: MV also counts leave taken on 28-Sep (next week). {ex("d2o_leave_days")}','DAG: count only leave inside the driven week.')
T['active_inactive_flag']=(f'Car was returned in the middle of hisaab week, but MV still says Active. {ex("active_inactive_flag")}','DAG: check if car is allocated on the LAST day of hisaab week.')
T['next_total_os']=(f'Partner has NO row in next week (left / not in collections), but MV still shows a next-week OS. {ex("next_total_os")} (Correct = blank because next week has no row.)','Confirm with DAG owner: for partners who left, is this their final OS? If yes, rename/document it.')
T['next_week_end_deposit']=(f'Two reasons: (1) partner has no row next week but MV shows a deposit, (2) next week still running so deposit changed after refresh. {ex("next_week_end_deposit", lambda e: pd.notna(MAN["next_week_end_deposit"][e]))}','Refresh this week and next week together; confirm value for partners who left.')
T['next_join_date']=(f'Partner never left, but MV shows a future join date (21-Oct). {ex("next_join_date")}','DAG: keep blank when partner never left.')
T['bad_debt_collected']=(f'Partner never left, but MV shows the week\'s payment as bad debt collected. {ex("bad_debt_collected", lambda e: MAN["bad_debt_collected"][e]==0)}','DAG: fill only money collected between leave date and rejoin date.')
T['previous_week_collection']=(f'MV shows an amount, but no payment found for 7–13 Sep in payment table. {ex("previous_week_collection")}','Check payment source for these partners (manual check).')
T['partners_not_paid_2_weeks']=(f'Only {nbad("partners_not_paid_2_weeks")} rows – happens because of previous_week_collection gap. {ex("partners_not_paid_2_weeks")}','Will fix itself when previous_week_collection is fixed.')
T['active_fleet_cash_blocked']=('Cannot check: database has only TODAY\'s cash-block status (84 blocked), MV says 7,304 blocked at week end.','Need cash-block history from Airflow / Cash Block API to validate.')
T['location']=(f'MV shows main hub, allocation table shows exact parking location. {ex("location", lambda e: m.loc[e,"location"]=="Thane")}','Decide which location to use (main hub or exact location), then align MV.')
T['revenue_type']=(f'Partner had 2 products in one week, MV picked the other one. {ex("revenue_type")}','DAG: use product with most days in driven week (see Revenue_Type_Script_Fix tab).')
assert set(T)==set(MAN), set(MAN)-set(T)
pickle.dump(T,open('issue_text.pkl','wb'))
for k,v in T.items(): print(k,'|',v[0][:150])
