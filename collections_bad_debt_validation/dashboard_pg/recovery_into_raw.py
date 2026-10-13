# Put car-recovery case rows into Raw_Data (PART 2 of final_raw_data.sql), point Summary rows 53-62
# at them, and drop the separate Recovery_Raw tab.
import json, datetime as dt
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
N = json.load(open('../dash/raw_refresh.json')); HDR = N[0][:59]; MV = N[1:]
v = json.load(open('../cr/rawdata.json')); HD = v[0]
D = lambda s: dt.date.fromisoformat(str(s)[:10])
weeks = sorted({r[0] for r in MV}); ix = {c: i for i, c in enumerate(HDR)}
case_rows = []
for r in v[1:]:
    if not r or r[0] == '': continue
    c = dict(zip(HD, r)); b, cw = D(c['week_start']), D(c['close_week'])
    for w in weeks:
        W = D(w)
        if not (b <= W <= cw): continue
        team_nr = cw == W and c['final_status'] == 'Completed' and c['finalstatus_reason'] == ''
        row = [''] * 62
        row[ix['partner_etm']], row[ix['city']], row[ix['product_type']], row[ix['fuel_type']] = c['partner_etid'], c['city'], c['product_type'], c['fuel_type']
        row[ix['recovery_initiated']] = int(b == W)
        row[ix['recovery_brought_fwd']] = int(b < W)
        row[ix['recovered_team']] = int(cw == W and c['final_status'] == 'Completed' and (c['finalstatus_reason'] == '' or W < dt.date(2026, 9, 7)))
        row[ix['recovered_organic']] = int(cw == W and c['final_status'] == 'Cancelled' and (
            (c['finalstatus_reason'] == 'Driver Dropped Vehicle' and c['checkin_dt'] == '') or (c['finalstatus_reason'] == '' and c['checkin_dt'] != '')))
        row[ix['recovery_pending']] = int(cw > W)
        row[ix['recovery_tat_hrs']] = round(float(c['tat_seconds']) / 3600, 1) if team_nr else ''
        row[ix['recovery_agent']] = c['agent_name'] if team_nr else ''
        row[59], row[60], row[61] = w, 'Recovery case', c['recovery_id']
        case_rows.append(row)
case_rows.sort(key=lambda x: (x[59], x[3], x[1]))
print('MV rows', len(MV), 'recovery case rows', len(case_rows))

meta = call('GET', f'{API}/{DS}', params={'fields': 'sheets.properties'})
P = {s['properties']['title']: s['properties'] for s in meta['sheets']}
p = P['Raw_Data']; g = p['gridProperties']; req = []
if g['columnCount'] < 62: req.append({'appendDimension': {'sheetId': p['sheetId'], 'dimension': 'COLUMNS', 'length': 62 - g['columnCount']}})
need = len(MV) + len(case_rows) + 1 - g['rowCount']
if need > 0: req.append({'appendDimension': {'sheetId': p['sheetId'], 'dimension': 'ROWS', 'length': need}})
if 'Recovery_Raw' in P: req.append({'deleteSheet': {'sheetId': P['Recovery_Raw']['sheetId']}})
if req: call('POST', f'{API}/{DS}:batchUpdate', json={'requests': req})
# BH..BJ for MV rows, then case rows below the MV rows
call('PUT', f"{API}/{DS}/values/'Raw_Data'!BH1:BJ1", params={'valueInputOption': 'RAW'}, json={'values': [['rec_week', 'row_type', 'recovery_id']]})
call('PUT', f"{API}/{DS}/values/'Raw_Data'!BH2", params={'valueInputOption': 'RAW'}, json={'values': [['', 'MV', '']] * len(MV)})
start = len(MV) + 2
call('POST', f"{API}/{DS}/values/'Raw_Data'!A{start}:BJ:clear", json={})
for i in range(0, len(case_rows), 5000):
    call('PUT', f"{API}/{DS}/values/'Raw_Data'!A{start + i}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': case_rows[i:i + 5000]})

# Summary rows 53-62: recovery metrics from case rows (rec_week = column week)
RD = lambda c: f'Raw_Data!${c}:${c}'
F = f'{RD("BH")},{{c}}$8,{RD("BI")},"Recovery case",{RD("D")},$B$2,{RD("H")},$B$4,{RD("F")},$B$5'
FF = ('(Raw_Data!$BH$2:$BH={c}$8)*(Raw_Data!$BI$2:$BI="Recovery case")*((Raw_Data!$D$2:$D=$B$2)+($B$2="*"))'
      '*((Raw_Data!$H$2:$H=$B$4)+($B$4="*"))*((Raw_Data!$F$2:$F=$B$5)+($B$5="*"))*(Raw_Data!$AW$2:$AW<>"")')
cols = [chr(ord('C') + j) for j in range(8)]
sm = lambda col: [f'=IFERROR(SUMIFS({RD(col)},{F.format(c=c)}), "-")' for c in cols]
pct = lambda p: [f'=IFERROR(ROUND(PERCENTILE(FILTER(Raw_Data!$AW$2:$AW,{FF.format(c=c)}),{p}),1)&" hrs", "-")' for c in cols]
V = [sm('AR'), sm('AS'), sm('AU'), sm('AT'), sm('AV'),
     [f'=IFERROR(ROUND(AVERAGEIFS({RD("AW")},{F.format(c=c)},{RD("AW")},"<>"),1)&" hrs", "-")' for c in cols],
     pct(0.9), pct(0.5), pct(0.25),
     [f'=IFERROR({c}56/COUNTUNIQUEIFS({RD("AX")},{F.format(c=c)},{RD("AX")},"<>"), "-")' for c in cols]]
call('PUT', f"{API}/{DS}/values/'Summary'!C53:J62", params={'valueInputOption': 'USER_ENTERED'}, json={'values': V})
json.dump([N[0][:59] + ['rec_week', 'row_type', 'recovery_id']] + [r[:59] + ['', 'MV', ''] for r in MV] + case_rows, open('../dash/raw_refresh.json', 'w'))
print('done')
