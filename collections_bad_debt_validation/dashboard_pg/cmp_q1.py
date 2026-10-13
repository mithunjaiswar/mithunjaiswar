# Compare Query 1 output (one week) with the sheet's Raw_Data rows, column by column.
import json, sys, collections
F = sys.argv[1]
Q = [l.strip()[2:].rstrip('|').rstrip().split('~') for l in json.load(open(F))['result'].split('\n') if l.strip().startswith('| 2026-')]
N = json.load(open('dash/raw_refresh.json')); h = N[0]
W = Q[0][0]
S = {r[1]: r for r in N[1:] if r[0] == W}
q = {r[1]: r for r in Q}
print('week', W, 'query rows', len(Q), 'sheet rows', len(S), 'only query', len(set(q) - set(S)), 'only sheet', len(set(S) - set(q)))
def eq(a, b):
    a, b = str(a).replace(',', ''), str(b).replace(',', '')
    if a == b: return True
    try: return abs(float(a or 0) - float(b or 0)) < 0.6
    except ValueError: return a.split('.')[0] == b.split('.')[0] if a[:4] == '2026' else False
bad = collections.Counter(); ex = {}
for p in set(q) & set(S):
    for i, c in enumerate(h):
        if c == 'mv_last_updated': continue
        if not eq(q[p][i], S[p][i]):
            bad[c] += 1; ex.setdefault(c, (p, q[p][i], S[p][i]))
for c in h:
    if bad[c]: print(f'{c:40s} diff {bad[c]:6d}  e.g. {ex[c][0]} query={ex[c][1]!r} sheet={ex[c][2]!r}')
print('columns all same:', sum(1 for c in h if not bad[c]), 'of', len(h))
