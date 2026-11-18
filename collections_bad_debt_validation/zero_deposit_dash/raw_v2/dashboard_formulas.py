# Formulas of the [TEST] raw_v2 sheet tabs Dashboard / Action_List / calc (hidden). Run: python3 dashboard_formulas.py out.json
import json,sys
N=30000
R=lambda c:f"raw_v2!${c}$4:${c}${N}"
M=f"calc!$A$4:$A${N}"
def col(c,off):
    n=0
    for ch in c: n=n*26+ord(ch)-64
    n+=off; s=''
    while n: n,r=divmod(n-1,26); s=chr(65+r)+s
    return s
# ---------- calc ----------
calc={}
calc['A1']='Selected week'
calc['B1']=f'=IFERROR(INDEX(SORT(UNIQUE(FILTER(raw_v2!A4:A{N},raw_v2!A4:A{N}<>"")),1,FALSE),IF(Dashboard!B3="Last week",2,1)),"")'
calc['A2']='Week start (date)'
calc['B2']='=IFERROR(IF(ISNUMBER(B1),B1,DATEVALUE(B1)),"")'
calc['A3']='mask (1 = row in filters)'; calc['B3']='action needed'; calc['C3']='action needed + NOT called today'; calc['D3']='P0 critical'
calc['A4']=(f'=ARRAYFORMULA(IF(raw_v2!C4:C{N}="",0,(raw_v2!A4:A{N}=$B$1)'
  f'*IF(Dashboard!$D$3="All",1,raw_v2!F4:F{N}=Dashboard!$D$3)'
  f'*IF(Dashboard!$F$3="All",1,raw_v2!G4:G{N}=Dashboard!$F$3)'
  f'*IF(Dashboard!$H$3="All",1,IF(Dashboard!$H$3="<=3K (incl. 0)",(raw_v2!X4:X{N}="0 Deposit")+(raw_v2!X4:X{N}="1-3K"),raw_v2!X4:X{N}=Dashboard!$H$3))'
  f'*IF(Dashboard!$J$3="All",1,IF(Dashboard!$J$3="Joined this week at 0 Deposit",raw_v2!AA4:AA{N}="Yes",IF(Dashboard!$J$3="Joined this week (any deposit)",raw_v2!U4:U{N}<>"Existing",raw_v2!U4:U{N}="Existing")))))')
calc['B4']=f'=ARRAYFORMULA(A4:A{N}*(raw_v2!Q4:Q{N}<>"No action"))'
calc['C4']=f'=ARRAYFORMULA(B4:B{N}*(N(raw_v2!CH4:CH{N})=0))'
calc['D4']=f'=ARRAYFORMULA(A4:A{N}*(LEFT(raw_v2!Q4:Q{N},2)="P0"))'
# dropdown lists
calc['F1']='Week'; calc['F2']='This week'; calc['F3']='Last week'
calc['G1']='City'; calc['G2']=f'={{"All";IFERROR(SORT(UNIQUE(FILTER(raw_v2!F4:F{N},raw_v2!F4:F{N}<>""))),"")}}'
calc['H1']='Product'; calc['H2']=f'={{"All";IFERROR(SORT(UNIQUE(FILTER(raw_v2!G4:G{N},raw_v2!G4:G{N}<>""))),"")}}'
for i,v in enumerate(['Deposit','All','0 Deposit','<=3K (incl. 0)','3-5K','5K+','Unknown']): calc[f'I{i+1}']=v
for i,v in enumerate(['Join','All','Joined this week at 0 Deposit','Joined this week (any deposit)','Existing pilots']): calc[f'J{i+1}']=v
ACTIONS=['P0 - Critical (Not in car recovery)','P0 - Critical (In car recovery)','P1 - Cancel the car recovery (OFC)','P1 - Near surpass (<=1 day rent to deposit)','P2 - OS not collected']
for i,v in enumerate(['Action','All']+ACTIONS): calc[f'K{i+1}']=v
for i,v in enumerate(['Called','All','NOT called today','Called today']): calc[f'L{i+1}']=v

