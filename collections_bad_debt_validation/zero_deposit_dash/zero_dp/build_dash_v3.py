"""24-Nov v3: 0_performance_dash on 0dp_raw v2 (zero_dp_raw_v2.sql, 0 DP = CURRENT deposit 0, + all joins).
Weekly C:E (C7:E7 = Mondays), daily G:M (G7 = E7 .. +6, current week). Filters B1 city (E), B2 product (F), B3 join type (I)."""
import json, sys
R = "'0dp_raw'!"
def c(col): return f"{R}${col}:${col}"
def blk(a, b): return f"{R}${a}:${b}"
FILT = f'{c("E")},$B$1,{c("F")},$B$2,{c("I")},$B$3'
def wc(x): return f'=COUNTIFS({c("A")},C$7,{FILT}{x})'
def ws(col, x=''): return f'=SUMIFS({c(col)},{c("A")},C$7,{FILT}{x})'
def dd(a, b, x=''): return f'=SUMIFS(INDEX({blk(a, b)},0,WEEKDAY(G$7,2)),{c("A")},G$7-WEEKDAY(G$7,3),{FILT}{x})'
F = 8
rows = [
 ('0 DP Pilots', 'Total 0 DP pilots with car (current deposit 0)', wc(f',{c("M")},1'), dd('Y', 'AE'), 'int'),          # 8
 ('Joins', 'Total pilots joined (any deposit)', wc(f',{c("G")},"Yes"'), dd('AF', 'AL'), 'int'),                          # 9
 ('', 'Joined at 0 deposit', wc(f',{c("K")},"Yes"'), dd('AM', 'AS'), 'int'),                                             # 10
 ('', '   New Join', wc(f',{c("K")},"Yes",{c("I")},"New Join"'), dd('AM', 'AS', f',{c("I")},"New Join"'), 'int'),        # 11
 ('', '   Rejoin', wc(f',{c("K")},"Yes",{c("I")},"Rejoin"'), dd('AM', 'AS', f',{c("I")},"Rejoin"'), 'int'),              # 12
 ('', '   Resurrection', wc(f',{c("K")},"Yes",{c("I")},"Resurrection"'), dd('AM', 'AS', f',{c("I")},"Resurrection"'), 'int'),  # 13
 ('', '0 deposit join % (of all joins)', '=IFERROR(C10/C9,0)', '=IFERROR(G10/G9,0)', 'pct'),                            # 14
 ('Left', '0 DP pilots left', wc(f',{c("Q")},1'), dd('AT', 'AZ'), 'int'),                                               # 15
 ('', 'OS left by them (Rs)', ws('R'), dd('BA', 'BG'), 'rs'),                                                            # 16
 ('', 'Left % (left / (with car + left))', '=IFERROR(C15/(C8+C15),0)', '=IFERROR(G15/(G8+G15),0)', 'pct'),               # 17
 ('Active & OS', '0 DP active pilots (driving)', wc(f',{c("O")},1'), dd('BH', 'BN'), 'int'),                             # 18
 ('', 'Active % (of 0 DP with car)', '=IFERROR(C18/C8,0)', '=IFERROR(G18/G8,0)', 'pct'),                                 # 19
 ('', 'OS owed - active 0 DP pilots (Rs)', ws('P'), dd('BO', 'BU'), 'rs'),                                               # 20
 ('', 'Total OS - 0 DP (Rs)  [week: net OS, day: live OS]', '=-' + ws('S', f',{c("S")},"<0"')[1:], '=G20', 'rs'),        # 21
 ('Collection', 'Collected from 0 DP pilots (Rs)', ws('T'), dd('BV', 'CB'), 'rs'),                                       # 22
 ('', 'Collection % (collected / (collected + OS))', '=IFERROR(C22/(C22+C21),0)', '=IFERROR(G22/(G22+G21),0)', 'pct'),   # 23
 ('Car Recovery', 'Car recovery raised', ws('U'), dd('CC', 'CI'), 'int'),                                               # 24
 ('', 'Car recovery closed', ws('V'), dd('CJ', 'CP'), 'int'),                                                           # 25
 ('', 'Cars recovered (status complete)', ws('W'), '', 'int'),                                                          # 26
 ('', 'Amount recovered in car recovery (Rs)', ws('X'), dd('CQ', 'CW'), 'rs'),                                           # 27
 ('', 'Recovery closed % (closed / raised)', '=IFERROR(C25/C24,0)', '=IFERROR(G25/G24,0)', 'pct'),                       # 28
]
notes = [
 'HOW TO READ  (filters B1:B3; weekly = Mon-Sun, current week = till today; daily = this week)',
 '0 DP pilot = CURRENT deposit 0: deposit balance at the end of a day the pilot had a car is 0 (on the exit day, the balance of the day before).',
 'Total pilots joined = every New Join / Rejoin / Resurrection (any deposit). Joined at 0 deposit = deposit 0 at the end of the join day.',
 '0 DP pilots left = 0 DP pilot returned the car and has no car at week end. OS left = OS owed on the last live OS row before leaving.',
 'Active = 0 DP pilot with a live OS row that day (driving). OS owed = live OS below 0.',
 'Total OS: week = net OS (total OS + collected) of the hisaab covering that week (current week = live OS today); day = live OS owed.',
 'Collected = Razorpay + PhonePe + other payments by 0 DP pilots (also after they left).',
 'Car recovery: raised on activation date, closed = tag 111/112/113, recovered = status complete. Amount recovered = payments made while the pilot was in car recovery.',
]
out = {'rows': rows, 'notes': notes, 'first': F}
json.dump(out, open(sys.argv[1], 'w'))
print(len(rows), 'rows', F, '->', F + len(rows) - 1)
