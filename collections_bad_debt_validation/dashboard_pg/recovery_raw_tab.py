# Create/refresh Recovery_Raw (1 row per recovery case, Recovery Dash logic) and point
# Summary car-recovery rows (53-62) at it so they match the Car Recovery Dash.
import json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
v = json.load(open('../cr/rawdata.json')); HD = v[0]; ix = {c: HD.index(c) for c in HD}
HDR = ['week_start', 'close_week', 'start_date', 'close_date', 'tat_hrs', 'city', 'location', 'fuel_type', 'product_type',
       'partner_etid', 'car_number', 'agent_name', 'final_status', 'final_reason', 'checkin_dt', 'recovery_id']
rows = []
for r in v[1:]:
    if not r or r[0] == '': continue
    g = lambda c: r[ix[c]] if ix[c] < len(r) else ''
    rows.append([g('week_start'), g('close_week'), g('start_date'), g('close_date') if g('final_status') != 'Pending' else '',
                 round(float(g('tat_seconds') or 0) / 3600, 1), g('city'), g('location'), g('fuel_type'), g('product_type'),
                 g('partner_etid'), g('car_number'), g('agent_name'), g('final_status'), g('finalstatus_reason'), g('checkin_dt'), g('recovery_id')])
rows.sort(key=lambda x: (x[0], x[5]))
m = call('GET', f'{API}/{DS}', params={'fields': 'sheets.properties'})
P = {s['properties']['title']: s['properties']['sheetId'] for s in m['sheets']}
if 'Recovery_Raw' not in P:
    call('POST', f'{API}/{DS}:batchUpdate', json={'requests': [{'addSheet': {'properties': {'title': 'Recovery_Raw',
        'gridProperties': {'rowCount': len(rows) + 500, 'columnCount': len(HDR), 'frozenRowCount': 1}}}}]})
else:
    call('POST', f"{API}/{DS}/values/'Recovery_Raw'!A:P:clear", json={})
call('PUT', f"{API}/{DS}/values/'Recovery_Raw'!A1", params={'valueInputOption': 'USER_ENTERED'}, json={'values': [HDR] + rows})

RR = lambda c: f'Recovery_Raw!${c}:${c}'
F = f'{RR("F")},$B$2,{RR("H")},$B$4,{RR("I")},$B$5'                       # city / fuel / product filters
FF = ('((Recovery_Raw!$F$2:$F=$B$2)+($B$2="*"))*((Recovery_Raw!$H$2:$H=$B$4)+($B$4="*"))*((Recovery_Raw!$I$2:$I=$B$5)+($B$5="*"))')
TEAM = lambda c: f'{RR("B")},{c}$8,{RR("M")},"Completed",{RR("N")},""'
TEAMF = lambda c: f'(Recovery_Raw!$B$2:$B={c}$8)*(Recovery_Raw!$M$2:$M="Completed")*(Recovery_Raw!$N$2:$N="")*{FF}'
def row(fn): return [fn(chr(ord('C') + j)) for j in range(8)]
pct = lambda p: (lambda c: f'=IFERROR(ROUND(PERCENTILE(FILTER(Recovery_Raw!$E$2:$E,{TEAMF(c)}),{p}),1)&" hrs", "-")')
V = [
 row(lambda c: f'=IFERROR(COUNTIFS({RR("A")},{c}$8,{RR("B")},">="&{c}$8,{F}), "-")'),                                   # 53 initiated
 row(lambda c: f'=IFERROR(COUNTIFS({RR("A")},"<"&{c}$8,{RR("B")},">="&{c}$8,{F}), "-")'),                               # 54 brought fwd
 row(lambda c: f'=IFERROR(COUNTIFS({RR("B")},{c}$8,{RR("M")},"Cancelled",{RR("N")},"Driver Dropped Vehicle",{RR("O")},"",{F})'
               f'+COUNTIFS({RR("B")},{c}$8,{RR("M")},"Cancelled",{RR("N")},"",{RR("O")},"<>",{F}), "-")'),                # 55 organic
 row(lambda c: f'=IFERROR(IF({c}$8<DATE(2026,9,7),COUNTIFS({RR("B")},{c}$8,{RR("M")},"Completed",{F}),COUNTIFS({TEAM(c)},{F})), "-")'),  # Recovery Dash counts all Completed before 07-Sep                                                              # 56 team
 row(lambda c: f'=IFERROR(COUNTIFS({RR("A")},"<="&{c}$8,{RR("B")},">"&{c}$8,{F}), "-")'),                               # 57 pending
 row(lambda c: f'=IFERROR(ROUND(AVERAGEIFS({RR("E")},{TEAM(c)},{F}),1)&" hrs", "-")'),                                  # 58 avg TAT
 row(pct(0.9)), row(pct(0.5)), row(pct(0.25)),                                                                          # 59-61
 row(lambda c: f'=IFERROR({c}56/COUNTUNIQUEIFS({RR("L")},{TEAM(c)},{F},{RR("L")},"<>"), "-")'),                          # 62 per agent
]
call('PUT', f"{API}/{DS}/values/'Summary'!C53:J62", params={'valueInputOption': 'USER_ENTERED'}, json={'values': V})
print('Recovery_Raw rows', len(rows))
