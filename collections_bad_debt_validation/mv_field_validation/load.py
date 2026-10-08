import json, os, pickle
TR='/root/.claude/projects/-home-user-mithunjaiswar/975ddfa8-2a6b-560b-8c6b-202af90fa71a/tool-results/mcp-Everest_Reporting_DB-run_read_only_query-'
def rows(ids):
    out=[]
    for i in ids:
        s=json.load(open(f'{TR}{i}.txt'))['result']
        for l in s.split('\n'):
            if l.startswith('| ') and not l.startswith('| r '):
                out.append(l[2:].rstrip().rstrip('|').rstrip().split('|'))
    return out
def save(name, ids):
    r=rows(ids); pickle.dump(r, open(f'{name}.pkl','wb')); print(name, len(r)); return r
