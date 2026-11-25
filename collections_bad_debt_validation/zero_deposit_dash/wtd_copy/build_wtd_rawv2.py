import json
D='"—"'
def A(x): return f'=ARRAYFORMULA(IF($H$4,{x},{D}))'
def C(*extra): return 'COUNTIFS(K_RIT'+''.join(','+e for e in extra)+')'
def S(rng,*extra): return f'SUMIFS({rng},K_RIT'+''.join(','+e for e in extra)+')'
BH,BI,BO,BG,M='raw_v2!$BH$4:$BH','raw_v2!$BI$4:$BI','raw_v2!$BO$4:$BO','raw_v2!$BG$4:$BG','raw_v2!$M$4:$M'
CH,CI,CP,AD,AE,AH,AN,AU='raw_v2!$CH$4:$CH','raw_v2!$CI$4:$CI','raw_v2!$CP$4:$CP','raw_v2!$AD$4:$AD','raw_v2!$AE$4:$AE','raw_v2!$AH$4:$AH','raw_v2!$AN$4:$AN','raw_v2!$AU$4:$AU'
ch_this=[f'{BO},">="&$D$4',f'{BO},"<="&$B$4',f'{M},"Inactive"']
ch_prev=[f'{BO},">="&($D$4-7)',f'{BO},"<="&($D$4-1)',f'{M},"Inactive"']
def opn(*pre): return '('+C(*pre,f'{BI},"NaN"')+'+'+C(*pre,f'{BI},">"&$B$4')+')'
act='L_OD,">-1E+15"'
R={
9:("Total drivers in the cohort",A(C())),
10:("Active drivers at cutoff (live OS that day)",A(C(act))),
11:("    Active drivers with negative live OS",A(C('L_OD,"<0"'))),
12:("    Active drivers under recovery",A(C(act,f'{BG},"Open"'))),
13:("Drivers churned in the period (jama this week, no car now)",A(C(*ch_this))),
14:("    Churn · had a car recovery case",A(C(*ch_this,f'{BG},"<>No"'))),
15:("    Churn · no recovery case (voluntary)",A(C(*ch_this,f'{BG},"No"'))),
16:("    Churn · other or unclear",A('B13:I13-B14:I14-B15:I15')),
17:("Drivers churned last week · still on this list",A(C(*ch_prev))),
18:("    Prior churn · had a car recovery case",A(C(*ch_prev,f'{BG},"<>No"'))),
19:("    Prior churn · no recovery case (voluntary)",A(C(*ch_prev,f'{BG},"No"'))),
20:("    Prior churn · other or unclear",A('B17:I17-B18:I18-B19:I19')),
21:("Total net dues",A('B23:I23+B24:I24')),
22:("    Info: last week closing credits (already inside opening OS, not deducted)",A(S(AD,f'{AD},">0"'))),
23:("    Net opening OS (Monday hisaab)",A('-'+S(AE,f'{CP},1'))),
24:("New dues from posted rent · WTD",A('-'+S(AU))),
25:("Total gross received · WTD",A(S(AH))),
26:("Gross received applied to opening dues",A(S(AN))),
27:("Gross received beyond opening allocation",A('IF(B25:I25-B26:I26>0,B25:I25-B26:I26,0)')),
28:("Collection %",A('IF(B21:I21>0,B25:I25/B21:I21,"—")')),
29:("Outstanding dues at cutoff",A('-'+'SUMIFS(L_OD,K_RIT,L_OD,"<0")')),
31:("Drivers with dues (negative OS)",A(C('L_OD,"<0"'))),
32:("% of drivers owing more than ₹1,000",A('IF(B9:I9>0,'+C('L_OD,"<-1000"')+'/B9:I9,"—")')),
33:("Drivers without dues (zero or credit)",A(C('L_OD,">=0"'))),
34:("Drivers with OS unavailable",A('B9:I9-'+C(act))),
35:("Drivers with dues · attempted (week)",A(C('L_OD,"<0"',f'{CH},">0"'))),
36:("Drivers with dues · reached (week)",A(C('L_OD,"<0"',f'{CI},">0"'))),
37:("Drivers with dues · not attempted (week)",A(C('L_OD,"<0"',f'{CH},0'))),
38:("Drivers with dues · not reached (week)",A(C('L_OD,"<0"',f'{CI},0'))),
39:("Outstanding on drivers not reached",A('-SUMIFS(L_OD,K_RIT,L_OD,"<0",'+CI+',0)')),
41:("Drivers under recovery at cutoff",A(opn(f'{BH},"<="&$B$4'))),
42:("Recovery cases raised · WTD (pilots)",A(C(f'{BH},">="&$D$4',f'{BH},"<="&$B$4'))),
43:("Open recovery cases at cutoff (pilots)",A('B41:I41')),
44:("Recovery cases raised this week and still open",A(opn(f'{BH},">="&$D$4',f'{BH},"<="&$B$4'))),
45:("Recovery cases closed · WTD",A(C(f'{BI},">="&$D$4',f'{BI},"<="&$B$4'))),
46:("    Closed · pilot still has the car",A(C(f'{BI},">="&$D$4',f'{BI},"<="&$B$4',f'{M},"Active"'))),
47:("    Closed · car taken back (no car now)",A(C(f'{BI},">="&$D$4',f'{BI},"<="&$B$4',f'{M},"Inactive"'))),
50:("Active drivers above deposit · recovery not initiated",A(C('O_WD,1',act,f'{BG},"<>Open"'))),
51:("Active drivers above deposit",A(C('O_WD,1',act))),
52:("Open recovery cases aged >2 days",A(opn(f'{BH},"<="&($B$4-3)'))),
53:("Drivers with dues unpaid >2 days",A(C('L_OD,"<0"','D_NP,">2"'))),
54:("Outstanding on drivers unpaid >2 days",A('-SUMIFS(L_OD,K_RIT,L_OD,"<0",D_NP,">2")')),
56:("Probable bad debt if active drivers leave",A('SUMIFS(B_DV,K_RIT,B_DT,1)')),
57:("Active drivers exposed",A(C('B_DT,1'))),
58:("Bad debt carried by exited drivers",A('SUMIFS(B_DV,K_RIT,B_DT,2)')),
59:("Exited drivers carrying bad debt",A(C('B_DT,2'))),
60:("Bad debt from drivers churned in the period",A('SUMIFS(B_DV,K_RIT,B_DT,2,'+','.join(ch_this)+')')),
}
blank=['']*7
rows={}
for r in range(9,61):
    if r in R: rows[r]=[R[r][0],R[r][1]]+blank
