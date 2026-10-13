# Write tab "Query" with the 3 SQL queries of final_raw_data.sql (1 SQL line per row).
import sys, os, json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip(); TAB = 'Query'
SQL = open(sys.argv[1]).read().rstrip().split('\n')
cut = lambda key: max(i for i, l in enumerate(SQL) if key in l and l.startswith('-- QUERY')) - 1  # the === line above
b2, b3 = cut('QUERY 2'), cut('QUERY 3')
Q = [('QUERY 1 -> Raw_Data tab', '1 row per pilot per hisaab week (MV + joined columns). Feeds Summary / WBR.', SQL[:b2]),
     ('QUERY 2 -> Deposit_Raw tab', '1 row per pilot who held a car in the hisaab week. Feeds Summary Deposit rows.', SQL[b2:b3]),
     ('QUERY 3 -> Recovery_Raw tab', '1 row per car recovery case per hisaab week. Feeds Summary Car Recovery rows.', SQL[b3:])]
trim = lambda L: L[next(i for i, l in enumerate(L) if l.strip()):len(L) - next(i for i, l in enumerate(reversed(L)) if l.strip())]
IDS = json.load(open('../dash/query_doc_ids.json')) if os.path.exists('../dash/query_doc_ids.json') else {}
DOCN = ['Collections Dashboard - Query 1 - Raw_Data', 'Collections Dashboard - Query 2 - Deposit_Raw', 'Collections Dashboard - Query 3 - Recovery_Raw']
LINK = [f'=HYPERLINK("https://docs.google.com/document/d/{IDS[n]}/edit","Open Google Doc")' if n in IDS else '' for n in DOCN]
V = [['Collections dashboard - SQL queries (run each one, paste result into its tab)', '', 'Google Doc link'], ['', '', '']]
for (t, d, _), lk in zip(Q, LINK): V.append([t, d, lk])
V.append(['', '', '']); heads = []
for (t, d, body), lk in zip(Q, LINK):
    V.append(['', '', '']); heads.append(len(V)); V.append([t, d, lk])
    V += [[l, '', ''] for l in trim(body)]
meta = call('GET', f'{API}/{DS}', params={'fields': 'sheets.properties'})
P = {s['properties']['title']: s['properties'] for s in meta['sheets']}
req = [{'deleteSheet': {'sheetId': P[TAB]['sheetId']}}] if TAB in P else []
req.append({'addSheet': {'properties': {'title': TAB, 'index': len(P) - (1 if TAB in P else 0),
            'gridProperties': {'rowCount': len(V) + 5, 'columnCount': 3, 'frozenRowCount': 1}}}})
sid = call('POST', f'{API}/{DS}:batchUpdate', json={'requests': req})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT', f"{API}/{DS}/values/'{TAB}'!A1", params={'valueInputOption': 'RAW'}, json={'values': [r[:2] for r in V]})
for i, r in enumerate(V):
    if r[2]: call('PUT', f"{API}/{DS}/values/'{TAB}'!C{i + 1}", params={'valueInputOption': 'USER_ENTERED'}, json={'values': [[r[2]]]})
rng = lambda a, b, c=0, d=3: {'sheetId': sid, 'startRowIndex': a, 'endRowIndex': b, 'startColumnIndex': c, 'endColumnIndex': d}
fmt = lambda R, f, fl: {'repeatCell': {'range': R, 'cell': {'userEnteredFormat': f}, 'fields': f'userEnteredFormat({fl})'}}
DK = {'red': 0.2, 'green': 0.25, 'blue': 0.4}; WH = {'red': 1, 'green': 1, 'blue': 1}; GR = {'red': 0.35, 'green': 0.35, 'blue': 0.35}
R = [fmt(rng(0, len(V)), {'textFormat': {'fontFamily': 'Roboto Mono', 'fontSize': 9}, 'wrapStrategy': 'OVERFLOW_CELL'}, 'textFormat,wrapStrategy'),
     fmt(rng(0, 1), {'textFormat': {'bold': True, 'fontSize': 12}}, 'textFormat'),
     fmt(rng(2, 5), {'textFormat': {'bold': True}}, 'textFormat'),
     {'updateDimensionProperties': {'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1}, 'properties': {'pixelSize': 900}, 'fields': 'pixelSize'}},
     {'updateDimensionProperties': {'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 2}, 'properties': {'pixelSize': 520}, 'fields': 'pixelSize'}},
     {'updateDimensionProperties': {'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': 3}, 'properties': {'pixelSize': 160}, 'fields': 'pixelSize'}}]
for h in heads:
    R.append(fmt(rng(h - 1, h), {'backgroundColor': DK, 'textFormat': {'bold': True, 'foregroundColor': WH, 'fontSize': 11}}, 'backgroundColor,textFormat'))
for i, r in enumerate(V):
    if r[0].lstrip().startswith('--') and i + 1 not in heads:
        R.append(fmt(rng(i, i + 1), {'textFormat': {'foregroundColor': GR, 'italic': True, 'fontFamily': 'Roboto Mono', 'fontSize': 9}}, 'textFormat'))
call('POST', f'{API}/{DS}:batchUpdate', json={'requests': R})
print('rows', len(V), 'query starts at rows', heads)
