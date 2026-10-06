"""Collections Bad Debt: compare Google Sheet Raw_Data vs PG analytics.collections_bad_debt_mv.

Inputs (CSV exports, see README.md):
  sheet.csv  - Raw_Data rows for the validated hisaab weeks (+ leading sheet_row column)
  pg.csv     - every column of analytics.collections_bad_debt_mv for the same weeks
  habit.pkl  - {employee_id: {week_start_date: payment_habit}} from driver_repayment_habit
Outputs: comparison tables under out/.
"""
import os, sys, json, pickle
import numpy as np
import pandas as pd

D = sys.argv[1] if len(sys.argv) > 1 else '.'
OUT = os.path.join(D, 'out'); os.makedirs(OUT, exist_ok=True)
CUR_WEEK = '2026-10-05'      # in-progress hisaab week at time of validation
FIXED_HABIT_WEEK = '2026-09-21'

s = pd.read_csv(f'{D}/sheet.csv', dtype=str, keep_default_na=False)
p = pd.read_csv(f'{D}/pg.csv', dtype=str, keep_default_na=False)
H = pickle.load(open(f'{D}/habit.pkl', 'rb'))
s.columns = ['sh_' + c for c in s.columns]
p.columns = ['pg_' + c for c in p.columns]
# date cells that Google Sheets returned as serial numbers (e.g. 46292) -> ISO date
for c in ['sh_last_paid_date', 'sh_last_jama_date']:
    ser = pd.to_numeric(s[c], errors='coerce')
    s.loc[ser.notna(), c] = (pd.Timestamp('1899-12-30') + pd.to_timedelta(ser[ser.notna()], unit='D')).dt.strftime('%Y-%m-%d')
s['key_w'] = s.sh_hisaab_week; s['key_e'] = s.sh_partner_et_id.str.strip().str.upper()
p['key_w'] = p.pg_hissab_week; p['key_e'] = p.pg_partner_etm.str.strip().str.upper()

def num(x):
    return pd.to_numeric(pd.Series(x).astype(str).str.replace(',', '').str.replace('%', '').str.strip(),
                         errors='coerce')

# previous-week PG values (same partner) used to explain in-progress-week behaviour
pw = p[['key_w', 'key_e', 'pg_active_inactive_flag', 'pg_current_week_nd_count', 'pg_last_car_number']].copy()
pw['key_w'] = (pd.to_datetime(pw.key_w) + pd.Timedelta(days=7)).dt.strftime('%Y-%m-%d')
pw.columns = ['key_w', 'key_e', 'pgprev_active', 'pgprev_nd', 'pgprev_car']
# PG car is it constant across all weeks for the partner (=> latest car, not week specific)
car_const = p.groupby('key_e').pg_last_car_number.nunique().eq(1)

m = p.merge(s, on=['key_w', 'key_e'], how='outer', indicator=True)
m = m.merge(pw, on=['key_w', 'key_e'], how='left')
m['week'] = m.key_w
m['city'] = np.where(m.sh_city.ne('') & m.sh_city.notna(), m.sh_city, m.pg_city)
m['employee'] = m.key_e
m['presence'] = m._merge.map({'both': 'Both', 'left_only': 'PG only', 'right_only': 'Sheet only'}).astype(str)
b = m[m._merge == 'both'].copy()
cur = b.week.eq(CUR_WEEK)
misaligned = cur & b.pg_last_car_number.ne(b.sh_last_car_number)   # Sheet current-week block belongs to other partner
pg_car_const = b.key_e.map(car_const).fillna(False)

def N(c): return num(b[c]).fillna(0).values
def T(c): return b[c].fillna('').astype(str).str.strip()
def blank(c): return T(c).eq('').values

R = {}  # reason texts
R['MISALIGN'] = ('Sheet issue: in the in-progress week (05-Oct) the Sheet block of columns last_car_number / '
                 'week_end_deposit / sd_week_start / last_paid_date belongs to a different partner (row misalignment '
                 'when pasted). PG value verified against car_allocation.')
R['INPROG'] = 'Timing: 05-Oct is the in-progress hisaab week; PG and Sheet were refreshed at different times.'

