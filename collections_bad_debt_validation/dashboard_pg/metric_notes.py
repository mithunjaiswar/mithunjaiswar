# Short logic, easy example, difference reason and real employee example for every
# Summary_City_Product metric. Key = metric name (deposit rows keyed by section too).
COLL_R = 'Same OS and same amount for every pilot. Small gap only from product tag: old Sheet saved product on its run day, MV has today\'s product. MV also has a few new pilots.'
COLL_X = 'ETB060954 (28-Sep): OS -2,12,914 in both. Old Sheet product = EV_D2O, MV product = EV, so it falls in a different product filter. ETB064372: in MV (EIP, OS -19,627), missing in old Sheet.'
DP_R = 'Amount per pilot is same. Gap = "active full week" check. Old Sheet flag looks taken on its run day. New logic: car allocated all 7 days of the hisaab week.'
DP_X = 'ETB08329 (14-Sep): car with pilot all 7 days. Old logic: not full week -> not counted. New logic: full week -> counted. ETB08127: jama on Mon 21-Sep. Old logic: full week -> counted. New logic: not full week -> not counted.'
LIVE_R = 'Old Sheet shows 0 for all buckets: its live OS column is not filled (stale). MV fills it.'
LIVE_X = 'All India, 14-Sep: old Sheet 0, MV 8,005 pilots not surpassing deposit.'
BD_R = 'MV bad debt amount differs for few pilots (MV calc vs old Sheet value). Most pilots same.'
BD_X = 'ETB04516: old Sheet bad debt -4,640, MV blank (no bad debt). ETB061509: old Sheet -16,725, MV -17,934.'
FUN_R = 'Old Sheet did not refresh next-week payments. MV takes payment made in next week, capped at bad debt.'
FUN_X = 'ETB39050: paid 2,250 in next week. Old Sheet 0, MV 2,250. ETB062035: bad debt -358, paid 5,917 on 22-Sep -> MV counts only 358.'
REC_R = 'Old Sheet recovery tab is missing, so it shows 0. MV numbers = Central Car Recovery Dash.'
REC_X = 'All India, 14-Sep: old Sheet 0, MV 1,110 initiated (same as Recovery Dash).'
RISK_R = 'Risk score uses payment habit, OS vs deposit, ND count, GPS, connects. MV values differ for some pilots, so the bucket moves.'
RISK_X = 'ETB01849 (28-Sep): old Sheet Low Risk, MV Minimal Risk. ETB02245: old Sheet Minimal Risk, MV No risk.'
PB_R = 'Summary uses MV last_week_payment_habit (col Z). It is different from the old Sheet habit. Our own habit col (BA) matches old Sheet 100%.'
PB_X = 'ETB00839 (28-Sep): old Sheet Average, MV Defaulter. Fix: count on col BA (payment_habit_week) -> matches.'
DT_R = 'Same deposit for each pilot. Small gap: old Sheet saved product on its run day; 92-98% pilots have same product.'
DT_X = 'Pilot moved product after old Sheet run (e.g. Own Now -> D2O). Old Sheet counts in old product, MV in current product.'
DA_R = 'Cannot match. Old Sheet deposit-at-allocation col (N) is pasted and shuffled, values jump week to week.'
DA_X = 'ETH050004: old Sheet col N = 50,000 / 15,000 / 2,500 / 1,50,000 in different weeks. Real deposit = 50,000 (MV).'

