"""Builds 0_performance_dash formulas (Zero & Low Deposit Monitoring Dashboard) on the 0_raw tab
(ONLY 0 deposit pilots, pilot x week, 3 weeks, data from row 4; daily values in D1..D7 column blocks).
Weekly block C:E (3 weeks), daily block G:T (last 14 days). Filters: B1 city, B2 product, B3 join type ('*' = all).
B4 = last data day. Writes column C (weekly) and G (daily); the other columns are copy-pasted (relative refs)."""
import json, sys

R = "'0dp_raw'!"
def c(col): return f"{R}${col}:${col}"
def blk(a, b): return f"{R}${a}:${b}"
FILT = f'{c("E")},$B$1,{c("F")},$B$2,{c("H")},$B$3'
WK = 'C$7'                                    # weekly: Monday of the week
DWK = 'G$7-WEEKDAY(G$7,3)'                    # daily: Monday of that day's week
DOW = 'WEEKDAY(G$7,2)'                        # daily: 1 = Monday .. 7 = Sunday
def day(a, b): return f'INDEX({blk(a, b)},0,{DOW})'
ACT, LO, RENT, COLL, BD, RC = (day('AH', 'AN'), day('AO', 'AU'), day('AV', 'BB'),
                               day('BC', 'BI'), day('BJ', 'BP'), day('BQ', 'BW'))

def wcount(extra=''): return f'=COUNTIFS({c("A")},{WK},{FILT}{extra})'
def wsum(col, extra=''): return f'=SUMIFS({c(col)},{c("A")},{WK},{FILT}{extra})'
def dcount(extra=''): return f'=COUNTIFS({c("A")},{DWK},{FILT}{extra})'
def dsum(rng, extra=''): return f'=SUMIFS({rng},{c("A")},{DWK},{FILT}{extra})'

FIRST = 8
rows = []
def add(sec, label, w, d, fmt='int'): rows.append((sec, label, w, d, fmt))
add('Joins', 'Joined at 0 deposit', wcount(f',{c("J")},"Yes"'), dcount(f',{c("G")},G$7'))                       # 0
add('', '  New Join', wcount(f',{c("J")},"Yes",{c("H")},"New Join"'), dcount(f',{c("G")},G$7,{c("H")},"New Join"'))
add('', '  Rejoin', wcount(f',{c("J")},"Yes",{c("H")},"Rejoin"'), dcount(f',{c("G")},G$7,{c("H")},"Rejoin"'))
add('', '  Resurrection', wcount(f',{c("J")},"Yes",{c("H")},"Resurrection"'), dcount(f',{c("G")},G$7,{c("H")},"Resurrection"'))
add('0 DP Pilots', '0 DP pilots (joined at 0 deposit)', wcount(), dcount(f',{c("G")},"<="&G$7'))                 # 4
add('', 'Active (Live OS) - EOD', wcount(f',{c("W")},1'), dcount(f',{ACT},1'))                                      # 5
add('', 'Active %', ('ratio', 5, 4), ('ratio', 5, 4), 'pct')                                                      # 6
add('', 'Has car - EOD', wcount(f',{c("X")},1'), None)                                                            # 7
add('', 'Active, still at 0 deposit - EOD', wcount(f',{c("W")},1,{c("M")},0'), None)                              # 8
add('', 'Active, deposit built (> 0) - EOD', ('diff', 5, 8), None)                                                # 9
add('', 'Avg deposit - active, EOD (Rs)', f'=IFERROR(AVERAGEIFS({c("M")},{c("A")},{WK},{FILT},{c("W")},1),0)', None, 'rs')  # 10
add('OS & Collection', 'Weekly OS - Monday hisaab (Rs)', wsum('P'), None, 'rs')                                   # 11
add('', 'Rent - new OS (Rs)', wsum('Q'), dsum(RENT), 'rs')                                                        # 12
add('', 'Total OS to collect (Rs)', wsum('R'), None, 'rs')                                                        # 13
add('', 'Collected - Razorpay / PhonePe / Other (Rs)', wsum('S'), dsum(COLL), 'rs')                               # 14
add('', 'Adjustment + DP to OS (Rs)', wsum('T'), None, 'rs')                                                      # 15
add('', 'Collection % (collected / total OS)', ('ratio', 14, 13), None, 'pct')                                    # 16
add('', 'Live OS owed - EOD (Rs)', '=-' + wsum('V', f',{c("V")},"<0"')[1:], '=-' + dsum(LO, f',{LO},"<0"')[1:], 'rs')  # 17
add('Bad Debt', 'Bad debt pilots - EOD', wcount(f',{c("Y")},">0"'), dcount(f',{BD},">0"'))                         # 18
add('', 'Bad debt (Rs) - EOD', wsum('Y'), dsum(BD), 'rs')                                                         # 19
add('', '  of which Active (has car) - pilots', wcount(f',{c("Z")},"Active"'), None)                              # 20
add('', '  of which Left (no car) - pilots', wcount(f',{c("Z")},"Left"'), None)                                   # 21
add('', 'Bad debt per 0 DP pilot (Rs)', ('ratio', 19, 4), ('ratio', 19, 4), 'rs')                                 # 22
add('Car Recovery', 'In car recovery - EOD', wcount(f',{c("AA")},1'), dcount(f',{RC},1'))                          # 23
add('', 'Recovery raised', wsum('AB'), None)                                                                      # 24
add('', 'Recovery closed', wsum('AC'), None)                                                                      # 25
add('', 'Car recovered (status complete)', wsum('AD'), None)                                                      # 26
add('', 'Car recovered % of raised', ('ratio', 26, 24), None, 'pct')                                              # 27
add('Calling', 'Calls attempted', wsum('AE'), None)                                                               # 28
add('', 'Calls connected', wsum('AF'), None)                                                                      # 29
add('', 'Connect %', ('ratio', 29, 28), None, 'pct')                                                              # 30

def resolve(f, col):
    if f is None: return ''
    if isinstance(f, tuple):
        k, a, b = f
        if k == 'ratio': return f'=IFERROR({col}{FIRST + a}/{col}{FIRST + b},0)'
        if k == 'diff': return f'={col}{FIRST + a}-{col}{FIRST + b}'
    return f

out = {'AB': [], 'C': [], 'G': [], 'fmts': [], 'first': FIRST, 'n': len(rows)}
for sec, label, w, d, fmt in rows:
    out['AB'].append([sec, label]); out['C'].append([resolve(w, 'C')]); out['G'].append([resolve(d, 'G')]); out['fmts'].append(fmt)
json.dump(out, open(sys.argv[1], 'w'))
print(len(rows), 'metric rows; last row', FIRST + len(rows) - 1)
