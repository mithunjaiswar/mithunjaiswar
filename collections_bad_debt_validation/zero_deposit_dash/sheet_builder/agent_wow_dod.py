import json
def L(i):  # 0-based -> letter
    s='';i+=1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s
day={'live':'AA AB AC AD AE AF AG','coll':'AH AI AJ AK AL AM AN','wos':'AO AP AQ AR AS AT AU','surp':'AV AW AX AY AZ BA BB',
     'att':'BC BD BE BF BG BH BI','conn':'BJ BK BL BM BN BO BP','crit':'CA CB CC CD CE CF CG','bd':'CT CU CV CW CX CY CZ'}
day={k:v.split() for k,v in day.items()}
qs=[]
for d in range(7):
    sel="select A,B,DC,count(%s),sum(%s),sum(%s),sum(%s),sum(%s),sum(%s),sum(%s),sum(%s) where DB='Include' and A is not null group by A,B,DC"%(
        day['live'][d],day['coll'][d],day['wos'][d],day['att'][d],day['conn'][d],day['crit'][d],day['surp'][d],day['bd'][d])
    qs.append(f'day{d+1}_,DROP(QUERY(raw!A2:DC,"{sel}",0),1)')
parts=",".join(qs)
f_day='=LET('+parts+',fx_,LAMBDA(qq,nn,HSTACK(CHOOSECOLS(qq,1)+nn-1,CHOOSECOLS(qq,2,3,4,5,6,7,8,9,10,11))),VSTACK({"date","city","agent","active_pilots","collection","wos_collected","attempts","connects","critical_eod","surpass","bad_debt_amt"},fx_(day1_,1),fx_(day2_,2),fx_(day3_,3),fx_(day4_,4),fx_(day5_,5),fx_(day6_,6),fx_(day7_,7)))'
f_week='=VSTACK({"week","city","agent","pilots","weekly_os","os_collected"},DROP(QUERY(raw!A2:DC,"select A,B,DC,count(D),sum(L),sum(O) where DB=\'Include\' and F=1 and A is not null group by A,B,DC",0),1))'
CITY='IF($B$2="All","*",$B$2)'
req=[]
def addsheet(sid,title,rows,cols,hidden=False,index=None,fr=0,fc=0):
    p={"title":title,"sheetId":sid,"hidden":hidden,"gridProperties":{"rowCount":rows,"columnCount":cols,"frozenRowCount":fr,"frozenColumnCount":fc}}
    if index is not None: p["index"]=index
    return {"addSheet":{"properties":p}}
def cellv(v):
    if v is None: return {}
    if isinstance(v,(int,float)): return {"userEnteredValue":{"numberValue":v}}
    if v.startswith('='): return {"userEnteredValue":{"formulaValue":v}}
    return {"userEnteredValue":{"stringValue":v}}
def put(sid,r,c,rows):
    return {"updateCells":{"start":{"sheetId":sid,"rowIndex":r,"columnIndex":c},"rows":[{"values":[cellv(x) for x in row]} for row in rows],"fields":"userEnteredValue"}}
