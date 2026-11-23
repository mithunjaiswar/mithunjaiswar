"""Builds 0_performance_dash formulas (Zero & Low Deposit Monitoring Dashboard).
Weekly block C:J (8 weeks, oldest -> this week), daily block L:Y (last 14 days).
Source: '0_raw' (JOIN rows = every join, DAY rows = 0 deposit pilot x day). Filters B1 city, B2 product, B3 join type ('*' = all)."""
import json, sys
from openpyxl.utils import get_column_letter as L

R = "'0_raw'!"
col = dict(A='A', date='B', week='C', city='D', prod='E', jdate='H', jtype='I', jweek='J', dep_join='K', zero='L',
           active='N', car='O', dep='P', bucket='Q', lo='R', rent='S', paid='T', adj='U', bda='V', bda_rs='W',
           bdl='X', bdl_rs='Y', inrc='Z', rcnew='AA', rcclose='AB', rcrec='AC', att='AD', conn='AE')
def c(k): return f"{R}${col[k]}:${col[k]}"
FILT = f'{c("city")},$B$1,{c("prod")},$B$2,{c("jtype")},$B$3'

WEEK_COLS = [L(i) for i in range(3, 11)]      # C..J
DAY_COLS = [L(i) for i in range(12, 26)]      # L..Y

def period(h, weekly):
    # date criteria: weekly = days of the week, daily = that day
    return (f'{c("date")},">="&{h}$7,{c("date")},"<="&{h}$7+6' if weekly else f'{c("date")},{h}$7')
def point(h, weekly):
    # point-in-time: weekly = last day of the week (or today), daily = that day
    return (f'{c("date")},MIN({h}$7+6,TODAY())' if weekly else f'{c("date")},{h}$7')

rows = []   # (section, label, kind, spec, fmt)
def add(sec, label, kind, spec=None, fmt='int'): rows.append((sec, label, kind, spec, fmt))

add('Joins', 'Total joins (all deposits)', 'join', [])
add('', 'Joined at 0 deposit', 'join', [('zero', '"Yes"')])
add('', '0 deposit share of joins %', 'ratio', (1, 0), 'pct')
add('', '0 DP - New Join', 'join', [('zero', '"Yes"'), ('jtype', '"New Join"')])
add('', '0 DP - Rejoin', 'join', [('zero', '"Yes"'), ('jtype', '"Rejoin"')])
add('', '0 DP - Resurrection', 'join', [('zero', '"Yes"'), ('jtype', '"Resurrection"')])
add('0 DP Pilots', '0 DP pilots (joined at 0 deposit, till date)', 'pcount', [])
add('', 'Active (Live OS) - EOD', 'pcount', [('active', 1)])
add('', 'Active %', 'ratio', (7, 6), 'pct')
add('', 'Has car - EOD', 'pcount', [('car', 1)])
add('', 'Active, still at 0 deposit', 'pcount', [('active', 1), ('bucket', '"0 Deposit"')])
add('', 'Active, deposit built (> 0)', 'diff', (7, 10))
add('', 'Avg deposit built - active (Rs)', 'pavg', ('dep', [('active', 1)]), 'rs')
add('Rent & Collection', 'Rent due (Rs)', 'psum', ('rent', []), 'rs')
add('', 'Paid - Razorpay / PhonePe / Other (Rs)', 'psum', ('paid', []), 'rs')
add('', 'Adjustment + DP to OS (Rs)', 'psum', ('adj', []), 'rs')
add('', 'Paid % of rent', 'ratio', (14, 13), 'pct')
add('', 'Live OS owed - EOD (Rs)', 'owed', None, 'rs')
add('Bad Debt', 'Active bad debt (owes >= deposit) - pilots', 'pcount', [('bda', 1)])
add('', 'Active bad debt (Rs)', 'ptsum', ('bda_rs', []), 'rs')
add('', 'Left bad debt (no car, owes > deposit) - pilots', 'pcount', [('bdl', 1)])
add('', 'Left bad debt (Rs)', 'ptsum', ('bdl_rs', []), 'rs')
add('', 'Total bad debt (Rs)', 'add', (19, 21), 'rs')
add('', 'Bad debt per 0 DP pilot (Rs)', 'ratio', (22, 6), 'rs')
add('Car Recovery', 'Recovery raised', 'psum', ('rcnew', []))
add('', 'Recovery closed', 'psum', ('rcclose', []))
add('', 'Car recovered (status complete)', 'psum', ('rcrec', []))
add('', 'Car recovered % of raised', 'ratio', (26, 24), 'pct')
add('', 'In car recovery - EOD', 'pcount', [('inrc', 1)])
add('Calling', 'Calls attempted', 'psum', ('att', []))
add('', 'Calls connected', 'psum', ('conn', []))
add('', 'Connect %', 'ratio', (30, 29), 'pct')

