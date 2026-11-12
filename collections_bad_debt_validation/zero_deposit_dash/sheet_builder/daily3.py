import json
S=113; N=21; C0=2; CL=C0+N  # C..W
def col(i):
    s='';i+=1
    while i: i,m=divmod(i-1,26); s=chr(65+m)+s
    return s
LAST=col(CL-1)  # W
B='raw!$A$2:$A,C$6,raw!$B$2:$B,$Y$4,raw!$DE$2:$DE,1'
Z0=',raw!$H$2:$H,"0 Deposit"'
def I(a,b): return f'INDEX(raw!${a}$2:${b},0,C$5)'
live=I("AH","AN"); coll=I("AO","AU"); wos=I("AV","BB"); sur=I("BC","BI"); cam=I("DH","DN"); ceod=I("DO","DU"); att=I("BX","CD"); con=I("CE","CK")
J=f'raw!$A$2:$A,C$6,raw!$B$2:$B,$Y$4,raw!$DE$2:$DE,1,raw!$V$2:$V,C$7,raw!$T$2:$T,"<>Existing"'
def wtd(e=""): return f'=IFERROR(SUM(MAP(SEQUENCE(C$5),LAMBDA(i,SUMIFS(INDEX(raw!$AV$2:$BB,0,i),{B},raw!$F$2:$F,1{e}))))/-SUMIFS(raw!$L$2:$L,{B},raw!$F$2:$F,1{e}),0)'
CLOSED='IF(raw!$J$1="Car Recovery Close Date",COUNTIFS({B},raw!$J$2:$J,C$7{e}),"after 8:15 AM")'
M=[
("S","A. PILOTS & JOINS","b"),
("act","Active pilots","Has live OS that day",f'=COUNTIFS({B},{live},">-1E+15")',"n"),
("zact","   of which 0 Deposit","Deposit at allocation = 0",f'=COUNTIFS({B},{live},">-1E+15"{Z0})',"n"),
("join","New joins + rejoins","Car given that day",f'=COUNTIFS({J})',"n"),
("zjoin","   of which 0 Deposit","Car given without deposit",f'=COUNTIFS({J}{Z0})',"n"),
("S","B. COLLECTION (Weekly OS = India Collections dash)","b"),
("wos","Weekly OS (Rs)","Monday OS of dash pilots",f'=-SUMIFS(raw!$L$2:$L,{B},raw!$F$2:$F,1)',"n"),
("wosc","Weekly OS collected that day (Rs)","Payment counted against Weekly OS",f'=SUMIFS({wos},{B},raw!$F$2:$F,1)',"n"),
("wosp","Weekly OS collected % (week to date)","Cumulative from Monday",wtd(),"p"),
("zwosp","   0 Deposit pilots - Weekly OS collected %","Lower than above = 0 deposit pays slower",wtd(Z0),"p"),
("tc","Total collection that day (Rs)","All payments",f'=SUMIFS({coll},{B})',"n"),
("lc","Collected on Live OS (Rs)","Only after Weekly OS is fully paid",'=MAX(0,C{tc}-C{wosc})',"n"),
("lo","Live OS owed at day end (Rs)","What pilots still owe",f'=-SUMIFS({live},{B},{live},"<0")',"n"),
("lp","Live OS collection %","Collected on Live OS / (collected + owed)",'=IFERROR(C{lc}/(C{lc}+C{lo}),0)',"p"),
("S","C. RISK & CALLING (Critical = MasterTab rule)","b"),
("cam","Critical - Morning (fixed list)","Start of day OS vs deposit, by product",f'=COUNTIFS({B},{cam},1)',"n"),
("ceod","Critical - Day end","Still critical after today's payment",f'=COUNTIFS({B},{ceod},1)',"n"),
("mo","Moved out of Critical %","(Morning - Day end) / Morning",'=IFERROR((C{cam}-C{ceod})/C{cam},0)',"p"),
("cnc","Critical NOT called (ACT)","Critical in morning, 0 attempts that day",f'=COUNTIFS({B},{cam},1,{att},0)',"a"),
("cal","Pilots called","At least 1 attempt",f'=COUNTIFS({B},{att},">0")',"n"),
("cp","Connect %","Connected / called",f'=IFERROR(COUNTIFS({B},{con},">0")/C{{cal}},0)',"p"),
("S","D. LIVE OS >= DEPOSIT -> CAR RECOVERY (position at day end)","b"),
("sur","Live OS >= Deposit (surpassed)","Deposit fully used",f'=COUNTIFS({B},{sur},1)',"n"),
("surr","   with car recovery raised","Case started on or before this day",f'=COUNTIFS({B},{sur},1,raw!$Z$2:$Z,"<="&C$7)',"n"),
("surn","   NO car recovery yet (ACT)","Loss keeps growing every day",'=C{sur}-C{surr}',"a"),
("surp","Recovery raised % of surpassed","Should be close to 100%",'=IFERROR(C{surr}/C{sur},0)',"p"),
("ro","Open car recovery cases (week)","Case open at week end",f'=COUNTIFS({B},raw!$Y$2:$Y,"Open")',"n"),
("S","E. WHAT HAPPENED THAT DAY (non-funnel - old days never change)","b"),
("ns","Newly surpassed deposit","Was below deposit the day before",f'=COUNTIFS({B},raw!$DY$2:$DY,C$7)',"n"),
("rr","Car recovery raised","New recovery cases that day",f'=COUNTIFS({B},raw!$Z$2:$Z,C$7)',"n"),
("rc","Car recovered / case closed","Recovery case closed that day",'='+CLOSED.format(B=B,e=""),"n"),
("gap","Newly surpassed minus recovery raised (ACT)","Positive = recovery backlog growing",'=C{ns}-C{rr}',"a"),
("S","F. 0 DEPOSIT CUT (deposit at allocation = 0)","z"),
("z_lo","Live OS owed at day end (Rs)","",f'=-SUMIFS({live},{B},{live},"<0"{Z0})',"n"),
("z_tc","Collection that day (Rs)","",f'=SUMIFS({coll},{B}{Z0})',"n"),
("z_ceod","Critical - Day end","",f'=COUNTIFS({B},{ceod},1{Z0})',"n"),
("z_cnc","Critical NOT called (ACT)","",f'=COUNTIFS({B},{cam},1,{att},0{Z0})',"a"),
("z_sur","Live OS >= Deposit (surpassed)","No deposit = any OS is unsecured",f'=COUNTIFS({B},{sur},1{Z0})',"n"),
("z_surn","   NO car recovery yet (ACT)","",f'=C{{z_sur}}-COUNTIFS({B},{sur},1,raw!$Z$2:$Z,"<="&C$7{Z0})',"a"),
("z_ns","Newly surpassed that day","Started owing",f'=COUNTIFS({B},raw!$DY$2:$DY,C$7{Z0})',"n"),
("z_rr","Car recovery raised that day","",f'=COUNTIFS({B},raw!$Z$2:$Z,C$7{Z0})',"n"),
("z_rc","Car recovered / case closed that day","",'='+CLOSED.format(B=B,e=Z0),"n"),
("z_ro","Open car recovery cases (week)","",f'=COUNTIFS({B},raw!$Y$2:$Y,"Open"{Z0})',"n"),
("S","G. JOIN FUNNEL - column = join date; status of those joiners TILL TODAY (old days can change)","g"),
("f_j","Joined (new + rejoin)","",f'=COUNTIFS({J})',"n"),
("f_s","-> Live OS crossed deposit","Any day after join",f'=COUNTIFS({J},raw!$DV$2:$DV,1)',"n"),
("f_sp","   % of joined","",'=IFERROR(C{f_s}/C{f_j},0)',"p"),
("f_r","-> Car recovery raised","",f'=COUNTIFS({J},raw!$DW$2:$DW,1)',"n"),
("f_c","-> Car recovered (case closed)","",f'=COUNTIFS({J},raw!$DX$2:$DX,1)',"n"),
("f_g","Crossed deposit, NO recovery (ACT)","",f'=COUNTIFS({J},raw!$DV$2:$DV,1,raw!$DW$2:$DW,0)',"a"),
("S","H. JOIN FUNNEL - 0 DEPOSIT JOINS","z"),
("g_j","0 Deposit joined","",f'=COUNTIFS({J}{Z0})',"n"),
("g_s","-> Started owing (crossed deposit)","",f'=COUNTIFS({J},raw!$DV$2:$DV,1{Z0})',"n"),
("g_sp","   % of joined","",'=IFERROR(C{g_s}/C{g_j},0)',"p"),
("g_r","-> Car recovery raised","",f'=COUNTIFS({J},raw!$DW$2:$DW,1{Z0})',"n"),
("g_c","-> Car recovered (case closed)","",f'=COUNTIFS({J},raw!$DX$2:$DX,1{Z0})',"n"),
("g_g","Started owing, NO recovery (ACT)","",f'=COUNTIFS({J},raw!$DV$2:$DV,1,raw!$DW$2:$DW,0{Z0})',"a"),
]
TOP=12  # insights rows 4..10 (idx3..9); helper rows 11,12? -> day# row 5? keep fixed rows 5,6,7 for C$5/C$6/C$7 references
# Layout: 1 title,2 filters,3 note,4 blank(helper Y4),5 day#,6 week,7 dates header(hidden? no) -> put insights ABOVE? need rows 5-7 fixed. Put insights in rows 8-14, table header row 16.
# To keep C$5..C$7 refs: rows 5,6 hidden helpers, row 7 = date header visible. Insights go rows 8.. ; then table starts.
rowno={}; r=16
for m in M:
    if m[0]!="S": rowno[m[0]]=r
    r+=1
