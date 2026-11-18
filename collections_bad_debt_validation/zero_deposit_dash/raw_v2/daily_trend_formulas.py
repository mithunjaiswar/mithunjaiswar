# Daily_Trend (test sheet copy) on raw_v2: only COUNTIFS / SUMIFS (+ INDEX to pick the day column). Run: python3 daily_trend_formulas.py out.json
import json, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import columns as c
H = [x[1] for x in c.COLS]
def L(i):
    s = ''; i += 1
    while i: i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s
def col(name): return L(H.index(name))
def rng(name): x = col(name); return f'raw_v2!${x}:${x}'
def day(block): a = H.index(f'{block} D1'); return f'raw_v2!${L(a)}:${L(a+6)}'
CITY, PROD, SDB, DEPA, HAB, ELC = rng('City'), rng('Product'), rng('Deposit Bucket at Allocation'), rng('Deposit at Allocation (Rs)'), rng('Payment Habit'), rng('ELC / Non-ELC')
WK = rng('Week (Mon)')
LO, CO, WO, SU = day('Live OS'), day('Collection'), day('Weekly OS Collected'), day('Owes >= Deposit')
AM, EOD, ATT, CON, BDT, BDA = day('Risk Morning'), day('Risk That Day'), day('Calls Attempted'), day('Calls Connected'), day('Bad Debt Type'), day('Bad Debt (Rs)')
RENT, DASH, WOS = rng('Daily Rent (Rs)'), rng('In Collections Dash'), rng('Weekly OS to Collect (Rs)')
JT, JD = rng('Joined This Week'), rng('Last Join Date')
RS, RC = rng('Recovery Start Date'), rng('Recovery Close Date')
DV, DW, DX, NS = rng('Surpassed After Last Join'), rng('Recovery Raised After Last Join'), rng('Recovered After Last Join'), rng('New Surpass Date')
T = 'Copy of Copy of Daily_Trend'
cols = [L(i) for i in range(2, 23)]   # C..W
out = {}
out['Z1'] = '=IF(OR($B$1="All",$B$1=""),"*",$B$1)'
out['Z3'] = '=IF(OR($B$2="All",$B$2=""),"*",$B$2)'
out['Z4'] = '=IF(OR($B$3="All",$B$3="",$B$3="<=3K (incl. 0)"),"*",$B$3)'
out['Z5'] = '=IF($B$3="<=3K (incl. 0)","<=3000","<>")'
out['Z6'] = '=IF(OR($B$4="All",$B$4=""),"*",$B$4)'
out['Z7'] = '=IF(OR($B$5="All",$B$5=""),"*",$B$5)'
out['P1'] = '=IFERROR("Last updated: "&TEXT(MAX(raw_v2!$B:$B),"dd-mmm hh:mm")&"  ("&TEXT((NOW()-MAX(raw_v2!$B:$B))*24,"0.0")&" hrs ago)","Last updated: -")'
out['A9'] = '=IFERROR("Data: "&TEXT(MAX(raw_v2!$B:$B),"dd-mmm hh:mm"),"Data: -")'
for k, x in enumerate(cols):
    p = cols[k-1] if k else None
    base = f'{WK},{x}$8,{CITY},$Z$1,{PROD},$Z$3,{SDB},$Z$4,{DEPA},$Z$5,{HAB},$Z$6,{ELC},$Z$7'
    d = lambda blk: f'INDEX({blk},0,{x}$7)'
    cnt = lambda *a: 'COUNTIFS(' + ','.join([base] + list(a)) + ')'
    sm = lambda r, *a: 'SUMIFS(' + ','.join([r, base] + list(a)) + ')'
    wtd = lambda row: f'SUMIFS($C${row}:{x}${row},$C$8:{x}$8,{x}$8)'   # week to date = sum of the day row in the same week
    f = {}
    f[7] = f'=WEEKDAY({x}9,2)'
    f[8] = f'={x}9-WEEKDAY({x}9,3)'
    f[9] = '=MIN(raw_v2!$A:$A)' if k == 0 else f'={p}9+1'
    act = f'{d(LO)},">-1E+15"'
    f[10] = '=' + cnt(act)
    f[11] = '=' + cnt(act, SDB, '"0 Deposit"')
    jn = f'{JD},{x}$9,{JT},"<>Existing"'
    f[12] = '=' + cnt(jn)
    f[13] = '=' + cnt(jn, SDB, '"0 Deposit"')
    f[14] = f'={x}12-' + cnt(jn, act)
    f[15] = f'={x}13-' + cnt(jn, act, SDB, '"0 Deposit"')
    f[16] = '=' + sm(RENT, act)
    f[17] = f'=MAX(0,{sm(d(CO))}-{sm(d(WO))})'
    f[18] = f'=IFERROR(MIN(1,{x}17/{x}16),0)'
    f[19] = '=' + wtd(16)
    f[20] = '=' + wtd(17)
    f[21] = f'=IFERROR(MIN(1,{x}20/{x}19),0)'
    f[22] = '=-' + sm(WOS, DASH, '1')
    f[23] = f'={x}19'
    f[24] = f'={x}22+{x}23'
    f[25] = f'=SUMIFS($C$80:{x}$80,$C$8:{x}$8,{x}$8)'   # row 80 = collection that day (helper row, kept below the table)
    f[80] = '=' + sm(d(CO))
    f[26] = f'=IFERROR({x}25/{x}24,0)'
    f[27] = '=' + sm(d(WO), DASH, '1')
    f[28] = f'=IFERROR({wtd(27)}/{x}22,0)'
    f[29] = f'=-SUMIFS({d(LO)},{base},{d(LO)},"<0")'
    f[30] = '=' + cnt(d(AM), '1')
    f[31] = '=' + cnt(d(EOD), '1')
    f[32] = f'=IFERROR(({x}30-{x}31)/{x}30,0)'
    f[33] = '=' + cnt(d(AM), '1', d(ATT), '">0"')
    f[34] = '=' + cnt(d(AM), '1', d(CON), '">0"')
    for r in range(35, 42): f[r] = ''   # dispositions per day are not in raw_v2
    f[42] = '=' + cnt(d(AM), '1', d(ATT), '0')
    f[43] = '=' + cnt(d(ATT), '">0"')
    f[44] = f'=IFERROR({cnt(d(CON), chr(34)+">0"+chr(34))}/{x}43,0)'
    lt = f'"<"&{x}$9'; le = f'"<="&{x}$9'
    f[45] = f'={cnt(RS, lt)}-{cnt(RS, lt, RC, lt)}'
    f[46] = '=' + cnt(RS, f'{x}$9')
    f[47] = '=' + cnt(RC, f'{x}$9')
    f[48] = f'=IFERROR(({sm(RC, RC, x+"$9")}-{sm(RS, RC, x+"$9")})/{x}47,0)'
    f[49] = f'={cnt(RS, le)}-{cnt(RS, le, RC, le)}'
    for r, (a, b) in zip(range(50, 55), [(2, 0), (5, 3), (7, 6), (14, 8), (None, 15)]):
        lo = f'">="&({x}$9-{a})' if a is not None else None
        hi = f'"<="&({x}$9-{b})'
        crit = ([RS, lo] if lo else []) + [RS, hi]
        f[r] = f'={cnt(*crit)}-{cnt(*(crit + [RC, le]))}'
    f[55] = '=' + cnt(d(SU), '1')
    f[56] = '=' + cnt(d(SU), '1', RS, le)
    f[57] = f'={x}55-{x}56'
    f[58] = f'=IFERROR({x}56/{x}55,0)'
    f[59] = '=' + cnt(NS, f'{x}$9')
    f[60] = f'={x}59-{x}46'
    f[61] = '=' + cnt(jn)
    f[62] = '=' + cnt(jn, DV, '1')
    f[63] = f'=IFERROR({x}62/{x}61,0)'
    f[64] = '=' + cnt(jn, DW, '1')
    f[65] = '=' + cnt(jn, DX, '1')
    f[66] = '=' + cnt(jn, DV, '1', DW, '0')
    f[67] = '=' + cnt(NS, f'{x}$9', JD, f'">="&({x}$9-28)')
    f[68] = '=' + cnt(RC, f'{x}$9', JD, f'">="&({x}$9-28)')
    f[69] = '=' + cnt(d(BDT), '1')
    f[70] = '=' + sm(d(BDA), d(BDT), '1')
    f[71] = f'=IFERROR({x}70/{x}$24,0)'
    f[72] = f'={x}70-N({p}70)' if p else '=C70'
    f[73] = f'=IFERROR({x}70/{x}69,0)'
    f[74] = '=' + cnt(d(BDT), '2')
    f[75] = '=' + sm(d(BDA), d(BDT), '2')
    f[76] = f'=IFERROR({x}75/{x}$24,0)'
    f[77] = f'={x}75-N({p}75)' if p else '=C75'
    f[78] = f'=IFERROR({x}75/{x}74,0)'
    f[79] = f'={x}70+{x}75'
    for r, v in f.items(): out[f'{x}{r}'] = v
out['B80'] = 'helper: collection that day (Rs)'
json.dump(out, open(sys.argv[1], 'w'))
print(len(out), max(len(v) for v in out.values()))
