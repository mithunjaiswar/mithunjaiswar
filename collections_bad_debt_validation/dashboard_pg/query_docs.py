# Create / update 3 Google Docs (one per dashboard SQL query) next to the dashboard; ids -> ../dash/query_doc_ids.json
import sys, os, json, requests
exec(open('write_tab.py').read().split('MAN,REM=pickle.load')[0])
DS = open('../dash/dash_sid.txt').read().strip()
SQL = open(sys.argv[1]).read().rstrip().split('\n')
cut = lambda key: max(i for i, l in enumerate(SQL) if key in l and l.startswith('-- QUERY')) - 1
b2, b3 = cut('QUERY 2'), cut('QUERY 3')
Q = [('Collections Dashboard - Query 1 - Raw_Data', SQL[:b2]), ('Collections Dashboard - Query 2 - Deposit_Raw', SQL[b2:b3]),
     ('Collections Dashboard - Query 3 - Recovery_Raw', SQL[b3:])]
f = '../dash/query_doc_ids.json'; ids = json.load(open(f)) if os.path.exists(f) else {}
parent = requests.get(f'https://www.googleapis.com/drive/v3/files/{DS}', headers=H, params={'fields': 'parents', 'supportsAllDrives': 'true'}).json().get('parents', [])
for name, body in Q:
    txt = '\n'.join(body).strip() + '\n'
    if name in ids:
        x = requests.patch(f'https://www.googleapis.com/upload/drive/v3/files/{ids[name]}?uploadType=media&supportsAllDrives=true',
                           headers={**H, 'Content-Type': 'text/plain'}, data=txt.encode(), timeout=120)
    else:
        bd = 'xxBOUNDARYxx'; meta = {'name': name, 'mimeType': 'application/vnd.google-apps.document', 'parents': parent}
        data = (f'--{bd}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n--{bd}\r\n'
                f'Content-Type: text/plain; charset=UTF-8\r\n\r\n{txt}\r\n--{bd}--').encode()
        x = requests.post('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true',
                          headers={**H, 'Content-Type': f'multipart/related; boundary={bd}'}, data=data, timeout=120)
        if x.ok: ids[name] = x.json()['id']
    if not x.ok: raise SystemExit(x.text[:300])
    print(name, f'https://docs.google.com/document/d/{ids[name]}/edit')
json.dump(ids, open(f, 'w'), indent=1)