last=r-1
L='$Y$5'  # latest data day
def at(k,off=0): return f'XLOOKUP({L}{"-7" if off else ""},$C$7:${LAST}$7,$C${rowno[k]}:${LAST}${rowno[k]},0)'
fmtn=lambda x:f'TEXT({x},"#,##0")'; fmtp=lambda x:f'TEXT({x},"0.0%")'
ins=[
 f'="•  "&TEXT({L},"ddd dd-mmm")&": "&{fmtn(at("act"))}&" active pilots ("&TEXT({at("act")}-{at("act",1)},"+#,##0;-#,##0")&" vs same day last week). "&{fmtn(at("join"))}&" new joins, of which "&{fmtn(at("zjoin"))}&" with 0 deposit."',
 f'="•  Weekly OS collected "&{fmtp(at("wosp"))}&" week-to-date (last week same day "&{fmtp(at("wosp",1))}&"). 0 deposit pilots: "&{fmtp(at("zwosp"))}&IF({at("zwosp")}<{at("wosp")}," -> they pay slower than others."," -> in line with others.")',
 f'="•  Critical: "&{fmtn(at("cam"))}&" in the morning -> "&{fmtn(at("ceod"))}&" at day end ("&{fmtp(at("mo"))}&" moved out). "&{fmtn(at("cnc"))}&" critical pilots got NO call."',
 f'="•  "&{fmtn(at("sur"))}&" pilots have Live OS >= deposit; recovery raised for only "&{fmtp(at("surp"))}&" -> "&{fmtn(at("surn"))}&" need car recovery now."',
 f'="•  That day: "&{fmtn(at("ns"))}&" newly crossed deposit vs "&{fmtn(at("rr"))}&" recoveries raised"&IF({at("ns")}>{at("rr")}," -> backlog GROWING."," -> backlog reducing.")',
 f'="•  0 deposit: "&{fmtn(at("zact"))}&" active, Rs "&{fmtn(at("z_lo"))}&" owed, "&{fmtn(at("z_sur"))}&" surpassed, "&{fmtn(at("z_surn"))}&" without car recovery."',
]
grid=[[None]]*0
g=[["2. DAILY TREND - last 21 days"],None,
   ['="Each column = one day (Monday in red = new week, Weekly OS resets). Red rows = action needed. Use filters in row 2. Data updated: "&TEXT(raw!CL2,"dd-mmm hh:mm")'],
   [None]*24+['=IF($B$2="All","*",$B$2)'],
   ["","(day #)"]+[f'=WEEKDAY({col(C0+i)}7,2)' for i in range(N)]+[None,f'=IFERROR(MAXIFS($C$7:${LAST}$7,$C${rowno["act"]}:${LAST}${rowno["act"]},">0"),TODAY()-1)'],
   ["","(week)"]+[f'={col(C0+i)}7-WEEKDAY({col(C0+i)}7,3)' for i in range(N)],
   ["Metric","What it means",'=TODAY()-20']+[f'={col(C0+i-1)}7+1' for i in range(1,N)],
   ["KEY INSIGHTS - latest day (auto, updates with every refresh)"]]