INT_COLS = {'lead_id', 'current_week_nd_count', 'tenure_days', 'partners_not_paid_2_weeks', 'recovery_tat'}

def cmp_num(pc, sc, tol=1.0):
    a, c = N(pc), N(sc)
    return np.abs(a - c) <= tol, a, c

def cmp_txt(pc, sc):
    return T(pc).str.lower().values == T(sc).str.lower().values, T(pc).values, T(sc).values

specs = []  # (pg_col, sheet_col, kind, comparator, reason_fn)

def spec(pc, sc, kind, fn=None, rfn=None, note=''):
    specs.append(dict(pg=pc, sheet=sc, kind=kind, fn=fn, rfn=rfn, note=note))

DD = 'Need to Deep Dive'

# ---------- reason functions (return array of reason strings for mismatched rows) ----------
def r_generic(pc, sc):
    def f(mask):
        out = np.full(len(b), DD, dtype=object)
        out[blank('pg_' + pc) & ~blank('sh_' + sc)] = f'PG {pc} is NULL while Sheet has a value'
        out[~blank('pg_' + pc) & blank('sh_' + sc)] = f'Sheet {sc} is blank while PG has a value'
        return out
    return f

CRM_LEAD = json.load(open(f'{D}/crm_lead.json')) if os.path.exists(f'{D}/crm_lead.json') else {}  # employee -> crm.lead_driver.lead_id

def r_lead(mask):
    out = np.full(len(b), DD + ' - lead_id differs; check crm.lead_driver', dtype=object)
    crm = b.key_e.map(CRM_LEAD).fillna('').values
    out[crm == T('pg_lead_id').values] = 'Sheet issue: Sheet lead_id differs from crm.lead_driver; PG lead_id matches CRM'
    return out

def r_city(mask):
    out = np.full(len(b), DD, dtype=object)
    out[T('sh_city').eq('NA').values] = "Sheet issue: city lookup missing in Sheet ('NA'); PG has the partner's city"
    return out

def r_eip(mask):
    out = np.full(len(b), DD, dtype=object)
    out[blank('pg_eip_tag')] = 'PG eip_tag is NULL (is_eip = 0 for same row)'
    return out

def r_product(mask):
    out = np.full(len(b), DD + ' - product classification differs', dtype=object)
    pt, st, rv, rs = T('pg_product_type'), T('sh_product_type'), T('pg_revenue_type'), T('sh_revenue_type')
    out[(rv.eq('') & pt.eq('SINGLE')).values] = 'PG revenue_type is NULL so PG product_type defaults to SINGLE; Sheet classifies as D2O / Own Now'
    out[(pt.eq('EIP') & T('pg_is_eip').eq('0')).values] = 'PG internal inconsistency: product_type = EIP but is_eip = 0 / eip_tag = 0; Sheet (eip_filter SINGLE) correct'
    lv = (rv.str.lower() != rs.str.lower()) & rv.ne('')
    out[(lv & ~(pt.eq('EIP'))).values] = 'Revenue type differs between PG and Sheet (Leasing vs D2O / Own Now) so product_type differs - ' + DD + ' on contract mapping'
    return out

def r_revenue(mask):
    out = np.full(len(b), DD + ' - revenue type classification (Leasing vs D2O / Own Now) differs', dtype=object)
    rv, rs, pt = T('pg_revenue_type'), T('sh_revenue_type'), T('pg_product_type')
    out[rv.eq('').values] = 'PG revenue_type is NULL (partner not mapped to a revenue type in PG)'
    out[(rv.eq('D2O') & rs.str.startswith('EV')).values] = 'PG classifies EV partner as D2O; Sheet as EV_Leasing / EV_Rent To Own'
    return out

