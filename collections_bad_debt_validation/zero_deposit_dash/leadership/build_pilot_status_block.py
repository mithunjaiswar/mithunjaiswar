"""24-Nov: Leadership | 0 DP (v2) - new block 'Pilot status, collection & critical resolution' from raw_v2.
Writes column D (Pan India) of block 1 (rows 75..); E:K are copy-pasted (relative refs), block 2 (last week) is a copy 25 rows below.
Filters reuse the tab's selectors: E5 deposit at allocation (X), G5 product (G), I5 habit (BE), K5 tenure / ELC (H). City = header row."""
import json, sys
T = 75                      # title row
WK = T + 1                  # week cell row (C)
H = T + 2                   # header row
R = "raw_v2!"
N = 30000
def rng(c): return f"{R}${c}$4:${c}${N}"
def crit(r):
    city = f'IF(D{H}="Pan India","*",D{H})'
    return (f'{rng("A")},$C{WK},{rng("F")},{city},{rng("G")},IF($G$5="All products","*",$G$5),'
            f'{rng("BE")},IF($I$5="All habits","*",$I$5),{rng("H")},IF($K$5="All tenures","*",$K$5),'
            f'{rng("X")},IF($E$5="0–₹3K",{{"0 Deposit","1-3K"}},IF($E$5="All deposits","*",$E$5))')
def cnt(x=''): return f'=SUMPRODUCT(COUNTIFS({crit(0)}{x}))'
def sm(col, x='', neg=False, lakh=True):
    f = f'SUMPRODUCT(SUMIFS({rng(col)},{crit(0)}{x}))'
    if neg: f = '-' + f
    return '=' + (f'{f}/100000' if lakh else f)
def arr(cond):   # SUMPRODUCT over rows (for "any day" logic)
    city = f'IF(D{H}="Pan India",1,{rng("F")}=D{H})'
    dep = f'IF($E$5="All deposits",1,IF($E$5="0–₹3K",({rng("X")}="0 Deposit")+({rng("X")}="1-3K"),{rng("X")}=$E$5))'
    base = (f'({rng("A")}=$C{WK})*{city}*IF($G$5="All products",1,{rng("G")}=$G$5)*'
            f'IF($I$5="All habits",1,{rng("BE")}=$I$5)*IF($K$5="All tenures",1,{rng("H")}=$K$5)*{dep}')
    return f'=SUMPRODUCT({base}*{cond})'
anycrit = 'ISNUMBER(FIND("1",' + '&'.join(rng(c) for c in ['DL','DM','DN','DO','DP','DQ','DR','DS','DT','DU','DV','DW','DX','DY']) + '))'
solved = f'{anycrit}*({rng("AZ")}<>"Yes")'
rows = [   # label, formula(row), fmt     (24-Nov v2: OS amounts on AF = weekly OS incl. live-only pilots, same base as the 100% cap of AN)
 ('Total pilots (in raw_v2 for the week)', lambda r: cnt(), 'int'),
 ('Active (has car now)', lambda r: cnt(f',{rng("M")},"Active"'), 'int'),
 ('Inactive (no car now)', lambda r: cnt(f',{rng("M")},"Inactive"'), 'int'),
 ('Pilots with weekly OS (Monday hisaab) to collect', lambda r: cnt(f',{rng("AF")},"<0"'), 'int'),
 ('Weekly OS (Monday hisaab) to collect', lambda r: sm('AF', f',{rng("AF")},"<0"', neg=True), 'lakh'),
 ('Weekly OS collected', lambda r: sm('AN'), 'lakh'),
 ('Weekly OS NOT collected', lambda r: f'=D{r-2}-D{r-1}', 'lakh'),
 ('Weekly OS collected %', lambda r: f'=IFERROR(D{r-2}/D{r-3},0)', 'pct'),
 ('Rent of the week (new OS)', lambda r: sm('AU', neg=True), 'lakh'),   # AU is negative in raw_v2
 ('Collected in the week (all payments)', lambda r: sm('AH'), 'lakh'),
 ('Collection % (collected / (weekly OS + rent))', lambda r: f'=IFERROR(D{r-1}/(D{r-6}+D{r-2}),0)', 'pct'),
 ('Pilots with weekly OS still pending', lambda r: cnt(f',{rng("AO")},"<0"'), 'int'),
 ('In car recovery (open)', lambda r: cnt(f',{rng("BG")},"Open"'), 'int'),
 ('Car recovery closed in the week', lambda r: cnt(f',{rng("BG")},"Closed"'), 'int'),
 ('Critical on any day in the week', lambda r: arr(anycrit), 'int'),
 ('Critical solved (not critical at latest day)', lambda r: arr(solved), 'int'),
 ('   solved by car recovery (case closed)', lambda r: arr(f'{solved}*({rng("BG")}="Closed")'), 'int'),
 ('   solved by payment (paid in the week)', lambda r: arr(f'{solved}*({rng("BG")}<>"Closed")*({rng("AH")}>0)'), 'int'),
 ('   solved other (no payment, no recovery close)', lambda r: f'=D{r-3}-D{r-2}-D{r-1}', 'int'),
 ('Still critical', lambda r: f'=D{r-5}-D{r-4}', 'int'),
 ('Critical solved %', lambda r: f'=IFERROR(D{r-5}/D{r-6},0)', 'pct'),
]
out = []
for i, (lab, f, fmt) in enumerate(rows):
    r = H + 1 + i
    out.append([lab, '', '', f(r), fmt])
json.dump({'rows': out, 'T': T, 'WK': WK, 'H': H, 'last': H + len(rows)}, open(sys.argv[1], 'w'))
print('rows', H + 1, '->', H + len(rows))
