import json
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS=open('../dash/dash_sid.txt').read().strip()
d=json.load(open('../dash/summary_cmp.json'))
v=call('GET',f"{API}/{DS}/values/'Summary'!A1:N86")['values']
d['new2']=v; json.dump(d,open('../dash/summary_cmp.json','w'))
for i in [12,13,15,16,18,21,22,25,27,28,29,30,46,47,48,49]:
    print(i+1,d['old'][i][1],'| OLD',d['old'][i][2:10],'\n      NEW',v[i][2:10])