req+= [addsheet(140,"agent_day",6000,11,True), addsheet(141,"agent_week",2000,6,True)]
req+= [put(140,0,0,[[f_day]]), put(141,0,0,[[f_week]])]
D='agent_day!'; W='agent_week!'
NUMFMT='[>=1000000]0.0,,"M";[>=1000]0.0,"K";0'
def view(sid,title,index,kind):
    out=[addsheet(sid,title,400,1+ (9*9 if kind=='dod' else 11*5),False,index,6,1)]
    rows=[]
    out.append(put(sid,0,0,[[f"Agent {'DoD - last 8 days' if kind=='dod' else 'WoW - last 4 hisaab weeks'} (from raw, Dash Status = Include)"],
                             ["City ▸","All", '=IFERROR("Raw data: "&TEXT(raw!DA2*1,"dd-mmm hh:mm"),"")']]))
    if kind=='dod':
        # period row (row 5 = index 4) per block; anchor date list in hidden cell? compute per block
        mets=[("Active pilots","active_pilots","D",None),("Collection (Rs)","collection","E",None),("WOS collected (Rs)","wos_collected","F",None),
              ("Attempts","attempts","G",None),("Connects","connects","H",None),("Connect %",None,None,("H","G")),
              ("Critical EOD pilots","critical_eod","I",None),("Surpass pilots (OS >= deposit)","surpass","J",None),("Bad debt amount (Rs)","bad_debt_amt","K",None)]
        n=8
        lastd=f'MAX(FILTER({D}$A$2:$A,{D}$D$2:$D>0))'
        out.append(put(sid,2,0,[["Last data day:", '=IFERROR(TEXT('+lastd+',"dd-mmm"),"")']]))
        out.append(put(sid,4,0,[["Agent"]]))
        out.append(put(sid,5,0,[["TOTAL"]]))
        out.append(put(sid,6,0,[['=IFERROR(SORT(UNIQUE(FILTER(agent_day!C2:C,agent_day!C2:C<>"",agent_day!A2:A>='+lastd+'-7,IF($B$2="All",agent_day!B2:B<>"",agent_day!B2:B=$B$2)))),"")']]))
        for i,(name,_,col,ratio) in enumerate(mets):
            c0=1+i*(n+1)
            dates=f'{L(c0)}$5:{L(c0+n-1)}$5'
            hdr=[f'=ARRAYFORMULA(IFERROR({lastd}-7+SEQUENCE(1,{n},0),""))']+[None]*(n-1)+['DoD']
            out.append(put(sid,3,c0,[[name]]))
            out.append(put(sid,4,c0,[hdr]))
            if ratio:
                a,b=ratio
                tot=f'=MAKEARRAY(1,{n},LAMBDA(rr,cc,IFERROR(SUMIFS({D}${a}$2:${a},{D}$A$2:$A,INDEX({dates},1,cc),{D}$B$2:$B,{CITY})/SUMIFS({D}${b}$2:${b},{D}$A$2:$A,INDEX({dates},1,cc),{D}$B$2:$B,{CITY}),0)))'
                body=f'=IF($A$7="","",MAKEARRAY(COUNTA($A$7:$A),{n},LAMBDA(rr,cc,IFERROR(SUMIFS({D}${a}$2:${a},{D}$C$2:$C,INDEX($A$7:$A,rr),{D}$A$2:$A,INDEX({dates},1,cc),{D}$B$2:$B,{CITY})/SUMIFS({D}${b}$2:${b},{D}$C$2:$C,INDEX($A$7:$A,rr),{D}$A$2:$A,INDEX({dates},1,cc),{D}$B$2:$B,{CITY}),0))))'
            else:
                tot=f'=MAKEARRAY(1,{n},LAMBDA(rr,cc,SUMIFS({D}${col}$2:${col},{D}$A$2:$A,INDEX({dates},1,cc),{D}$B$2:$B,{CITY})))'
                body=f'=IF($A$7="","",MAKEARRAY(COUNTA($A$7:$A),{n},LAMBDA(rr,cc,SUMIFS({D}${col}$2:${col},{D}$C$2:$C,INDEX($A$7:$A,rr),{D}$A$2:$A,INDEX({dates},1,cc),{D}$B$2:$B,{CITY}))))'
            last=L(c0+n-1); prev=L(c0+n-2); dl=L(c0+n)
            out.append(put(sid,5,c0,[[tot]+[None]*(n-1)+[f'={last}6-{prev}6']]))
            out.append(put(sid,6,c0,[[body]]))
            out.append(put(sid,6,c0+n,[[f'=ARRAYFORMULA(IF($A$7:$A="","",{last}7:{last}-{prev}7:{prev}))']]))
            out.append(fmt(sid,4,5,c0,c0+n,{"numberFormat":{"type":"DATE","pattern":"dd-mmm"}}))
            pct= ratio is not None
            out.append(fmt(sid,5,400,c0,c0+n+1,{"numberFormat":{"type":"PERCENT","pattern":"0%"} if pct else {"type":"NUMBER","pattern":NUMFMT}}))
            out.append(merge(sid,3,c0,c0+n+1))
            out.append(border(sid,c0))
    else:
        n=4
        weeks=f'{W}$A$2:$A'
        mets=[("Pilots (in dash)","D",'w'),("Weekly OS (Rs)","E",'wneg'),("OS collected (Rs)","F",'w'),("Recovery %",("F","E"),'wratio_neg'),
              ("Attempts","G",'d'),("Connects","H",'d'),("Connect %",("H","G"),'dratio'),("Attempts per pilot",("G","D"),'mix'),
              ("Critical EOD pilots (week end)","I",'end'),("Surpass pilots (week end)","J",'end'),("Bad debt amount (Rs, week end)","K",'end')]
        lastd=f'MAX(FILTER({D}$A$2:$A,{D}$D$2:$D>0))'
        out.append(put(sid,2,0,[["Last data day:", '=IFERROR(TEXT('+lastd+',"dd-mmm"),"")']]))
        out.append(put(sid,4,0,[["Agent"]]))
        out.append(put(sid,5,0,[["TOTAL"]]))
        out.append(put(sid,6,0,[['=IFERROR(SORT(UNIQUE(FILTER(agent_week!C2:C,agent_week!C2:C<>"",IF($B$2="All",agent_week!B2:B<>"",agent_week!B2:B=$B$2)))),"")']]))
        for i,(name,col,typ) in enumerate(mets):
            c0=1+i*(n+1)
            wk=f'{L(c0)}$5:{L(c0+n-1)}$5'
            hdr=[f'=IFERROR(TRANSPOSE(SORT(UNIQUE(FILTER({weeks},{weeks}<>"")))),"")']+[None]*(n-1)+['WoW']
            out.append(put(sid,3,c0,[[name]])); out.append(put(sid,4,c0,[hdr]))
            def ws(c,agent,w): # weekly helper sum
                a=f',{W}$C$2:$C,{agent}' if agent else ''
                return f'SUMIFS({W}${c}$2:${c},{W}$A$2:$A,{w}{a},{W}$B$2:$B,{CITY})'
            def ds(c,agent,w): # daily helper sum over week
                a=f',{D}$C$2:$C,{agent}' if agent else ''
                return f'SUMIFS({D}${c}$2:${c},{D}$A$2:$A,">="&{w},{D}$A$2:$A,"<="&({w}+6){a},{D}$B$2:$B,{CITY})'
            def de(c,agent,w): # daily helper at week-end day
                a=f',{D}$C$2:$C,{agent}' if agent else ''
                return f'SUMIFS({D}${c}$2:${c},{D}$A$2:$A,MIN({w}+6,{lastd}){a},{D}$B$2:$B,{CITY})'
            def expr(agent,w):
                if typ=='w': return ws(col,agent,w)
                if typ=='wneg': return '-'+ws(col,agent,w)
                if typ=='wratio_neg': return f'IFERROR({ws(col[0],agent,w)}/-{ws(col[1],agent,w)},0)'
                if typ=='d': return ds(col,agent,w)
                if typ=='dratio': return f'IFERROR({ds(col[0],agent,w)}/{ds(col[1],agent,w)},0)'
                if typ=='mix': return f'IFERROR({ds(col[0],agent,w)}/{ws(col[1],agent,w)},0)'
                if typ=='end': return de(col,agent,w)
            W1=f'INDEX({wk},1,cc)'
            tot=f'=MAKEARRAY(1,{n},LAMBDA(rr,cc,{expr(None,W1)}))'
            body=f'=IF($A$7="","",MAKEARRAY(COUNTA($A$7:$A),{n},LAMBDA(rr,cc,{expr("INDEX($A$7:$A,rr)",W1)})))'
            last=L(c0+n-1); prev=L(c0+n-2)
            out.append(put(sid,5,c0,[[tot]+[None]*(n-1)+[f'={last}6-{prev}6']]))
            out.append(put(sid,6,c0,[[body]]))
            out.append(put(sid,6,c0+n,[[f'=ARRAYFORMULA(IF($A$7:$A="","",{last}7:{last}-{prev}7:{prev}))']]))
            out.append(fmt(sid,4,5,c0,c0+n,{"numberFormat":{"type":"DATE","pattern":"dd-mmm"}}))
            pct='%' in name; dec= name=="Attempts per pilot"
            nf={"type":"PERCENT","pattern":"0%"} if pct else ({"type":"NUMBER","pattern":"0.0"} if dec else {"type":"NUMBER","pattern":NUMFMT})
            out.append(fmt(sid,5,400,c0,c0+n+1,{"numberFormat":nf}))
            dnf={"type":"PERCENT","pattern":"+0%;-0%;0%"} if pct else ({"type":"NUMBER","pattern":"+0.0;-0.0;0"} if dec else {"type":"NUMBER","pattern":'[>=1000]+0.0,"K";[<=-1000]-0.0,"K";0'})
            out.append(fmt(sid,5,400,c0+n,c0+n+1,{"numberFormat":dnf,"backgroundColorStyle":{"rgbColor":{"red":0.95,"green":0.95,"blue":0.95}}}))
            out.append(merge(sid,3,c0,c0+n+1)); out.append(border(sid,c0))
    out.append(fmt(sid,3,6,0,(82 if kind=='dod' else 56),{"textFormat":{"bold":True},"horizontalAlignment":"CENTER","backgroundColorStyle":{"rgbColor":{"red":0.85,"green":0.9,"blue":0.98}}}))
    out.append(fmt(sid,0,1,0,1,{"textFormat":{"bold":True,"fontSize":13}}))
    out.append({"setDataValidation":{"range":{"sheetId":sid,"startRowIndex":1,"endRowIndex":2,"startColumnIndex":1,"endColumnIndex":2},"rule":{"condition":{"type":"ONE_OF_RANGE","values":[{"userEnteredValue":"=lists!$B$2:$B$20"}]},"strict":True,"showCustomUi":True}}})
    out.append({"updateDimensionProperties":{"range":{"sheetId":sid,"dimension":"COLUMNS","startIndex":0,"endIndex":1},"properties":{"pixelSize":160},"fields":"pixelSize"}})
    return out