def r_weekly_os(mask):
    out = np.full(len(b), DD, dtype=object)
    pcf, otd = N('pg_prev_carryforward_os'), N('pg_os_to_deposit')
    base = ('Definition difference: PG total_os = weekly_os + prev_carryforward_os + os_to_deposit; '
            'Sheet current_week_os = negative_os - prev_carry_forward. ')
    out[otd != 0] = base + 'PG keeps the OS-to-deposit installment out of weekly_os; Sheet includes it in current_week_os.'
    out[pcf > 0] = base + 'PG nets a positive (advance) carry-forward against the week; Sheet floors carry-forward at 0.'
    rest = (out == DD)
    out[rest] = base + 'Carry-forward split differs (see prev_carryforward_os row).'
    return out

def r_pcf(mask):
    out = np.full(len(b), DD, dtype=object)
    pcf, spcf, otd, tos = N('pg_prev_carryforward_os'), N('sh_prev_carry_forward'), N('pg_os_to_deposit'), N('pg_total_os')
    out[(pcf > 0) & (spcf == 0)] = 'Definition difference: PG keeps positive (advance / credit) carry-forward; Sheet floors prev carry-forward at 0'
    out[(np.abs(pcf + otd - spcf) <= 1) & (out == DD)] = 'Definition difference: Sheet prev_carry_forward includes the OS-to-deposit installment (PG keeps it in os_to_deposit)'
    out[(np.abs(np.maximum(pcf + otd, tos) - spcf) <= 1) & (out == DD)] = 'Definition difference: Sheet caps prev carry-forward at the total OS (current-week payment applied to old OS first)'
    out[(np.abs(np.maximum(pcf, tos) - spcf) <= 1) & (out == DD)] = 'Definition difference: Sheet caps prev carry-forward at the total OS (current-week payment applied to old OS first)'
    out[(np.abs(spcf + N('sh_prev_recovery')) <= 1) & (out == DD)] = 'Definition difference: Sheet prev_carry_forward = only the part of old OS recovered this week (= -prev_recovery); PG shows the full previous carry-forward'
    return out

def r_otd(mask):
    return np.full(len(b), 'Different metric: PG os_to_deposit = weekly deposit installment moved from OS (-500 / -1000); '
                           'Sheet dp_to_os = deposit adjusted against OS as recovery. Not like-for-like.', dtype=object)

def r_coll(mask):
    out = np.full(len(b), DD, dtype=object)
    out[cur.values] = R['INPROG'] + ' Sheet has collections posted after the PG refresh (PG total_collected_amount_in_week blank/lower).'
    return out

def r_tillwed(mask):
    out = np.full(len(b), DD, dtype=object)
    a, c, tos = N('pg_collection_till_wed'), N('sh_till_wed_100pct'), N('pg_total_os')
    capped = np.minimum(a, np.abs(np.minimum(tos, 0)))
    out[np.abs(capped - c) <= 1] = 'Definition difference: Sheet till_wed_100pct caps collection at 100% of OS; PG collection_till_wed is the actual (uncapped) amount'
    out[cur.values & (out == DD)] = R['INPROG'] + ' Mon-Wed collections still being posted.'
    return out

def r_bd(mask):
    return np.full(len(b), DD + ' - bad debt amount differs for inactive (jama) partner; check deposit adjustment at jama', dtype=object)

def r_bdc(mask):
    out = np.full(len(b), DD, dtype=object)
    a, tc, bd = N('pg_bad_debt_collected'), N('pg_total_collected_amount_in_week'), N('pg_bad_debt_amount')
    out[(bd == 0) & (a > 0)] = 'PG logic issue: bad_debt_collected is filled even though the partner has no bad debt (bad_debt_amount = 0); Sheet bad_debt_rec = 0'
    out[(bd == 0) & (np.abs(a - tc) <= 1) & (a > 0)] = 'PG logic issue: bad_debt_collected = total collection of the week for a partner with no bad debt (bad_debt_amount = 0); Sheet bad_debt_rec = 0'
    out[(bd != 0) & (np.abs(a - tc) <= 1) & (a > 0) & (out == DD)] = DD + ' - PG counts the full week collection as bad-debt collected for a bad-debt partner; Sheet bad_debt_rec = 0'
    out[cur.values & (out == DD)] = R['INPROG']
    return out

