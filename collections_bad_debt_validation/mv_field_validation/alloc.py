from mv import *
import pickle
a=pd.DataFrame(pickle.load(open('alloc.pkl','rb')),columns=['emp','al','ja','car','loc','rt','aid'])
a['al']=pd.to_datetime(a.al,format='mixed'); a['ja']=pd.to_datetime(a.ja.replace('',None),format='mixed')
grp={k:list(zip(v.al,v.ja)) for k,v in a.groupby('emp')}
def dayset(e):
    S=set()
    for al,ja in grp.get(e,[]):
        st=al.normalize(); en=(ja if pd.notna(ja) else pd.Timestamp('2026-10-08')).normalize()
        for d in pd.date_range(max(st,pd.Timestamp('2026-09-14')), min(en,pd.Timestamp('2026-10-08'))): S.add(d)
    return S
