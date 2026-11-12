import json
from common import *
S=113; N=21; C0=2; CL=C0+N   # C..W, X = total
def col(i):
    s='';i+=1
    while i: i,m=divmod(i-1,26); s=chr(65+m)+s
    return s
TOT=col(CL)  # X
B='raw!$A$2:$A,C$6,raw!$B$2:$B,$Z$4,raw!$DE$2:$DE,1'
Z0=',raw!$H$2:$H,"0 Deposit"'
def I(a,b): return f'INDEX(raw!${a}$2:${b},0,C$5)'
live=I("AH","AN"); coll=I("AO","AU"); wos=I("AV","BB"); sur=I("BC","BI"); cam=I("DH","DN"); ceod=I("DO","DU"); att=I("BX","CD"); con=I("CE","CK")
J=f'raw!$A$2:$A,C$6,raw!$B$2:$B,$Z$4,raw!$DE$2:$DE,1,raw!$V$2:$V,C$7,raw!$T$2:$T,"<>Existing"'
def wtd(extra=""): return f'=IFERROR(SUM(MAP(SEQUENCE(C$5),LAMBDA(i,SUMIFS(INDEX(raw!$AV$2:$BB,0,i),{B},raw!$F$2:$F,1{extra}))))/-SUMIFS(raw!$L$2:$L,{B},raw!$F$2:$F,1{extra}),0)'
# (key, label, definition, formula(with {r:key} refs), fmt, total?)
M=[
("S","PILOTS"),
("act","Active pilots","Has live OS that day",f'=COUNTIFS({B},{live},">-1E+15")',"n",0),
("join","New joins + rejoins","Car given that day",f'=COUNTIFS({J})',"n",1),
("S","WEEKLY OS (Monday OS - same as India Collections dash)"),
("wos","Weekly OS (Rs)","Monday OS of dash pilots",f'=-SUMIFS(raw!$L$2:$L,{B},raw!$F$2:$F,1)',"n",0),
("wosc","Weekly OS collected that day (Rs)","Payment that went to Weekly OS",f'=SUMIFS({wos},{B},raw!$F$2:$F,1)',"n",1),
("wosp","Weekly OS collected % (week to date)","Cumulative from Monday",wtd(),"p",0),
("S","LIVE OS (new rent this week)"),
("tc","Total collection that day (Rs)","All payments",f'=SUMIFS({coll},{B})',"n",1),
("lc","Collected on Live OS (Rs)","Payment after Weekly OS fully paid",f'=MAX(0,C{{tc}}-SUMIFS({wos},{B}))',"n",1),
("lo","Live OS owed at day end (Rs)","Amount pilots still owe",f'=-SUMIFS({live},{B},{live},"<0")',"n",0),
("lp","Live OS collection %","Collected on live OS / (collected + owed)",'=IFERROR(C{lc}/(C{lc}+C{lo}),0)',"p",0),
("S","RISK (Critical = MasterTab rule)"),
("cam","Critical - Morning (fixed)","Start of day OS vs deposit, by product",f'=COUNTIFS({B},{cam},1)',"n",0),
("ceod","Critical - Day end","Still critical after today's payment",f'=COUNTIFS({B},{ceod},1)',"n",0),
("mo","Moved out of Critical %","(Morning - Day end) / Morning",'=IFERROR((C{cam}-C{ceod})/C{cam},0)',"p",0),
("cnc","Critical (morning) NOT called","No attempt that day",f'=COUNTIFS({B},{cam},1,{att},0)',"n",0),
("S","CALLING"),
("cal","Pilots called","At least 1 attempt",f'=COUNTIFS({B},{att},">0")',"n",0),
("con","Pilots connected","At least 1 connect",f'=COUNTIFS({B},{con},">0")',"n",0),
("cp","Connect %","Connected / called",'=IFERROR(C{con}/C{cal},0)',"p",0),
("S","DEPOSIT SURPASSED -> CAR RECOVERY (all pilots, not funnel)"),
("sur","Owes >= deposit (surpassed)","Live OS owed >= current deposit",f'=COUNTIFS({B},{sur},1)',"n",0),
("surr","   with car recovery raised","Recovery case started on or before this day",f'=COUNTIFS({B},{sur},1,raw!$Z$2:$Z,"<="&C$7)',"n",0),
("surn","   NO car recovery yet (ACT)","Surpassed but no case = loss growing",'=C{sur}-C{surr}',"n",0),
("surp","Recovery raised % of surpassed","Target: close to 100%",'=IFERROR(C{surr}/C{sur},0)',"p",0),
("rs","Car recovery started that day","New cases that day",f'=COUNTIFS({B},raw!$Z$2:$Z,C$7)',"n",1),
("ro","Open car recovery (week)","Case open at week end",f'=COUNTIFS({B},raw!$Y$2:$Y,"Open")',"n",0),
("rc","Car recovery closed (week)","Car back / settled in the week",f'=COUNTIFS({B},raw!$Y$2:$Y,"Closed")',"n",0),
("S","0 DEPOSIT CUT (deposit at allocation = 0)"),
("z_act","0-Dep active pilots","",f'=COUNTIFS({B},{live},">-1E+15"{Z0})',"n",0),
("z_join","0-Dep new joins + rejoins","Car given with 0 deposit",f'=COUNTIFS({J}{Z0})',"n",1),
("z_lo","0-Dep live OS owed (Rs)","",f'=-SUMIFS({live},{B},{live},"<0"{Z0})',"n",0),
("z_tc","0-Dep collection that day (Rs)","",f'=SUMIFS({coll},{B}{Z0})',"n",1),
("z_wosp","0-Dep Weekly OS collected % (WTD)","Compare with all pilots above",wtd(Z0),"p",0),
("z_ceod","0-Dep critical - day end","",f'=COUNTIFS({B},{ceod},1{Z0})',"n",0),
("z_cnc","0-Dep critical NOT called","",f'=COUNTIFS({B},{cam},1,{att},0{Z0})',"n",0),
("z_sur","0-Dep surpassed (owes anything)","No deposit = any OS is unsecured",f'=COUNTIFS({B},{sur},1{Z0})',"n",0),
("z_surr","   with car recovery raised","",f'=COUNTIFS({B},{sur},1,raw!$Z$2:$Z,"<="&C$7{Z0})',"n",0),
("z_surn","   NO car recovery yet (ACT)","",'=C{z_sur}-C{z_surr}',"n",0),
("z_rs","0-Dep car recovery started that day","",f'=COUNTIFS({B},raw!$Z$2:$Z,C$7{Z0})',"n",1),
("z_ro","0-Dep open car recovery (week)","",f'=COUNTIFS({B},raw!$Y$2:$Y,"Open"{Z0})',"n",0),
("z_rc","0-Dep car recovery closed (week)","",f'=COUNTIFS({B},raw!$Y$2:$Y,"Closed"{Z0})',"n",0),
("S","JOIN FUNNEL - ALL PILOTS (column = join date; what happened to them after joining, till today)"),
("f_j","Joined (new + rejoin)","Car given that day",f'=COUNTIFS({J})',"n",1),
("f_s","-> Deposit surpassed after join","Owed >= deposit any day after join",f'=COUNTIFS({J},raw!$DV$2:$DV,1)',"n",1),
("f_sp","   % surpassed","",'=IFERROR(C{f_s}/C{f_j},0)',"p",0),
("f_r","-> Car recovery raised","",f'=COUNTIFS({J},raw!$DW$2:$DW,1)',"n",1),
("f_c","-> Car recovered (case closed)","",f'=COUNTIFS({J},raw!$DX$2:$DX,1)',"n",1),
("f_g","Surpassed but NO recovery (ACT)","Loss risk - raise recovery",f'=COUNTIFS({J},raw!$DV$2:$DV,1,raw!$DW$2:$DW,0)',"n",1),
("S","JOIN FUNNEL - 0 DEPOSIT JOINS"),
("g_j","0-Dep joined (new + rejoin)","",f'=COUNTIFS({J}{Z0})',"n",1),
("g_s","-> Deposit surpassed after join","For 0 deposit = any OS",f'=COUNTIFS({J},raw!$DV$2:$DV,1{Z0})',"n",1),
("g_sp","   % surpassed","",'=IFERROR(C{g_s}/C{g_j},0)',"p",0),
("g_r","-> Car recovery raised","",f'=COUNTIFS({J},raw!$DW$2:$DW,1{Z0})',"n",1),
("g_c","-> Car recovered (case closed)","",f'=COUNTIFS({J},raw!$DX$2:$DX,1{Z0})',"n",1),
("g_g","Surpassed but NO recovery (ACT)","",f'=COUNTIFS({J},raw!$DV$2:$DV,1,raw!$DW$2:$DW,0{Z0})',"n",1),
]
rowno={}; r=8
for m in M:
    if m[0]!="S": rowno[m[0]]=r
    r+=1
