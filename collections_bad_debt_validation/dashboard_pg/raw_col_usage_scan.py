import json,re,sys,collections
def col2n(c):
    n=0
    for ch in c: n=n*26+ord(ch)-64
    return n
pat=re.compile(r"Raw_Data'?!\$?([A-Z]{1,2})\$?\d*(?::\$?([A-Z]{1,2})\$?\d*)?")
res=collections.defaultdict(lambda: collections.Counter())
for f in sys.argv[1:]:
    d=json.load(open(f))
    for s in d['content']['sheets']:
        t=s['properties']['title']
        for dd in s.get('data',[]):
            for r in dd.get('rowData',[]) or []:
                for v in r.get('values',[]) or []:
                    fm=v.get('userEnteredValue',{}).get('formulaValue')
                    if not fm or 'Raw_Data' not in fm: continue
                    for a,b in pat.findall(fm):
                        a1=col2n(a); b1=col2n(b) if b else a1
                        for n in range(a1,b1+1): res[n][t]+=1
out={n:dict(c) for n,c in res.items()}
json.dump(out,open('usage_'+str(len(sys.argv))+'.json','w'))
for n in sorted(out): print(n, out[n])
