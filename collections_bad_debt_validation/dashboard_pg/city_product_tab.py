# Write tab Summary_City_Product from ../dash/city_product.json, with a week-on-week splitter.
import json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip(); TAB = 'Summary_City_Product'
from metric_notes import note
RES0 = json.load(open('../dash/city_product.json'))
def _row(r):
    lg, ex, why, emp = note(r[1], r[2]); a, b = r[-1].split('/')
    if a == b: why, emp = 'Matches - no gap.', '-'
    return r[:3] + [lg, ex] + r[3:] + [why, emp]
RES = [_row(r) for r in RES0]
WEEKS = [('Sep-14', '14-Sep-2026'), ('Sep-21', '21-Sep-2026'), ('Sep-28', '28-Sep-2026'), ('Oct-05', '05-Oct-2026')]
FILT = list(dict.fromkeys(r[0] for r in RES))
NC = 5 + 4 * len(WEEKS) + 3
wk_row = ['', '', '', '', ''] + sum([[f'Week {k + 1} - {d}', '', '', ''] for k, (_, d) in enumerate(WEEKS)], []) + ['', '', '']
hdr = ['Filter (City | Product)', 'Section', 'Metric', 'Logic', 'Easy example'] + ['Sheet', 'MV', 'Diff (MV-Sheet)', 'Diff %'] * len(WEEKS) + ['Weeks matched', 'Difference reason (old Sheet vs MV)', 'Employee example (old Sheet vs MV)']
V = [wk_row, hdr] + RES   # detail table only (no title / summary block)
meta = call('GET', f'{API}/{DS}', params={'fields': 'sheets.properties'})
P = {s['properties']['title']: s['properties'] for s in meta['sheets']}
idx = P[TAB]['index'] if TAB in P else 1
req = [{'deleteSheet': {'sheetId': P[TAB]['sheetId']}}] if TAB in P else []
req.append({'addSheet': {'properties': {'title': TAB, 'index': idx, 'gridProperties': {'rowCount': len(V) + 10, 'columnCount': NC}}}})
sid = call('POST', f'{API}/{DS}:batchUpdate', json={'requests': req})['replies'][-1]['addSheet']['properties']['sheetId']
call('PUT', f"{API}/{DS}/values/'{TAB}'!A1", params={'valueInputOption': 'USER_ENTERED'}, json={'values': V})
w0 = 0; h0 = 1; r0, r1 = h0 + 1, h0 + 1 + len(RES)      # 0-based rows
rng = lambda a, b, c, d: {'sheetId': sid, 'startRowIndex': a, 'endRowIndex': b, 'startColumnIndex': c, 'endColumnIndex': d}
DK = {'red': 0.2, 'green': 0.25, 'blue': 0.4}; WH = {'red': 1, 'green': 1, 'blue': 1}; RED = {'red': 0.85, 'green': 0, 'blue': 0}
WB = [{'red': 0.27, 'green': 0.45, 'blue': 0.62}, {'red': 0.36, 'green': 0.55, 'blue': 0.42}]
WL = [{'red': 0.93, 'green': 0.96, 'blue': 0.99}, {'red': 0.94, 'green': 0.98, 'blue': 0.94}]
fmt = lambda R, f, fields: {'repeatCell': {'range': R, 'cell': {'userEnteredFormat': f}, 'fields': f'userEnteredFormat({fields})'}}
L = lambda st, c: {'style': st, 'color': c}
R = [     fmt(rng(w0, h0 + 1, 0, 5), {'backgroundColor': DK, 'textFormat': {'bold': True, 'foregroundColor': WH}, 'wrapStrategy': 'WRAP', 'verticalAlignment': 'MIDDLE'}, 'backgroundColor,textFormat,wrapStrategy,verticalAlignment'),
     fmt(rng(w0, h0 + 1, NC - 3, NC), {'backgroundColor': DK, 'textFormat': {'bold': True, 'foregroundColor': WH}, 'wrapStrategy': 'WRAP'}, 'backgroundColor,textFormat,wrapStrategy'),
     {'updateSheetProperties': {'properties': {'sheetId': sid, 'gridProperties': {'frozenRowCount': h0 + 1, 'frozenColumnCount': 3}}, 'fields': 'gridProperties(frozenRowCount,frozenColumnCount)'}},
     {'setBasicFilter': {'filter': {'range': rng(h0, r1, 0, NC)}}},
     {'updateDimensionProperties': {'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1}, 'properties': {'pixelSize': 170}, 'fields': 'pixelSize'}},
     {'updateDimensionProperties': {'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': 3}, 'properties': {'pixelSize': 240}, 'fields': 'pixelSize'}}]
for k in range(len(WEEKS)):
    c0 = 5 + 4 * k
    R.append({'mergeCells': {'range': rng(w0, w0 + 1, c0, c0 + 4), 'mergeType': 'MERGE_ALL'}})
    R.append(fmt(rng(w0, h0 + 1, c0, c0 + 4), {'backgroundColor': WB[k % 2], 'horizontalAlignment': 'CENTER', 'wrapStrategy': 'WRAP',
                                                'textFormat': {'bold': True, 'foregroundColor': WH}}, 'backgroundColor,horizontalAlignment,wrapStrategy,textFormat'))
    R.append(fmt(rng(r0, r1, c0, c0 + 4), {'backgroundColor': WL[k % 2]}, 'backgroundColor'))
    R.append(fmt(rng(r0, r1, c0 + 3, c0 + 4), {'numberFormat': {'type': 'PERCENT', 'pattern': '0.0%'}}, 'numberFormat'))
    R.append({'updateBorders': {'range': rng(w0, r1, c0, c0 + 4), 'left': L('SOLID_THICK', DK), 'right': L('SOLID_THICK', DK)}})
    for c in (c0 + 2, c0 + 3):
        col_l = chr(65 + c0 + 3)
        R.append({'addConditionalFormatRule': {'index': 0, 'rule': {'ranges': [rng(r0, r1, c, c + 1)], 'booleanRule': {
            'condition': {'type': 'CUSTOM_FORMULA', 'values': [{'userEnteredValue': f'=AND(ISNUMBER(${col_l}{r0 + 1}),ABS(${col_l}{r0 + 1})>0.02)'}]},
            'format': {'textFormat': {'foregroundColor': RED, 'bold': True}}}}}})
# horizontal splitter between filters
row = r0
for f in FILT:
    n = sum(1 for r in RES if r[0] == f)
    R.append({'updateBorders': {'range': rng(row, row + 1, 0, NC), 'top': L('SOLID_MEDIUM', DK)}})
    R.append(fmt(rng(row, row + n, 0, 1), {'textFormat': {'bold': True}}, 'textFormat'))
    row += n
for c, px in ((3, 260), (4, 260), (NC - 2, 300), (NC - 1, 380)):
    R.append({'updateDimensionProperties': {'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': c, 'endIndex': c + 1}, 'properties': {'pixelSize': px}, 'fields': 'pixelSize'}})
R.append(fmt(rng(r0, r1, 3, 5), {'wrapStrategy': 'WRAP', 'verticalAlignment': 'TOP', 'backgroundColor': {'red': 1, 'green': 0.98, 'blue': 0.9}}, 'wrapStrategy,verticalAlignment,backgroundColor'))
R.append(fmt(rng(r0, r1, NC - 2, NC), {'wrapStrategy': 'WRAP', 'verticalAlignment': 'TOP', 'backgroundColor': {'red': 0.99, 'green': 0.94, 'blue': 0.92}}, 'wrapStrategy,verticalAlignment,backgroundColor'))
call('POST', f'{API}/{DS}:batchUpdate', json={'requests': R})
print('tab rewritten', len(RES), 'rows')
