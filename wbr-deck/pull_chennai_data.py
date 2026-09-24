"""Chennai Weekly City Review deck — same template/format as the BLR deck
(build_all.py), with every table pulled from its source sheet filtered to
Chennai. Sources with no accessible Chennai data are listed per section on a
'not available' slide instead of being silently dropped."""
import json, re, time, httplib2
from google_auth_httplib2 import AuthorizedHttp

SP = "/tmp/claude-0/-home-user-mithunjaiswar/a3071d57-7e4f-504e-99c9-482796a8dddc/scratchpad/"

# ---- reuse BLR helpers, re-labelled for Chennai ----
src = open(SP + "build_all.py").read().split("pres = slides.presentations().get")[0]
src = src.replace("BLR Weekly City Review", "CHN Weekly City Review")
src = src.replace("Bangalore data only", "Chennai data only")
src = src.replace('"Source: BLR WBR doc"', "SRC_LABEL[0]")
src = src.replace('        up = "(up" in body\n        down = "(down" in body',
                  '        up = MOVE.get((lbl, body)) == "up"\n        down = MOVE.get((lbl, body)) == "down"')
src = src.replace('combined_body = "  ".join(f"{label}: {body}" for label, body in wins[:2])',
                  'combined_body = " ".join(f"{label}: {body}" for label, body in wins[:2])')
src = src.replace('cx0 + 0.15, cy, cw - 0.3, 0.8, combined_body', 'cx0 + 0.15, cy, cw - 0.3, 1.1, combined_body')
src = src.replace('content_h += (0.18 if (concerns or neutral) else 0) + 0.3 + 0.85',
                  'content_h += (0.18 if (concerns or neutral) else 0) + 0.3 + 1.15')
MOVE = {}
SRC_LABEL = ["Source"]
exec(src)


def _is_plan(label):
    return "plan" in label.lower()


