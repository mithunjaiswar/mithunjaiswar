import json
D='"—"'
def W(x): return f'=IF($H$4,{x},{D})'
def C(*extra): return 'COUNTIFS(KC_RIT'+''.join(','+e for e in extra)+')'
def S(rng,*extra): return f'SUMIFS({rng},KC_RIT'+''.join(','+e for e in extra)+')'
def SP(block,first,cmp): return f'SUMPRODUCT(KM_ASK*IFERROR(raw_v2!${block[0]}$4:${block[1]}*1,0)*(COLUMN(raw_v2!${block[0]}$4:${block[1]}$4)-COLUMN(raw_v2!${block[0]}$4)+1{cmp}$F$4))'
BH,BI,BO,BG,M='raw_v2!$BH$4:$BH','raw_v2!$BI$4:$BI','raw_v2!$BO$4:$BO','raw_v2!$BG$4:$BG','raw_v2!$M$4:$M'
CH,CI,CP,AD,AE='raw_v2!$CH$4:$CH','raw_v2!$CI$4:$CI','raw_v2!$CP$4:$CP','raw_v2!$AD$4:$AD','raw_v2!$AE$4:$AE'
ch_this=[f'{BO},">="&$D$4',f'{BO},"<="&$B$4',f'{M},"Inactive"']
ch_prev=[f'{BO},">="&($D$4-7)',f'{BO},"<="&($D$4-1)',f'{M},"Inactive"']
def opn(*pre): return '('+C(*pre,f'{BI},"NaN"')+'+'+C(*pre,f'{BI},">"&$B$4')+')'
act='L_OD,">-1E+15"'
R={9:C(),10:C(act),11:C('L_OD,"<0"'),12:C(act,f'{BG},"Open"'),13:C(*ch_this),14:C(*ch_this,f'{BG},"<>No"'),15:C(*ch_this,f'{BG},"No"'),
16:'B13-B14-B15',17:C(*ch_prev),18:C(*ch_prev,f'{BI},">="&($D$4-7)'),19:'B17-B18',
21:'B23+B24',22:S(AD,f'{AD},">0"'),23:'-'+S(AE,f'{CP},1'),
24:SP(('FI','FO'),1,'<'),25:SP(('CX','DD'),1,'<='),26:SP(('DE','DK'),1,'<='),
27:'MAX(0,B25-B26)',28:'IF(B21>0,B25/B21,"—")',29:'-SUMIFS(L_OD,KC_RIT,L_OD,"<0")',
31:C('L_OD,"<0"'),32:'IF(B9>0,'+C('L_OD,"<-1000"')+'/B9,"—")',33:C('L_OD,">=0"'),34:'B9-'+C(act),
35:C('L_OD,"<0"',f'{CH},">0"'),36:C('L_OD,"<0"',f'{CI},">0"'),37:C('L_OD,"<0"',f'{CH},0'),38:C('L_OD,"<0"',f'{CI},0'),
39:'-SUMIFS(L_OD,KC_RIT,L_OD,"<0",'+CI+',0)',
41:opn(f'{BH},"<="&$B$4'),42:C(f'{BH},">="&$D$4',f'{BH},"<="&$B$4'),43:'B41',44:opn(f'{BH},">="&$D$4',f'{BH},"<="&$B$4'),
45:C(f'{BI},">="&$D$4',f'{BI},"<="&$B$4'),46:C(f'{BI},">="&$D$4',f'{BI},"<="&$B$4',f'{M},"Active"'),47:C(f'{BI},">="&$D$4',f'{BI},"<="&$B$4',f'{M},"Inactive"'),
50:C('O_WD,1',act,f'{BG},"<>Open"'),51:C('O_WD,1',act),52:opn(f'{BH},"<="&($B$4-3)'),53:C('L_OD,"<0"','D_NP,">2"'),
54:'-SUMIFS(L_OD,KC_RIT,L_OD,"<0",D_NP,">2")',56:'SUMIFS(B_DV,KC_RIT,B_DT,1)',57:C('B_DT,1'),58:'SUMIFS(B_DV,KC_RIT,B_DT,2)',59:C('B_DT,2'),
60:'SUMIFS(B_DV,KC_RIT,B_DT,2,'+','.join(ch_this)+')'}
col=[]
for r in range(9,61):
    if r in R: col.append([W(R[r])])
    elif r==20: col.append(['—'])
    elif r==48: col.append(['—'])
    elif r==49: col.append([''])
    else: col.append([None])
json.dump(col,open('colB.json','w'),ensure_ascii=False)
print(json.dumps(col,ensure_ascii=False))
