# Rewrite Raw_Data A..BG from ../dash/raw_refresh.json (built by build_refresh.py).
import json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
D = json.load(open('../dash/raw_refresh.json')); HDR, R = D[0], D[1:]
meta = call('GET', f'{API}/{DS}', params={'fields': 'sheets.properties'})
p = [s['properties'] for s in meta['sheets'] if s['properties']['title'] == 'Raw_Data'][0]
need = len(R) + 1 - p['gridProperties']['rowCount']
if need > 0:
    call('POST', f'{API}/{DS}:batchUpdate', json={'requests': [{'appendDimension': {'sheetId': p['sheetId'], 'dimension': 'ROWS', 'length': need}}]})
call('POST', f"{API}/{DS}/values/'Raw_Data'!A2:BG:clear", json={})
call('PUT', f"{API}/{DS}/values/'Raw_Data'!A1:BG1", params={'valueInputOption': 'RAW'}, json={'values': [HDR]})
for i in range(0, len(R), 5000):
    call('PUT', f"{API}/{DS}/values/'Raw_Data'!A{i+2}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': R[i:i+5000]})
print('written', len(R))