rows[48]=['    (Cancelled / failed split not in raw_v2)','—']+blank
rows[49]=['','']+blank
json.dump(rows,open('rows.json','w'),ensure_ascii=False)
tot=sum(len(v[1]) for v in rows.values()); print('chars',tot)
TOK={
'K_RIT':'raw_v2!$A$4:$A,$D$4,raw_v2!$F$4:$F,IF($B$7:$I$7="Pan India","*",$B$7:$I$7),raw_v2!$G$4:$G,IF($D$3="All products","*",$D$3),raw_v2!$AB$4:$AB,IF($F$3="All deposits","*",$F$3),raw_v2!$BE$4:$BE,IF($B$5="All habits","*",$B$5),raw_v2!$H$4:$H,IF($D$5="All tenures","*",$D$5),raw_v2!$M$4:$M,IF($F$5="All drivers","*",$F$5)',
'L_OD':'INDEX(raw_v2!$CQ$4:$CW,0,$F$4)','O_WD':'INDEX(raw_v2!$DZ$4:$EF,0,$F$4)','D_NP':'INDEX(raw_v2!$FP$4:$FV,0,$F$4)',
'B_DT':'INDEX(raw_v2!$EU$4:$FA,0,$F$4)','B_DV':'INDEX(raw_v2!$FB$4:$FH,0,$F$4)'}
json.dump(TOK,open('tok.json','w'))
