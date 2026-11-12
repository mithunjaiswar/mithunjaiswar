from common import *
S=113
rq=[{"addSheet":{"properties":{"title":"2_Daily_Trend","sheetId":S,"index":1,"gridProperties":{"rowCount":80,"columnCount":20,"frozenRowCount":7,"frozenColumnCount":2},"tabColorStyle":{"rgbColor":rgb("#2E75B6")}}}}]
rq+=title(S,"2. DAILY TREND - last 14 days (pick a City in B2 or All)","=\"Each column = one day. Monday columns start a new week (Weekly OS resets). Live OS counts only after Weekly OS is fully paid. Data updated: \"&TEXT(raw_pilot_week!CL2,\"dd-mmm hh:mm\")")
rq+=filter_bar(S)
# helper rows: idx4 = day# , idx5 = week start ; idx6 = header dates
rq.append(cells(S,3,19,[['=IF($B$2="All","*",$B$2)']]))  # T4 city crit
d=[f'=WEEKDAY({chr(67+i)}7,2)' for i in range(14)]
w=[f'={chr(67+i)}7-WEEKDAY({chr(67+i)}7,3)' for i in range(14)]
h=['=TODAY()-13']+[f'={chr(66+i)}7+1' for i in range(1,14)]
rq.append(cells(S,4,0,[["","(day #)"]+d,["","(week)"]+w,["Metric","Definition"]+h]))
rq.append(hide_rows(S,4,6))
c='C'
B=f'r_A,C$6,r_B,$T$4,r_DE,1'
def I(n): return f'INDEX({n},0,C$5)'
M=[("PILOTS",None,None,None),
 ("Active pilots","Has live OS that day",f'=COUNTIFS({B},{I("d_live")},">-1E+15")',"#,##0"),
 ("0-Deposit active pilots","Deposit at allocation = 0",f'=COUNTIFS({B},{I("d_live")},">-1E+15",r_H,"0 Deposit")',"#,##0"),
 ("New joins + rejoins that day","Allocation date = this day",f'=COUNTIFS({B},r_V,C$7,r_T,"<>Existing")',"#,##0"),
 ("   of which 0 Deposit","",f'=COUNTIFS({B},r_V,C$7,r_T,"<>Existing",r_H,"0 Deposit")',"#,##0"),
 ("WEEKLY OS (Monday OS - same as India Collections dash)",None,None,None),
 ("Weekly OS (Rs)","Monday OS of dash pilots",f'=-SUMIFS(r_L,{B},r_F,1)',"#,##0"),
 ("Weekly OS collected that day (Rs)","Payment that went to Weekly OS",f'=SUMIFS({I("d_wos")},{B},r_F,1)',"#,##0"),
 ("Weekly OS collected % (week to date)","Cumulative from Monday",f'=IFERROR(SUM(MAP(SEQUENCE(C$5),LAMBDA(i,SUMIFS(INDEX(d_wos,0,i),{B},r_F,1))))/C14,0)',"0.0%"),
 ("LIVE OS (new rent this week)",None,None,None),
 ("Total collection that day (Rs)","All payments",f'=SUMIFS({I("d_coll")},{B})',"#,##0"),
 ("Collected on Live OS (Rs)","Payment after Weekly OS fully paid",f'=MAX(0,C18-SUMIFS({I("d_wos")},{B}))',"#,##0"),
 ("Live OS owed at day end (Rs)","Amount pilots still owe",f'=-SUMIFS({I("d_live")},{B},{I("d_live")},"<0")',"#,##0"),
 ("Live OS collection %","Collected on live OS / (collected + owed)",f'=IFERROR(C19/(C19+C20),0)',"0.0%"),
 ("RISK",None,None,None),
 ("Critical - Morning","Owes >= 1 day rent before payment",f'=COUNTIFS({B},{I("d_cam")},1)',"#,##0"),
 ("Critical - Day end","Still owes >= 1 day rent",f'=COUNTIFS({B},{I("d_ceod")},1)',"#,##0"),
 ("Moved out of Critical %","(Morning - Day end) / Morning",f'=IFERROR((C23-C24)/C23,0)',"0.0%"),
 ("Owes >= Deposit (surpassed)","Live OS owed >= current deposit",f'=COUNTIFS({B},{I("d_sur")},1)',"#,##0"),
 ("   of which 0 Deposit","",f'=COUNTIFS({B},{I("d_sur")},1,r_H,"0 Deposit")',"#,##0"),
 ("CALLING",None,None,None),
 ("Critical (morning) NOT called","No attempt that day",f'=COUNTIFS({B},{I("d_cam")},1,{I("d_att")},0)',"#,##0"),
 ("Pilots called","At least 1 attempt",f'=COUNTIFS({B},{I("d_att")},">0")',"#,##0"),
 ("Pilots connected","At least 1 connect",f'=COUNTIFS({B},{I("d_conn")},">0")',"#,##0"),
 ("Connect %","Connected / called",f'=IFERROR(C31/C30,0)',"0.0%"),
 ("CAR RECOVERY (all cases, not funnel)",None,None,None),
 ("Car recovery started that day","Case created that day",f'=COUNTIFS({B},r_Z,C$7)',"#,##0"),
 ("Open car recovery (week)","Case open in the week",f'=COUNTIFS({B},r_Y,"Open")',"#,##0"),
]
rows=[]; r=8
for lab,dfn,f,pat in M:
    rows.append([lab,dfn or "",f] if f else [lab,""])
rq.append(cells(S,7,0,rows))
for k,(lab,dfn,f,pat) in enumerate(M):
    ri=7+k
    if f is None: rq.append(style(S,ri,ri+1,0,16,bg=LBLUE,bold=True,color=NAVY)); continue
    rq.append(pastec(S,ri,ri+1,2,16)); rq.append(numfmt(S,ri,ri+1,2,16,pat))
# sanity print row numbers
for k,(lab,_,f,_) in enumerate(M): print(8+k,lab)
rq.append(style(S,6,7,0,16,bg=NAVY,bold=True,color="#FFFFFF",align="CENTER"))
rq.append(numfmt(S,6,7,2,16,"ddd dd-mmm","DATE"))
rq.append(style(S,7,7+len(M),1,2,italic=True,color="#7F7F7F",wrap="WRAP"))
rq.append(style(S,7,7+len(M),0,1,bold=True))
rq.append({"addConditionalFormatRule":{"rule":{"ranges":[grid(S,6,7,2,16)],"booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":"=C$5=1"}]},"format":{"backgroundColorStyle":{"rgbColor":rgb(RED)}}}},"index":0}})
for rr_ in (24,26,27,29):  # heat on risk rows (row numbers)
    rq.append(cf_scale(S,rr_-1,rr_,2,16))
rq+=[width(S,0,1,300),width(S,1,2,230),width(S,2,16,95),border(S,6,7+len(M),0,16),hide_cols(S,19,20)]
json.dump(rq,open('daily.json','w')); print(len(rq),len(json.dumps(rq)))