COLL = 'Collection'
N = {
 'Collections Target%': ('Target collections / target OS from City_Targets tab.', 'Target collect 83, target OS 100 -> 83%.', '', ''),
 'Total Collections %': ('Total collected (capped at OS) / Total OS.', 'OS 100, paid 50 -> 50 / 100 = 50%.', COLL_R, COLL_X),
 'Total Outstanding': ('Sum of total OS of all pilots in the week.', 'Pilot A OS -100, Pilot B OS -50 -> Total OS -150.', COLL_R, COLL_X),
 'Total Actual Collections': ('Razorpay + Other + PhonePe + Adjustment + Deposit to rent. Each 100% based (capped at OS).', 'OS 100, paid 110 -> count only 100. Extra 10 not counted.', COLL_R, COLL_X),
 'Razorpay Collections': ('Razorpay paid, capped at OS (counted first).', 'OS 100, Razorpay 120 -> 100 counted.', COLL_R, COLL_X),
 'Other Collections': ('Other mode paid, capped at OS left after Razorpay.', 'OS 100, Razorpay 70, Other 50 -> Other = 30.', COLL_R, COLL_X),
 'Phonepe Collections': ('PhonePe paid, capped at OS left after Razorpay + Other.', 'OS 100, Razorpay 80, PhonePe 40 -> PhonePe = 20.', COLL_R, COLL_X),
 'Adjustments': ('Adjustment, capped at OS left after Razorpay + Other + PhonePe.', 'OS 100, paid 90, adjustment 30 -> Adjustment = 10.', COLL_R, COLL_X),
 'Deposit Convert to Rent': ('Deposit used for rent, capped at OS left after all other modes.', 'OS 100, paid 60, deposit to rent 50 -> 40 counted.', COLL_R, COLL_X),
 'Total Collections % (wt Advances)': ('Total paid incl. extra/advance (no cap) / Total OS.', 'OS 100, paid 110 -> 110%.', COLL_R, COLL_X),
 'Razorpay Collections %': ('Razorpay / Total Actual Collections.', 'Collected 100, Razorpay 60 -> 60%.', COLL_R, COLL_X),
 'Other Collections %': ('Other / Total Actual Collections.', 'Collected 100, Other 20 -> 20%.', COLL_R, COLL_X),
 'Phonepe Collections %': ('PhonePe / Total Actual Collections.', 'Collected 100, PhonePe 10 -> 10%.', COLL_R, COLL_X),
 'Adjustments %': ('Adjustment / Total Actual Collections.', 'Collected 100, Adjustment 5 -> 5%.', COLL_R, COLL_X),
 'Deposit Convert to Rent %': ('Deposit to rent / Total Actual Collections.', 'Collected 100, Deposit to rent 5 -> 5%.', COLL_R, COLL_X),
 'Total no of Pilots In negative': ('Count of pilots with OS < 0.', '10 pilots, 7 have OS below 0 -> 7.', COLL_R, COLL_X),
 'Not-paid pilots counts': ('Pilots with OS < 0 and paid 0 in the week.', 'OS -500 and paid 0 -> counted. OS -500 and paid 100 -> not counted.', COLL_R, COLL_X),
 'Not paid > 2 weeks': ('Pilots who did not pay in last 2 weeks.', 'No payment in 2 weeks -> counted.', COLL_R, COLL_X),
 'Till Wed Collections %': ('Paid till Wednesday (capped at OS) / Total OS.', 'OS 100, paid 40 by Wed -> 40%.', COLL_R, COLL_X),
 'Total Collections % (wo Convert to Rent) %': ('(Razorpay + Other + Adjustment) / Total OS. No deposit to rent.', 'OS 100, Razorpay 50, Other 10, Adj 5, Dep-to-rent 20 -> 65%.', COLL_R, COLL_X),
 'Active driver DP to OS Amount': ('Deposit to rent amount, only pilots with car all 7 days of the week.', 'Pilot with car 7 days, 1,000 deposit used -> 1,000. Car 5 days -> not counted.', DP_R, DP_X),
 'Active driver DP to OS Count': ('Count of full-week pilots with deposit to rent > 0.', '3 full-week pilots used deposit -> 3.', DP_R, DP_X),
 'Active driver DP to OS %': ('Active DP to OS amount / Total OS.', 'OS 1,00,000, DP to OS 2,000 -> 2%.', DP_R, DP_X),
 'Live OS Not Surpass deposit': ('Active pilots with OS < 0 but OS not more than deposit.', 'OS -3,000, deposit 5,000 -> not surpass.', LIVE_R, LIVE_X),
 'Live OS Surpass Deposit - Below 500': ('Active pilots: OS - deposit between 1 and 499.', 'OS -5,300, deposit 5,000 -> 300 -> this bucket.', LIVE_R, LIVE_X),
 'Live OS Surpass Deposit - 500 to 2K': ('Active pilots: OS - deposit 500 to 1,999.', 'OS -6,000, deposit 5,000 -> 1,000.', LIVE_R, LIVE_X),
 'Live OS Surpass Deposit - 2K to 5K': ('Active pilots: OS - deposit 2,000 to 4,999.', 'OS -8,000, deposit 5,000 -> 3,000.', LIVE_R, LIVE_X),
 'Live OS Surpass Deposit - 5K to 10K': ('Active pilots: OS - deposit 5,000 to 9,999.', 'OS -12,000, deposit 5,000 -> 7,000.', LIVE_R, LIVE_X),
 'Live OS Surpass Deposit - 10K to 30K': ('Active pilots: OS - deposit 10,000 to 29,999.', 'OS -25,000, deposit 5,000 -> 20,000.', LIVE_R, LIVE_X),
 'Live OS Surpass Deposit - 30K to 50K': ('Active pilots: OS - deposit 30,000 to 49,999.', 'OS -45,000, deposit 5,000 -> 40,000.', LIVE_R, LIVE_X),
 'Live OS Surpass Deposit - More than 50K': ('Active pilots: OS - deposit 50,000 or more.', 'OS -60,000, deposit 5,000 -> 55,000.', LIVE_R, LIVE_X),
 'Bad Debt Target%': ('Target bad debt / target OS from City_Targets tab.', 'Target bad debt 2.3, target OS 100 -> 2.3%.', '', ''),
 'Bad Debt %': ('Total bad debt / Total OS.', 'Bad debt -5, OS -100 -> 5%.', BD_R, BD_X),
 'Total Bad debt Amount': ('Sum of bad debt (unpaid OS of pilots who left).', 'Pilot left with OS -4,000 not paid -> -4,000.', BD_R, BD_X),
 'Bad Debt Partner Count': ('Count of pilots with bad debt < 0.', '3 pilots with bad debt -> 3.', BD_R, BD_X),
 'Bad debt partner %': ('Bad debt pilots / pilots in negative.', '5 bad debt pilots, 100 negative pilots -> 5%.', BD_R, BD_X),
 'Bad debt per partner': ('Total bad debt / bad debt pilot count.', '-10,000 / 2 pilots -> -5,000.', BD_R, BD_X),
 'Bad debt collected (Funnel)': ('Next-week payment by bad debt pilot, max = bad debt amount.', 'Bad debt -100, paid 50 next week -> 50. Paid 150 -> only 100.', FUN_R, FUN_X),
 '% Of OS collected': ('Bad debt collected (Funnel) / Total bad debt.', 'Bad debt 100, 50 came back -> 50%.', FUN_R, FUN_X),
 'Net Bad Debt': ('Total bad debt + Funnel collected.', 'Bad debt -100, collected 30 -> -70.', BD_R + ' Funnel: ' + FUN_R, BD_X),
 'Net Bad Debt %': ('Net bad debt / Total OS.', 'Net bad debt -70, OS -1,000 -> 7%.', BD_R + ' Funnel: ' + FUN_R, BD_X),
 'Cars recomended for Recovery': ('Pilots where OS not paid is more than week-end deposit.', 'OS gap 6,000, deposit 5,000 -> Yes, recommend.', 'Small gap (~4%). Same rule; deposit / OS value of some pilots differs from old Sheet run day.', 'Pilot with OS gap 5,200, deposit 5,000 on week end -> MV Yes. If old Sheet took deposit 6,000 on its run day -> No.'),
 'No of vehicles Initiated for recovery': ('Recovery cases started in the week (Recovery Dash rule).', '3 cases started Mon-Sun -> 3.', REC_R, REC_X),
 'Brought Forward Recovery': ('Cases started before the week and still open at week start.', 'Case started last week, still open -> 1.', REC_R, REC_X),
 'Vehicles Recovered - Organic': ('Cancelled cases closed in week where pilot dropped car / check-in done.', 'Pilot returned car himself -> organic 1.', REC_R, REC_X),
 'Vehicles Recovered - Recovery Team': ('Completed cases closed in the week.', 'Team picked 2 cars -> 2.', REC_R, REC_X),
 'Pending Car Recoveries': ('Cases started till week end and still open after week end.', '5 open cases at Sunday -> 5.', REC_R, REC_X),
 'Critical Risk': ('Risk score 6 of 6 (all bad signs).', 'Not paid, OS > deposit, defaulter, ND > 2, GPS off, no connects -> 6 -> Critical.', RISK_R, RISK_X),
 'High Risk': ('Risk score 5.', '5 bad signs out of 6 -> High.', RISK_R, RISK_X),
 'Moderate Risk': ('Risk score 4.', '4 bad signs -> Moderate.', RISK_R, RISK_X),
 'Low Risk': ('Risk score 3.', '3 bad signs -> Low.', RISK_R, RISK_X),
 'Minimal Risk': ('Risk score 2.', '2 bad signs -> Minimal.', RISK_R, RISK_X),
 'No risk': ('Risk score 0 or 1.', '0 or 1 bad sign -> No risk.', RISK_R, RISK_X),
 'Excellent': ('Pilot OS = 0 (nothing due).', 'OS 0 -> Excellent.', PB_R, PB_X),
 'Very Good': ('Paid full OS by Wednesday.', 'OS 100, paid 100 by Wed -> Very Good.', PB_R, PB_X),
 'Good': ('Paid full OS in the week (after Wed).', 'OS 100, paid 100 on Sat -> Good.', PB_R, PB_X),
 'Average': ('Paid 75% to 99% of OS.', 'OS 100, paid 80 -> Average.', PB_R, PB_X),
 'Defaulter': ('Paid less than 75% of OS.', 'OS 100, paid 50 -> Defaulter.', PB_R, PB_X),
}
DEP = {'Deposit <= 0': ('deposit 0 or less', 'Deposit 0 -> this bucket.'),
       'Deposit Between 0-2000': ('deposit 1 to 2,000', 'Deposit 1,500 -> this bucket.'),
       'Deposit Between 2000-5000': ('deposit 2,001 to 5,000', 'Deposit 4,000 -> this bucket.'),
       'Deposit Between 5000-10000': ('deposit 5,001 to 10,000', 'Deposit 8,000 -> this bucket.'),
       'Deposit Between 10000-20000': ('deposit 10,001 to 20,000', 'Deposit 15,000 -> this bucket.'),
       'Deposit 20000+': ('deposit more than 20,000', 'Deposit 25,000 -> this bucket.')}

def note(section, metric):
    if section.startswith('Deposit Threshold') and metric in DEP:
        b, e = DEP[metric]
        return ('Active pilots in the week, week-end deposit: ' + b + '.', e, DT_R, DT_X)
    if section.startswith('Deposit [At') and metric in DEP:
        b, e = DEP[metric]
        return ('Active pilots: deposit at week end of their last allocation week: ' + b + '.', e.replace('Deposit', 'Deposit at alloc week'), DA_R, DA_X)
    return N.get(metric, ('', '', '', ''))
