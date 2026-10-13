# Build Raw_Data A..BG rows from the per-week MV pulls + joined source pulls,
# applying the same derivations as final_raw_data.sql. Writes ../dash/raw_refresh.json
import json
TR = '/root/.claude/projects/-home-user-mithunjaiswar/975ddfa8-2a6b-560b-8c6b-202af90fa71a/tool-results/mcp-Everest_Reporting_DB-run_read_only_query-%s.txt'
REC, ML, RC = TR % '1791867793708', TR % '1791867814827', TR % '1791867848408'
HDR = json.load(open('../raw_hdr.json'))
MVC = json.load(open('../mvpart_cols.json')) + ['np', 'first_bd']

def lines(f):
    for l in json.load(open(f))['result'].split('\n'):
        l = l.strip()
        if l.startswith('| 2026-'):
            yield l[2:].rstrip('|').strip().split('~')

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def fmt(v):
    if v is None: return ''
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    return str(round(v, 2)) if isinstance(v, float) else str(v)

rec = {(v[0], v[1]): [float(x) for x in v[2:7]] for v in lines(REC)}
ml = {(v[0], v[1]): v[2:6] for v in lines(ML)}
rc = {(v[0], v[1]): v[2:9] for v in lines(RC)}
old = json.load(open('../dash/raw_final.json'))
oh = old[0]; ia, idp = oh.index('alloc_date'), oh.index('dep_at_alloc')
alloc = {(r[0], r[1]): (r[ia], r[idp]) for r in old[1:]}
last_alloc = {}
for r in sorted(old[1:], key=lambda r: r[0]): last_alloc[r[1]] = (r[ia], r[idp])

out, carried = [], 0
for wk, f in sorted(json.load(open('../mvparts/files.json')).items()):
    for v in lines(f):
        m = dict(zip(MVC, v))
        k = (m['hissab_week'], m['partner_etm'])
        os_ = num(m['total_os']) or 0.0; aos = abs(os_)
        tc = num(m['total_collected_amount_in_week']) or 0.0
        tc100 = num(m['total_collected_100_pct'])
        cw = num(m['collection_till_wed'])
        wed = num(m['week_end_deposit'])
        tad = num(m['total_allocated_days'])
        nd = num(m['current_week_nd_count']) or 0.0
        npv = int(m['np'] or 0)
        active = m['active_inactive_flag'] == 'Active'
        # waterfall split of recovery modes, each capped at the OS still unpaid
        rz, ot, pp, ad, dto = rec.get(k, [0.0] * 5)
        sp = [min(rz, aos), max(0, min(ot, aos - rz)), max(0, min(pp, aos - rz - ot)),
              max(0, min(ad, aos - rz - ot - pp)), max(0, min(dto, aos - rz - ot - pp - ad))]
        if os_ == 0: habit = 'Excellent'
        elif (cw or 0) >= aos: habit = 'Very Good'
        elif tc >= aos: habit = 'Good'
        elif tc >= 0.75 * aos: habit = 'Average'
        else: habit = 'Defaulter'
        gap = (tc100 or 0) - aos
        rr = 'Yes' if gap < 0 and abs(gap) > (wed or 0) else 'No'
        elc, conn, gps, uber = ml.get(k, ['', '', '', ''])
        connv = num(conn) or 0.0
        gpsi = 1 if active and num(gps) == 0 and (num(uber) or 0) == 0 else 0
        score = (npv >= 1) + (rr == 'Yes') + (habit == 'Defaulter') + (nd > 2) + gpsi + (connv <= 0)
        risk = {6: 'Critical Risk', 5: 'High Risk', 4: 'Moderate Risk', 3: 'Low Risk', 2: 'Minimal Risk'}.get(score, 'No risk')
        fb = m['first_bd']
        funnel = (tc100 or 0) if fb and fb < m['hissab_week'] and m['active_inactive_flag'] == 'Inactive' else 0
        if k in alloc: ad_, dp_ = alloc[k]
        else: ad_, dp_ = last_alloc.get(m['partner_etm'], ('', '')); carried += 1
        r = rc.get(k, ['0'] * 5 + ['', ''])
        row = {
            'hissab_week': m['hissab_week'], 'partner_etm': m['partner_etm'], 'lead_id': m['lead_id'],
            'city': m['city'], 'location': m['location'], 'product_type': m['product_type'],
            'revenue_type': m['revenue_type'], 'fuel_type': m['fuel_type'],
            'eip_filter': 'EIP' if m['eip_tag'] == '1' else 'SINGLE', 'elc_filter': elc or 'Non_ELC',
            'active_inactive_flag': m['active_inactive_flag'],
            'in_car_recovery': 'Yes' if m['in_car_recovery_hissab_week'].lower() in ('true', 't') else 'No',
            'total_os': m['total_os'], 'weekly_os': m['weekly_os'], 'prev_carryforward_os': m['prev_carryforward_os'],
            'total_collected_amount_in_week': fmt(tc), 'total_collected_100_pct': m['total_collected_100_pct'],
            'till_wed_100pct': fmt(min(cw or 0, aos)), 'os_to_deposit': m['os_to_deposit'],
            'razorpay_100pct': fmt(sp[0]), 'other_100pct': fmt(sp[1]), 'phonepe_100pct': fmt(sp[2]),
            'adjustment_100pct': fmt(sp[3]), 'deposit_to_rent_100pct': fmt(sp[4]),
            'partners_not_paid_2_weeks': m['partners_not_paid_2_weeks'], 'last_week_payment_habit': m['last_week_payment_habit'],
            'total_allocated_days': m['total_allocated_days'], 'entire_week_active': 1 if (tad or 0) >= 7 else 0,
            'last_payment_date_till_hissab_week': m['last_payment_date_till_hissab_week'], 'last_jama_date': m['last_jama_date'],
            'tenure_days': m['tenure_days'], 'week_start_deposit': m['week_start_deposit'], 'week_end_deposit': m['week_end_deposit'],
            'alloc_date': ad_, 'dep_at_alloc': dp_,
            'os_surpass_deposit_amt': fmt(max(-os_ - (wed or 0), 0)) if active else '',
            'bad_debt_amount': m['bad_debt_amount'], 'bad_debt_collected_nonfunnel': m['bad_debt_collected'],
            'bad_debt_collected_funnel': fmt(funnel), 'asset_risk': risk, 'recovery_recommended': rr,
            'cars_under_recovery_hissab_week': m['cars_under_recovery_hissab_week'], 'recovery_tat': m['recovery_tat'],
            'recovery_initiated': r[0], 'recovery_brought_fwd': r[1], 'recovered_team': r[2], 'recovered_organic': r[3],
            'recovery_pending': r[4], 'recovery_tat_hrs': r[5], 'recovery_agent_id': r[6], 'mv_last_updated': m['last_updated'],
            'risk_score': score, 'payment_habit_week': habit, 'not_paid_prev_2w': npv, 'nd_count_hw': fmt(nd),
            'gps_inactive': gpsi, 'connects': fmt(connv), 'advance_amount': fmt(max(tc - aos, 0)),
            'carry_forward_os_neg': fmt(min(num(m['prev_carryforward_os']) or 0, 0)),
        }
        out.append([str(row[h]) for h in HDR])
out.sort(key=lambda r: (r[0], r[3], r[1]))
json.dump([HDR] + out, open('../dash/raw_refresh.json', 'w'))
print('rows', len(out), 'alloc carried from prior week', carried)
