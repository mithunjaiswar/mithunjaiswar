# Daily_Trend v6 (manager review): rows from 10, dates in row 9, day# row 7, week row 8, city wildcard $Z$1
import json
S=113; N=21; R0=10
B='raw!$A$2:$A,C$8,raw!$B$2:$B,$Z$1,raw!$DE$2:$DE,1'
def I(a,b): return f'INDEX(raw!${a}$2:${b},0,C$7)'
live=I("AH","AN"); coll=I("AO","AU"); wos=I("AV","BB"); sur=I("BC","BI"); cam=I("DH","DN"); ceod=I("DO","DU"); att=I("BX","CD"); con=I("CE","CK")
J=f'{B},raw!$V$2:$V,C$9,raw!$T$2:$T,"<>Existing"'
Z=lambda c,op,v: f'raw!${c}$2:${c},"{op}"&{v}'
def pend(lo,hi):  # open at day end, raised between C9-hi .. C9-lo days ago
    a=[]
    if hi is not None: a.append(Z("Z",">=",f"(C$9-{hi})"))
    a.append(Z("Z","<=",f"(C$9-{lo})"))
    s=",".join(a)
    return f'=COUNTIFS({B},{s})-COUNTIFS({B},{s},{Z("J","<=","C$9")})'
# SUMPRODUCT masks (bad debt)
M_='(raw!$A$2:$A=C$8)*(raw!$DE$2:$DE=1)*IF($B$1="All",1,raw!$B$2:$B=$B$1)'
DEP='IF(ISNUMBER(raw!$I$2:$I),IF(raw!$I$2:$I>0,raw!$I$2:$I,0),0)'
LEFT='(IFERROR(raw!$EA$2:$EA*1,0)>0)*(IFERROR(raw!$EA$2:$EA*1,0)<C$7)*NOT(ISNUMBER('+live+'))'
EC='IFERROR(raw!$EC$2:$EC*1,0)'
MA=f'{M_}*ISNUMBER({live})*(IFERROR({sur}*1,0)=1)'
MJ=f'{M_}*{LEFT}*(raw!$T$2:$T<>"Existing")*(IFERROR(raw!$V$2:$V*1,0)>=C$8)*({EC}>0)'
MW=f'{M_}*{LEFT}*(raw!$T$2:$T="Existing")*(raw!$F$2:$F&""="1")*(IFERROR(raw!$L$2:$L*1,0)<0)*({EC}>0)'
OWA=f'LET(o,-IFERROR({live}*1,0)-{DEP},IF(o>0,o,0))'
RZ='ISNUMBER(raw!$Z$2:$Z)*(raw!$Z$2:$Z<=C$9)'
RJ='ISNUMBER(raw!$J$2:$J)*(raw!$J$2:$J<=C$9)'
CL=f'IFERROR({coll}*1,0)'
def SP(x): return f'=ARRAYFORMULA(SUMPRODUCT({x}))'
def bd(k,name,mask,amt,dfn):
    return [(k,name,dfn,SP(mask),"n"),
            (k+"a","   Bad debt amount (Rs)","OS above deposit",SP(f'{mask}*{amt}'),"n"),
            (k+"r","   car recovery raised","Case started on or before this day",SP(f'{mask}*{RZ}'),"n"),
            (k+"c","   car recovered (case closed)","Car taken back on or before this day",SP(f'{mask}*{RJ}'),"n"),
            (k+"m","   collected from them that day (Rs)","Money recovered from these pilots that day",SP(f'{mask}*{CL}'),"n")]