for s in ins: g.append([s])
g.append([]) # row 15 blank
for m in M:
    if m[0]=="S": g.append([m[1]]); continue
    k,lab,dfn,f,fm=m
    f=f.replace("{{","{").replace("}}","}").format(**rowno)
    g.append([lab,dfn,f])
# row 2 untouched -> write rows separately: rows1, 3..last
def rg(r1,r2,c1,c2): return {"sheetId":S,"startRowIndex":r1,"endRowIndex":r2,"startColumnIndex":c1,"endColumnIndex":c2}
NAV={"red":0.122,"green":0.22,"blue":0.392}; LB={"red":0.863,"green":0.902,"blue":0.945}; AMB={"red":1,"green":0.93,"blue":0.8}; GR={"red":0.886,"green":0.937,"blue":0.855}
PK={"red":0.988,"green":0.894,"blue":0.894}; RED={"red":0.753,"green":0,"blue":0}; WH={"red":1,"green":1,"blue":1}; GY={"red":0.5,"green":0.5,"blue":0.5}; YL={"red":1,"green":0.976,"blue":0.89}
def rc(r,f,fl): return {"repeatCell":{"range":r,"cell":{"userEnteredFormat":f},"fields":fl}}
pre=[rc(rg(2,90,0,26),{},"userEnteredFormat"),{"updateCells":{"range":rg(2,90,0,26),"fields":"userEnteredValue"}},
     {"unmergeCells":{"range":rg(0,90,0,26)}},
     {"updateSheetProperties":{"properties":{"sheetId":S,"gridProperties":{"frozenRowCount":7,"frozenColumnCount":2}},"fields":"gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}}]
post=[{"copyPaste":{"source":rg(15,last,2,3),"destination":rg(15,last,3,CL),"pasteType":"PASTE_FORMULA"}},
 rc(rg(0,1,0,CL),{"textFormat":{"bold":True,"fontSize":14,"foregroundColorStyle":{"rgbColor":WH}},"backgroundColorStyle":{"rgbColor":NAV},"verticalAlignment":"MIDDLE"},"userEnteredFormat.textFormat,userEnteredFormat.backgroundColorStyle,userEnteredFormat.verticalAlignment"),
 rc(rg(2,3,0,CL),{"textFormat":{"italic":True,"foregroundColorStyle":{"rgbColor":GY}}},"userEnteredFormat.textFormat"),
 rc(rg(6,7,0,CL),{"textFormat":{"bold":True,"foregroundColorStyle":{"rgbColor":WH}},"backgroundColorStyle":{"rgbColor":NAV},"horizontalAlignment":"CENTER","verticalAlignment":"MIDDLE","wrapStrategy":"WRAP","numberFormat":{"type":"DATE","pattern":"ddd\ndd-mmm"}},"userEnteredFormat"),
 rc(rg(6,7,0,2),{"horizontalAlignment":"LEFT"},"userEnteredFormat.horizontalAlignment"),
 rc(rg(7,8,0,CL),{"textFormat":{"bold":True,"foregroundColorStyle":{"rgbColor":NAV}},"backgroundColorStyle":{"rgbColor":YL}},"userEnteredFormat.textFormat,userEnteredFormat.backgroundColorStyle"),
 rc(rg(8,14,0,CL),{"backgroundColorStyle":{"rgbColor":YL},"textFormat":{"fontSize":10}},"userEnteredFormat.backgroundColorStyle,userEnteredFormat.textFormat"),
 rc(rg(15,last,0,1),{"textFormat":{"bold":True}},"userEnteredFormat.textFormat"),
 rc(rg(15,last,1,2),{"textFormat":{"italic":True,"fontSize":9,"foregroundColorStyle":{"rgbColor":GY}},"wrapStrategy":"CLIP"},"userEnteredFormat.textFormat,userEnteredFormat.wrapStrategy"),
 rc(rg(15,last,2,CL),{"numberFormat":{"type":"NUMBER","pattern":"#,##0;-#,##0;-"},"horizontalAlignment":"RIGHT"},"userEnteredFormat.numberFormat,userEnteredFormat.horizontalAlignment"),
]
for i in range(8,14): post.append({"mergeCells":{"range":rg(i,i+1,0,CL),"mergeType":"MERGE_ALL"}})
rr=16
for m in M:
    if m[0]=="S":
        bg={"b":LB,"z":AMB,"g":GR}[m[2]]
        post.append(rc(rg(rr-1,rr,0,CL),{"textFormat":{"bold":True,"foregroundColorStyle":{"rgbColor":NAV}},"backgroundColorStyle":{"rgbColor":bg}},"userEnteredFormat.textFormat,userEnteredFormat.backgroundColorStyle"))
        post.append({"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"ROWS","startIndex":rr-1,"endIndex":rr},"properties":{"pixelSize":26},"fields":"pixelSize"}})
    else:
        if m[4]=="p": post.append(rc(rg(rr-1,rr,2,CL),{"numberFormat":{"type":"NUMBER","pattern":"0.0%"}},"userEnteredFormat.numberFormat"))
        if m[4]=="a": post.append(rc(rg(rr-1,rr,0,CL),{"backgroundColorStyle":{"rgbColor":PK},"textFormat":{"bold":True,"foregroundColorStyle":{"rgbColor":RED}}},"userEnteredFormat.backgroundColorStyle,userEnteredFormat.textFormat"))
    rr+=1
# light bottom border per data row for readability
b={"style":"SOLID","width":1,"colorStyle":{"rgbColor":{"red":0.85,"green":0.85,"blue":0.85}}}
post.append({"updateBorders":{"range":rg(15,last,0,CL),"innerHorizontal":b,"bottom":b}})
post.append({"updateBorders":{"range":rg(6,last,1,2),"right":{"style":"SOLID","width":1,"colorStyle":{"rgbColor":{"red":0.6,"green":0.6,"blue":0.6}}}}})
post+=[{"addConditionalFormatRule":{"rule":{"ranges":[rg(6,7,2,CL)],"booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":"=C$5=1"}]},"format":{"backgroundColorStyle":{"rgbColor":RED}}}},"index":0}},
 {"addConditionalFormatRule":{"rule":{"ranges":[rg(15,last,2,CL)],"booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":"=C$7=$Y$5"}]},"format":{"textFormat":{"bold":True}}}},"index":1}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"ROWS","startIndex":4,"endIndex":6},"properties":{"hiddenByUser":True},"fields":"hiddenByUser"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"ROWS","startIndex":6,"endIndex":7},"properties":{"pixelSize":38},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"ROWS","startIndex":0,"endIndex":1},"properties":{"pixelSize":34},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":0,"endIndex":1},"properties":{"pixelSize":300},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":1,"endIndex":2},"properties":{"pixelSize":230},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":2,"endIndex":CL},"properties":{"pixelSize":78},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":CL,"endIndex":26},"properties":{"hiddenByUser":True},"fields":"hiddenByUser"}}]
g1=[g[0]]; g3=g[2:]
json.dump({"pre":pre,"g1":g1,"g3":g3,"post":post},open('daily3.json','w'),separators=(',',':'))
print(last,rowno)