def r_lastpaid(mask):
    out = np.full(len(b), DD, dtype=object)
    lp, ls = T('pg_last_payment_date_till_hissab_week'), T('sh_last_paid_date')
    out[(ls.eq('') & lp.ne('')).values] = 'Sheet last_paid_date blank while PG has a payment date'
    out[((lp > ls) & ls.ne('')).values] = 'Timing: Sheet snapshot taken before the hisaab week closed; PG includes payments up to the hisaab week end'
    out[misaligned.values] = R['MISALIGN']
    return out

def r_jama(mask):
    out = np.full(len(b), DD, dtype=object)
    lj, sj = T('pg_last_jama_date'), T('sh_last_jama_date')
    out[(lj > '2026-10-06').values] = 'PG issue: last_jama_date is a future date (> validation date 06-Oct-2026), not a real jama date; Sheet blank'
    out[(lj.ne('') & sj.eq('') & (lj <= '2026-10-06')).values] = 'Definition difference: Sheet shows jama date only for the current allocation; PG keeps the last historical jama date of an earlier allocation'
    out[(lj.eq('') & sj.ne('')).values] = 'PG last_jama_date NULL while Sheet has a jama date'
    out[(lj.ne('') & sj.ne('') & (sj > lj) & (lj <= '2026-10-06')).values] = 'PG last_jama_date not updated with the latest jama; Sheet has a more recent jama date'
    return out

def r_car(mask):
    out = np.full(len(b), DD, dtype=object)
    out[blank('sh_last_car_number') & ~blank('pg_last_car_number')] = 'Sheet last_car_number blank'
    out[~blank('sh_last_car_number') & blank('pg_last_car_number')] = 'PG last_car_number NULL'
    out[(out == DD) & (T('pgprev_car').values == T('sh_last_car_number').values)] = "Car changed during the week: Sheet shows the previous week's car, PG the newer car"
    out[(out == DD) & pg_car_const.values] = 'PG shows the latest car at refresh time (same car on every week); Sheet shows the car driven in that week (car changed after the week)'
    out[misaligned.values] = R['MISALIGN']
    return out

def r_wsd(mask):
    out = np.full(len(b), DD, dtype=object)
    a, c, dp = N('pg_week_start_deposit'), N('sh_sd_week_start'), N('sh_dp_to_os')
    out[np.abs(a + dp - c) <= 1] = 'Definition difference: Sheet sd_week_start adds back the deposit adjusted to OS (dp_to_os) in the week; PG is net deposit at week start'
    out[(np.abs(2 * a - c) <= 1) & (a != 0)] = 'Sheet issue: deposit counted twice in Sheet sd_week_start (2 x PG value)'
    out[(np.abs(a + np.abs(N('pg_os_to_deposit')) - c) <= 1) & (out == DD)] = "Definition difference: Sheet sd_week_start includes this week's OS-to-deposit installment; PG does not"
    out[(c % 500 == 0) & (c > a) & (a % 500 != 0) & (out == DD)] = 'Definition difference (likely): Sheet sd_week_start shows the agreed / full security deposit (round amount); PG shows the actual deposit balance at week start'
    out[misaligned.values] = R['MISALIGN']
    return out

def r_wed(mask):
    out = np.full(len(b), DD, dtype=object)
    c, wsd = N('sh_week_end_deposit'), N('pg_week_start_deposit')
    a, otd = N('pg_week_end_deposit'), N('pg_os_to_deposit')
    out[np.abs(a - np.abs(otd) - c) <= 1] = "Definition difference: Sheet week_end_deposit excludes this week's OS-to-deposit installment; PG adds it"
    out[(c < 0) & (a == 0)] = 'Sheet shows a negative deposit; PG floors deposit at 0'
    out[np.abs(wsd - c) <= 1] = 'Definition difference: Sheet week_end_deposit = deposit at week START (excludes this week\'s OS-to-deposit installment / deposit-to-OS adjustment); PG applies them'
    out[misaligned.values] = R['MISALIGN']
    return out

