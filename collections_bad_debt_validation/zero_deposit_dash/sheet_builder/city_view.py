# City_View tab: WBR-style city x last-4-weeks comparison of Daily_Trend metrics (values at latest day of each week)
import json
CITIES=["All","Bangalore","Chennai","Delhi NCR","Hyderabad","Kolkata","Mumbai","Pune"]
def Bc(r): return f'raw!$A$2:$A,C$3,raw!$B$2:$B,$A{r},raw!$EX$2:$EX,1'
I=lambda a,b: f'INDEX(raw!${a}$2:${b},0,C$4)'
M=[
("Active pilots", lambda r: f'=COUNTIFS({Bc(r)},{I("AH","AN")},">-1E+15")',"n"),
("Live OS (Rs)", lambda r: f'=-SUMIFS({I("AH","AN")},{Bc(r)},{I("AH","AN")},"<0")',"n"),
("Weekly OS (Rs)", lambda r: f'=-SUMIFS(raw!$L$2:$L,{Bc(r)},raw!$F$2:$F,1)',"n"),
("Weekly OS collected % (week to date)", lambda r: f'=IFERROR(SUMIFS(raw!$O$2:$O,{Bc(r)},raw!$F$2:$F,1)/-SUMIFS(raw!$L$2:$L,{Bc(r)},raw!$F$2:$F,1),0)',"p"),
("Critical - day end", lambda r: f'=COUNTIFS({Bc(r)},{I("DO","DU")},1)',"n"),
("Critical - NOT called", lambda r: f'=COUNTIFS({Bc(r)},{I("DH","DN")},1,{I("BX","CD")},0)',"n"),
("Pending car recovery (open at day end)", lambda r: f'=COUNTIFS({Bc(r)},raw!$Z$2:$Z,"<="&C$5)-COUNTIFS({Bc(r)},raw!$Z$2:$Z,"<="&C$5,raw!$J$2:$J,"<="&C$5)',"n"),
("Needed car recovery (Live OS >= deposit, no recovery)", lambda r: f'=COUNTIFS({Bc(r)},{I("BC","BI")},1)-COUNTIFS({Bc(r)},{I("BC","BI")},1,raw!$Z$2:$Z,"<="&C$5)',"n"),
("Active bad debt amount (Rs)", lambda r: f'=SUMIFS({I("EN","ET")},{Bc(r)},{I("EG","EM")},1)',"n"),
("Non-active bad debt amount (Rs)", lambda r: f'=SUMIFS({I("EN","ET")},{Bc(r)},{I("EG","EM")},2)',"n"),
]
rows=[["","Zero & Low Deposit - City comparison (latest day of each week)","","","","",""],
      ["","Filters (Product / SD / Habit / ELC) follow Daily_Trend B2:B5. Bad debt fills from SQL refresh.","","","","",""],
      ["","Week start","=F3-21","=F3-14","=F3-7","=TODAY()-WEEKDAY(TODAY(),3)",""],
      ["","Day # used","=IF(C3=$F$3,lists!$R$10,7)","=IF(D3=$F$3,lists!$R$10,7)","=IF(E3=$F$3,lists!$R$10,7)","=lists!$R$10",""],
      ["","Date","=C3+C4-1","=D3+D4-1","=E3+E4-1","=F3+F4-1",""],
      ["","","","","","",""]]
blocks=[]; fmt=[]
r=7
for name,f,kind in M:
    rows.append(["",name,"=C$5","=D$5","=E$5","=F$5","WoW"]); blocks.append(r); fmt.append((r,kind)); r+=1
    for c in CITIES:
        crit='*' if c=="All" else c
        row=[crit,c]
        base=f(r)
        for col in "CDEF": row.append(base.replace("C$3",f"{col}$3").replace("C$4",f"{col}$4").replace("C$5",f"{col}$5"))
        row.append(f'=IFERROR((F{r}-E{r})/ABS(E{r}),"-")')
        rows.append(row); r+=1
    rows.append([""]*7); r+=1
json.dump({"rows":rows,"blocks":blocks,"fmt":fmt,"last":r},open('city_view.json','w'))
print(len(rows),blocks)
