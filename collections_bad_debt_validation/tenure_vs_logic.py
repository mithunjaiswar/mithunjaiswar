import json,pandas as pd,numpy as np
s=json.load(open('/root/.claude/projects/-home-user-mithunjaiswar/975ddfa8-2a6b-560b-8c6b-202af90fa71a/tool-results/mcp-Everest_Reporting_DB-run_read_only_query-1791453941799.txt'))['result']
rows=[[x.strip() for x in l.strip('| ').split('|')] for l in s.split('\n') if l.startswith('| 2026')]
db=pd.DataFrame(rows,columns=['week','emp','mv','logic','upd'])
for c in ['mv','logic']: db[c]=pd.to_numeric(db[c],errors='coerce')
db['emp']=db.emp.str.upper()
print('MV last_updated range', db.upd.min(), db.upd.max())
sh=pd.concat([pd.read_csv('run3/sheet.csv',usecols=['hisaab_week','partner_et_id','tenure_days'],dtype=str),
   pd.read_csv('run2/sheet.csv',usecols=['hisaab_week','partner_et_id','tenure_days'],dtype=str).query("hisaab_week=='2026-10-05'")])
sh['emp']=sh.partner_et_id.str.strip().str.upper(); sh['sheet']=pd.to_numeric(sh.tenure_days.str.replace(',',''),errors='coerce')
m=db.merge(sh[['hisaab_week','emp','sheet']].rename(columns={'hisaab_week':'week'}),on=['week','emp'],how='left')
m.to_pickle('run2/ten_logic.pkl')
def stats(d):
    a=d.abs()
    return [ (a==0).mean()*100, (a<=1).mean()*100, int((a!=0).sum()), d[d!=0].mean(), d[d!=0].median(),
             int(((a>=1)&(a<=3)).sum()), int(((a>=4)&(a<=7)).sum()), int(((a>=8)&(a<=30)).sum()), int((a>30).sum())]
cols=['exact%','±1%','wrong','avg_diff','median_diff','1-3d','4-7d','8-30d','>30d']
res=[]
for w,g in list(m.groupby('week'))+[('ALL',m)]:
    gs=g[g.sheet.notna()]
    res.append([w,len(g),'MV']+stats(g.mv-g.logic)); res.append([w,len(gs),'Sheet']+stats(gs.sheet-gs.logic))
r=pd.DataFrame(res,columns=['week','n','side']+cols).round(1)
pd.set_option('display.width',250); print(r.to_string(index=False))
r.to_pickle('run2/ten_logic_summary.pkl')