def r_habit(mask):
    out = np.full(len(b), DD, dtype=object)
    for i, (e, w, ph, sh) in enumerate(zip(b.key_e, b.week, T('pg_last_week_payment_habit'), T('sh_payment_habit'))):
        src = H.get(e, {})
        sw, sf = src.get(w, ''), src.get(FIXED_HABIT_WEEK, '')
        if ph == sf and w != FIXED_HABIT_WEEK and sh == sw and sw != '':
            out[i] = f'PG logic issue: habit taken from fixed week {FIXED_HABIT_WEEK} for every hisaab week; Sheet uses the week-specific habit (matches driver_repayment_habit)'
        elif ph == sf and w != FIXED_HABIT_WEEK:
            out[i] = f'PG logic issue: habit taken from fixed week {FIXED_HABIT_WEEK} for every hisaab week (not week specific)'
        elif ph == sw and ph != '':
            out[i] = 'Sheet issue: Sheet habit does not match driver_repayment_habit for the week; PG matches source'
        elif ph == '' and sh != '':
            out[i] = 'PG habit NULL (no driver_repayment_habit row for the week); Sheet has a value'
    return out

def r_nd(mask):
    out = np.full(len(b), DD, dtype=object)
    out[cur.values] = R['INPROG'] + ' PG counts not-driven days of the running week (future days counted as not driven).'
    out[(~cur.values) & (N('pgprev_nd') == N('sh_not_driven_count')) & (b.pgprev_nd.notna().values)] = 'Week alignment: Sheet not_driven_count equals PG count of the previous week'
    d = N('sh_not_driven_count') - N('pg_current_week_nd_count')
    out[(b.week.eq('2026-09-21').values) & (d == -1) & (out == DD)] = 'Systematic off-by-one in week 21-Sep: PG counts one more not-driven day than the Sheet (date-window boundary differs for that week)'
    return out

def r_tenure(mask):
    out = np.full(len(b), DD, dtype=object)
    d = N('pg_tenure_days') - N('sh_tenure_days')
    out[(d > 0) & (d <= 14)] = 'Reference date difference: PG tenure computed on a later refresh date than the Sheet (difference of a few days)'
    out[(d < 0) & (d >= -14)] = 'Reference date difference: Sheet tenure computed on a later date than PG'
    out[(N('sh_tenure_days') == 0) & (N('pg_tenure_days') > 0) & (out == DD)] = 'Sheet tenure_days = 0 (tenure missing in Sheet)'
    return out

def r_active(mask):
    out = np.full(len(b), DD, dtype=object)
    out[blank('sh_1d_active')] = 'Sheet 1d_active blank'
    out[cur.values & ~blank('sh_1d_active')] = R['INPROG'] + ' PG flags activity of the running hisaab week; Sheet shows activity of the completed driven week.'
    return out

def r_icr(mask):
    out = np.full(len(b), DD, dtype=object)
    out[blank('sh_in_car_recovery')] = 'Sheet in_car_recovery blank'
    out[cur.values & ~blank('sh_in_car_recovery')] = R['INPROG'] + ' Car-recovery status changed between the two refreshes.'
    return out

def r_tat(mask):
    out = np.full(len(b), DD, dtype=object)
    a, c = N('pg_recovery_tat'), N('sh_car_recovery_pending_tat')
    out[(a != 0) & (c == 0)] = 'Sheet car_recovery_pending_tat blank while PG has TAT'
    out[(a == 0) & (c != 0)] = 'PG recovery_tat NULL while Sheet has TAT'
    out[(a != 0) & (c != 0)] = 'TAT reference date differs (pending TAT counted to different refresh dates)'
    out[cur.values & (out == DD)] = R['INPROG']
    return out

def r_npd(mask):
    return np.full(len(b), 'Definition difference: PG flag = 1 only when last_week_collection AND previous_week_collection are both 0 '
                           '(reproduced 100%); Sheet not_paid_last_2_weeks counts unpaid weeks (0/1/2) on a different window', dtype=object)

def r_loc(mask):
    out = np.full(len(b), DD + ' - hub differs between PG location and Sheet allocation_location (hub transfer / hub mapping)', dtype=object)
    out[blank('sh_allocation_location')] = 'Sheet allocation_location not filled for this week (Sheet location column holds city cluster, not hub)'
    return out