# ---------- Dashboard ----------
D={}
fmt={}   # cell -> 'rs' | 'pct' | 'int'
D['A1']='Zero / Low Deposit - Weekly & Daily Action Dashboard'
D['A2']='=IF(raw_v2!B4="","No data yet - raw_v2 is empty","Data refreshed: "&raw_v2!B4&"     |     Week shown (Mon): "&IFERROR(TEXT(calc!B2,"dd-mmm-yyyy"),"")&"     |     Source: raw_v2 tab only")'
for c,l,v in [('A','Week ▸','This week'),('C','City ▸','All'),('E','Product ▸','All'),('G','Deposit at allocation ▸','All'),('I','Join ▸','All')]:
    D[f'{c}3']=l; D[f'{chr(ord(c)+1)}3']=v
def sec(r,t): D[f'A{r}']=t
cnt=lambda *a: 'COUNTIFS('+','.join(list(a)+[M,'1'])+')'
sm=lambda rng,*a: 'SUMIFS('+','.join([rng]+list(a)+[M,'1'])+')'
# 1. at a glance
sec(5,'1. WEEK AT A GLANCE')
k=[('Pilots',f'=SUM({M})','int'),
   ('Weekly OS to collect (Rs)',f'=-{sm(R("AC"))}','rs'),
   ('Collected towards weekly OS (Rs)',f'={sm(R("AL"))}','rs'),
   ('Collection %','=IFERROR(C7/B7,0)','pct'),
   ('Not paid (pilots)',f'={cnt(R("AO"),chr(34)+"Not Paid"+chr(34))}','int'),
   ('New joins this week',f'={cnt(R("U"),chr(34)+"<>Existing"+chr(34))}','int'),
   ('Joined at 0 deposit',f'={cnt(R("AA"),chr(34)+"Yes"+chr(34))}','int'),
   ('Owes >= deposit now (pilots)',f'={cnt(R("AZ"),chr(34)+"Yes"+chr(34))}','int'),
   ('In car recovery (pilots)',f'={cnt(R("BE"),chr(34)+"Open"+chr(34))}','int')]
for i,(l,f,t) in enumerate(k):
    c=chr(65+i); D[f'{c}6']=l; D[f'{c}7']=f; fmt[f'{c}7']=t
# 2. what to do
sec(9,'2. WHAT TO DO TODAY  (Action To Take)  -  and how many are NOT called yet')
hdr=['Action To Take','Pilots','Owed now (Rs)','Called today','NOT called today','NOT called this week','What the agent should do']
for i,h in enumerate(hdr): D[f'{chr(65+i)}10']=h
todo=['Raise car recovery + collect today','Push recovery team + collect','Cancel the car recovery (OS is below deposit)','Call - collect before the deposit is crossed','Call - collect the weekly OS']
q=lambda s: chr(34)+s+chr(34)
for j,a in enumerate(ACTIONS):
    r=11+j; D[f'A{r}']=a
    D[f'B{r}']=f'={cnt(R("Q"),f"$A{r}")}'
    D[f'C{r}']=f'=-{sm(R("AU"),R("Q"),f"$A{r}",R("AU"),q("<0"))}'
    D[f'D{r}']=f'={cnt(R("Q"),f"$A{r}",R("CH"),q(">0"))}'
    D[f'E{r}']=f'=B{r}-D{r}'
    D[f'F{r}']=f'=B{r}-{cnt(R("Q"),f"$A{r}",R("CF"),q(">0"))}'
    D[f'G{r}']=todo[j]
    for c,t in zip('BCDEF',['int','rs','int','int','int']): fmt[f'{c}{r}']=t
