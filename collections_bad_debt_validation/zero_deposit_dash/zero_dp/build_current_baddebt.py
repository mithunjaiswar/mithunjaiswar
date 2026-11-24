# 24-Nov: bad debt amount / partners count ONLY attrition = Yes pilots (as Raja's sheet). User later removed the Pilots # block + moved filter to L1.
# Builds Current_BadDebt summary (L1:T44) + logic (L47+) in the Zero & Low Deposit sheet. Data A:J = automation (current_baddebt_0dp.sql).
import json
cities=['*','Mumbai','Kolkata','Bangalore','Delhi NCR','Hyderabad','Chennai','Pune']
prods=['*','SINGLE','EIP','D2O','Own Now','EV','Fixed Pay']
cols='NOPQRST'
F='IF($M$1="All","*",$M$1)'
base='$B$2:$B,$M{r},$C$2:$C,{c}$4,$H$2:$H,'+F
blocks=[('Pilots #','=COUNTIFS('+base+')'),
        ('Total Negative OS (Rs)','=SUMIFS($D$2:$D,'+base+',$D$2:$D,"<0")'),
        ('Bad Debt Amount (Rs)','=SUMIFS($F$2:$F,'+base+',$F$2:$F,"<0",$G$2:$G,"Yes")'),
        ('Bad Debt % (of negative OS)','=IFERROR({c}{r8}/{c}{r16},"-")'),
        ('Bad Debt Partners #','=COUNTIFS('+base+',$F$2:$F,"<0",$G$2:$G,"Yes")'),
        ('Attrition Pilots (left last week) #','=COUNTIFS('+base+',$G$2:$G,"Yes")')]
rows=[['0 DP filter ▸','All','=IFERROR("Updated: "&INDEX($J:$J,2)&"  |  All = every pilot, Yes = joined at 0 deposit, No = joined with deposit","")'],
      ['Hisaab week ▸','=TEXT(TODAY()-WEEKDAY(TODAY(),3),"dd-mmm-yyyy")'],[],
      ['Metric','City']+prods]
r=5
for name,f in blocks:
  for i,c in enumerate(cities):
    rows.append([name if i==0 else '',c]+[f.format(r=r,c=cl,r8=r-8,r16=r-16) for cl in cols])
    r+=1
logic=['LOGIC (data A:J is refreshed every hour by SQL Automation; do not edit A:J by hand)',
'Pilots: every pilot in this week\'s Monday hisaab (collections_bad_debt_mv, for_collections = 1), one row per pilot.',
'net_os (D) = total OS + total collected of the hisaab. Negative = the pilot owes money.',
'deposit (E) = security deposit at the end of the week.',
'bad_debt (F) = Own Now: the full net OS. Other products: net OS + deposit if that is below 0 (pilot owes more than the deposit), else 0.',
'attrition (G) = Yes if the pilot returned the car (jama) last week and has no car allocated today.',
'joined_at_0_deposit (H) = Yes if the latest New Join / Rejoin / Resurrection in the last 8 weeks had deposit 0 at the end of the join day (same rule as 0dp_raw).',
'last_join_date (I) = date of that latest join (blank if no join in the last 8 weeks).',
'Summary: "*" = all. Negative OS = sum of net_os below 0. Bad Debt % = Bad Debt Amount / Negative OS. Change M1 (All / Yes / No) to see only 0 deposit pilots.',
'Same logic as Calling Masterlist V2.0 > Current_BadDebt (Raja\'s Monday query); only the 0 deposit flag and last join date are new.']
json.dump({'summary':rows,'logic':[[x] for x in logic],'end':r-1},open('/tmp/claude-0/-home-user-mithunjaiswar/975ddfa8-2a6b-560b-8c6b-202af90fa71a/scratchpad/cbd.json','w'))
print(r-1)