DB=['OS Recovery / Promise','Unclear','Busy / Hang up / No response','App / Payment / Hisaab issue','Car recovery','Other','No disposition']
def dsp(b): return f'=COUNTIFS(dispo!$A$2:$A,C$9,dispo!$D$2:$D,1,dispo!$F$2:$F,1,dispo!$E$2:$E,$Z$1,dispo!$C$2:$C,"{b}")'
W=lambda rng,extra="": f'SUM(MAP(SEQUENCE(C$7),LAMBDA(i,SUMIFS(INDEX(raw!${rng[0]}$2:${rng[1]},0,i),{B}{extra}))))'
M=[
("S","Pilots & Joins"),
("act","Active pilots","Has live OS that day",f'=COUNTIFS({B},{live},">-1E+15")',"n"),
("zact","   of which 0 Deposit","Deposit at allocation = 0",f'=COUNTIFS({B},{live},">-1E+15",raw!$H$2:$H,"0 Deposit")',"n"),
("join","New joins + rejoins","Car given that day",f'=COUNTIFS({J})',"n"),
("zjoin","   of which 0 Deposit","Car given without deposit",f'=COUNTIFS({J},raw!$H$2:$H,"0 Deposit")',"n"),
("S","Rent vs Paid"),
("rg","Rent generated that day (Rs)","Daily rent of all active pilots",f'=SUMIFS(raw!$W$2:$W,{B},{live},">-1E+15")',"n"),
("tc","Paid towards rent that day (Rs)","Only money paid AFTER the pilot's Weekly OS is cleared (payment - Weekly OS part)",f'=MAX(0,SUMIFS({coll},{B})-SUMIFS({wos},{B}))',"n"),
("rgp","   Rent paid % (that day, max 100%)","Paid towards rent / rent generated",'=IFERROR(MIN(1,C{tc}/C{rg}),0)',"p"),
("rgw","Rent generated - week to date (Rs)","Monday to this day",f'=SUM(MAP(SEQUENCE(C$7),LAMBDA(i,SUMIFS(raw!$W$2:$W,{B},INDEX(raw!$AH$2:$AN,0,i),">-1E+15"))))',"n"),
("tcw","Paid towards rent - week to date (Rs)","Monday to this day, after Weekly OS is cleared",f'=MAX(0,{W(("AO","AU"))}-{W(("AV","BB"))})',"n"),
("rgwp","   Rent paid % (week to date, max 100%)","Below 100% = pilots paying less than rent",'=IFERROR(MIN(1,C{tcw}/C{rgw}),0)',"p"),
("S","Collection"),
("wos","Weekly OS (Rs)","Monday opening OS (only negative), same as India Collections dash",f'=-SUMIFS(raw!$L$2:$L,{B},raw!$F$2:$F,1)',"n"),
("nos","New OS this week (Rs)","Rent charged from Monday to this day",'=C{rgw}',"n"),
("tos","Total OS (Rs)","Weekly OS + New OS this week",'=C{wos}+C{nos}',"n"),
("tcol","Collected - week to date (Rs)","All payments Monday to this day",f'={W(("AO","AU"))}',"n"),
("tcp","   Collected % of Total OS","Collected / Total OS",'=IFERROR(C{tcol}/C{tos},0)',"p"),
("wosc","Weekly OS collected that day (Rs)","Payment counted against Weekly OS",f'=SUMIFS({wos},{B},raw!$F$2:$F,1)',"n"),
("wosp","Weekly OS collected % (week to date)","Cumulative from Monday",f'=IFERROR({W(("AV","BB"),",raw!$F$2:$F,1")}/C{{wos}},0)',"p"),
("lo","Pending OS at day end (Rs)","What pilots still owe",f'=-SUMIFS({live},{B},{live},"<0")',"n"),
("S","Critical & Calling"),
("cam","Critical - Morning (fixed list)","MasterTab rule OR Live OS >= Deposit, start of day",f'=COUNTIFS({B},{cam},1)',"n"),
("ceod","Critical - Day end","Still critical after today's payment",f'=COUNTIFS({B},{ceod},1)',"n"),
("mo","Moved out of Critical %","(Morning - Day end) / Morning",'=IFERROR((C{cam}-C{ceod})/C{cam},0)',"p"),
("cat","Critical - Attempted","Morning critical with 1+ call attempt",f'=COUNTIFS({B},{cam},1,{att},">0")',"n"),
("ccn","   of which Connected","Pilot picked the call",f'=COUNTIFS({B},{cam},1,{con},">0")',"n"),
]+[("d"+str(i),"   disposition: "+b,"Last call disposition of the day (critical pilots called)",dsp(b),"n") for i,b in enumerate(DB)]+[
("cnc","Critical - NOT called (ACT)","Morning critical, 0 attempts that day",f'=COUNTIFS({B},{cam},1,{att},0)',"a"),
("cal","All pilots called","At least 1 attempt",f'=COUNTIFS({B},{att},">0")',"n"),
("cp","Connect % (all called)","Connected / called",f'=IFERROR(COUNTIFS({B},{con},">0")/C{{cal}},0)',"p"),
("S","Car Recovery"),
("rex","Existing car recovery (open at start of day)","Raised earlier, not closed yet",f'=COUNTIFS({B},{Z("Z","<","C$9")})-COUNTIFS({B},{Z("Z","<","C$9")},{Z("J","<","C$9")})',"n"),
("rnew","New car recovery (raised that day)","New cases that day",f'=COUNTIFS({B},raw!$Z$2:$Z,C$9)',"n"),
("rcl","Car recovered / case closed that day","",f'=COUNTIFS({B},raw!$J$2:$J,C$9)',"n"),
("tat","   Car recovery TAT - closed that day (avg days)","Average days from case start to close",f'=IFERROR((SUMIFS(raw!$J$2:$J,{B},raw!$J$2:$J,C$9)-SUMIFS(raw!$Z$2:$Z,{B},raw!$J$2:$J,C$9))/C{{rcl}},0)',"d"),
("rpe","Pending car recovery (open at day end)","Existing + new - closed",pend(0,None),"n"),
("rp2","   pending 0-2 days","",pend(0,2),"n"),
("rp5","   pending 3-5 days","",pend(3,5),"n"),
("rp7","   pending 6-7 days","",pend(6,7),"n"),
("rp14","   pending 8-14 days","",pend(8,14),"n"),
("rp15","   pending 15+ days (ACT)","Old cases - escalate",pend(15,None),"a"),
("sur","Deposit used up: Live OS >= Deposit","All of these are also Critical",f'=COUNTIFS({B},{sur},1)',"n"),
("surr","   with car recovery raised","Case started on or before this day",f'=COUNTIFS({B},{sur},1,{Z("Z","<=","C$9")})',"n"),
("surn","   NO car recovery yet (ACT)","Loss keeps growing every day",'=C{sur}-C{surr}',"a"),
("surp","   Recovery raised % of deposit used up","Should be close to 100%",'=IFERROR(C{surr}/C{sur},0)',"p"),
("ns","Newly crossed deposit that day","Was below deposit the day before",f'=COUNTIFS({B},raw!$DY$2:$DY,C$9)',"n"),
("gap","Newly crossed minus new recovery (ACT)","Positive = recovery backlog growing",'=C{ns}-C{rnew}',"a"),
("S","Join Funnel (All)"),
("f_j","Joined (new + rejoin)","FUNNEL: column = join date; status of those joiners till today",f'=COUNTIFS({J})',"n"),
("f_s","-> Live OS crossed deposit","Any day after join",f'=COUNTIFS({J},raw!$DV$2:$DV,1)',"n"),
("f_sp","   % of joined","",'=IFERROR(C{f_s}/C{f_j},0)',"p"),
("f_r","-> Car recovery raised","",f'=COUNTIFS({J},raw!$DW$2:$DW,1)',"n"),
("f_c","-> Car recovered (case closed)","",f'=COUNTIFS({J},raw!$DX$2:$DX,1)',"n"),
("f_g","Crossed deposit, NO recovery (ACT)","",f'=COUNTIFS({J},raw!$DV$2:$DV,1,raw!$DW$2:$DW,0)',"a"),
("n_s","NON-FUNNEL: crossed deposit that day","Event on that day, pilot joined in the last 28 days (fixed, does not change later)",f'=COUNTIFS({B},raw!$DY$2:$DY,C$9,{Z("V",">=","(C$9-28)")})',"n"),
("n_r","NON-FUNNEL: car recovery raised that day","Same, joined in last 28 days",f'=COUNTIFS({B},raw!$Z$2:$Z,C$9,{Z("V",">=","(C$9-28)")})',"n"),
("n_c","NON-FUNNEL: car recovered / closed that day","Same, joined in last 28 days",f'=COUNTIFS({B},raw!$J$2:$J,C$9,{Z("V",">=","(C$9-28)")})',"n"),
("S","Bad Debt"),
]+bd("b1","1. Active bad debt (expected) - pilots",MA,OWA,"Still active but Live OS >= deposit")+\
  bd("b2","2. Joined this week & left - pilots",MJ,EC,"Joined/rejoined this week, left by this day, owes more than deposit")+\
  bd("b3","3. Weekly collection pilots who left - pilots",MW,EC,"Had Weekly OS (in collection list), left this week, owes more than deposit")+[
("bt","Total bad debt amount (Rs)","1 + 2 + 3",'=C{b1a}+C{b2a}+C{b3a}',"n"),
]
DIR={'act':'g','join':'g','rg':'g','tc':'g','rgw':'g','tcw':'g','tcol':'g','tcp':'g','wosc':'g','wosp':'g','mo':'g','cat':'g','cal':'g','cp':'g','rcl':'g','surp':'g','f_j':'g',
     'lo':'b','cam':'b','ceod':'b','cnc':'b','rex':'b','rpe':'b','rp15':'b','tat':'b','sur':'b','surn':'b','ns':'b','gap':'b','f_g':'b','b1':'b','b2':'b','b3':'b','bt':'b','n_s':'b'}
