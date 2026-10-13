# Load a dashboard tab straight from a saved query result (MCP tool-result file, rows joined with '~').
# usage: python3 load_query_tab.py <tab> <result_file> <col1,col2,...>
import sys, json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
TAB, F, HDR = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
rows = []
for l in json.load(open(F))['result'].split('\n'):
    l = l.strip()
    if l.startswith('| 2026-') or l.startswith('| 2025-'):
        r = l[2:].rstrip('|').rstrip().split('~'); assert len(r) == len(HDR), (len(r), r); rows.append(r)
meta = call('GET', f'{API}/{DS}', params={'fields': 'sheets.properties'})
p = [s['properties'] for s in meta['sheets'] if s['properties']['title'] == TAB][0]
g = p['gridProperties']; req = []
if g['rowCount'] != len(rows) + 1:
    if g['rowCount'] < len(rows) + 1: req.append({'appendDimension': {'sheetId': p['sheetId'], 'dimension': 'ROWS', 'length': len(rows) + 1 - g['rowCount']}})
    else: req.append({'deleteDimension': {'range': {'sheetId': p['sheetId'], 'dimension': 'ROWS', 'startIndex': len(rows) + 1, 'endIndex': g['rowCount']}}})
if g['columnCount'] < len(HDR): req.append({'appendDimension': {'sheetId': p['sheetId'], 'dimension': 'COLUMNS', 'length': len(HDR) - g['columnCount']}})
if req: call('POST', f'{API}/{DS}:batchUpdate', json={'requests': req})
call('POST', f"{API}/{DS}/values/'{TAB}'!A1:ZZ:clear", json={})
call('PUT', f"{API}/{DS}/values/'{TAB}'!A1", params={'valueInputOption': 'RAW'}, json={'values': [HDR]})
for i in range(0, len(rows), 10000):
    call('PUT', f"{API}/{DS}/values/'{TAB}'!A{i + 2}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': rows[i:i + 10000]})
json.dump([HDR] + rows, open(f'../dash/{TAB}_from_query.json', 'w'))
print(TAB, 'loaded', len(rows), 'rows')