def fmt(sid,r0,r1,c0,c1,f):
    return {"repeatCell":{"range":{"sheetId":sid,"startRowIndex":r0,"endRowIndex":r1,"startColumnIndex":c0,"endColumnIndex":c1},"cell":{"userEnteredFormat":f},"fields":",".join("userEnteredFormat."+k for k in f.keys())}}
def merge(sid,r,c0,c1):
    return {"mergeCells":{"range":{"sheetId":sid,"startRowIndex":r,"endRowIndex":r+1,"startColumnIndex":c0,"endColumnIndex":c1},"mergeType":"MERGE_ALL"}}
def border(sid,c0):
    return {"updateBorders":{"range":{"sheetId":sid,"startRowIndex":3,"endRowIndex":400,"startColumnIndex":c0,"endColumnIndex":c0+1},"left":{"style":"SOLID_MEDIUM","colorStyle":{"rgbColor":{"red":0,"green":0,"blue":0}}}}}
v1=view(142,"Agent_DoD",5,'dod'); v2=view(143,"Agent_WoW",6,'wow')
json.dump(req,open('wd_1.json','w'))
json.dump(v1,open('wd_dod.json','w')); json.dump(v2,open('wd_wow.json','w'),separators=(',',':'))
print(len(json.dumps(req)),len(json.dumps(v1)),len(json.dumps(v2)))