secs=[];cur=None
for m in M:
    if m[0]=="S": cur=[m[1],[]]; secs.append(cur)
    else: cur[1].append(m)
rowno={}; r=R0; spans=[]
for name,items in secs:
    s0=r
    for it in items: rowno[it[0]]=r; r+=1
    spans.append((name,s0,r-1))
last=r-1
grid=[]
for name,items in secs:
    for i,(k,lab,dfn,f,fm) in enumerate(items):
        f=f.replace("{{","{").replace("}}","}").format(**rowno)
        grid.append([name if i==0 else "",lab.strip(),f])
readme=[["Section","Metric","What it means"]]
for name,items in secs:
    for k,lab,dfn,f,fm in items: readme.append([name,lab.strip(),dfn or ""])
def rg(r1,r2,c1,c2): return {"sheetId":S,"startRowIndex":r1,"endRowIndex":r2,"startColumnIndex":c1,"endColumnIndex":c2}
def rc(r,f,fl): return {"repeatCell":{"range":r,"cell":{"userEnteredFormat":f},"fields":fl}}
BLUE={"red":0.235,"green":0.471,"blue":0.847}; WH={"red":1,"green":1,"blue":1}
GRN={"red":0.341,"green":0.733,"blue":0.541}; RED={"red":0.902,"green":0.486,"blue":0.451}
bdr={"style":"SOLID","width":1,"colorStyle":{"rgbColor":{"red":0.75,"green":0.75,"blue":0.75}}}
a0=R0-1; L=last  # 0-based start, exclusive end
post=[{"copyPaste":{"source":rg(a0,L,2,3),"destination":rg(a0,L,3,23),"pasteType":"PASTE_FORMULA"}},
 rc(rg(a0,L,0,23),{"textFormat":{"fontSize":9},"verticalAlignment":"MIDDLE","backgroundColorStyle":{"rgbColor":WH}},"userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment,userEnteredFormat.backgroundColorStyle"),
 rc(rg(a0,L,2,23),{"numberFormat":{"type":"NUMBER","pattern":"#,##0;-#,##0;0"},"horizontalAlignment":"CENTER"},"userEnteredFormat.numberFormat,userEnteredFormat.horizontalAlignment"),
 {"updateBorders":{"range":rg(a0-1,L,0,23),"top":bdr,"bottom":bdr,"left":bdr,"right":bdr,"innerHorizontal":bdr,"innerVertical":bdr}}]
