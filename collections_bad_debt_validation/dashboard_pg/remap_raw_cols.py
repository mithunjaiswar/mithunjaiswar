# Point Summary / WBR / City_Targets / Metric_Summary formulas at the new Raw_Data layout
# (old Collections Sheet columns A..BS + BT..BV). Run once, right after Raw_Data is reloaded.
import re, sys, json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
MAP = {'A': 'A', 'B': 'D', 'D': 'F', 'F': 'H', 'H': 'AO', 'J': 'AN', 'K': 'AD', 'L': 'BC', 'M': 'E', 'P': 'I',
       'Q': 'U', 'R': 'O', 'T': 'P', 'U': 'Q', 'V': 'R', 'W': 'S', 'X': 'T', 'Z': 'AF', 'AB': 'AC', 'AF': 'BB',
       'AJ': 'BT', 'AK': 'AW', 'AL': 'BU', 'AM': 'AY', 'AN': 'AL', 'AO': 'AH', 'AY': 'BV', 'BB': 'AA', 'BF': 'AU',
       'BG': 'AQ'}
DRY = '--dry' in sys.argv
def fix(f):
    def rep(m):
        a, rest, b = m.group(1), m.group(2), m.group(3)
        if a == 'AV' and b == 'AV': return m.group(0)          # handled below
        if a not in MAP or b not in MAP: raise ValueError(f'unmapped column {a}/{b} in {f[:120]}')
        return f'Raw_Data!${MAP[a]}{rest}:${MAP[b]}'
    f = re.sub(r'Raw_Data!\$([A-Z]{1,2})(\$?\d*):\$([A-Z]{1,2})', rep, f)
    # recovery_pending (old AV > 0) -> case still open after the week end (BN end date > week end, BM start <= week end)
    f = re.sub(r'Raw_Data!\$A:\$A,([A-Z]+)\$8(.*?)Raw_Data!\$AV:\$AV,">0"',
               lambda m: f'Raw_Data!$A:$A,{m.group(1)}$8{m.group(2)}Raw_Data!$BN:$BN,">"&({m.group(1)}$8+6),Raw_Data!$BM:$BM,"<="&({m.group(1)}$8+6)', f)
    assert 'Raw_Data!$AV' not in f, f
    return f
for t in ['Summary', 'WBR', 'City_Targets', 'Metric_Summary']:
    v = call('GET', f"{API}/{DS}/values/'{t}'", params={'valueRenderOption': 'FORMULA'}).get('values', [])
    out, n = [], 0
    for r in v:
        row = []
        for x in r:
            if isinstance(x, str) and x.startswith('=') and 'Raw_Data!' in x:
                y = fix(x); n += y != x; row.append(y)
            else: row.append(x)
        out.append(row)
    print(t, 'formulas changed', n)
    if n and not DRY:
        json.dump(v, open(f'../dash/formulas_before_remap_{t}.json', 'w'))
        call('PUT', f"{API}/{DS}/values/'{t}'!A1", params={'valueInputOption': 'USER_ENTERED'}, json={'values': out})
