from common import *
S=111
rq=[{"addSheet":{"properties":{"title":"1_Eye_View","sheetId":S,"index":0,"gridProperties":{"rowCount":150,"columnCount":26,"frozenRowCount":3},"tabColorStyle":{"rgbColor":rgb(RED)}}}}]
rq+=title(S,"1. BIRD'S EYE VIEW - TODAY  |  Zero & Low Deposit Monitoring","=\"Week \"&TEXT($Z$1,\"dd-mmm\")&\" | Day \"&$Z$2&\" of 7 | Data updated: \"&TEXT(raw_pilot_week!CL2,\"dd-mmm hh:mm\")&\" | Weekly OS = India Collections dash (exception list removed)\"")
rq+=filter_bar(S)
rq.append(cells(S,0,25,[["=TODAY()-WEEKDAY(TODAY(),3)"],["=WEEKDAY(TODAY(),2)"],["=Z1-7"],['=IF($B$2="All","*",$B$2)']]))
def b(w,city="$Z$4"): return f'r_A,{w},r_B,{city},r_DD,1'
T=[("Active pilots today",'COUNTIFS({b},r_CP,1)',"#,##0"),
 ("0-Deposit pilots active",'COUNTIFS({b},r_CP,1,r_H,"0 Deposit")',"#,##0"),
 ("Weekly OS collected % (week to date)",'IFERROR(SUMIFS(r_O,{b},r_F,1)/-SUMIFS(r_L,{b},r_F,1),0)',"0.0%"),
 ("Live OS owed now (Rs)",'SUMIFS(r_CQ,{b})',"#,##0"),
 ("Critical - Morning (fixed)",'COUNTIFS({b},r_CS,1)',"#,##0"),
 ("Critical - Now / Day end",'COUNTIFS({b},r_CT,1)',"#,##0"),
 ("Moved out of Critical %",None,"0.0%"),
 ("ACT NOW: owes >= deposit, no car recovery",'COUNTIFS({b},r_DC,"4.*")',"#,##0"),
 ("Money at risk above deposit (Rs)",'SUMIFS(r_CZ,{b})',"#,##0"),
 ("Critical (morning) NOT called today",'COUNTIFS({b},r_CS,1,r_CU,0)',"#,##0"),
 ("Open car recovery cases",'COUNTIFS({b},r_Y,"Open")',"#,##0"),
 ("New joins / rejoins this week with 0 Deposit",'COUNTIFS({b},r_T,"<>Existing",r_H,"0 Deposit")',"#,##0")]
for blk in range(2):
    r=4+blk*4; labs=[];vals=[];prevs=[]
    for i in range(6):
        lab,f,pat=T[blk*6+i]; labs.append(lab)
        if f: vals.append("="+f.format(b=b("$Z$1"))); prevs.append("="+f.format(b=b("$Z$3")))
        else: vals.append('=IFERROR((E6-F6)/E6,0)'); prevs.append('=IFERROR((E7-F7)/E7,0)')
        rq.append(numfmt(S,r+1,r+2,i,i+1,pat)); rq.append(numfmt(S,r+2,r+3,i,i+1,'"Last week end: "'+pat))
    rq.append(cells(S,r,0,[labs,vals,prevs]))
    rq.append(style(S,r,r+1,0,6,bg=NAVY,bold=True,color="#FFFFFF",align="CENTER",wrap="WRAP"))
    rq.append(style(S,r+1,r+2,0,6,bold=True,size=18,align="CENTER",color=NAVY))
    rq.append(style(S,r+2,r+3,0,6,italic=True,color="#7F7F7F",align="CENTER"))
    rq.append(border(S,r,r+3,0,6)); rq.append(height(S,r,r+1,42))
