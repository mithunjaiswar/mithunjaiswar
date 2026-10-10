import json,re
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS=open('../dash/dash_sid.txt').read().strip()
MAP={'A':'A','D':'B','E':'M','F':'D','H':'F','I':'P','N':'X','O':'R','P':'T','Q':'U','R':'V','S':'W','T':'X','U':'Q',
     'AA':'Y','AC':'AB','AD':'K','AF':'Z','AH':'AO','AL':'AN','AN':'J','AO':'H','AW':'AK','AY':'AM','BC':'L','BD':'F','AQ':'O'}
def remap(f):
    def rep(mo):
        a,b=mo.group(2),mo.group(4)
        if a not in MAP: raise Exception('unmapped '+a+' in '+f[:120])
        return f"Raw_Data!{mo.group(1)}{MAP[a]}:{mo.group(3)}{MAP[b]}"
    return re.sub(r'Raw_Data!(\$?)([A-Z]{1,2}):(\$?)([A-Z]{1,2})',rep,f)
FILT=lambda c: f'Raw_Data!$D:$D,$B$2,Raw_Data!$A:$A,{c}$8,Raw_Data!$F:$F,$B$5,Raw_Data!$J:$J,$B$6,Raw_Data!$H:$H,$B$4,Raw_Data!$K:$K,$B$7'
FILT2=lambda c: f'Raw_Data!$D:$D,$B$2,Raw_Data!$A:$A,{c}$8,Raw_Data!$F:$F,$B$5,Raw_Data!$H:$H,$B$4'
def FX(c):  # FILTER() condition for percentiles
    return (f'((Raw_Data!$A$2:$A={c}$8))*((Raw_Data!$D$2:$D=$B$2)+($B$2="*"))*((Raw_Data!$F$2:$F=$B$5)+($B$5="*"))*((Raw_Data!$H$2:$H=$B$4)+($B$4="*"))*(Raw_Data!$AW$2:$AW>0)')
def summary_override(r,c):
    F=FILT(c); F2=FILT2(c)
    S={
    26:f'=IFERROR(COUNTIFS({F},Raw_Data!$Y:$Y,">0"), "-")',
    32:f'=IFERROR(COUNTIFS({F2},Raw_Data!$K:$K,"Active",Raw_Data!$M:$M,"<0",Raw_Data!$AJ:$AJ,0), "-")',
    33:f'=IFERROR(COUNTIFS({F2},Raw_Data!$K:$K,"Active",Raw_Data!$AJ:$AJ,">0",Raw_Data!$AJ:$AJ,"<500"), "-")',
    34:f'=IFERROR(COUNTIFS({F2},Raw_Data!$K:$K,"Active",Raw_Data!$AJ:$AJ,">=500",Raw_Data!$AJ:$AJ,"<2000"), "-")',
    35:f'=IFERROR(COUNTIFS({F2},Raw_Data!$K:$K,"Active",Raw_Data!$AJ:$AJ,">=2000",Raw_Data!$AJ:$AJ,"<5000"), "-")',
    36:f'=IFERROR(COUNTIFS({F2},Raw_Data!$K:$K,"Active",Raw_Data!$AJ:$AJ,">=5000",Raw_Data!$AJ:$AJ,"<10000"), "-")',
    37:f'=IFERROR(COUNTIFS({F2},Raw_Data!$K:$K,"Active",Raw_Data!$AJ:$AJ,">=10000",Raw_Data!$AJ:$AJ,"<30000"), "-")',
    38:f'=IFERROR(COUNTIFS({F2},Raw_Data!$K:$K,"Active",Raw_Data!$AJ:$AJ,">=30000",Raw_Data!$AJ:$AJ,"<50000"), "-")',
    39:f'=IFERROR(COUNTIFS({F2},Raw_Data!$K:$K,"Active",Raw_Data!$AJ:$AJ,">=50000"), "-")',
    46:f'=IFERROR(SUMIFS(Raw_Data!$AL:$AL,Raw_Data!$D:$D,$B$2,Raw_Data!$F:$F,$B$5,Raw_Data!$H:$H,$B$4,Raw_Data!$A:$A,"<="&{c}$8,Raw_Data!$A:$A,">"&({c}$8-105)), "-")',
    51:f'=IFERROR(AVERAGEIFS(Raw_Data!$AF:$AF,{F2},Raw_Data!$AF:$AF,">0"), "-")',
    53:f'=IFERROR(SUMIFS(Raw_Data!$AR:$AR,{F2}), "-")',
    54:f'=IFERROR(SUMIFS(Raw_Data!$AS:$AS,{F2}), "-")',
    55:f'=IFERROR(SUMIFS(Raw_Data!$AU:$AU,{F2}), "-")',
    56:f'=IFERROR(SUMIFS(Raw_Data!$AT:$AT,{F2}), "-")',
    57:f'=IFERROR(SUMIFS(Raw_Data!$AV:$AV,{F2}), "-")',
    58:f'=IFERROR(ROUND(AVERAGEIFS(Raw_Data!$AW:$AW,{F2},Raw_Data!$AW:$AW,">0"),1)&" hrs", "-")',
    59:f'=IFERROR(ROUND(PERCENTILE(FILTER(Raw_Data!$AW$2:$AW,{FX(c)}),0.9),1)&" hrs", "-")',
    60:f'=IFERROR(ROUND(PERCENTILE(FILTER(Raw_Data!$AW$2:$AW,{FX(c)}),0.5),1)&" hrs", "-")',
    61:f'=IFERROR(ROUND(PERCENTILE(FILTER(Raw_Data!$AW$2:$AW,{FX(c)}),0.25),1)&" hrs", "-")',
    62:f'=IFERROR({c}56/COUNTUNIQUEIFS(Raw_Data!$AX:$AX,{F2},Raw_Data!$AX:$AX,"<>"), "-")',
    63:f'=IFERROR(SUMIFS(Raw_Data!$M:$M,{F2},Raw_Data!$AV:$AV,">0"), "-")',
    64:f'=IFERROR(COUNTIFS({F},Raw_Data!$AN:$AN,"Critical_Risk"), "-")',
    70:f'=IFERROR(COUNTUNIQUEIFS(Raw_Data!$B:$B,{F},Raw_Data!$Z:$Z,"Excellent"), "-")',
    }
    for k,(lo,hi) in zip(range(75,81),[(None,0),(0,2000),(2000,5000),(5000,10000),(10000,20000),(20000,None)]):
        for base,col_ in ((k,'AF'),(k+6,'AI')):
            crit=(f'Raw_Data!${col_}:${col_},"<=0"' if lo is None else
                  f'Raw_Data!${col_}:${col_},">{lo}"'+(f',Raw_Data!${col_}:${col_},"<={hi}"' if hi else ''))
            S[base]=f'=IFERROR(COUNTIFS({F2},{crit}), "-")'
    for k in range(65,70): S[k]='N/A - no PG source (see Validation)'
    return S.get(r)