def _secs(n):
    n = int(round(abs(n)))
    h, rem = divmod(n, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def _fmt_like(sample, n):
    """Format a computed number the way the source cells look."""
    if ":" in sample:
        return _secs(n)
    if "%" in sample:
        return f"{n:.1f}%"
    if abs(n) >= 1000:
        return f"{n:,.0f}"
    return f"{n:.1f}".rstrip("0").rstrip(".") if n != int(n) else f"{int(n)}"


def compute_insight(section_title, table_title, norm):
    headers, rows = norm["headers"], norm["rows"]
    no_heat = norm.get("no_heat", False)
    wk = headers[-1] if len(headers) > 1 else ""
    MOVE.clear()

    if no_heat:
        cand = [r for r in rows if not _is_plan(r[0]) and parse_num(r[-1]) is not None]
        cand.sort(key=lambda r: parse_num(r[-1]), reverse=True)
        if not cand:
            return f"{table_title}: current snapshot for Chennai.", [], ""
        top = cand[0]
        headline = f"{top[0]} is the largest line in {table_title} at {top[-1].strip()} ({wk})."
        calls = [(r[0], f"{r[-1].strip()} under {wk}; {r[1].strip()} under {headers[1]}.") for r in cand[:3]]
        low = cand[-1]
        read = f"Read: {top[0]} leads at {top[-1].strip()} and {low[0]} is lowest at {low[-1].strip()} ({wk})." if low is not top else ""
        return headline, calls, read

    plan = {}
    for r in rows:
        if r[0].endswith(" — Plan"):
            plan[r[0][:-7]] = r[1:]

    def fmt_gap(sample, g):
        if ":" in sample:
            return _secs(g)
        if "%" in sample:
            return f"{abs(g):.1f} pts"
        return _fmt_like(sample, abs(g))

    movers = []
    for r in rows:
        if _is_plan(r[0]):
            continue
        vals = r[1:]
        nums = [parse_num(v) for v in vals]
        idx = [i for i, n in enumerate(nums) if n is not None]
        if len(idx) < 2:
            continue
        i1, i0 = idx[-1], idx[-2]
        last, prev = nums[i1], nums[i0]
        s_last, s_prev = vals[i1].strip(), vals[i0].strip()
        inv = compute_row_invert(r[0], table_title)
        diff = last - prev
        up = diff > 0
        if ":" in s_last:
            chg = _secs(diff)
        elif "%" in s_last:
            chg = f"{abs(diff):.1f} pts"
        elif prev > 0 and last >= 0 and prev >= 10 and abs(diff) / prev * 100 >= 0.5:
            chg = f"{abs(diff) / prev * 100:.0f}%"
        else:
            chg = _fmt_like(s_last, abs(diff))
        wow = "flat week on week" if diff == 0 else f"{'up' if up else 'down'} {chg} week on week from {s_prev}"

        # plan gap (when the table carries a Plan row for this metric)
        pv = None
        if r[0] in plan and i1 < len(plan[r[0]]):
            pv = parse_num(plan[r[0]][i1])
        if pv:
            gap = last - pv
            behind = gap > 0 if inv else gap < 0
            p_str = plan[r[0]][i1].strip()
            body = (f"{s_last} in the week of {wk} against a {p_str} plan — "
                    f"{fmt_gap(s_last, gap)} {'short of' if behind else 'ahead of'} plan; {wow}.")
            score = abs(gap) / abs(pv) + (1 if behind else 0)
            bad = behind
        else:
            if diff == 0:
                continue
            window = [nums[i] for i in idx]
            note = ""
            if len(window) >= 3:
                if last == max(window):
                    note = f" — highest of the last {len(window)} weeks"
                elif last == min(window):
                    note = f" — lowest of the last {len(window)} weeks"
                else:
                    note = f"; {len(window)}-week average {_fmt_like(s_last, sum(window) / len(window))}"
            body = f"{s_last} in the week of {wk}, {wow}{note}."
            score = abs(diff) / (abs(prev) if prev else (abs(last) or 1))
            bad = up if inv else not up
            gap = None
        movers.append((score, r[0], body, bad, s_last, chg, up, pv, gap))

    if not movers:
        return f"{table_title}: no week-on-week change in the week of {wk}.", [], ""
    movers.sort(key=lambda m: (m[3], m[0]), reverse=True)   # concerns first, then biggest
    calls = []
    for m in movers[:3]:
        inv = compute_row_invert(m[1], table_title)
        calls.append((m[1], m[2]))
        MOVE[(m[1], m[2])] = ("up" if inv else "down") if m[3] else ("down" if inv else "up")

    top = movers[0]
    _, lab, _, bad, s_last, chg, up, pv, gap = top
    if pv:
        headline = (f"{lab} at {s_last} in the week of {wk}, "
                    f"{fmt_gap(s_last, gap)} {'short of' if bad else 'ahead of'} plan.")
    else:
        headline = f"{lab} {'rose' if up else 'fell'} to {s_last} in the week of {wk}, {'up' if up else 'down'} {chg} week on week."
    planned = [m for m in movers if m[7]]
    if planned:
        behind = [m for m in planned if m[3]]
        read = f"Read: {len(behind)} of {len(planned)} metrics with a plan are behind it in the week of {wk}"
        read += f"; widest gap is {behind[0][1]}." if behind else "; all are on or ahead of plan."
    else:
        worse = sum(1 for m in movers if m[3])
        read = (f"Read: {len(movers) - worse} of {len(movers)} moving metrics improved and {worse} worsened "
                f"in the week of {wk}; " + (f"biggest flag is {movers[0][1]}." if worse else f"largest improvement is {movers[0][1]}."))
    return headline, calls, read


http2 = AuthorizedHttp(creds, http=httplib2.Http(timeout=180))
from googleapiclient.discovery import build as gbuild
sheets = gbuild("sheets", "v4", http=http2)
slides = gbuild("slides", "v1", http=AuthorizedHttp(creds, http=httplib2.Http(timeout=300)))

CITY = "chennai"
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
WEEK_CUTOFF = (9, 14)   # last complete week label: 14-Sep
DAY_CUTOFF = (9, 20)    # last complete day inside that week
NWEEKS = 6


def pdate(h):
    h = (h or "").strip().lower().replace(",", "")
    m = re.match(r"^(\d{1,2})[\-\s]([a-z]{3})", h)
    if m and m.group(2) in MONTHS:
        return (MONTHS[m.group(2)], int(m.group(1)))
    m = re.match(r"^([a-z]{3})[\-\s](\d{1,2})$", h)
    if m and m.group(1) in MONTHS:
        return (MONTHS[m.group(1)], int(m.group(2)))
    m = re.match(r"^(\d{1,2})/(\d{1,2})/\d{2,4}$", h)
    if m:
        return (int(m.group(2)), int(m.group(1)))
    return None


def first_run(cols_with_dates):
    """Only the first contiguous run of date columns — many dashboards put
    a second (weekly/monthly) view to the right of the first one."""
    run = []
    for j, d in cols_with_dates:
        if run and j != run[-1][0] + 1:
            break
        run.append((j, d))
    return run


def pick_dates(cols_with_dates, cutoff, n=NWEEKS):
    ok = [(j, d) for j, d in first_run(cols_with_dates) if d <= cutoff]
    return ok[-n:]


def vals_of(sid, tab, rng="A1:BZ500"):
    return sheets.spreadsheets().values().get(spreadsheetId=sid, range=f"'{tab}'!{rng}").execute().get("values", [])


def cell(r, j):
    return r[j] if j < len(r) else ""


EMPTYISH = {"", "-", "#n/a", "ytm", "0", "0%", "0.0%", "0.00%", "0.0", "0.00", "#div/0!", "#ref!"}


def is_empty_row(vals):
    return all((v or "").strip().lower() in EMPTYISH for v in vals)


def chunk(title, header, rows, n=8):
    rows = [r for r in rows if not is_empty_row(r[1:])]
    names = {r[0] for r in rows}
    rows = [r for r in rows if not (r[0].endswith(" — Plan") and r[0][:-7] not in names)]
    if not rows:
        return []
    parts = [rows[i:i + n] for i in range(0, len(rows), n)]
    out = []
    for k, p in enumerate(parts, 1):
        t = title if len(parts) == 1 else f"{title} ({k}/{len(parts)})"
        out.append((t, [header] + p))
    return out


# ---------- extractors ----------
def ex_metric_city(vals, title, cutoff=WEEK_CUTOFF, n=NWEEKS):
    """Layout: a header row with 'Metric' | 'City' | dates…; one row per
    (metric, city). Handles several Metric/City panels side by side."""
    tables = []
    for h, row in enumerate(vals[:12]):
        pairs = [(j, j + 1) for j in range(len(row) - 1)
                 if row[j].strip().lower().startswith("metric") and row[j + 1].strip().lower() == "city"]
        if not pairs:
            continue
        for pi, (mc, cc) in enumerate(pairs):
            end = pairs[pi + 1][0] if pi + 1 < len(pairs) else len(row)
            dcols = [(j, pdate(row[j])) for j in range(cc + 1, end) if pdate(row[j])]
            dcols = pick_dates(dcols, cutoff, n)
            hdr = ["Metric"] + [row[j].strip() for j, _ in dcols]
            rows, seen = [], set()
            for r in vals[h + 1:]:
                if cell(r, cc).strip().lower() == CITY:
                    lab = cell(r, mc).strip() or "-"
                    if lab in seen:
                        continue
                    seen.add(lab)
                    rows.append([lab] + [cell(r, j) for j, _ in dcols])
            tables += chunk(title if len(pairs) == 1 else f"{title} — panel {pi + 1}", hdr, rows)
        break
    return tables


def ex_metric_city_categories(vals, title, keep=6):
    """Same layout but columns are categories, not dates (snapshot)."""
    for h, row in enumerate(vals[:12]):
        if len(row) > 1 and row[0].strip().lower().startswith("metric") and row[1].strip().lower() == "city":
            cats = [(j, re.sub(r"\s+", " ", row[j]).strip()) for j in range(2, len(row)) if row[j].strip()][:keep]
            hdr = ["Metric"] + [c for _, c in cats]
            rows = [[cell(r, 0).strip()] + [cell(r, j) for j, _ in cats] for r in vals[h + 1:] if cell(r, 1).strip().lower() == CITY]
            return chunk(title, hdr, rows)
    return []


def ex_block_rows(vals, title, city_col=0, cutoff=WEEK_CUTOFF, n=NWEEKS):
    """Layout: a block title row (title | dates…) followed by one row per
    city (city | values…). Emits one Chennai row per block, labelled by
    the block title."""
    rows, header, cur = [], None, None
    for r in vals:
        if len(r) > 2 and pdate(cell(r, 1)) and cell(r, 0).strip().lower() not in ("*", CITY):
            cur = (cell(r, 0).strip(), [(j, pdate(r[j])) for j in range(1, len(r)) if pdate(r[j])])
            continue
        if cur and cell(r, city_col).strip().lower() == CITY:
            dcols = pick_dates(cur[1], cutoff, n)
            if header is None:
                header = ["Metric"] + [f"{d[1]}-{list(MONTHS)[d[0]-1].title()}" for _, d in dcols]
            rows.append([cur[0] or "-"] + [cell(r, j) for j, _ in dcols])
    return chunk(title, header, rows) if rows else []


def ex_panels(vals, title, cutoff=WEEK_CUTOFF, n=NWEEKS):
    """Layout: side-by-side city panels; a panel header cell 'Chennai' with
    dates to its right, then metric rows under it in the same column."""
    tables = []
    for h, r in enumerate(vals):
        for c in range(len(r)):
            if r[c].strip().lower() == CITY and pdate(cell(r, c + 1)):
                dcols = [(j, pdate(r[j])) for j in range(c + 1, len(r)) if pdate(r[j])]
                # stop at first gap in the date run
                run = []
                for j, d in dcols:
                    if run and j != run[-1][0] + 1:
                        break
                    run.append((j, d))
                run = pick_dates(run, cutoff, n)
                hdr = ["Metric"] + [r[j].strip() for j, _ in run]
                rows = []
                for rr in vals[h + 1:]:
                    lab = cell(rr, c).strip()
                    if not lab:
                        break
                    rows.append([lab] + [cell(rr, j) for j, _ in run])
                tables += chunk(title, hdr, rows)
    return tables


def ex_parking(vals, title):
    hdr_row = vals[3]
    c1 = next(j for j in range(len(hdr_row)) if hdr_row[j].strip().lower() == CITY)
    c2 = next((j for j in range(c1 + 1, len(hdr_row)) if hdr_row[j].strip().lower() == CITY), None)
    rows = []
    for r in vals[4:]:
        lab = cell(r, 0).strip()
        if not lab:
            continue
        v1 = cell(r, c1)
        v2 = cell(r, c2) if c2 else ""
        if (v1 or "").strip() in ("", "-") and (v2 or "").strip() in ("", "-"):
            continue
        rows.append([lab, v1, v2])
    hdr = ["Metric", "Chennai — count", "Chennai — %"]
    return chunk(title, hdr, rows)


def ex_group_block(vals, title, start_label):
    """Collections Deck_CityView: 'Chennai' group row, header row, rows."""
    for i, r in enumerate(vals):
        if cell(r, 0).strip().lower() == CITY:
            grp = [r[0]] + [c for c in r[1:] if c.strip()]
            body = []
            for rr in vals[i + 1:]:
                if not rr or not any(c.strip() for c in rr):
                    break
                body.append(rr)
            return [(title, [grp] + body)]
    return []


def ex_core_wbr(vals, sections, title_map=None):
    """Chennai SSOT CORE_WBR: section in col A, metric in col B, weeks."""
    hdr = vals[1]
    dcols = [(j, pdate(hdr[j])) for j in range(2, 119) if pdate(hdr[j])]
    dcols = [(j, d) for j, d in dcols if d <= WEEK_CUTOFF][-NWEEKS:]
    header = ["Metric"] + [hdr[j].strip() for j, _ in dcols]
    out = {}
    sec, prev = None, None
    for r in vals[2:]:
        if cell(r, 0).strip():
            sec = cell(r, 0).strip().replace("\n", " ")
            prev = None
        lab = cell(r, 1).strip()
        if not lab or lab in ("*", "#N/A"):
            continue
        shown = f"{prev} — {lab}" if lab.lower().startswith("plan") and prev else lab
        if not lab.lower().startswith("plan"):
            prev = lab
        out.setdefault(sec, []).append([shown] + [cell(r, j) for j, _ in dcols])
    tables = {}
    for s in sections:
        key = next((k for k in out if k.lower().startswith(s.lower())), None)
        if key:
            tables[s] = chunk((title_map or {}).get(s, key), header, out[key])
    return tables


def ex_agent_weekly(vals, title, top=8):
    """[Chennai Collections] Agent Tracking APR_Weekly_Dash: group row,
    'Agent Name' header, several week blocks separated by 'Avg.'."""
    grp = [c for c in vals[0][1:] if c.strip()]
    hdr = vals[1]
    blocks, cur = [], []
    for j in range(1, len(hdr)):
        d = pdate(hdr[j])
        if d:
            cur.append((j, d))
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    tables = []
    for bi, b in enumerate(blocks):
        b = pick_dates(b, WEEK_CUTOFF, NWEEKS)
        header = ["Agent"] + [hdr[j].strip() for j, _ in b]
        rows = [[cell(r, 0).strip()] + [cell(r, j) for j, _ in b] for r in vals[2:] if cell(r, 0).strip()]
        last = lambda r: parse_num(r[-1]) or 0
        rows = sorted([r for r in rows if not is_empty_row(r[1:])], key=last, reverse=True)[:top]
        g = grp[bi] if bi < len(grp) else f"Block {bi + 1}"
        tables += chunk(f"{title} — {g} (top {top} agents)", header, rows)
    return tables


# ---------- sources ----------
def sid_for(file_prefix, tab):
    scan = json.load(open(SP + "sources_scan.json"))
    for ln in scan["links"]:
        if ln.get("file", "").startswith(file_prefix) and ln.get("tab") == tab:
            return ln["id"], ln.get("gid")
    raise KeyError(file_prefix)


def url(sid, gid=None):
    return f"https://docs.google.com/spreadsheets/d/{sid}/edit" + (f"#gid={gid}" if gid else "")


def src(file_prefix, tab):
    sid, gid = sid_for(file_prefix, tab)
    return sid, tab, url(sid, gid), file_prefix.strip()


print("pulling Chennai data from sources…")
T = {}   # section -> list of (title, raw, source_url, source_name)

SSOT_ID = "1bgcN-GJlk1nEOBji_-49nkUGi5xLK5LQ30gSbGvyQ8Q"
ssot_vals = vals_of(SSOT_ID, "CORE_ WBR [make copy for changes]", "A1:DZ262")
ssot = ex_core_wbr(ssot_vals, [
    "EoW Cars", "Utilisation", "Uber Active Vehicle", "Growth", "Channel Performance",
    "Attrition & Rejoin", "Referrals", "Total Chennal Conversion", "Workshop ThroughPut",
    "DSA Revisit", "Quality-TA", "Car Status", "RTA%", "Recovery %", "Repair Pendency", "Service Pendency", "FSE", "Vendor",
])
SSOT_URL = url(SSOT_ID, 1489414580)
SSOT_NAME = "Chennai SSOT Scorecards (CORE_WBR)"


def add(section, tables, surl, sname):
    for t, raw in tables:
        T.setdefault(section, []).append((t, raw, surl, sname))


def add_ssot(section, key):
    add(section, ssot.get(key, []), SSOT_URL, SSOT_NAME)


NA = {}  # section -> list of (table, reason)


def na(section, table, reason):
    NA.setdefault(section, []).append((table, reason))


# 1 City Overview
add_ssot("City Overview", "EoW Cars")

# 2 Workshop Overview
add_ssot("Workshop Overview", "Workshop ThroughPut")
add_ssot("Workshop Overview", "DSA Revisit")
add_ssot("Workshop Overview", "Quality-TA")
add_ssot("Workshop Overview", "RTA%")
sid, tab, u, n = src("Driver Wanted Sticker", "Dashboard")
add("Workshop Overview", ex_metric_city_categories(vals_of(sid, tab), "Driver Wanted Sticker Installation"), u, n)
if not ssot.get("Repair Pendency"):
    na("Workshop Overview", "Repair Pendency (agingwise / categorywise)", "blank ('-') for Chennai in SSOT CORE_WBR")
if not ssot.get("Service Pendency"):
    na("Workshop Overview", "Service Pendency", "#N/A for Chennai in SSOT CORE_WBR")
for t, why in [
    ("EFG Review", "source 'EFG Review-Bangalore' is a Bangalore-only file"),
    ("Service Due Vehicle Plan Wise", "source sheet not shared with this account (403)"),
    ("Urgent Service", "source sheet not shared with this account (403)"),
    ("City Wise Weekly Budget Tracking", "'EFG - Pan India Budget New' City_Wise_Tracking has no Chennai rows"),
    ("Revisit", "source 'BLR Revisit_Analysis' is Bangalore-only (DSA revisit buckets shown from SSOT instead)"),
    ("Washing Report", "source sheet not shared with this account (403)"),
    ("Fitness Cars Status / Vehicles Movement", "'VM reports' has no Chennai data"),
    ("Saturday Reco Report", "source sheet not shared with this account (403)"),
    ("Funnel View / Petrol Consumption", "source sheet not shared with this account (403)"),
    ("BLR_KEY_Master — CNG", "Bangalore key-master sheet, no Chennai equivalent found"),
]:
    na("Workshop Overview", t, why)

# 3 VMT Overview
add_ssot("VMT Overview", "Car Status")
sid, tab, u, n = src("Parking _Reco", "City_Wise_Summary")
add("VMT Overview", ex_parking(vals_of(sid, tab), "Parking Reco — City Wise Summary (19-Sep, CNG)"), u, n)
na("VMT Overview", "Vehicles Movement Weekly-Wise Report", "'VM reports' VM Weekly Review has no Chennai data")

# 4 EIP
sid, tab, u, n = src("Central EIP Dashboard", "Dash for Deck")
add("EIP", ex_metric_city(vals_of(sid, tab), "EIP — Chennai"), u, n)

# 5 DTO
sid, tab, u, n = src("DTO Dashboard", "Dash_For_Deck")
add("DTO", ex_panels(vals_of(sid, tab), "Drive To Own — Product Overview"), u, n)

# 6 Own Now
sid, tab, u, n = src("Central Own Now Dashboard", "City_Wise_Performance_Dashboard_WOW")
add("Own Now", ex_block_rows(vals_of(sid, tab), "OWN NOW — Product Overview"), u, n)
sid, tab, u, n = src("Central Existing Calling", "Deck_View")
add("Own Now", ex_panels(vals_of(sid, tab), "Input Metrics — Existing Calling"), u, n)

# 7 Helpdesk / 8 Support
na("Helpdesk", "Help Desk Dash", "'Helpdesk Team Dash' Weekly_Dash has no Chennai data")
na("Support", "Weekly Trend / Issue Health Summary", "'Support Performance Dashboard | Zoho' has a city dropdown set to Bangalore; not changed (shared sheet)")
na("Support", "Input Metrics — Support", "'Support | APR zoho + exotel' Weekly publish Report has no Chennai data")

# 9 Collection
sid, tab, u, n = src("Everest | India Collections", "Deck_CityView")
add("Collection", ex_group_block(vals_of(sid, tab), "Collections — Chennai", "Chennai"), u, n)
CID = "192b4gADIm3KfvshyjeuEvP0DGgVgIPzGehe_uChnE4I"
add("Collection", ex_agent_weekly(vals_of(CID, "APR_Weekly_Dash", "A1:Z40"), "Input Metrics — Collection"),
    url(CID), "[Chennai Collections] Agent Tracking")

# 10 Car Recovery
add_ssot("Car Recovery", "Recovery %")
na("Car Recovery", "Car Recovery / Agent-Vendor-wise", "'Central Car Recovery Dash' city dropdown set to Pune (shared sheet, not changed); 'Car Recovery Tracker' has no readable Chennai data")

# 11 CNG Operations
add_ssot("CNG Operations", "Utilisation")
add_ssot("CNG Operations", "Uber Active Vehicle")

# 12 EV / 13 EV SSOT
na("EV Operations", "Car Utilization — EV", "'Car_Utilization [EV]' Dash_Final has no Chennai EV data")
na("EV SSOT Overview", "BLR_KEY_Master — EV", "Bangalore key-master sheet, no Chennai equivalent found")

# 14 On Boarding
add_ssot("On Boarding", "Growth")
na("On Boarding", "Onboarding — City deck / Agent Level OB", "'India Onboarding Dashboard' City_deck has no Chennai rows; agent-level sheet not shared (403)")

# 15 Vendor Channel
sid, tab, u, n = src("Central  Vendor", "City Review_Vendor")
add("Vendor Channel", ex_block_rows(vals_of(sid, tab), "Vendor — Daily View", cutoff=DAY_CUTOFF, n=6), u, n)
na("Vendor Channel", "Vendor Level", "source sheet not shared with this account (403)")

# 16 Rejoin and Resurrection
add_ssot("Rejoin and Resurrection", "Attrition & Rejoin")
sid, tab, u, n = src("Central Rejoining", "Copy of City_Wise [Weekly] 1")
add("Rejoin and Resurrection", ex_metric_city(vals_of(sid, tab), "Rejoin — TC Metrics"), u, n)
sid, tab, u, n = src("Central Resurrection", "City_Wise [Weekly]")
add("Rejoin and Resurrection", ex_metric_city(vals_of(sid, tab), "Resurrection — TC Metrics"), u, n)

# 17 Referral Channel
add_ssot("Referral Channel", "Referrals")
na("Referral Channel", "Referral Funnel / New Referral Dash", "'Referral Process - V2' city dropdown set to Pune (shared sheet, not changed)")

# 18 Perf Marketing
add_ssot("Perf Marketing", "Channel Performance")
sid, tab, u, n = src("Recruitment Channel Funnel", "Dash [% ToF]")
add("Perf Marketing", ex_metric_city(vals_of(sid, tab), "Funnel Perf_Marketing"), u, n)
sid, tab, u, n = src("Recruitment Channel Funnel", "Speed_Of_Funnel_Dash")
add("Perf Marketing", ex_metric_city(vals_of(sid, tab), "Speed of Funnel"), u, n)
sid, tab, u, n = src("Agent_Performance_Report_BI", "[WOW-Pan India]")
add("Perf Marketing", ex_metric_city(vals_of(sid, tab), "Agent Performance — Perf Marketing"), u, n)
sid, tab, u, n = src("Recruitment: Inbound Synopsis", "NBD RD [WEEKLY]")
add("Perf Marketing", ex_metric_city(vals_of(sid, tab), "Inbound Report — Perf Marketing"), u, n)
sid, tab, u, n = src("Outbound Efficiency Analysis", "Non_funnel_dash(%)")
add("Perf Marketing", ex_metric_city(vals_of(sid, tab), "Outbound Efficiency — Perf Marketing", cutoff=DAY_CUTOFF), u, n)
add_ssot("Perf Marketing", "Total Chennal Conversion")
na("Perf Marketing", "Allocation Split: Performance Marketing", "source sheet not shared with this account (403)")

ORDER = ["City Overview", "Workshop Overview", "VMT Overview", "EIP", "DTO", "Own Now", "Helpdesk", "Support",
         "Collection", "Car Recovery", "CNG Operations", "EV Operations", "EV SSOT Overview", "On Boarding",
         "Vendor Channel", "Rejoin and Resurrection", "Referral Channel", "Perf Marketing", "Discussion"]

summary = []
for s in ORDER:
    summary.append((s, len(T.get(s, [])), len(NA.get(s, []))))
    for t, raw, u, n in T.get(s, []):
        print(f"  [{s}] {t}: {len(raw) - 1} rows, cols={raw[0][:7] if raw else None}")
json.dump({"T": {k: [(t, raw, u, n) for t, raw, u, n in v] for k, v in T.items()}, "NA": NA}, open(SP + "chennai_tables.json", "w"), indent=1)
print("\nSECTION SUMMARY (tables, not-available):")
for s, a, b in summary:
    print(f"  {s}: {a} tables, {b} n/a")


# =====================================================================
# Build the Chennai deck
# =====================================================================
import sys
if "--build" not in sys.argv:
    sys.exit(0)

drive = gbuild("drive", "v3", http=AuthorizedHttp(creds, http=httplib2.Http(timeout=120)))
CPRES = json.load(open(SP + "chennai_deck.json"))["pres"]
default_slides = [s["objectId"] for s in slides.presentations().get(presentationId=CPRES, fields="slides.objectId").execute()["slides"]]
PFX = "c5"
print("rebuilding presentation", CPRES, "removing", len(default_slides), "old slides after")


def build_cover(page_id):
    reqs = [{"createSlide": {"objectId": page_id, "slideLayoutReference": {"predefinedLayout": "BLANK"}}}]
    add_rect(reqs, next_id(page_id, "rule"), page_id, 0.8, 2.55, 1.1, 0.06, BLACK, border=False)
    add_text(reqs, next_id(page_id, "t"), page_id, 0.8, 2.75, 11.7, 1.2, "CHN Weekly City Review", 34, True, BLACK)
    add_text(reqs, next_id(page_id, "s"), page_id, 0.8, 3.75, 11.7, 0.5, "Everest Fleet  ·  Chennai  ·  Strategy & Analytics", 16, False, GRAY_TEXT)
    add_text(reqs, next_id(page_id, "wk"), page_id, 0.8, 4.25, 11.7, 0.4, "Week ending 20 Sep 2026", 14, False, GRAY_TEXT)
    return reqs


def build_na_slide(page_id, section_title, items):
    reqs = [{"createSlide": {"objectId": page_id, "slideLayoutReference": {"predefinedLayout": "BLANK"}}}]
    add_text(reqs, next_id(page_id, "cat"), page_id, 0.4, 0.22, 12.5, 0.3, f"{section_title} - Not available for Chennai", 9, True, GRAY_TEXT)
    add_text(reqs, next_id(page_id, "hl"), page_id, 0.4, 0.5, 12.5, 0.85,
             f"{len(items)} {section_title} table(s) from the BLR deck have no accessible Chennai data yet.", 17, True, DARK)
    add_rect(reqs, next_id(page_id, "div"), page_id, 0.4, 1.42, 12.53, 0.025, DARK, border=False)
    add_text(reqs, next_id(page_id, "note"), page_id, 0.4, 1.5, 12.53, 0.4,
             "Listed so nothing is silently dropped — share the Chennai source / access and these slides get filled.", 10.5, False, GRAY_TEXT, valign="TOP")
    x0, y = 0.4, 2.05
    row_h = min(0.42, (6.95 - y) / (len(items) + 1))
    cols = [(4.2, "Table (as in BLR deck)"), (8.33, "Why it's missing for Chennai")]
    cx = x0
    for i, (w, lab) in enumerate(cols):
        add_rect(reqs, next_id(page_id, f"hc{i}"), page_id, cx, y, w, row_h, BLACK, border_color=WHITE)
        add_text(reqs, next_id(page_id, f"ht{i}"), page_id, cx + 0.08, y, w - 0.16, row_h, lab, 10, True, WHITE)
        cx += w
    ry = y + row_h
    for i, (t, why) in enumerate(items):
        bg = WHITE if i % 2 == 0 else LABEL_BG
        cx = x0
        for (w, _), val, bold in zip(cols, (t, why), (True, False)):
            add_rect(reqs, next_id(page_id, "c"), page_id, cx, ry, w, row_h, bg, border_color=WHITE)
            add_text(reqs, next_id(page_id, "t"), page_id, cx + 0.08, ry, w - 0.16, row_h, val, 9.5, bold, DARK)
            cx += w
        ry += row_h
    add_text(reqs, next_id(page_id, "ft"), page_id, 0.4, 7.15, 10.0, 0.28,
             "Everest Fleet  ·  CHN Weekly City Review  ·  Strategy & Analytics", 9, False, GRAY_TEXT)
    return reqs


reqs_all = build_cover(f"{PFX}cover")
order_ids = [f"{PFX}cover"]
seq = 0
for s in [o for o in ORDER if T.get(o) or o == "Discussion"]:
    seq += 1
    sid_ = f"{PFX}sc{seq:02d}"
    reqs_all += build_section_title_slide(sid_, s, None)
    order_ids.append(sid_)
    for j, (t, raw, surl, sname) in enumerate(T.get(s, [])):
        norm = normalize_table(raw, max_rows=8)
        pid = f"{PFX}tb{seq:02d}_{j:02d}"
        SRC_LABEL[0] = f"Source: {sname}"
        if norm:
            reqs_all += build_metrics_slide(pid, section_title=s, table_title=t, table=norm, source_url=surl, week_no=seq)
        else:
            reqs_all += build_fallback_slide(pid, s, t, raw, surl)
        order_ids.append(pid)
    if False and NA.get(s):
        pid = f"{PFX}na{seq:02d}"
        reqs_all += build_na_slide(pid, s, NA[s])
        order_ids.append(pid)

print("total requests:", len(reqs_all), "slides:", len(order_ids))
CHUNK = 400
for i in range(0, len(reqs_all), CHUNK):
    slides.presentations().batchUpdate(presentationId=CPRES, body={"requests": reqs_all[i:i + CHUNK]}).execute()
    print("submitted", min(i + CHUNK, len(reqs_all)), "/", len(reqs_all))
    time.sleep(1)

# delete the default blank slide, then pin order
slides.presentations().batchUpdate(presentationId=CPRES, body={"requests": [{"deleteObject": {"objectId": o}} for o in default_slides]}).execute()
cur = [s["objectId"] for s in slides.presentations().get(presentationId=CPRES, fields="slides.objectId").execute()["slides"]]
if cur != order_ids:
    print("reordering (ids differ):", len(cur), len(order_ids))
    slides.presentations().batchUpdate(presentationId=CPRES, body={"requests": [
        {"updateSlidesPosition": {"slideObjectIds": [o], "insertionIndex": i}} for i, o in enumerate(order_ids) if o in cur]}).execute()
json.dump({"pres": CPRES, "order": order_ids}, open(SP + "chennai_deck.json", "w"))
print("done:", f"https://docs.google.com/presentation/d/{CPRES}/edit")
