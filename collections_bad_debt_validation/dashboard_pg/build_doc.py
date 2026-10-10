import json,re
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
exec(open('doc_catalog.py').read())
DS=open('../dash/dash_sid.txt').read().strip()
D=json.load(open('../dash/doc_data.json')); OLD=json.load(open('../dash/summary_cmp.json'))['old']
SN=D['sum_new']; WN=D['wbr_new']; WR=D['wbr_ref']; FM=D['field_match']; N14=D['n14']
def num(s):
    s=str(s).replace(',','').replace(' hrs','').replace(' ','')
    m_=re.fullmatch(r'(-?[\d.]+)(K|%)?',s)
    if not m_: return None
    v=float(m_.group(1)); return v*1000 if m_.group(2)=='K' else (v/100 if m_.group(2)=='%' else v)
g=lambda R,i,j: (R[i][j] if i<len(R) and j<len(R[i]) else '')
def cmp(src,row):
    if src=='S': A,B,cols,lab=OLD,SN,range(2,9),'Aug17-Sep28 (Delhi NCR / Own Now)'
    else: A,B,cols,lab=WR,WN,range(2,6),'Sep14-Oct05 (all India, *)'
    i=row-1; pc=any('%' in g(A,i,j) for j in cols)
    so=sm=0; ok=c=0; seen=False
    for j in cols:
        a,b=g(A,i,j),g(B,i,j); x,y=num(a),num(b); c+=1
        if x is None or y is None: ok+=(str(a).strip()==str(b).strip()); continue
        seen=True; so+=x; sm+=y
        tol=max(abs(x)*0.02,0.0015 if pc else (1 if abs(x)>=20 else 0)); ok+=abs(y-x)<=tol+1e-9
    if not seen: return ('','','','',f'{ok}/{c}',lab,pc)
    if pc: so/=c; sm/=c
    d=sm-so; dp=(d/abs(so)) if so else ('' if d==0 else 'n/a (Sheet 0)')
    return (so,sm,d,dp,f'{ok}/{c}',lab,pc)
EXP={'S11':[19,20,21,22,23],'S17':[29,30,31],'S19':[33,34,35,36,37,38,39],'S21':[41,42],'S22':[43,44,45],'S24':[47,48],'S25':[49,50],
     'S33':[58,59,60,61],'S36':[64,65,66,67,68,69],'S37':[70,71,72,73,74],'S38':[75,76,77,78,79,80],'S39':[81,82,83,84,85,86],
     'W07':[86,97,108],'W08':[121,132,154],'W09':[165,187],'W10':[176,198],'W11':[211,222],'W12':[235,246],'W13':[259,270],'W14':[283,294,305],
     'W16':[329,340,352,363,375,386,398,409,421,432,444,455,467,478]}
FIELD={'S02':'total_collected_100_pct','S03':'total_os','S04':'total_collected_100_pct','S10':'total_collected_amount_in_week','S12':'total_os','S13':'total_collected_amount_in_week',
 'S14':'partners_not_paid_2_weeks','S15':'collection_till_wed','S17':'total_allocated_days','S21':'bad_debt_amount','S22':'bad_debt_amount','S23':'bad_debt_collected',
 'S26':'week_start_deposit','S37':'last_week_payment_habit','S38':'week_start_deposit','W02':'total_os','W03':'total_collected_100_pct','W04':'total_collected_100_pct',
 'W08':'bad_debt_amount','W10':'bad_debt_collected','W11':'prev_carryforward_os','W12':'total_allocated_days','W15':'total_os','W16':'total_os'}
INMV={OK:'Yes',BAD:'Yes - data incorrect',LOGIC:'Yes - logic to confirm',ADD:'No - added via join',DER:'Derived from MV columns',BIZ:'N/A (business input)',NOSRC:'No'}
rows=[]
for (iid,met,req,what,rc,src,st,calc,flt,jn,corr,ref) in C:
    subs=EXP.get(iid,[ref[1]])
    fm=FM.get(FIELD.get(iid,''),('',''))
    rec=f"{100-float(fm[0][:-1]):.1f}% ({fm[1]} of {N14:,} rows)" if fm[0].endswith('%') else ''
    for k,r in enumerate(subs):
        so,sm,d,dp,wm,lab,pc=cmp(ref[0],r)
        if ref[0]=='S': name=g(OLD,r-1,1).strip() if len(subs)>1 else met
        else: name=(g(WR,[x for x in range(r-1,0,-1) if g(WR,x-1,2)=='*' and g(WR,x-1,1) not in ('*','')][0]-1,1) if len(subs)>1 else met)
        if ref[0]=='W' and len(subs)>1:
            t=r-1
            while t>0 and not (g(WR,t,2)=='*' and g(WR,t,1) not in ('*','')): t-=1
            name=g(WR,t,1)
        rows.append([iid if k==0 else '',name,req,st,INMV[st],what if k==0 else '',rc,src,calc if k==0 else '',flt if k==0 else '',jn if k==0 else '',
                     so,sm,d,dp,wm,lab,rec,corr if k==0 else '',pc])
print('rows',len(rows))
json.dump(rows,open('../dash/doc_rows.json','w'))
