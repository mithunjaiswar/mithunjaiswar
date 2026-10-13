# Compare Summary (Delhi NCR) and WBR before vs after the MV rebuild, plus vs the reference Sheet.
import json,re,time
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS=open('../dash/dash_sid.txt').read().strip(); REF='1wkebsPPLwXnRYAuvRV_fhMGQLRxv6JwH-cYlaIEBjRw'
B=json.load(open('../dash/before_snapshot.json'))
call('POST',f'{API}/{DS}/values:batchUpdate',json={'valueInputOption':'RAW','data':[{'range':"'Summary'!B2",'values':[['Delhi NCR']]}]})
time.sleep(20)
SA=call('GET',f"{API}/{DS}/values/'Summary'!A1:J86")['values']
call('POST',f'{API}/{DS}/values:batchUpdate',json={'valueInputOption':'RAW','data':[{'range':"'Summary'!B2",'values':[['*']]}]})
WA=call('GET',f"{API}/{DS}/values/'WBR'!A1:H486")['values']
SR=call('GET',f"{API}/{REF}/values/'Summary'!A1:J86")['values']
WR=call('GET',f"{API}/{REF}/values/'WBR View'!A1:H486")['values']
json.dump({'S':SA,'W':WA},open('../dash/after_snapshot.json','w'))
g=lambda R,i,j: (R[i][j] if i<len(R) and j<len(R[i]) else '')
def num(s):
    s=str(s).replace(',','').replace(' hrs','').replace(' ','')
    m=re.fullmatch(r'(-?[\d.]+)(K|%)?',s)
    if not m: return None
    v=float(m.group(1)); return v*1000 if m.group(2)=='K' else (v/100 if m.group(2)=='%' else v)
out=[]
def run(tag,Bf,Af,Rf,hr,lo,hi,namecol):
    cb={g(Bf,hr,j):j for j in range(lo,hi)}; ca={g(Af,hr,j):j for j in range(lo,hi)}; cr={g(Rf,hr,j):j for j in range(lo,hi)}
    weeks=[w for w in ca if w in cb and w in cr and w]
    for i in range(hr+1,max(len(Bf),len(Af))):
        nm=(g(Af,i,namecol) or g(Af,i,namecol-1)).strip()
        for w in weeks:
            b,a,r=num(g(Bf,i,cb[w])),num(g(Af,i,ca[w])),num(g(Rf,i,cr[w]))
            if b is None or a is None or r is None: continue
            eb,ea=abs(b-r),abs(a-r)
            if abs(a-b)>max(abs(b)*0.005,0.5 if abs(b)>=20 else 0.0005):
                out.append((tag,i+1,nm,w,r,b,a,'closer' if ea<eb-1e-9 else ('further' if ea>eb+1e-9 else 'same')))
    return weeks
print('S weeks',run('Summary',B['S'],SA,SR,7,2,10,1)); print('W weeks',run('WBR',B['W'],WA,WR,5,2,6,1))
json.dump(out,open('../dash/before_after.json','w'))
from collections import Counter
print(Counter((o[0],o[7]) for o in out))
for o in out[:400]:
    if o[0]=='Summary': print(o)