D['A16']='TOTAL action needed'
for c,t in zip('BCDEF',['int','rs','int','int','int']): D[f'{c}16']=f'=SUM({c}11:{c}15)'; fmt[f'{c}16']=t
D['A17']='No action (paid up / OK)'; D['B17']=f'={cnt(R("Q"),q("No action"))}'; fmt['B17']='int'
# 3. car recovery
sec(19,'3. CAR RECOVERY CHECK')
for i,h in enumerate(['Check','Pilots','Owed above deposit (Rs)','What it means']): D[f'{chr(65+i)}20']=h
st4='4. Owes >= Deposit - START RECOVERY'
rows=[('Should be in car recovery - NOT raised',f'={cnt(R("R"),q(st4))}',f'=-{sm(R("AV"),R("R"),q(st4),R("AV"),q("<0"))}','Owes >= deposit and no recovery case -> raise car recovery'),
      ('Critical but not in car recovery (P0)','=B11',f'=-{sm(R("AV"),R("Q"),"$A$11",R("AV"),q("<0"))}','P0 pilots with no recovery case'),
      ('Surpassed after last join, recovery never raised',f'={cnt(R("BI"),"1",R("BJ"),"0")}',f'=-{sm(R("AV"),R("BI"),"1",R("BJ"),"0",R("AV"),q("<0"))}','Crossed the deposit at least once since joining (3 weeks), no case yet'),
      ('In car recovery now',f'={cnt(R("BE"),q("Open"))}',f'=-{sm(R("AV"),R("BE"),q("Open"),R("AV"),q("<0"))}','Open recovery case'),
      ('Can cancel the car recovery (OFC)','=B13','','In recovery but OS is now below the deposit'),
      ('Car recovered / case closed this week',f'={cnt(R("BE"),q("Closed"))}','','Closed in this week')]
for j,(a,b,c_,d) in enumerate(rows):
    r=21+j; D[f'A{r}']=a; D[f'B{r}']=b; D[f'C{r}']=c_; D[f'D{r}']=d; fmt[f'B{r}']='int'; fmt[f'C{r}']='rs'
# 4. day by day
sec(28,'4. DAY BY DAY  (Mon .. Sun of the week shown)')
D['A29']='Day'
for i in range(7):
    c=chr(66+i); D[f'{c}29']=f'=IF(calc!$B$2="","{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][i]}",TEXT(calc!$B$2+{i},"ddd dd-mmm"))'
days=[('Live OS - total owed (Rs)','CO','owed','rs'),('Collection (Rs)','CV','sum','rs'),('Weekly OS collected (Rs)','DC','sum','rs'),
      ('Risk - Morning (pilots)','DJ','sum','int'),('Risk - That Day / EOD (pilots)','DQ','sum','int'),('Out of risk by end of day (pilots)','DJ','out','int'),
      ('Owes >= Deposit (pilots)','DX','sum','int'),('Calls attempted','EE','sum','int'),('Calls connected','EL','sum','int'),('Bad debt (Rs)','EZ','sum','rs')]
for j,(lab,c0,kind,t) in enumerate(days):
    r=30+j; D[f'A{r}']=lab
    for i in range(7):
        c=chr(66+i); cc=col(c0,i)
        if kind=='owed': e=f'-{sm(R(cc),R(cc),q("<0"))}'
        elif kind=='out': e=f'{cnt(R(cc),"1",R(col("DQ",i)),"0")}'
        else: e=sm(R(cc))
        D[f'{c}{r}']=f'=IF(OR(calc!$B$2="",calc!$B$2+{i}>TODAY()),"",{e})'; fmt[f'{c}{r}']=t
