from common import *
S=115
rq=[{"addSheet":{"properties":{"title":"4_Pilot_Journey","sheetId":S,"index":3,"gridProperties":{"rowCount":80,"columnCount":26,"frozenRowCount":3},"tabColorStyle":{"rgbColor":rgb("#548235")}}}}]
rq+=title(S,"4. PILOT JOURNEY - what must happen after allocation (step by step)","=\"Current week \"&TEXT($Z$1,\"dd-mmm\")&\" vs last week. Each step = one check. If 'This week' is higher than 'Last week' on a risk step, act on that step first.\"")
rq+=filter_bar(S)
rq.append(cells(S,0,25,[["=TODAY()-WEEKDAY(TODAY(),3)"],["=WEEKDAY(TODAY(),2)"],["=Z1-7"],['=IF($B$2="All","*",$B$2)']]))
rq+=section(S,4,"A. PLAYBOOK - 7 steps after a car is allocated",10)
hdr=["Step","When","What must happen","Check (pilots)","This week","Last week","Change","Rs this week","Rs last week","Who acts"]
def b(w): return f'r_A,{w},r_B,$Z$4,r_DG,1'
ST=[("1. Allocation","Before handover","Collect security deposit. 0 deposit only with approval","New joins / rejoins with 0 deposit",
     'COUNTIFS({b},r_T,"<>Existing",r_H,"0 Deposit")', None,"City / onboarding team"),
    ("2. First rent","Day 1-2","First daily rent paid","Joined this week, 2+ days, paid nothing yet",
     'COUNTIFS({b},r_T,"<>Existing",r_DB,">=2",r_N,0)', None,"Onboarding + agent"),
    ("3. Daily habit","Every day","Owe less than 1 day rent","Owes < 1 day rent",
     'COUNTIFS({b},r_DC,"2.*")','SUMIFS(r_CQ,{b},r_DC,"2.*")',"Reminder (WhatsApp / IVR)"),
    ("4. Critical","Same day","Agent calls, gets payment or PTP","Critical now (owes >= 1 day rent)",
     'COUNTIFS({b},r_CT,1)','SUMIFS(r_CQ,{b},r_CT,1)',"Collections agent"),
    ("4b. Critical not called","Same day","No critical pilot left uncalled","Critical (morning) with 0 calls today",
     'COUNTIFS({b},r_CS,1,r_CU,0)',None,"Team lead"),
    ("5. Deposit used up","Within 24 hours","Start car recovery - every extra day is loss","Owes >= deposit, NO car recovery",
     'COUNTIFS({b},r_DC,"4.*")','SUMIFS(r_CZ,{b},r_DC,"4.*")',"Recovery team"),
    ("6. Car recovery","Close in 48 hours","Car back or full payment","Open car recovery, started 2+ days ago",
     'COUNTIFS({b},r_Y,"Open",r_Z,"<="&(TODAY()-2))','SUMIFS(r_CQ,{b},r_Y,"Open")',"Recovery team"),
    ("7. Closed","After recovery","Adjust deposit, settle OS, decide rejoin","Car recovery closed in week",
     'COUNTIFS({b},r_Y,"Closed")','SUMIFS(r_CQ,{b},r_Y,"Closed")',"Finance + city")]
rows=[hdr]
for k,(s,wn,what,chk,f,rs,who) in enumerate(ST):
    r=7+k
    rows.append([s,wn,what,chk,"="+f.format(b=b("$Z$1")),"="+f.format(b=b("$Z$3")),f'=IF(E{r}>F{r},"▲ worse",IF(E{r}<F{r},"▼ better","="))',
                 ("="+rs.format(b=b("$Z$1"))) if rs else "-",("="+rs.format(b=b("$Z$3"))) if rs else "-",who])
rq.append(cells(S,5,0,rows))
e=6+len(ST)
rq+=[style(S,5,6,0,10,bg=GREY,bold=True,align="CENTER",wrap="WRAP"),numfmt(S,6,e,4,6,"#,##0"),numfmt(S,6,e,7,9,"#,##0"),
     style(S,6,e,0,1,bold=True),style(S,6,e,2,4,wrap="WRAP"),style(S,6,e,4,5,bold=True,size=12,align="CENTER"),border(S,5,e,0,10),
     style(S,6+5,6+6,0,10,bg=PINK)]
