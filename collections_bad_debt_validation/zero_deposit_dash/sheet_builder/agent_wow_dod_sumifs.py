import json
def L(i):
    s='';i+=1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s
R0,R1=4,160   # rows 5..160 (0-based start 4, end exclusive 160)
CRIT='raw!$DC$2:$DC,$A5,raw!$B$2:$B,$B$1,raw!$DB$2:$DB,"Include"'
def rc(sid,c0,c1,f):
    return {"repeatCell":{"range":{"sheetId":sid,"startRowIndex":R0,"endRowIndex":R1,"startColumnIndex":c0,"endColumnIndex":c1},"cell":{"userEnteredValue":{"formulaValue":f}},"fields":"userEnteredValue"}}
req=[]
# ---------- DoD (sheet 142): 9 blocks x 9 cols starting col 1 ----------
dod=[('cnt','AA','AG'),('sum','AH','AN'),('sum','AO','AU'),('sum','BC','BI'),('sum','BJ','BP'),('ratio',None,None),('sum','CA','CG'),('sum','AV','BB'),('sum','CT','CZ')]
for i,(k,a,b) in enumerate(dod):
    c0=1+i*9; h=L(c0)
    day=f'WEEKDAY({h}$4,2)'; wk=f'{h}$4-WEEKDAY({h}$4,3)'
    if k=='cnt': f=f'=IF($A5="","",COUNTIFS(INDEX(raw!${a}$2:${b},0,{day}),">-1E+15",raw!$A$2:$A,{wk},{CRIT}))'
    elif k=='sum': f=f'=IF($A5="","",SUMIFS(INDEX(raw!${a}$2:${b},0,{day}),raw!$A$2:$A,{wk},{CRIT}))'
    else: f=f'=IF($A5="","",IFERROR({L(1+4*9)}5/{L(1+3*9)}5,0))'  # connects block / attempts block, same offset
    req.append(rc(142,c0,c0+8,f))
    d=c0+8
    if i==0:  # J6 has the user's ARRAYFORMULA; only fill J5
        req.append({"updateCells":{"start":{"sheetId":142,"rowIndex":4,"columnIndex":d},"rows":[{"values":[{"userEnteredValue":{"formulaValue":'=I5-H5'}}]}],"fields":"userEnteredValue"}})
    else:
        req.append(rc(142,d,d+1,f'=IF($A5="","",{L(d-1)}5-{L(d-2)}5)'))
# ---------- WoW (sheet 143): 11 blocks x 5 cols starting col 1 ----------
def wsum(col,h,extra=''): return f'SUMIFS(raw!${col}$2:${col},raw!$A$2:$A,{h}$4{extra},{CRIT})'
def wsum7(a,h):
    cols=[]; s=a
    import string
    def n(c):
        x=0
        for ch in c: x=x*26+ord(ch)-64
        return x
    start=n(a)
    return '+'.join(wsum(L(start-1+j),h) for j in range(7))
wow=[]
for i in range(11):
    c0=1+i*5; h=L(c0)
    endday=f'IF({h}$4=TODAY()-WEEKDAY(TODAY(),3),lists!$R$10,7)'
    if i==0: f=f'=IF($A5="","",COUNTIFS(raw!$A$2:$A,{h}$4,raw!$F$2:$F,1,{CRIT}))'
    elif i==1: f=f'=IF($A5="","",-{wsum("L",h,",raw!$F$2:$F,1")})'
    elif i==2: f=f'=IF($A5="","",{wsum("O",h,",raw!$F$2:$F,1")})'
    elif i==3: f=f'=IF($A5="","",IFERROR({L(c0-5)}5/{L(c0-10)}5,0))'
    elif i==4: f=f'=IF($A5="","",{wsum7("BC",h)})'
    elif i==5: f=f'=IF($A5="","",{wsum7("BJ",h)})'
    elif i==6: f=f'=IF($A5="","",IFERROR({L(c0-5)}5/{L(c0-10)}5,0))'
    elif i==7: f=f'=IF($A5="","",IFERROR({L(c0-15)}5/{L(c0-35)}5,0))'
    else:
        a,b={8:('CA','CG'),9:('AV','BB'),10:('CT','CZ')}[i]
        f=f'=IF($A5="","",SUMIFS(INDEX(raw!${a}$2:${b},0,{endday}),raw!$A$2:$A,{h}$4,{CRIT}))'
    req.append(rc(143,c0,c0+4,f))
    d=c0+4
    req.append(rc(143,d,d+1,f'=IF($A5="","",{L(d-1)}5-{L(d-2)}5)'))
json.dump(req,open('sumifs_req.json','w'),separators=(',',':'))
print(len(req),len(json.dumps(req,separators=(',',':'))))
for x in req:
    if 'repeatCell' in x: print(x['repeatCell']['range']['sheetId'],L(x['repeatCell']['range']['startColumnIndex']),x['repeatCell']['cell']['userEnteredValue']['formulaValue'][:200])