# 5. city view
sec(41,'5. CITY VIEW')
ch=['City','Pilots','Weekly OS to collect (Rs)','Collected (Rs)','Collection %','Action needed','NOT called today','P0 not in car recovery','Should be in recovery - not raised','Joined at 0 deposit']
for i,h in enumerate(ch): D[f'{chr(65+i)}42']=h
A='A43:A54'
D['A43']=f'=IFERROR(SORT(UNIQUE(FILTER(raw_v2!F4:F{N},{M}=1))),"")'
AF=lambda body: f'=ARRAYFORMULA(IF({A}="","",{body}))'
D['B43']=AF(f'COUNTIFS({R("F")},{A},{M},1)')
D['C43']=AF(f'-SUMIFS({R("AC")},{R("F")},{A},{M},1)')
D['D43']=AF(f'SUMIFS({R("AL")},{R("F")},{A},{M},1)')
D['E43']=AF('IFERROR(D43:D54/C43:C54,0)')
D['F43']=AF(f'SUMIFS(calc!$B$4:$B${N},{R("F")},{A})')
D['G43']=AF(f'SUMIFS(calc!$C$4:$C${N},{R("F")},{A})')
D['H43']=AF(f'COUNTIFS({R("F")},{A},{R("Q")},$A$11,{M},1)')
D['I43']=AF(f'COUNTIFS({R("F")},{A},{R("R")},"{st4}",{M},1)')
D['J43']=AF(f'COUNTIFS({R("F")},{A},{R("AA")},"Yes",{M},1)')
D['A55']='TOTAL'
for c in 'BCDFGHIJ': D[f'{c}55']=f'=SUM({c}43:{c}54)'
D['E55']='=IFERROR(D55/C55,0)'
for c,t in zip('BCDEFGHIJ',['int','rs','rs','pct','int','int','int','int','int']):
    fmt[f'{c}43:{c}55']=t
# 6. stage
sec(57,'6. STAGE TODAY  (pilots)')
D['A58']='Stage'; D['B58']='Pilots'
stages=['0. Not Active','1. Paid Up','2. Owes - not critical yet','3. Critical',st4,'5. In Car Recovery','6. Car Recovery Closed']
for j,s in enumerate(stages):
    r=59+j; D[f'A{r}']=s; D[f'B{r}']=f'={cnt(R("R"),f"$A{r}")}'; fmt[f'B{r}']='int'
# 7. agent
sec(67,'7. AGENT VIEW  (who has pilots to act on and has not called today)')
D['A68']=(f'=IFERROR(QUERY({{raw_v2!N4:N{N},calc!A4:D{N}}},"select Col1, sum(Col2), sum(Col3), sum(Col4), sum(Col5) where Col2 = 1 group by Col1 order by sum(Col4) desc '
          f'label Col1 \'Agent\', sum(Col2) \'Pilots\', sum(Col3) \'Action needed\', sum(Col4) \'NOT called today\', sum(Col5) \'P0 Critical\'",0),"No data")')

# ---------- Action_List ----------
AL={}
AL['A1']='Action List - pilots to act on (same filters as the Dashboard tab)'
AL['A2']='Action ▸'; AL['B2']='All'; AL['D2']='Called today ▸'; AL['E2']='All'
AL['G2']='=IF(raw_v2!B4="","","Data refreshed: "&raw_v2!B4)'
cols=[('Employee ID','C'),('Pilot Name','E'),('City','F'),('Product','G'),('Agent','N'),('Action To Take','Q'),('Stage Today','R'),
      ('Live OS Now (Rs)','AU'),('Deposit Now (Rs)','Y'),('Live OS + Deposit (Rs)','AV'),('Weekly OS Left (Rs)','AM'),
      ('Calls Today','CH'),('Calls This Week','CF'),('Last Disposition','CL'),('In Car Recovery','BE'),('Last Paid Date','AQ'),('Yesterday Remarks','CM')]
for i,(h,c) in enumerate(cols): AL[f'{col("A",i)}4']=h
arr='{'+','.join(f'raw_v2!{c}4:{c}{N}' for _,c in cols)+'}'
cond=(f'calc!B4:B{N}=1,IF($B$2="All",raw_v2!Q4:Q{N}<>"",raw_v2!Q4:Q{N}=$B$2),'
      f'IF($E$2="All",raw_v2!C4:C{N}<>"",IF($E$2="NOT called today",N(raw_v2!CH4:CH{N})=0,N(raw_v2!CH4:CH{N})>0))')
