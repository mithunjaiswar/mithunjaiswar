"""Download Raw_Data rows of given hisaab weeks into <D>/sheet.csv (same layout validate.py expects).
Usage: python3 fetch_sheet.py <D> <token.json> <header_template_csv> week1 week2 ..."""
import sys, json, csv, time, requests
D, TOKEN, TEMPLATE, WEEKS = sys.argv[1], sys.argv[2], sys.argv[3], set(sys.argv[4:])
SID = '1wkebsPPLwXnRYAuvRV_fhMGQLRxv6JwH-cYlaIEBjRw'
API = f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/'
tok = json.load(open(TOKEN))
r = requests.post(tok['token_uri'], data=dict(client_id=tok['client_id'], client_secret=tok['client_secret'],
                                              refresh_token=tok['refresh_token'], grant_type='refresh_token'), timeout=60)
H = {'Authorization': 'Bearer ' + r.json()['access_token']}
def get(rng):
    for a in range(6):
        resp = requests.get(API + rng, headers=H, params={'valueRenderOption': 'FORMATTED_VALUE'}, timeout=300)
        if resp.status_code in (429, 500, 502, 503): time.sleep(2 ** a * 2); continue
        resp.raise_for_status(); return resp.json().get('values', [])
colA = get("'Raw_Data'!A1:A")
idx = [i + 1 for i, v in enumerate(colA) if v and v[0] in WEEKS]
lo, hi = min(idx), max(idx)
print('rows', lo, hi, len(idx), flush=True)
hdr = next(csv.reader(open(TEMPLATE)))
out = csv.writer(open(f'{D}/sheet.csv', 'w')); out.writerow(hdr)
n = 0
for start in range(lo, hi + 1, 10000):
    end = min(start + 9999, hi)
    for k, row in enumerate(get(f"'Raw_Data'!A{start}:BV{end}")):
        if row and row[0] in WEEKS:
            out.writerow([start + k] + row + [''] * (74 - len(row))); n += 1
print('written', n)