last=r-1
hdr_dates=['=TODAY()-20']+[f'={col(C0+i-1)}7+1' for i in range(1,N)]
grid=[["2. DAILY TREND - last 21 days (pick a City in B2 or All)"],
      ["City ▸","All","Product ▸","All","SD Bucket ▸","All","Payment Habit ▸","All","ELC / Non ELC ▸","All"],
      ['="Each column = one day. Monday (red) starts a new week - Weekly OS resets. Live OS counts only after Weekly OS is fully paid. Data updated: "&TEXT(raw!CL2,"dd-mmm hh:mm")'],
      [None]*25+['=IF($B$2="All","*",$B$2)'],
      ["","(day #)"]+[f'=WEEKDAY({col(C0+i)}7,2)' for i in range(N)],
      ["","(week)"]+[f'={col(C0+i)}7-WEEKDAY({col(C0+i)}7,3)' for i in range(N)],
      ["Metric","Definition"]+hdr_dates+["21-day total"]]
sec=[];pct=[];tot=[]
for m in M:
    if m[0]=="S": grid.append([m[1]]); sec.append(len(grid)); continue
    k,lab,dfn,f,fm,t=m
    f=f.replace("{{","{").replace("}}","}")
    f=f.format(**rowno)
    rowv=[lab,dfn,f]+[None]*(N-1)
    if t: rowv.append(f'=SUM(C{len(grid)+1}:{col(CL-1)}{len(grid)+1})'); tot.append(len(grid)+1)
    grid.append(rowv)
    if fm=="p": pct.append(len(grid))