AL['A5']=f'=IFERROR(SORT(FILTER({arr},{cond}),6,TRUE,8,TRUE),"No pilots for these filters")'
json.dump({'calc':calc,'Dashboard':D,'Action_List':AL,'fmt':fmt,'actions':ACTIONS},open(sys.argv[1],'w'))
print(len(calc),len(D),len(AL))

# ---- 18-Nov fix: the automation resizes raw_v2 (deletes the extra rows), which shrank fixed ranges (#VALUE! / #REF!).
# Every range now goes through INDIRECT with the live row count in calc!N1, so raw_v2 and calc ranges always have the same size.
import re as _re
def _fix(f):
    if not f.startswith('='): return f
    f=_re.sub(r'raw_v2!\$?([A-Z]+)\$?4:\$?([A-Z]+)\$?'+str(N), lambda m: f'INDIRECT("raw_v2!{m.group(1)}4:{m.group(2)}"&calc!$N$1)', f)
    f=_re.sub(r'calc!\$?([A-Z]+)\$?4:\$?([A-Z]+)\$?'+str(N), lambda m: f'INDIRECT("calc!{m.group(1)}4:{m.group(2)}"&calc!$N$1)', f)
    f=_re.sub(r'(?<![!A-Z$])([A-D])4:\1(?:'+str(N)+')', lambda m: f'INDIRECT("calc!{m.group(1)}4:{m.group(1)}"&calc!$N$1)', f)   # own calc columns
    f=f.replace('raw_v2!B4','INDIRECT("raw_v2!B4")')
    assert str(N) not in f, f
    return f
calc['N1']='=ROWS(INDIRECT("raw_v2!A:A"))'
for _t in (calc, D, AL):
    for _k in list(_t): _t[_k]=_fix(_t[_k])
# ---- 18-Nov additions (written straight to the sheet): refresh time as date-time, city-wise unassigned agents, not-paid by OS bucket
_RI=lambda c: f'INDIRECT("raw_v2!{c}4:{c}"&calc!$N$1)'
_MI='INDIRECT("calc!A4:A"&calc!$N$1)'
D['A2']='=IF(INDIRECT("raw_v2!B4")="","No data yet - raw_v2 is empty","Data refreshed: "&IFERROR(TEXT(INDIRECT("raw_v2!B4"),"dd-mmm-yyyy hh:mm"),INDIRECT("raw_v2!B4"))&"     |     Week shown (Mon): "&IFERROR(TEXT(calc!B2,"dd-mmm-yyyy"),"")&"     |     Source: raw_v2 tab only")'
D['K42']='Agent not mapped (Unassigned)'
D['K43']=f'=ARRAYFORMULA(IF(A43:A54="","",COUNTIFS({_RI("F")},A43:A54,{_RI("N")},"Unassigned",{_MI},1)))'
D['K55']='=SUM(K43:K54)'
D['G58']='NOT PAID - by OS bucket (weekly OS to collect)'
for _i,_h in enumerate(['OS Bucket','Not paid (pilots)','Not paid OS (Rs)','All pilots in bucket']): D[f'{"GHIJ"[_i]}59']=_h
for _j,_b in enumerate(['0-500','500-1K','1-2K','2-3K','3-5K','5-10K','10-15K','15-20K','20-25K','25-30K','30K+']):
    _r=60+_j; D[f'G{_r}']=_b
    D[f'H{_r}']=f'=COUNTIFS({_RI("AO")},"Not Paid",{_RI("AE")},$G{_r},{_MI},1)'
    D[f'I{_r}']=f'=-SUMIFS({_RI("AC")},{_RI("AO")},"Not Paid",{_RI("AE")},$G{_r},{_MI},1)'
    D[f'J{_r}']=f'=COUNTIFS({_RI("AE")},$G{_r},{_MI},1)'
D['G71']='TOTAL'
for _c in 'HIJ': D[f'{_c}71']=f'=SUM({_c}60:{_c}70)'
json.dump({'calc':calc,'Dashboard':D,'Action_List':AL,'fmt':fmt,'actions':ACTIONS},open(sys.argv[1],'w'))
