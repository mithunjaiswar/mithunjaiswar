import json
def table(fn):
    t=json.load(open(fn))['result'].split('\n')
    rows=[l for l in t if l.startswith('|')]
    hdr=[x.strip() for x in rows[0].strip('|').split('|')]
    out=[]
    for l in rows[1:]:
        out.append(dict(zip(hdr,[x.strip() for x in l.strip('|').split('|')])))
    return out