# ---------- column specs: every PG column ----------
spec('id', None, 'none', note='PG surrogate key - no Sheet equivalent')
spec('driven_week', 'hisaab_week - 7 days', 'derived', note='Sheet has no driven_week; derived as hisaab_week - 7')
spec('hissab_week', 'hisaab_week', 'key')
spec('partner_etm', 'partner_et_id', 'key')
spec('lead_id', 'lead_id', 'num', rfn=r_lead)
spec('city', 'city', 'txt', rfn=r_city)
spec('eip_tag', 'eip_filter', 'eip', rfn=r_eip)
spec('fuel_type', 'fuel_type', 'txt')
spec('product_type', 'product_type', 'txt', rfn=r_product)
spec('revshare_days_working', None, 'none')
spec('total_os', 'negative_os', 'num')
spec('weekly_os', 'current_week_os', 'num', rfn=r_weekly_os)
spec('prev_carryforward_os', 'prev_carry_forward', 'num', rfn=r_pcf)
spec('os_to_deposit', 'dp_to_os', 'num', rfn=r_otd)
spec('kuber_amount', None, 'none')
spec('total_allocated_days', None, 'none')
spec('uber_active_days', None, 'none')
spec('rental_days', None, 'none')
spec('total_rent_amount', None, 'none')
spec('total_collected_amount_in_week', 'total_recovery', 'num', rfn=r_coll)
spec('last_payment_date_till_hissab_week', 'last_paid_date', 'txt', rfn=r_lastpaid)
spec('last_jama_date', 'last_jama_date', 'txt', rfn=r_jama)
spec('last_car_number', 'last_car_number', 'txt', rfn=r_car)
spec('week_start_deposit', 'sd_week_start', 'num', rfn=r_wsd)
spec('week_end_deposit', 'week_end_deposit', 'num', rfn=r_wed)
spec('last_week_payment_habit', 'payment_habit', 'txt', rfn=r_habit)
spec('last_week_nd_count', None, 'none')
spec('current_week_nd_count', 'not_driven_count', 'num', rfn=r_nd)
spec('hissab_week_active_days', None, 'none')
spec('tenure_days', 'tenure_days', 'num', rfn=r_tenure)
spec('d2o_leave_days', None, 'none')
spec('active_inactive_flag', '1d_active', 'txt', rfn=r_active)
spec('bad_debt_amount', 'bad_debt', 'num', rfn=r_bd)
spec('next_weekly_os', None, 'none')
spec('next_total_os', None, 'none')
spec('next_week_end_deposit', None, 'none')
spec('next_join_date', None, 'none')
spec('in_car_recovery_driven_week', None, 'none')
spec('in_car_recovery_hissab_week', 'in_car_recovery', 'bool', rfn=r_icr)
spec('for_collections', 'row present in Raw_Data', 'presence')
spec('last_updated', None, 'none', note='PG refresh timestamp')
spec('collection_till_wed', 'till_wed_100pct', 'num', rfn=r_tillwed)
spec('bad_debt_collected', 'bad_debt_rec', 'num', rfn=r_bdc)
spec('last_week_collection', None, 'none')
spec('previous_week_collection', None, 'none')
spec('partners_not_paid_2_weeks', 'not_paid_last_2_weeks', 'num', rfn=r_npd)
spec('cars_under_recovery_driven_week', None, 'none', note='aggregate count; compared at city level only')
spec('cars_under_recovery_hissab_week', 'COUNT(in_car_recovery = Yes)', 'agg', note='compared at city level')
spec('recovery_tat', 'car_recovery_pending_tat', 'num', rfn=r_tat)
spec('active_fleet_cash_blocked', None, 'none')
spec('location', 'allocation_location', 'txt', rfn=r_loc)
spec('revenue_type', 'revenue_type', 'txt', rfn=r_revenue)
spec('is_eip', 'eip_filter', 'eip', rfn=r_eip)

assert [x['pg'] for x in specs] == [c[3:] for c in p.columns if c.startswith('pg_')], 'every PG column must be specified'

