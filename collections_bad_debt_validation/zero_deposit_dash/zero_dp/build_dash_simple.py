"""24-Nov: SIMPLE 0_performance_dash (user asked: joins, left, active, OS generated, collected, OS left behind).
Same frame as build_dash.py: filters B1 city / B2 product / B3 join type, C7:E7 weeks, G7:T7 days, metrics from row 8.
Source = '0dp_raw' (only 0 deposit pilots, pilot x week, 3 weeks)."""
import json, sys
R = "'0dp_raw'!"
def c(col): return f"{R}${col}:${col}"
def blk(a, b): return f"{R}${a}:${b}"
FILT = f'{c("E")},$B$1,{c("F")},$B$2,{c("H")},$B$3'
WK, DWK, DOW = 'C$7', 'G$7-WEEKDAY(G$7,3)', 'WEEKDAY(G$7,2)'
def day(a, b): return f'INDEX({blk(a, b)},0,{DOW})'
ACT, LO, RENT, COLL = day('AH', 'AN'), day('AO', 'AU'), day('AV', 'BB'), day('BC', 'BI')
def wcount(x=''): return f'=COUNTIFS({c("A")},{WK},{FILT}{x})'
def wsum(col, x=''): return f'=SUMIFS({c(col)},{c("A")},{WK},{FILT}{x})'
def dcount(x=''): return f'=COUNTIFS({c("A")},{DWK},{FILT}{x})'
def dsum(rng, x=''): return f'=SUMIFS({rng},{c("A")},{DWK},{FILT}{x})'
F = 8
rows = [  # section, label, weekly C, daily G, format
 ('Pilots', 'Joined at 0 deposit', wcount(f',{c("J")},"Yes"'), dcount(f',{c("G")},G$7'), 'int'),
 ('', 'Total 0 deposit pilots (joined till date)', wcount(), dcount(f',{c("G")},"<="&G$7'), 'int'),
 ('', 'Active (driving) - end of day', wcount(f',{c("W")},1'), dcount(f',{ACT},1'), 'int'),
 ('', 'Left / not active - end of day', f'=C{F+1}-C{F+2}', f'=G{F+1}-G{F+2}', 'int'),
 ('', 'Active %', f'=IFERROR(C{F+2}/C{F+1},0)', f'=IFERROR(G{F+2}/G{F+1},0)', 'pct'),
 ('OS', 'OS generated - rent (Rs)', wsum('Q'), dsum(RENT), 'rs'),
 ('', 'Collected (Rs)', wsum('S'), dsum(COLL), 'rs'),
 ('', 'Collection % (collected / OS generated)', f'=IFERROR(C{F+6}/C{F+5},0)', f'=IFERROR(G{F+6}/G{F+5},0)', 'pct'),
 ('', 'OS pending - active pilots, end of day (Rs)', '=-' + wsum('V', f',{c("V")},"<0"')[1:], '=-' + dsum(LO, f',{LO},"<0"')[1:], 'rs'),
 ('Left with OS', 'Pilots who left with unpaid OS', wcount(f',{c("Z")},"Left"'), '', 'int'),
 ('', 'OS left unpaid by them (Rs)', wsum('Y', f',{c("Z")},"Left"'), '', 'rs'),
]
notes = [
 'HOW TO READ (only pilots who joined at 0 deposit; filters in B1:B3; weekly = Mon-Sun, daily = last 14 days)',
 'Joined at 0 deposit = New Join / Rejoin / Resurrection that week (or day) with deposit 0 at the end of the join day.',
 'Total 0 deposit pilots = all 0 deposit joins (last 8 weeks) till that week end / day.',
 'Active = pilot has a live OS row that day (car running). Left / not active = total - active.',
 'OS generated = rent booked for the days of that week / day. Collected = Razorpay + PhonePe + other payments.',
 'OS pending = money active pilots still owe at the end of the day.',
 'Pilots who left with unpaid OS = no car and no live OS at week end, and the last OS was more than the deposit. OS left unpaid = that amount (last OS - deposit).',
]
json.dump({'rows': rows, 'notes': notes, 'first': F}, open(sys.argv[1], 'w'))
print(len(rows), 'rows ->', F, 'to', F + len(rows) - 1)
