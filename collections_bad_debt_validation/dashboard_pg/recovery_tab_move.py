# Move car-recovery case rows out of Raw_Data into their own tab Recovery_Raw (QUERY 3 of
# final_raw_data.sql); drop Raw_Data BH:BJ and point Summary rows 53-62 at Recovery_Raw.
import json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
N = json.load(open('../dash/raw_refresh.json')); h = N[0]; it = h.index('row_type')
ix = {c: i for i, c in enumerate(h)}
MV = [r[:59] for r in N[1:] if r[it] == 'MV']; RC = [r for r in N[1:] if r[it] == 'Recovery case']
RH = ['rec_week', 'partner_etm', 'city', 'product_type', 'fuel_type', 'recovery_id', 'recovery_initiated', 'recovery_brought_fwd',
      'recovered_team', 'recovered_organic', 'recovery_pending', 'recovery_tat_hrs', 'recovery_agent']
RR = [[str(r[ix[c]]).replace(',', '') if c == 'recovery_id' else r[ix[c]] for c in RH] for r in RC]
RR.sort(key=lambda x: (x[0], x[2], x[1]))
print('MV', len(MV), 'cases', len(RR))
meta = call('GET', f'{API}/{DS}', params={'fields': 'sheets.properties'})
P = {s['properties']['title']: s['properties'] for s in meta['sheets']}
raw = P['Raw_Data']; g = raw['gridProperties']; req = []
if g['rowCount'] > len(MV) + 1:
    req.append({'deleteDimension': {'range': {'sheetId': raw['sheetId'], 'dimension': 'ROWS', 'startIndex': len(MV) + 1, 'endIndex': g['rowCount']}}})
if g['columnCount'] > 59:
    req.append({'deleteDimension': {'range': {'sheetId': raw['sheetId'], 'dimension': 'COLUMNS', 'startIndex': 59, 'endIndex': g['columnCount']}}})
if 'Recovery_Raw' in P: req.append({'deleteSheet': {'sheetId': P['Recovery_Raw']['sheetId']}})
req.append({'addSheet': {'properties': {'title': 'Recovery_Raw', 'index': P['Deposit_Raw']['index'] + 1,
            'gridProperties': {'rowCount': len(RR) + 1, 'columnCount': len(RH), 'frozenRowCount': 1}}}})
sid = call('POST', f'{API}/{DS}:batchUpdate', json={'requests': req})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT', f"{API}/{DS}/values/'Recovery_Raw'!A1", params={'valueInputOption': 'RAW'}, json={'values': [RH]})
for i in range(0, len(RR), 10000):
    call('PUT', f"{API}/{DS}/values/'Recovery_Raw'!A{i + 2}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': RR[i:i + 10000]})
call('POST', f'{API}/{DS}:batchUpdate', json={'requests': [
    {'repeatCell': {'range': {'sheetId': sid, 'startRowIndex': 0, 'endRowIndex': 1}, 'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}}, 'fields': 'userEnteredFormat.textFormat'}},
    {'repeatCell': {'range': {'sheetId': sid, 'startRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': 1}, 'cell': {'userEnteredFormat': {'numberFormat': {'type': 'DATE', 'pattern': 'yyyy-mm-dd'}}}, 'fields': 'userEnteredFormat.numberFormat'}}]})

# Summary rows 53-62 -> Recovery_Raw (A week, C city, E fuel, D product)
RD = lambda c: f'Recovery_Raw!${c}:${c}'
F = f'{RD("A")},{{c}}$8,{RD("C")},$B$2,{RD("E")},$B$4,{RD("D")},$B$5'
FF = ('(Recovery_Raw!$A$2:$A={c}$8)*((Recovery_Raw!$C$2:$C=$B$2)+($B$2="*"))'
      '*((Recovery_Raw!$E$2:$E=$B$4)+($B$4="*"))*((Recovery_Raw!$D$2:$D=$B$5)+($B$5="*"))*(Recovery_Raw!$L$2:$L<>"")')
cols = [chr(ord('C') + j) for j in range(8)]
sm = lambda col: [f'=IFERROR(SUMIFS({RD(col)},{F.format(c=c)}), "-")' for c in cols]
pct = lambda p: [f'=IFERROR(ROUND(PERCENTILE(FILTER(Recovery_Raw!$L$2:$L,{FF.format(c=c)}),{p}),1)&" hrs", "-")' for c in cols]
V = [sm('G'), sm('H'), sm('J'), sm('I'), sm('K'),
     [f'=IFERROR(ROUND(AVERAGEIFS({RD("L")},{F.format(c=c)},{RD("L")},"<>"),1)&" hrs", "-")' for c in cols],
     pct(0.9), pct(0.5), pct(0.25),
     [f'=IFERROR({c}56/COUNTUNIQUEIFS({RD("M")},{F.format(c=c)},{RD("M")},"<>"), "-")' for c in cols]]
before = call('GET', f"{API}/{DS}/values/'Summary'!C53:J62")['values']
call('PUT', f"{API}/{DS}/values/'Summary'!C53:J62", params={'valueInputOption': 'USER_ENTERED'}, json={'values': V})
after = call('GET', f"{API}/{DS}/values/'Summary'!C53:J62")['values']
print('Summary 53-62 same as before:', before == after)
if before != after:
    for b, a in zip(before, after): print(b, '->', a)
json.dump([h[:59]] + MV, open('../dash/raw_refresh.json', 'w'))
json.dump([RH] + RR, open('../dash/recovery_raw.json', 'w'))