m=call('GET',f'{API}/{DS}',params={'fields':'sheets.properties'})
P={s['properties']['title']:s['properties']['sheetId'] for s in m['sheets']}
# ---------- WBR
W=call('GET',f"{API}/{DS}/values/'WBR View'!A1:BA486",params={'valueRenderOption':'FORMULA'})['values']
outw=[]
for i,r in enumerate(W):
    row=[]
    for j,c in enumerate(r):
        if isinstance(c,str) and c.startswith('='):
            if 'collections_data' in c:
                c=c.replace('MAX(collections_data!$K$2:$K)','MAX(Raw_Data!$AY$2:$AY)')
            c=remap(c)
            c=c.replace('#REF!,$C$2','Raw_Data!$L:$L,$C$2')
            c=re.sub(r'#REF!,(\$?[A-Z]{1,2}\$5)',r'Raw_Data!$F:$F,\1',c)
            if 'NonFunnel_BadDebt_Collected' in c:
                c=re.sub(r'NonFunnel_BadDebt_Collected!\$F:\$F,NonFunnel_BadDebt_Collected!\$A:\$A,([^,]+),NonFunnel_BadDebt_Collected!\$C:\$C,([^,]+),NonFunnel_BadDebt_Collected!\$D:\$D,([^,\)]+)',
                         r'Raw_Data!$AL:$AL,Raw_Data!$A:$A,\1,Raw_Data!$D:$D,\2,Raw_Data!$F:$F,\3',c)
            c=re.sub(r'(,Raw_Data!\$AN:\$AN,"<>[^"]*")+',',Raw_Data!$AN:$AN,"Critical_Risk"',c)
            if '#REF' in c: raise Exception(f'REF left r{i+1} c{j}: {c[:150]}')
            # funnel bad debt collected: AM already = paid after bad debt -> drop same-row AK<0 condition
            c=re.sub(r'(SUMIFS\(Raw_Data!\$AM:\$AM[^)]*?),Raw_Data!\$AK:\$AK,"<0"',r'\1',c)
            if 'NonFunnel' in c or 'collections_data' in c: raise Exception(f'leftover WBR r{i+1} c{j}: {c[:120]}')
        row.append(c)
    outw.append(row)
for i in range(0,len(outw),100):
    call('PUT',f"{API}/{DS}/values/'WBR View'!A{i+1}",params={'valueInputOption':'USER_ENTERED'},json={'values':outw[i:i+100]})
print('WBR done')
