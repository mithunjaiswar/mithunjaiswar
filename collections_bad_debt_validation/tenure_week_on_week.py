import json,pandas as pd
s=json.load(open('/root/.claude/projects/-home-user-mithunjaiswar/975ddfa8-2a6b-560b-8c6b-202af90fa71a/tool-results/mcp-Everest_Reporting_DB-run_read_only_query-1791453255355.txt'))['result']
rows=[l.strip('| ').split('|') for l in s.split('\n') if l.startswith('| 2026')]
db=pd.DataFrame([[x.strip() for x in r] for r in rows],columns=['week','emp','mv','dw_start','dw_end','hw_mon','hw_sun'])
for c in ['mv','dw_start','dw_end','hw_mon','hw_sun']: db[c]=pd.to_numeric(db[c],errors='coerce')
db['emp']=db.emp.str.upper()
sh=pd.concat([pd.read_csv('run3/sheet.csv',usecols=['hisaab_week','partner_et_id','tenure_days'],dtype=str),
   pd.read_csv('run2/sheet.csv',usecols=['hisaab_week','partner_et_id','tenure_days'],dtype=str).query("hisaab_week=='2026-10-05'")])
sh['emp']=sh.partner_et_id.str.strip().str.upper(); sh['sheet']=pd.to_numeric(sh.tenure_days.str.replace(',',''),errors='coerce')
m=db.merge(sh[['hisaab_week','emp','sheet']].rename(columns={'hisaab_week':'week'}),on=['week','emp'])
print('db rows',len(db),'joined',len(m))
out=[]
for w,g in m.groupby('week'):
    r={'week':w,'driven_week':str((pd.Timestamp(w)-pd.Timedelta(days=7)).date()),'n':len(g)}
    r['MV=Sheet']=(g.mv==g.sheet).mean()
    for ref in ['dw_start','dw_end','hw_sun']:
        r[f'Sheet={ref}']=(g.sheet==g[ref]).mean(); r[f'MV={ref}']=(g.mv==g[ref]).mean()
    # best offset for sheet relative to dw_end
    d=(g.sheet-g.dw_end); r['sheet_offset_mode']=d.mode().iloc[0]; r['share_at_mode']=(d==d.mode().iloc[0]).mean()
    out.append(r)
o=pd.DataFrame(out); pd.set_option('display.width',250)
print(o.round(3).to_string(index=False))
m.to_pickle('run2/ten_wow.pkl')