# requests
pre=[{"updateSheetProperties":{"properties":{"sheetId":S,"gridProperties":{"rowCount":90,"columnCount":27,"frozenRowCount":7,"frozenColumnCount":2}},"fields":"gridProperties.rowCount,gridProperties.columnCount,gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}},
     {"unmergeCells":{"range":grid_(S:=S) if False else {"sheetId":S}}} ] if False else []
def rg(r1,r2,c1,c2): return {"sheetId":S,"startRowIndex":r1,"endRowIndex":r2,"startColumnIndex":c1,"endColumnIndex":c2}
pre=[{"appendDimension":{"sheetId":S,"dimension":"COLUMNS","length":7}},
     {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":19,"endIndex":20},"properties":{"hiddenByUser":False},"fields":"hiddenByUser"}},
     {"updateCells":{"range":rg(0,90,0,27),"fields":"userEnteredValue,userEnteredFormat"}},
     {"deleteConditionalFormatRule":{"sheetId":S,"index":0}},{"deleteConditionalFormatRule":{"sheetId":S,"index":0}}]
post=[{"copyPaste":{"source":rg(8,last,2,3),"destination":rg(8,last,3,CL),"pasteType":"PASTE_FORMULA"}}]
NAV={"red":0.122,"green":0.22,"blue":0.392}; LB={"red":0.863,"green":0.902,"blue":0.945}; PK={"red":0.988,"green":0.894,"blue":0.894}
def rc(r,f,fl): return {"repeatCell":{"range":r,"cell":{"userEnteredFormat":f},"fields":fl}}
post+=[rc(rg(0,1,0,CL+1),{"textFormat":{"bold":True,"fontSize":14,"foregroundColorStyle":{"rgbColor":{"red":1,"green":1,"blue":1}}},"backgroundColorStyle":{"rgbColor":NAV}},"userEnteredFormat.textFormat,userEnteredFormat.backgroundColorStyle"),
      rc(rg(1,2,0,10),{"textFormat":{"bold":True},"backgroundColorStyle":{"rgbColor":{"red":1,"green":0.949,"blue":0.8}},"horizontalAlignment":"CENTER"},"userEnteredFormat.textFormat,userEnteredFormat.backgroundColorStyle,userEnteredFormat.horizontalAlignment"),
      rc(rg(2,3,0,1),{"textFormat":{"italic":True}},"userEnteredFormat.textFormat"),
      rc(rg(6,7,0,CL+1),{"textFormat":{"bold":True,"foregroundColorStyle":{"rgbColor":{"red":1,"green":1,"blue":1}}},"backgroundColorStyle":{"rgbColor":NAV},"horizontalAlignment":"CENTER","numberFormat":{"type":"DATE","pattern":"ddd dd-mmm"}},"userEnteredFormat"),
      rc(rg(7,last,0,1),{"textFormat":{"bold":True}},"userEnteredFormat.textFormat"),
      rc(rg(7,last,1,2),{"textFormat":{"italic":True,"foregroundColorStyle":{"rgbColor":{"red":0.5,"green":0.5,"blue":0.5}}},"wrapStrategy":"CLIP"},"userEnteredFormat.textFormat,userEnteredFormat.wrapStrategy"),
      rc(rg(7,last,2,CL+1),{"numberFormat":{"type":"NUMBER","pattern":"#,##0"}},"userEnteredFormat.numberFormat"),
      rc(rg(7,last,CL,CL+1),{"textFormat":{"bold":True},"backgroundColorStyle":{"rgbColor":{"red":0.949,"green":0.949,"blue":0.949}}},"userEnteredFormat.textFormat,userEnteredFormat.backgroundColorStyle")]
for s in sec: post.append(rc(rg(s-1,s,0,CL+1),{"textFormat":{"bold":True,"foregroundColorStyle":{"rgbColor":NAV}},"backgroundColorStyle":{"rgbColor":LB}},"userEnteredFormat.textFormat,userEnteredFormat.backgroundColorStyle"))
for p in pct: post.append(rc(rg(p-1,p,2,CL),{"numberFormat":{"type":"NUMBER","pattern":"0.0%"}},"userEnteredFormat.numberFormat"))
act=[rowno[k] for k in ("surn","z_surn","f_g","g_g","cnc","z_cnc")]
for a in act: post.append(rc(rg(a-1,a,0,CL+1),{"backgroundColorStyle":{"rgbColor":PK},"textFormat":{"bold":True,"foregroundColorStyle":{"rgbColor":{"red":0.753,"green":0,"blue":0}}}},"userEnteredFormat.backgroundColorStyle,userEnteredFormat.textFormat"))
zs=[s for s in sec if "0 DEPOSIT" in grid[s-1][0]]
post+=[{"addConditionalFormatRule":{"rule":{"ranges":[rg(6,7,2,CL)],"booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":"=C$5=1"}]},"format":{"backgroundColorStyle":{"rgbColor":{"red":0.753,"green":0,"blue":0}}}}},"index":0}},
       {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"ROWS","startIndex":4,"endIndex":6},"properties":{"hiddenByUser":True},"fields":"hiddenByUser"}},
       {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":0,"endIndex":1},"properties":{"pixelSize":290},"fields":"pixelSize"}},
       {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":1,"endIndex":2},"properties":{"pixelSize":200},"fields":"pixelSize"}},
       {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":2,"endIndex":CL+1},"properties":{"pixelSize":82},"fields":"pixelSize"}},
       {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":25,"endIndex":26},"properties":{"hiddenByUser":True},"fields":"hiddenByUser"}}]
dv=[{"setDataValidation":{"range":rg(1,2,c,c+1),"rule":{"condition":{"type":"ONE_OF_RANGE","values":[{"userEnteredValue":src}]},"strict":True,"showCustomUi":True}}} for c,src in [(1,"=lists!$B$2:$B$30"),(3,"=lists!$A$2:$A$30"),(5,"=lists!$C$2:$C$30"),(7,"=lists!$D$2:$D$30"),(9,"=lists!$E$2:$E$5")]]
post+=dv
json.dump({"pre":pre,"grid":grid,"post":post},open('daily2.json','w'),separators=(',',':'))
print(last,rowno,len(json.dumps(pre)),len(json.dumps(grid,separators=(',',':'))),len(json.dumps(post,separators=(',',':'))))