# ---------- run agent-level comparison ----------
agent = b[['week', 'city', 'employee']].copy().reset_index(drop=True)
results = {}
for sp in specs:
    pc, sc, k = sp['pg'], sp['sheet'], sp['kind']
    if k in ('none', 'key', 'presence', 'agg'):
        continue
    if k == 'num':
        ok, a, c = cmp_num('pg_' + pc, 'sh_' + sc, tol=0 if pc in INT_COLS else 1.0)
        a = num(b['pg_' + pc]).values; c = num(b['sh_' + sc]).values
    elif k == 'txt':
        ok, a, c = cmp_txt('pg_' + pc, 'sh_' + sc)
    elif k == 'eip':
        a = T('pg_' + pc).values
        c = T('sh_eip_filter').values
        ok = (np.where(c == 'EIP', '1', '0') == a)
    elif k == 'bool':
        a = T('pg_' + pc).values; c = T('sh_' + sc).values
        ok = (a == 'true') == (c == 'Yes')
    elif k == 'derived':
        a = T('pg_driven_week').values
        c = (pd.to_datetime(b.key_w) - pd.Timedelta(days=7)).dt.strftime('%Y-%m-%d').values
        ok = a == c
    ok = np.asarray(ok)
    reason = np.full(len(b), '', dtype=object)
    if (~ok).any():
        rr = (sp['rfn'] or r_generic(pc, sc if sc else ''))(~ok)
        reason[~ok] = np.asarray(rr)[~ok]
    agent[f'{pc} | Sheet'] = c
    agent[f'{pc} | PG'] = a
    agent[f'{pc} | Status'] = np.where(ok, 'Matched', 'Mismatched')
    agent[f'{pc} | Reason'] = reason
    results[pc] = (ok, reason)

stat_cols = [c for c in agent.columns if c.endswith('| Status')]
agent['Overall Status'] = np.where((agent[stat_cols] == 'Matched').all(axis=1), 'Matched', 'Mismatched')
agent['Mismatched Columns'] = agent[stat_cols].apply(lambda r: ', '.join(c.split(' |')[0] for c, v in r.items() if v != 'Matched'), axis=1)
agent = agent.sort_values(['week', 'city', 'employee']).reset_index(drop=True)
agent.to_pickle(f'{OUT}/agent.pkl')

# presence (for_collections) checks
pres = m[['week', 'city', 'employee', 'presence', 'pg_for_collections']].copy()
pres['Status'] = 'Matched'; pres['Reason'] = ''
po = pres.presence.eq('PG only')
pres.loc[po & pres.pg_for_collections.eq('0'), 'Reason'] = 'Expected: PG for_collections = 0 rows are not part of the Sheet (Sheet = for_collections 1)'
pres.loc[po & pres.pg_for_collections.eq('1'), ['Status', 'Reason']] = ['Mismatched', DD + ' - PG for_collections = 1 but partner missing in Sheet Raw_Data']
bo = pres.presence.eq('Both') & pres.pg_for_collections.eq('0')
pres.loc[bo, ['Status', 'Reason']] = ['Mismatched', DD + ' - partner in Sheet but PG for_collections = 0']
pres.loc[pres.presence.eq('Sheet only'), ['Status', 'Reason']] = ['Mismatched', DD + ' - partner in Sheet but missing in PG']
pres.to_pickle(f'{OUT}/presence.pkl')

pickle.dump(dict(specs=[{k: v for k, v in sp.items() if k not in ('fn', 'rfn')} for sp in specs]), open(f'{OUT}/specs.pkl', 'wb'))
b_out = b.copy(); b_out.to_pickle(f'{OUT}/joined.pkl'); m.to_pickle(f'{OUT}/merged.pkl')

# quick console summary
for pc, (ok, reason) in results.items():
    r = pd.Series(reason[~ok]).value_counts()
    dd = r[[i for i in r.index if i.startswith(DD)]].sum() if len(r) else 0
    print(f'{pc:36s} mism={int((~ok).sum()):6d} deep_dive={int(dd):6d}')
print(pres.groupby(['presence', 'pg_for_collections', 'Status']).size())