rq.append({"addConditionalFormatRule":{"rule":{"ranges":[grid(S,6,e,6,7)],"booleanRule":{"condition":{"type":"TEXT_CONTAINS","values":[{"userEnteredValue":"worse"}]},"format":{"textFormat":{"foregroundColorStyle":{"rgbColor":rgb(RED)},"bold":True}}}},"index":0}})
rq.append({"addConditionalFormatRule":{"rule":{"ranges":[grid(S,6,e,6,7)],"booleanRule":{"condition":{"type":"TEXT_CONTAINS","values":[{"userEnteredValue":"better"}]},"format":{"textFormat":{"foregroundColorStyle":{"rgbColor":rgb("#38761D")},"bold":True}}}},"index":0}})
# B cohort
c0=e+1
rq+=section(S,c0,"B. JOIN COHORTS - pilots who joined / rejoined in each week: where are they NOW?",13)
ch=["Join week","Joined","of which 0 Deposit","In data this week","Paid up","Owes < 1 day","Critical","Owes >= deposit (no recovery)","In car recovery","Recovery closed","Not active","Money at risk (Rs)","0-Dep money at risk (Rs)"]
y=c0+3
nb=f'r_A,$Z$1,r_B,$Z$4,r_DG,1,r_DA,$A{y}'
jb=f'r_A,$A{y},r_B,$Z$4,r_DG,1,r_T,"<>Existing"'
first=["=$Z$1",f'=COUNTIFS({jb})',f'=COUNTIFS({jb},r_H,"0 Deposit")',f'=COUNTIFS({nb})']+[f'=COUNTIFS({nb},r_DC,"{n}.*")' for n in "1234560"]+[f'=SUMIFS(r_CZ,{nb})',f'=SUMIFS(r_CZ,{nb},r_H,"0 Deposit")']
rq.append(cells(S,c0+1,0,[ch,first])); rq.append(paste(S,y-1,1,13,y+3))
rq.append(cells(S,y,0,[[f"=A{y}-7"],[f"=A{y+1}-7"],[f"=A{y+2}-7"]]))
e2=y+3
rq+=[style(S,c0+1,c0+2,0,13,bg=GREY,bold=True,align="CENTER",wrap="WRAP"),numfmt(S,y-1,e2,0,1,'"Week "dd-mmm',"DATE"),numfmt(S,y-1,e2,1,13,"#,##0"),
     border(S,c0+1,e2,0,13),style(S,y-1,e2,7,8,bg=PINK,bold=True),cf_scale(S,y-1,e2,11,13)]
# C days since join
d0=e2+1
rq+=section(S,d0,"C. WHEN DOES RISK START? - by days since join (current week)",8)
dh=["Days since join","Pilots","% critical now","% owes >= deposit","Money at risk (Rs)","0-Dep pilots","0-Dep % owes >= deposit","0-Dep money at risk (Rs)"]
bins=[("0-7",0,7),("8-14",8,14),("15-30",15,30),("31-60",31,60),("61-180",61,180),("180+",181,99999)]
rq.append(cells(S,d0+1,0,[dh]))
z=d0+3
db=f'r_A,$Z$1,r_B,$Z$4,r_DG,1,r_DB,">="&$K{z},r_DB,"<="&$L{z}'
first=[bins[0][0],f'=COUNTIFS({db})',f'=IFERROR(COUNTIFS({db},r_CT,1)/B{z},0)',f'=IFERROR(COUNTIFS({db},r_CR,1)/B{z},0)',f'=SUMIFS(r_CZ,{db})',
       f'=COUNTIFS({db},r_H,"0 Deposit")',f'=IFERROR(COUNTIFS({db},r_H,"0 Deposit",r_CR,1)/F{z},0)',f'=SUMIFS(r_CZ,{db},r_H,"0 Deposit")']
rq.append(cells(S,d0+2,0,[first])); rq.append(paste(S,z-1,1,8,z-1+len(bins)))
rq.append(cells(S,z,0,[[x[0]] for x in bins[1:]]))
rq.append(cells(S,z-1,10,[[lo,hi] for _,lo,hi in bins]))
e3=z-1+len(bins)
rq+=[style(S,d0+1,d0+2,0,8,bg=GREY,bold=True,align="CENTER",wrap="WRAP"),numfmt(S,z-1,e3,1,8,"#,##0"),numfmt(S,z-1,e3,2,4,"0.0%"),numfmt(S,z-1,e3,6,7,"0.0%"),
     border(S,d0+1,e3,0,8),cf_scale(S,z-1,e3,3,4),cf_scale(S,z-1,e3,6,7),hide_cols(S,10,12),hide_cols(S,25,26)]
rq+=[width(S,0,1,190),width(S,1,2,120),width(S,2,3,300),width(S,3,4,280),width(S,4,13,110)]
json.dump(rq,open('journey.json','w')); print(len(rq),len(json.dumps(rq)),e,c0,y,e2,d0,z,e3)
