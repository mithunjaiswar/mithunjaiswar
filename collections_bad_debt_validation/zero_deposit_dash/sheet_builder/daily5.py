import json
exec(open('m4.py').read())
# direction tags: good-high (g) / bad-high (b)
DIR={'act':'g','join':'g','rg':'g','tc':'g','rgw':'g','tcw':'g','wosc':'g','wosp':'g','lc':'g','lp':'g','mo':'g','cat':'g','cal':'g','cp':'g','rcl':'g','surp':'g',
     'cam':'b','ceod':'b','cnc':'b','lo':'b','rex':'b','rnew':None,'rpe':'b','rp16':'b','sur':'b','surn':'b','ns':'b','gap':'b',
     'z_lo':'b','z_ceod':'b','z_cnc':'b','z_sur':'b','z_surn':'b','z_rpe':'b','z_ns':'b','f_g':'b','g_g':'b','f_j':'g','g_j':None}
SHORT={"A. PILOTS & JOINS":"Pilots & Joins","B. RENT GENERATED vs RENT PAID":"Rent vs Paid","C. WEEKLY OS & LIVE OS COLLECTION (Weekly OS = India Collections dash)":"Collection",
 "D. CRITICAL & CALLING (Critical = MasterTab rule OR Live OS >= Deposit)":"Critical & Calling","E. CAR RECOVERY TRACKING (all cases, non-funnel)":"Car Recovery",
 "F. LIVE OS >= DEPOSIT (deposit used up)":"Deposit Used Up","G. 0 DEPOSIT CUT (deposit at allocation = 0)":"0 Deposit Cut",
 "H. JOIN FUNNEL - column = join date; status of those joiners TILL TODAY (old days can change)":"Join Funnel (All)","I. JOIN FUNNEL - 0 DEPOSIT JOINS":"Join Funnel (0 Dep)"}
secs=[];cur=None
for m in M:
    if m[0]=="S": cur=[SHORT[m[1]],m[1],[]]; secs.append(cur)
    else: cur[2].append(m)
rowno={}; r=8; spans=[]
for name,full,items in secs:
    s0=r
    for it in items: rowno[it[0]]=r; r+=1
    spans.append((name,s0,r-1)); 
last=r-1
grid=[]
for name,full,items in secs:
    for k,lab,dfn,f,fm in items:
        f=f.replace("{{","{").replace("}}","}").format(**rowno)
        grid.append([None,lab.strip(),f])
# README rows
readme=[["Section","Metric","What it means"]]
for name,full,items in secs:
    for k,lab,dfn,f,fm in items: readme.append([name,lab.strip(),dfn or ""])
S=113
def rg(r1,r2,c1,c2): return {"sheetId":S,"startRowIndex":r1,"endRowIndex":r2,"startColumnIndex":c1,"endColumnIndex":c2}
def rc(r,f,fl): return {"repeatCell":{"range":r,"cell":{"userEnteredFormat":f},"fields":fl}}
BLUE={"red":0.235,"green":0.471,"blue":0.847}; NAV={"red":0.067,"green":0.333,"blue":0.8}; WH={"red":1,"green":1,"blue":1}
GRN={"red":0.341,"green":0.733,"blue":0.541}; RED={"red":0.902,"green":0.486,"blue":0.451}; PK={"red":0.988,"green":0.894,"blue":0.894}
bd={"style":"SOLID","width":1,"colorStyle":{"rgbColor":{"red":0.75,"green":0.75,"blue":0.75}}}
post=[{"copyPaste":{"source":rg(7,last,2,3),"destination":rg(7,last,3,23),"pasteType":"PASTE_FORMULA"}},
 rc(rg(7,last,0,23),{"textFormat":{"fontSize":9},"verticalAlignment":"MIDDLE"},"userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment"),
 rc(rg(7,last,2,23),{"numberFormat":{"type":"NUMBER","pattern":"#,##0;-#,##0;0"},"horizontalAlignment":"CENTER"},"userEnteredFormat.numberFormat,userEnteredFormat.horizontalAlignment"),
 rc(rg(6,7,0,23),{"textFormat":{"bold":True,"fontSize":9,"foregroundColorStyle":{"rgbColor":WH}},"backgroundColorStyle":{"rgbColor":NAV},"horizontalAlignment":"CENTER","verticalAlignment":"MIDDLE","numberFormat":{"type":"DATE","pattern":"dd-mmm"}},"userEnteredFormat"),
 {"updateBorders":{"range":rg(6,last,0,23),"top":bd,"bottom":bd,"left":bd,"right":bd,"innerHorizontal":bd,"innerVertical":bd}},
]
for name,a,b in spans:
    post.append({"mergeCells":{"range":rg(a-1,b,0,1),"mergeType":"MERGE_ALL"}})
    post.append(rc(rg(a-1,b,0,1),{"backgroundColorStyle":{"rgbColor":BLUE},"textFormat":{"bold":True,"fontSize":10,"foregroundColorStyle":{"rgbColor":WH}},"horizontalAlignment":"LEFT","verticalAlignment":"MIDDLE","wrapStrategy":"WRAP"},"userEnteredFormat"))
    post.append({"updateBorders":{"range":rg(a-1,b,0,23),"top":{"style":"SOLID_MEDIUM","width":2,"colorStyle":{"rgbColor":{"red":0.2,"green":0.2,"blue":0.2}}}}})