for name,a,b in spans:
    post.append({"mergeCells":{"range":rg(a-1,b,0,1),"mergeType":"MERGE_ALL"}})
    post.append(rc(rg(a-1,b,0,1),{"backgroundColorStyle":{"rgbColor":BLUE},"textFormat":{"bold":True,"fontSize":10,"foregroundColorStyle":{"rgbColor":WH}},"horizontalAlignment":"LEFT","verticalAlignment":"MIDDLE","wrapStrategy":"WRAP"},"userEnteredFormat"))
    post.append({"updateBorders":{"range":rg(a-1,b,0,23),"top":{"style":"SOLID_MEDIUM","width":2,"colorStyle":{"rgbColor":{"red":0.2,"green":0.2,"blue":0.2}}}}})
cf=[]
for name,items in secs:
    for k,lab,dfn,f,fm in items:
        rr=rowno[k]-1; sub=lab.startswith("   ")
        if fm=="p": post.append(rc(rg(rr,rr+1,2,23),{"numberFormat":{"type":"NUMBER","pattern":"0.0%"}},"userEnteredFormat.numberFormat"))
        if fm=="d": post.append(rc(rg(rr,rr+1,2,23),{"numberFormat":{"type":"NUMBER","pattern":"0.0"}},"userEnteredFormat.numberFormat"))
        if sub or fm=="p": post.append(rc(rg(rr,rr+1,1,2),{"textFormat":{"italic":True,"fontSize":9}},"userEnteredFormat.textFormat"))
        else: post.append(rc(rg(rr,rr+1,1,2),{"textFormat":{"bold":True,"fontSize":9}},"userEnteredFormat.textFormat"))
        if fm=="a": post.append(rc(rg(rr,rr+1,1,2),{"textFormat":{"bold":True,"fontSize":9,"foregroundColorStyle":{"rgbColor":{"red":0.753,"green":0,"blue":0}}}},"userEnteredFormat.textFormat"))
        d=DIR.get(k) if not sub else None
        if fm=="a": d='b'
        if d:
            lo,hi=(RED,GRN) if d=='g' else (GRN,RED)
            cf.append({"addConditionalFormatRule":{"rule":{"ranges":[rg(rr,rr+1,2,23)],"gradientRule":{"minpoint":{"colorStyle":{"rgbColor":lo},"type":"MIN"},"midpoint":{"colorStyle":{"rgbColor":WH},"type":"PERCENTILE","value":"50"},"maxpoint":{"colorStyle":{"rgbColor":hi},"type":"MAX"}}},"index":0}})
post+=cf
post+=[{"addConditionalFormatRule":{"rule":{"ranges":[rg(8,9,2,23)],"booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":"=C$7=1"}]},"format":{"backgroundColorStyle":{"rgbColor":{"red":0.6,"green":0,"blue":0}}}}},"index":0}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"ROWS","startIndex":a0,"endIndex":L},"properties":{"pixelSize":19},"fields":"pixelSize"}}]
json.dump({"grid":grid,"post":post,"readme":readme,"last":last,"rowno":rowno},open('daily6.json','w'),separators=(',',':'))
print("last row",last,"rows",len(grid),"post",len(post),"cf",len(cf))
for name,a,b in spans: print(name,a,b)
