import json,collections
exec(open('val/write_tab.py').read().split('MAN,REM=pickle.load')[0])
REF='1wkebsPPLwXnRYAuvRV_fhMGQLRxv6JwH-cYlaIEBjRw'
F=json.load(open('dash/ref_raw_cols.json'))
D=json.load(open('dash/raw_final.json')); h=D[0]; ix={c:i for i,c in enumerate(h)}
MV={(r[0],r[1].upper()):r for r in D[1:]}
TR='/root/.claude/projects/-home-user-mithunjaiswar/975ddfa8-2a6b-560b-8c6b-202af90fa71a/tool-results/mcp-Everest_Reporting_DB-run_read_only_query-1791623301163.txt'
K={}
for l in json.load(open(TR))['result'].split('\n'):
    l=l.strip()
    if l.startswith('| 2026-'):
        v=l[2:].rstrip('|').strip().split('~'); K[(v[0],v[1])]=v[2:]
def idx(w,e):
    for i in range(len(F['A'])):
        if str(F['A'][i])[:10]==w and str(F['D'][i]).strip().upper()==e: return i
def row(i,cols): 
    r=call('GET',f"{API}/{REF}/values:batchGet",params={'ranges':[f"'Raw_Data'!{c}{i+2}" for c in cols],'valueRenderOption':'UNFORMATTED_VALUE'})
    return {c:(v.get('values',[['']])[0][0] if v.get('values') else '') for c,v in zip(cols,r['valueRanges'])}
out={}
i=idx('2026-08-17','ETN77730'); out['risk']=dict(sheet=row(i,['AA','AH','AF','AG','AI','AK','AL']),mv=K[('2026-08-17','ETN77730')])
for e in ['ETN84045','ETN090225']:
    out['bd_'+e]=[(w,MV[(w,e)][ix['bad_debt_amount']]) for w in sorted({k[0] for k in MV}) if (w,e) in MV]
    out['bd_sheet_'+e]=[(str(F['A'][j])[:10],F['AW'][j]) for j in range(len(F['A'])) if str(F['D'][j]).strip().upper()==e]
e='ETN41666'; out['cf']=dict(mv=[(w,MV[(w,e)][ix['prev_carryforward_os']],MV[(w,e)][ix['total_os']],MV[(w,e)][ix['total_collected_amount_in_week']]) for w in sorted({k[0] for k in MV}) if (w,e) in MV],
    sheet=[(str(F['A'][j])[:10],F['E'][j],F['I'][j],F['AP'][j],F['AQ'][j]) for j in range(len(F['A'])) if str(F['D'][j]).strip().upper()==e])
e='ETN01260'; out['funnel']=dict(mv=[(w,MV[(w,e)][ix['bad_debt_amount']],MV[(w,e)][ix['active_inactive_flag']],MV[(w,e)][ix['total_collected_100_pct']],MV[(w,e)][ix['deposit_to_rent_100pct']]) for w in sorted({k[0] for k in MV}) if (w,e) in MV])
i=idx('2026-09-07','ETN78958'); m=MV[('2026-09-07','ETN78958')]
out['rec']=dict(sheet=row(i,['E','U','AV','AB']),mv=(m[ix['total_os']],m[ix['total_collected_100_pct']],m[ix['week_end_deposit']]))
i=idx('2026-08-31','ETN69666'); m=MV[('2026-08-31','ETN69666')]
out['dep']=dict(sheet=row(i,['BB','BH']),mv=(m[ix['week_start_deposit']],m[ix['week_end_deposit']]))
# habit: sheet AF vs payment_habit_week
W={'2026-08-17','2026-08-24','2026-08-31','2026-09-07','2026-09-14','2026-09-21','2026-09-28'}
t=b=0
for j in range(len(F['A'])):
    w=str(F['A'][j])[:10]; e=str(F['D'][j]).strip().upper()
    if w in W and (w,e) in K:
        t+=1; b+= str(F['AF'][j]).lower()!=K[(w,e)][1].lower()
out['habit_week_match']=(t,b)
out['np_ex']=[(str(F['A'][j])[:10],F['AA'][j],MV[(str(F['A'][j])[:10],'ETN65068')][ix['partners_not_paid_2_weeks']]) for j in range(len(F['A'])) if str(F['D'][j]).strip().upper()=='ETN65068' and (str(F['A'][j])[:10],'ETN65068') in MV]
json.dump(out,open('dash/ex_detail.json','w'),default=str)
for k,v in out.items(): print(k,':',v)