rq.append(style(S,9,10,1,4,bg=PINK,color=RED))  # tiles 8,9,10 values (row idx 9, cols 1..3)
# Stage table
r0=12
rq+=section(S,r0,"WHERE ARE PILOTS TODAY? - one stage per pilot (current week, latest day)",8)
stages=[("1. Paid Up","No action - keep weekly habit"),("2. Owes < 1 day rent","Reminder call / WhatsApp today"),("3. Critical - owes >= 1 day rent","Agent call today, follow up till paid (connect + PTP)"),("4. Owes >= Deposit - START RECOVERY","Deposit used up - start car recovery within 24 hours"),("5. In Car Recovery","Close case in 48 hours (car back or full payment)"),("6. Car Recovery Closed","Adjust deposit, settle balance OS"),("0. Not Active","No live OS today - check car / deallocation")]
hdr=["Stage","Pilots","% of pilots","Owed now (Rs)","0-Deposit pilots","0-Deposit owed (Rs)","Money at risk above deposit (Rs)","What to do"]
x=r0+3  # first stage row number
B=b("$Z$1")
first=[stages[0][0],f'=COUNTIFS({B},r_DC,$A{x})',f'=IFERROR(B{x}/B${x+7},0)',f'=SUMIFS(r_CQ,{B},r_DC,$A{x})',f'=COUNTIFS({B},r_DC,$A{x},r_H,"0 Deposit")',f'=SUMIFS(r_CQ,{B},r_DC,$A{x},r_H,"0 Deposit")',f'=SUMIFS(r_CZ,{B},r_DC,$A{x})',stages[0][1]]
rq.append(cells(S,r0+1,0,[hdr,first]))
rq.append(paste(S,x-1,1,7,x-1+7))
rq.append(cells(S,x,0,[[s] for s,_ in stages[1:]])); rq.append(cells(S,x,7,[[a] for _,a in stages[1:]]))
rq.append(cells(S,x+6,0,[["Total"]+[f'=SUM({c}{x}:{c}{x+6})' for c in "BCDEFG"]]))
rq.append(style(S,r0+1,r0+2,0,8,bg=GREY,bold=True,wrap="WRAP",align="CENTER"))
rq.append(style(S,x+6,x+7,0,8,bold=True,bg=GREY))
rq.append(numfmt(S,x-1,x+7,1,7,"#,##0")); rq.append(numfmt(S,x-1,x+7,2,3,"0.0%"))
rq.append(style(S,x+1,x+3,0,8,bg=PINK)); rq.append(style(S,x+2,x+3,0,1,bold=True,color=RED))
rq.append(border(S,r0+1,x+7,0,8))
# City table
c0=x+8
rq+=section(S,c0,"CITY VIEW - TODAY (darker red = needs attention)",12)
ch=["City","Active pilots","0-Dep active","WOS collected % (WTD)","Live OS owed (Rs)","Critical - Morning","Critical - Now","Out of Critical %","Critical not called","ACT NOW (>= deposit, no recovery)","Money at risk (Rs)","Open car recovery"]
y=c0+3
cb=b("$Z$1",f'IF($A{y}="Total",$Z$4,$A{y})')
first=["Bangalore",f'=COUNTIFS({cb},r_CP,1)',f'=COUNTIFS({cb},r_CP,1,r_H,"0 Deposit")',f'=IFERROR(SUMIFS(r_O,{cb},r_F,1)/-SUMIFS(r_L,{cb},r_F,1),0)',f'=SUMIFS(r_CQ,{cb})',f'=COUNTIFS({cb},r_CS,1)',f'=COUNTIFS({cb},r_CT,1)',f'=IFERROR((F{y}-G{y})/F{y},0)',f'=COUNTIFS({cb},r_CS,1,r_CU,0)',f'=COUNTIFS({cb},r_DC,"4.*")',f'=SUMIFS(r_CZ,{cb})',f'=COUNTIFS({cb},r_Y,"Open")']
rq.append(cells(S,c0+1,0,[ch,first]))
rq.append(paste(S,y-1,1,12,y-1+8))
rq.append(cells(S,y,0,[[c] for c in ["Chennai","Delhi NCR","Hyderabad","Kolkata","Mumbai","Pune","Total"]]))
ce=y-1+8
rq.append(style(S,c0+1,c0+2,0,12,bg=GREY,bold=True,wrap="WRAP",align="CENTER"))
rq.append(style(S,ce-1,ce,0,12,bold=True,bg=GREY))
rq.append(numfmt(S,y-1,ce,1,12,"#,##0")); rq.append(numfmt(S,y-1,ce,3,4,"0.0%")); rq.append(numfmt(S,y-1,ce,7,8,"0.0%"))
for cc in (8,9,10): rq.append(cf_scale(S,y-1,ce-1,cc,cc+1))
rq.append(border(S,c0+1,ce,0,12))
# Action list
a0=ce+1
rq+=section(S,a0,"ACTION LIST - top 100 pilots to act on NOW (stage 4 first, then critical; biggest money at risk first)",13)
ah=["Employee ID","City","Product","SD Bucket","Current Deposit","Owed now (Rs)","Money at risk (Rs)","Stage","Days since join","Calls today","Connects this week","Payment Habit","Agent (weekly)"]
af=('=LET(ok,(r_A=$Z$1)*(r_DD=1)*((LEFT(r_DC,1)="4")+(LEFT(r_DC,1)="3"))*IF($B$2="All",1,r_B=$B$2),'
    't,FILTER({r_D,r_B,r_CN,r_H,r_I,r_CQ,r_CZ,r_DC,r_DB,r_CU,r_CW,r_Q},ok=1),IFERROR(ARRAY_CONSTRAIN(SORT(t,8,FALSE,7,FALSE,6,FALSE),100,12),"No pilot in Critical / Owes >= Deposit stage"))')
ar=a0+3
agent=f'=ARRAYFORMULA(IF(A{ar}:A{ar+99}="","",IFERROR(VLOOKUP(TEXT($Z$1,"yyyy-mm-dd")&"|"&A{ar}:A{ar+99},{{TO_TEXT(agent_weekly!A3:A)&"|"&agent_weekly!B3:B,agent_weekly!C3:C}},2,0),"-")))'
rq.append(cells(S,a0+1,0,[ah,[af]+[None]*11+[agent]]))
rq.append(style(S,a0+1,a0+2,0,13,bg=GREY,bold=True,wrap="WRAP",align="CENTER"))
rq.append(numfmt(S,ar-1,ar+99,4,7,"#,##0"))
rq.append({"addConditionalFormatRule":{"rule":{"ranges":[grid(S,ar-1,ar+99,0,13)],"booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":f'=LEFT($H{ar},1)="4"'}]},"format":{"backgroundColorStyle":{"rgbColor":rgb(PINK)}}}},"index":0}})
rq+=[width(S,0,7,175),width(S,7,8,330),width(S,8,13,110),width(S,0,1,200),hide_cols(S,25,26)]
json.dump(rq,open('eye.json','w')); print(len(rq),len(json.dumps(rq)),r0,x,c0,y,ce,a0,ar)
