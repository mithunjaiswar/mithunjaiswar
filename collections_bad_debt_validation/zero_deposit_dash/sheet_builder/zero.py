from common import *
S=114
rq=[{"addSheet":{"properties":{"title":"3_Zero_Deposit","sheetId":S,"index":2,"gridProperties":{"rowCount":90,"columnCount":26,"frozenRowCount":3},"tabColorStyle":{"rgbColor":rgb("#BF8F00")}}}}]
rq+=title(S,"3. ZERO vs DEPOSIT - is 0 deposit making OS & bad debt worse?","Columns = deposit taken at allocation. Pick the week in L2. 'Money at risk' = what pilot owes above his deposit = loss if he runs away today.")
rq+=filter_bar(S,include_sd=False)
rq.append(cells(S,1,10,[["Week ▸","=MAX(lists!$I$2:$I$10)"]]))
rq.append(dv_range(S,1,11,"=lists!$I$2:$I$10"))
rq.append(style(S,1,2,10,11,bg=GREY,bold=True,align="RIGHT")); rq.append(style(S,1,2,11,12,bg=YEL,bold=True,align="CENTER")); rq.append(numfmt(S,1,2,11,12,"dd-mmm-yy","DATE"))
rq.append(cells(S,3,25,[['=IF($B$2="All","*",$B$2)']]))
# Table 1
rq+=section(S,4,"A. SELECTED WEEK - by deposit bucket (latest day of that week)",9)
bk=["0 Deposit","1-3K","3-5K","5-10K","10K+","All"]
rq.append(cells(S,5,0,[["Metric"]+bk+["0-Dep vs 10K+","What it means"]]))
b='r_A,$L$2,r_B,$Z$4,r_DF,1,r_H,IF(B$6="All","*",B$6)'
M=[("Pilots",f'=COUNTIFS({b})',"#,##0",False,"Size of each bucket"),
 ("Share of all pilots",'=IFERROR(B7/$G7,0)',"0.0%",False,""),
 ("New joins + rejoins in week",f'=COUNTIFS({b},r_T,"<>Existing")',"#,##0",False,"Fresh 0-deposit joins add risk"),
 ("Weekly OS (Rs, dash)",f'=-SUMIFS(r_L,{b},r_F,1)',"#,##0",False,"Same as India Collections dash"),
 ("Weekly OS collected %",f'=IFERROR(SUMIFS(r_O,{b},r_F,1)/B10,0)',"0.0%",True,"Lower = weaker payers"),
 ("Live OS owed - latest day (Rs)",f'=SUMIFS(r_CQ,{b})',"#,##0",False,""),
 ("Avg owed per pilot (Rs)",'=IFERROR(B12/B7,0)',"#,##0",True,""),
 ("% owes >= deposit (any day in week)",f'=IFERROR(COUNTIFS({b},r_CX,1)/B7,0)',"0.0%",True,"0 deposit: any OS = surpassed"),
 ("% owes >= deposit (latest day)",f'=IFERROR(COUNTIFS({b},r_CR,1)/B7,0)',"0.0%",True,""),
 ("% critical at day end (latest day)",f'=IFERROR(COUNTIFS({b},r_CT,1)/B7,0)',"0.0%",True,"Owes >= 1 day rent"),
 ("Money at risk above deposit (Rs)",f'=SUMIFS(r_CZ,{b})',"#,##0",False,"LOSS if pilot runs today"),
 ("Money at risk per pilot (Rs)",'=IFERROR(B17/B7,0)',"#,##0",True,"Main 0-deposit risk number"),
 ("Owes >= deposit & NO car recovery",f'=COUNTIFS({b},r_DC,"4.*")',"#,##0",False,"Start recovery now"),
 ("Open car recovery",f'=COUNTIFS({b},r_Y,"Open")',"#,##0",False,""),
 ("GPS inactive at week start %",f'=IFERROR(COUNTIFS({b},r_K,"GPS Inactive")/B7,0)',"0.0%",True,"Car not tracked = higher run risk"),
 ("Defaulter payment habit %",f'=IFERROR(COUNTIFS({b},r_Q,"Defaulter")/B7,0)',"0.0%",True,""),
]
rows=[]
for lab,f,pat,ratio,mean in M:
    rows.append([lab,f,None,None,None,None,None,"",mean])
rq.append(cells(S,6,0,rows))
for k,(lab,f,pat,ratio,mean) in enumerate(M):
    ri=6+k; r=ri+1
    if ratio: rq.append(cells(S,ri,7,[[f'=IFERROR(B{r}/F{r},"-")']]))
    rq.append(pastec(S,ri,ri+1,1,7)); rq.append(numfmt(S,ri,ri+1,1,7,pat))