FIRST = 8  # first metric row
def extra(spec): return ''.join(f',{c(k)},{v}' for k, v in spec)

def formula(kind, spec, h, weekly, rowno):
    if kind == 'join':
        d = f'{c("jweek")},{h}$7' if weekly else f'{c("date")},{h}$7'
        return f'=COUNTIFS({c("A")},"JOIN",{d},{FILT}{extra(spec)})'
    if kind == 'pcount':
        return f'=COUNTIFS({c("A")},"DAY",{point(h, weekly)},{FILT}{extra(spec)})'
    if kind == 'psum':
        k, sp = spec
        return f'=SUMIFS({c(k)},{c("A")},"DAY",{period(h, weekly)},{FILT}{extra(sp)})'
    if kind == 'ptsum':
        k, sp = spec
        return f'=SUMIFS({c(k)},{c("A")},"DAY",{point(h, weekly)},{FILT}{extra(sp)})'
    if kind == 'pavg':
        k, sp = spec
        return f'=IFERROR(AVERAGEIFS({c(k)},{c("A")},"DAY",{point(h, weekly)},{FILT}{extra(sp)}),0)'
    if kind == 'owed':
        return f'=-SUMIFS({c("lo")},{c("A")},"DAY",{point(h, weekly)},{FILT},{c("lo")},"<0")'
    if kind == 'ratio':
        a, b = spec
        return f'=IFERROR({h}{FIRST + a}/{h}{FIRST + b},0)'
    if kind == 'diff':
        a, b = spec
        return f'={h}{FIRST + a}-{h}{FIRST + b}'
    if kind == 'add':
        a, b = spec
        return f'={h}{FIRST + a}+{h}{FIRST + b}'

grid = []
grid.append(['City ▸', '*', '', '="Last updated: "&IFERROR(INDEX(\'0_raw\'!AF2:AF2,1),"-")&"  |  0 deposit = deposit balance 0 at the end of the join day (New Join / Rejoin / Resurrection)"'] + [''] * 21)
grid.append(['Product ▸', '*'] + [''] * 23)
grid.append(['Join Type ▸', '*'] + [''] * 23)
grid.append([''] * 25)
grid.append(['', '', 'WEEKLY  |  join week for joins, Mon-Sun total for amounts, end of week (or today) for pilot counts'] + [''] * 8 +
            ['DAILY TREND  |  last 14 days'] + [''] * 13)
grid.append(['', '(week)'] + [f'=TEXT({h}7,"dd-mmm")' for h in WEEK_COLS] + [''] + [f'=TEXT({h}7,"ddd")' for h in DAY_COLS])
hdr = ['Section', 'Metric']
hdr += ['=TODAY()-WEEKDAY(TODAY(),3)-49'] + [f'={WEEK_COLS[i-1]}7+7' for i in range(1, 8)]
hdr += [''] + ['=TODAY()-13'] + [f'={DAY_COLS[i-1]}7+1' for i in range(1, 14)]
grid.append(hdr)
fmts = []
for i, (sec, label, kind, spec, fmt) in enumerate(rows):
    r = FIRST + i
    line = [sec, label] + [formula(kind, spec, h, True, r) for h in WEEK_COLS] + [''] + [formula(kind, spec, h, False, r) for h in DAY_COLS]
    grid.append(line); fmts.append(fmt)
json.dump({'grid': grid, 'fmts': fmts, 'first': FIRST}, open(sys.argv[1], 'w'))
print(len(grid), 'rows')