cf=[]
for name,full,items in secs:
    for k,lab,dfn,f,fm in items:
        rr=rowno[k]-1
        sub=lab.startswith("   ")
        if fm=="p": post.append(rc(rg(rr,rr+1,2,23),{"numberFormat":{"type":"NUMBER","pattern":"0.0%"}},"userEnteredFormat.numberFormat"))
        if sub or fm=="p": post.append(rc(rg(rr,rr+1,1,2),{"textFormat":{"italic":True,"fontSize":9}},"userEnteredFormat.textFormat"))
        else: post.append(rc(rg(rr,rr+1,1,2),{"textFormat":{"bold":True,"fontSize":9}},"userEnteredFormat.textFormat"))
        if fm=="a": post.append(rc(rg(rr,rr+1,1,2),{"textFormat":{"bold":True,"fontSize":9,"foregroundColorStyle":{"rgbColor":{"red":0.753,"green":0,"blue":0}}}},"userEnteredFormat.textFormat"))
        d=DIR.get(k,None) if not sub else None
        if fm=="a": d='b'
        if d:
            lo,hi=(RED,GRN) if d=='g' else (GRN,RED)
            cf.append({"addConditionalFormatRule":{"rule":{"ranges":[rg(rr,rr+1,2,23)],"gradientRule":{"minpoint":{"colorStyle":{"rgbColor":lo},"type":"MIN"},"midpoint":{"colorStyle":{"rgbColor":WH},"type":"PERCENTILE","value":"50"},"maxpoint":{"colorStyle":{"rgbColor":hi},"type":"MAX"}}},"index":0}})
post+=cf
post+=[{"addConditionalFormatRule":{"rule":{"ranges":[rg(6,7,2,23)],"booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":"=C$5=1"}]},"format":{"backgroundColorStyle":{"rgbColor":{"red":0.6,"green":0,"blue":0}}}}},"index":0}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":0,"endIndex":1},"properties":{"pixelSize":110},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":1,"endIndex":2},"properties":{"pixelSize":260},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":2,"endIndex":23},"properties":{"pixelSize":62},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"ROWS","startIndex":7,"endIndex":last},"properties":{"pixelSize":19},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"ROWS","startIndex":6,"endIndex":7},"properties":{"pixelSize":24},"fields":"pixelSize"}},
 {"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"ROWS","startIndex":2,"endIndex":6},"properties":{"hiddenByUser":True},"fields":"hiddenByUser"}}]
top=[["2. DAILY TREND - last 21 days    (definitions: see tab 2_Daily_Trend_README)"],None,None,
     [None]*24+['=IF($B$2="All","*",$B$2)'],
     ["","(day #)"]+[f'=WEEKDAY({col(C0+i)}7,2)' for i in range(N)]+[None,f'=IFERROR(MAXIFS($C$7:$W$7,$C${rowno["act"]}:$W${rowno["act"]},">0"),TODAY()-1)'],
     ["","(week)"]+[f'={col(C0+i)}7-WEEKDAY({col(C0+i)}7,3)' for i in range(N)],
     ['="Data: "&TEXT(raw!CL2,"dd-mmm hh:mm")',"Metric",'=TODAY()-20']+[f'={col(C0+i-1)}7+1' for i in range(1,N)]]
json.dump({"top":top[3:],"grid":grid,"post":post,"readme":readme,"last":last,"rowno":rowno},open('daily5.json','w'),separators=(',',':'))
print(last,len(json.dumps(post)),len(json.dumps(grid)),len(readme))