e1=6+len(M)
rq.append(numfmt(S,6,e1,7,8,'0.0"x"'))
rq.append(style(S,5,6,0,9,bg=GREY,bold=True,align="CENTER",wrap="WRAP"))
rq.append(style(S,5,e1,1,2,bg=PINK)); rq.append(style(S,5,6,1,2,bg="#F4C7C3",bold=True))
rq.append(style(S,6,e1,8,9,italic=True,color="#7F7F7F"))
rq.append(style(S,6,e1,7,8,bold=True,color=RED,align="CENTER"))
rq.append(style(S,16,18,0,9,bold=True))
rq.append(border(S,5,e1,0,9))
# Table 2 trend
t0=e1+1
rq+=section(S,t0,"B. TREND - 0 Deposit vs All pilots, last 4 weeks",6)
rq.append(cells(S,t0+1,0,[["Metric","Segment","=lists!I2","=lists!I3","=lists!I4","=lists!I5"]]))
tb='r_A,C${h},r_B,$Z$4,r_DF,1,r_H,IF($B{r}="All","*",$B{r})'
TM=[("Pilots",'=COUNTIFS({b})',"#,##0"),
    ("Weekly OS collected %",'=IFERROR(SUMIFS(r_O,{b},r_F,1)/-SUMIFS(r_L,{b},r_F,1),0)',"0.0%"),
    ("% owes >= deposit (any day)",'=IFERROR(COUNTIFS({b},r_CX,1)/COUNTIFS({b}),0)',"0.0%"),
    ("% critical at day end",'=IFERROR(COUNTIFS({b},r_CT,1)/COUNTIFS({b}),0)',"0.0%"),
    ("Money at risk above deposit (Rs)",'=SUMIFS(r_CZ,{b})',"#,##0"),
    ("Money at risk per pilot (Rs)",'=IFERROR(SUMIFS(r_CZ,{b})/COUNTIFS({b}),0)',"#,##0")]
h=t0+2
for k,(lab,f,pat) in enumerate(TM):
    for j,seg in enumerate(["0 Deposit","All"]):
        ri=t0+2+2*k+j; r=ri+1
        rq.append(cells(S,ri,0,[[lab if j==0 else "",seg,f.format(b=tb.format(h=h,r=r))]]))
        rq.append(pastec(S,ri,ri+1,2,6)); rq.append(numfmt(S,ri,ri+1,2,6,pat))
        if j==0: rq.append(style(S,ri,ri+1,1,6,bg=PINK))
e2=t0+2+2*len(TM)
rq.append(style(S,t0+1,t0+2,0,6,bg=GREY,bold=True,align="CENTER")); rq.append(numfmt(S,t0+1,t0+2,2,6,'"Week "dd-mmm',"DATE"))
rq.append(border(S,t0+1,e2,0,6))
# Table 3 product
p0=e2+1
rq+=section(S,p0,"C. BY PRODUCT (Leasing split EIP / Single) - selected week",8)
rq.append(cells(S,p0+1,0,[["Product","0-Dep pilots","0-Dep % owes >= deposit","0-Dep money at risk (Rs)","All pilots","All % owes >= deposit","All money at risk (Rs)","0-Dep share of money at risk"]]))
prods=["Leasing - EIP","Leasing - Single","D2O","Revenue Share","Own Now","EV_Leasing","EV_D2O","EV_Revenue Share","Fixed Pay","All"]
y=p0+3
pb=f'r_A,$L$2,r_B,$Z$4,r_DF,1,r_CN,IF($A{y}="All","*",$A{y})'
first=[prods[0],f'=COUNTIFS({pb},r_H,"0 Deposit")',f'=IFERROR(COUNTIFS({pb},r_H,"0 Deposit",r_CX,1)/B{y},0)',f'=SUMIFS(r_CZ,{pb},r_H,"0 Deposit")',f'=COUNTIFS({pb})',f'=IFERROR(COUNTIFS({pb},r_CX,1)/E{y},0)',f'=SUMIFS(r_CZ,{pb})',f'=IFERROR(D{y}/G{y},0)']
rq.append(cells(S,p0+2,0,[first])); rq.append(paste(S,y-1,1,8,y-1+len(prods)))
rq.append(cells(S,y,0,[[p] for p in prods[1:]]))
e3=y-1+len(prods)
rq+= [numfmt(S,y-1,e3,1,8,"#,##0"),numfmt(S,y-1,e3,2,3,"0.0%"),numfmt(S,y-1,e3,5,6,"0.0%"),numfmt(S,y-1,e3,7,8,"0.0%"),
      style(S,p0+1,p0+2,0,8,bg=GREY,bold=True,wrap="WRAP",align="CENTER"),style(S,e3-1,e3,0,8,bold=True,bg=GREY),border(S,p0+1,e3,0,8),
      cf_scale(S,y-1,e3-1,3,4),cf_scale(S,y-1,e3-1,2,3)]
rq+=[width(S,0,1,280),width(S,1,8,120),width(S,8,9,280),width(S,9,12,110),hide_cols(S,25,26)]
json.dump(rq,open('zero.json','w')); print(len(rq),len(json.dumps(rq)),e1,t0,e2,p0,e3)
