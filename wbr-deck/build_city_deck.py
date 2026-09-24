"""Chennai WBR deck in the approved house style (docs/wbr-deck-style.md).
Reads the Chennai tables pulled by build_chennai.py (chennai_tables.json)."""
import json, re, sys, time, httplib2
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build as gbuild
from google_auth_httplib2 import AuthorizedHttp

TOKEN_PATH = "/home/user/mithunjaiswar/google-workspace-access/token.json"
SP = "/tmp/claude-0/-home-user-mithunjaiswar/a3071d57-7e4f-504e-99c9-482796a8dddc/scratchpad/"
creds = Credentials.from_authorized_user_info(json.load(open(TOKEN_PATH)))
slides = gbuild("slides", "v1", http=AuthorizedHttp(creds, http=httplib2.Http(timeout=300)))
CPRES = json.load(open(SP + "chennai_deck.json"))["pres"]
PFX = sys.argv[1] if len(sys.argv) > 1 else "d1"

CITY = "Chennai"
WK, PWK = "14 Sep", "7 Sep"
FOOT = "Everest Fleet  ·  Chennai Weekly City Review  ·  Week starting 14 Sep ending on 20 Sep 2026  ·  Strategy & Planning"
FONT = "Helvetica Neue"
BLACK, WHITE = (0, 0, 0), (1, 1, 1)
GREY_TXT, DARK_TXT = (0.4, 0.4, 0.4), (0.251, 0.251, 0.251)
LIGHT = (0.949, 0.949, 0.949)
SECT = (0.851, 0.851, 0.851)
GREEN, RED = (0.18, 0.49, 0.196), (0.776, 0.157, 0.157)
OUTL = (0.741, 0.741, 0.741)
LINK = (0.067, 0.494, 0.702)
H_RED, H_AMB, H_GRN = (0.906, 0.522, 0.447), (0.973, 0.816, 0.553), (0.525, 0.757, 0.478)
T_GRN, T_RED = (0.851, 0.925, 0.839), (0.957, 0.780, 0.780)
EMU = 914400
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
CUTOFF = (9, 14)
NW = 6

# ---------------------------------------------------------------- data
D = json.load(open(SP + "chennai_tables.json"))


def pdate(h):
    h = (h or "").strip().lower().replace(",", "")
    m = re.match(r"^(\d{1,2})[\-\s]([a-z]{3})", h)
    if m and m.group(2) in MONTHS:
        return (MONTHS.index(m.group(2)) + 1, int(m.group(1)))
    m = re.match(r"^([a-z]{3})[\-\s](\d{1,2})$", h)
    if m and m.group(1) in MONTHS:
        return (MONTHS.index(m.group(1)) + 1, int(m.group(2)))
    return None


def wlabel(d):
    return f"{MONTHS[d[0]-1].title()} {d[1]}"


def dlabel(d):
    return f"{d[1]} {MONTHS[d[0]-1].title()}"


ROWS = {}   # (section, title, label, occ) -> {"vals": {date: text}, "next": key of following row}
SRC = {}    # (section, title) -> (url, name)
for sec, tabs in D["T"].items():
    merged = {}
    for t, raw, u, n in tabs:
        base = re.sub(r" \(\d+/\d+\)$", "", t)
        SRC[(sec, base)] = (u, n)
        if sec == "Collection" and base.startswith("Collections"):
            groups, hdr = raw[0], raw[1]
            for r in raw[2:]:
                prod = "All products" if r[0] == "*" else r[0]
                for g in range(1, len(groups)):
                    c0 = 1 + 5 * (g - 1)
                    vals = {pdate(hdr[c0 + k]): r[c0 + k] for k in range(4) if c0 + k < len(r)}
                    merged.setdefault(base, []).append((f"{groups[g].split(chr(10))[0].strip()} — {prod}", vals))
            continue
        hdr = raw[0]
        for r in raw[1:]:
            vals = {pdate(hdr[j]): r[j] for j in range(1, len(hdr)) if j < len(r) and pdate(hdr[j])}
            merged.setdefault(base, []).append((r[0], vals))
    for base, rows in merged.items():
        cnt = {}
        keys = []
        for lab, vals in rows:
            occ = cnt.get(lab, 0)
            cnt[lab] = occ + 1
            k = (sec, base, lab, occ)
            ROWS[k] = {"vals": vals}
            keys.append(k)
        for a, b in zip(keys, keys[1:]):
            ROWS[a]["next"] = b


def parse(v):
    """-> (number, kind) kind in pct/time/num, or (None, None)."""
    s = (v or "").strip()
    if not s or s.lower() in ("-", "–", "ytm", "#n/a", "na", "#div/0!", "#ref!"):
        return None, None
    m = re.match(r"^(-?)(\d+):(\d{2})(?::(\d{2}))?$", s)
    if m:
        sec = int(m.group(2)) * 3600 + int(m.group(3)) * 60 + int(m.group(4) or 0) if m.group(4) else int(m.group(2)) * 60 + int(m.group(3))
        return (-sec if m.group(1) else sec), "time"
    t = s.replace(",", "").replace("₹", "").strip()
    try:
        if t.endswith("%"):
            return float(t[:-1]), "pct"
        return float(t), "num"
    except ValueError:
        return None, None


def fmt_num(x, dec=None):
    if dec is None:
        dec = 0 if abs(x - round(x)) < 1e-9 else (1 if abs(x) >= 10 else 2)
    s = f"{abs(x):,.{dec}f}"
    return ("-" if x < 0 else "") + s


def fmt_cell(v):
    n, k = parse(v)
    if n is None:
        return "–"
    if k == "num":
        dec = len(v.split(".")[1]) if "." in v else 0
        return fmt_num(n, min(dec, 2))
    if k == "time":
        h, r = divmod(int(abs(n)), 3600)
        return f"{h}:{r // 60:02d}" if h else f"{r // 60}:{r % 60:02d}"
    return v.strip()


def fmt_time(sec, hm=False):
    sign = "-" if sec < 0 else "+"
    sec = abs(int(round(sec)))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{sign}{h}:{m:02d}" if hm else f"{sign}{m}:{s:02d}"


def fmt_delta(d, kind, hm=False):
    if kind == "pct":
        return f"{d:+.1f} pp"
    if kind == "time":
        return fmt_time(d, hm)
    return ("+" if d >= 0 else "") + fmt_num(d)


def R(sec, title, label, disp=None, pol=1, occ=0, plan="auto"):
    return dict(key=(sec, title, label, occ), disp=disp or label.strip(), pol=pol, plan=plan)


def plan_of(spec):
    k = spec["key"]
    if spec["plan"] is None:
        return None
    if spec["plan"] != "auto":
        return ROWS.get(spec["plan"])
    nk = ROWS[k].get("next")
    if nk and nk[2].startswith(k[2].strip() + " — Plan"):
        return ROWS[nk]
    return None


# ---------------------------------------------------------------- slide spec
SS = "Chennai SSOT Scorecards (CORE_WBR)"
EOW, UT, UB, CS = "EoW Cars", "Utilisation", "Uber Active Vehicle  (Daily Average)", "Car Status"
CO, VM, CN = "City Overview", "VMT Overview", "CNG Operations"
AR, RR = "Rejoin and Resurrection", "Attrition & Rejoin (Everest Logic)"
PM = "Perf Marketing"

DEPTS = [
    ("Business overview", None, [
        dict(fn="City", sub="Fleet, utilisation and realisation", owner="Vigneshwar Munuswamy",
             note="On Road Cars = cars on road at week end; Growth = week-on-week change in on-road cars. Uber utilisation is the daily average.",
             rows=[R(CO, EOW, "On Road Cars"), R(CO, EOW, "Total Cars"), R(CO, EOW, "Growth"),
                   R(CN, UT, "Utilisation"), R(CN, UT, "WagonR Util"), R(CN, UB, "Uber Daily Util"),
                   R(CN, UB, "WagonR Daily Util"), R(CN, UB, "Uber vs Everest util Delta", pol=0), R(VM, CS, "Alloted %")]),
        dict(fn="City", sub="Cars by product", owner="Vigneshwar Munuswamy",
             note="Week-end cars by product from the Chennai SSOT; Plan = weekly plan row in the same sheet.",
             rows=[R(CO, EOW, "EIP Cars"), R(CO, EOW, "EIP Growth"), R(CO, EOW, "D20 Cars"), R(CO, EOW, "D20 Growth"),
                   R(CO, EOW, "Own_Now cars"), R(CO, EOW, "Own_Now Growth"), R(CO, EOW, "Leasing Individual Cars"),
                   R(CO, EOW, "Individual Growth"), R(CO, EOW, "Salary cars", pol=0)]),
        dict(fn="City", sub="Attrition and rejoins", owner="Vigneshwar Munuswamy",
             note="Everest logic: attrition shown as negative counts, so a smaller negative is better. Net attrition = attrition + temp attrition − rejoins.",
             rows=[R(AR, RR, "Net Attrition %", pol=-1), R(AR, RR, "Net Attrition"), R(AR, RR, "Attrition + Temp Attrition"),
                   R(AR, RR, "Attrition + Temp Attrition %"), R(AR, RR, "Rejoins"), R(AR, RR, "Temp Rejoin"),
                   R(AR, RR, "Rejoins + Temp Rejoin")]),
    ]),
    ("Driver Operations", "Yamini A", [
        dict(fn="EIP", sub="Operations", owner="Yamini A",
             note="Plan = active cars as per the EIP supply plan. Partner bands = unique EIP partners by fleet size.",
             rows=[R("EIP", "EIP — Chennai", "EIP Week Ending Active Cars", "EIP active cars (week end)",
                     plan=("EIP", "EIP — Chennai", "Active Cars as per Supply Plan", 0)),
                   R("EIP", "EIP — Chennai", "Active EIP_Partners", "Active EIP partners"),
                   R("EIP", "EIP — Chennai", "EIP Cars add-on"), R("EIP", "EIP — Chennai", "EIP Cars drop-off", pol=-1),
                   R("EIP", "EIP — Chennai", "EIP Cars Net Add Ons"), R("EIP", "EIP — Chennai", "New EIP's"),
                   R("EIP", "EIP — Chennai", "EIP_attrition", "EIP attrition", pol=-1),
                   R("EIP", "EIP — Chennai", "Unique EIP Partners (>=20 Cars)"),
                   R("EIP", "EIP — Chennai", "Unique EIP Partners (10-19 Cars)"),
                   R("EIP", "EIP — Chennai", "Collections Till Wednesday %"),
                   R("EIP", "EIP — Chennai", "Collections Till Sunday %")]),
        dict(fn="D2O", sub="Operations", owner="Vigneshwar Munuswamy",
             note="Drive To Own product view. Downtime cars = D2O cars not on road in the week.",
             rows=[R("DTO", "Drive To Own — Product Overview", "DTO Active Cars"),
                   R("DTO", "Drive To Own — Product Overview", "DTO Active Pilots"),
                   R("DTO", "Drive To Own — Product Overview", "DTO Allocation Count"),
                   R("DTO", "Drive To Own — Product Overview", "Net Allocation"),
                   R("DTO", "Drive To Own — Product Overview", "New Joins"),
                   R("DTO", "Drive To Own — Product Overview", "Net Attrition", pol=-1),
                   R("DTO", "Drive To Own — Product Overview", "Net Attiriton %", pol=-1),
                   R("DTO", "Drive To Own — Product Overview", "Collections Till Sunday %"),
                   R("DTO", "Drive To Own — Product Overview", "Bad Debts %", pol=-1),
                   R("DTO", "Drive To Own — Product Overview", "Car recovery pending > 30 days", pol=-1),
                   R("DTO", "Drive To Own — Product Overview", "% of Downtime", pol=-1)]),
        dict(fn="Own Now", sub="Operations", owner="R Sarathy",
             note="Own Now product view. OEPH = earnings per hour; TPV = trips per vehicle.",
             rows=[R("Own Now", "OWN NOW — Product Overview", "Own Now Active cars"),
                   R("Own Now", "OWN NOW — Product Overview", "Total ON (Own Now) Allocations"),
                   R("Own Now", "OWN NOW — Product Overview", "ON New joins"),
                   R("Own Now", "OWN NOW — Product Overview", "ON Rejoins"),
                   R("Own Now", "OWN NOW — Product Overview", "Own Active Drivers"),
                   R("Own Now", "OWN NOW — Product Overview", "Net Attrition", pol=-1),
                   R("Own Now", "OWN NOW — Product Overview", "Net Allocation"),
                   R("Own Now", "OWN NOW — Product Overview", "Collection %"),
                   R("Own Now", "OWN NOW — Product Overview", "Bad_debt", "Bad debt %", pol=-1),
                   R("Own Now", "OWN NOW — Product Overview", "OEPH"),
                   R("Own Now", "OWN NOW — Product Overview", "TPV")]),
        dict(fn="Own Now", sub="Existing-driver calling", owner="R Sarathy",
             note="Existing-driver calling team, weekly totals per the Existing Calling dashboard.",
             rows=[R("Own Now", "Input Metrics — Existing Calling", "Total Calls"),
                   R("Own Now", "Input Metrics — Existing Calling", "Total Connected calls"),
                   R("Own Now", "Input Metrics — Existing Calling", "Disposed calls"),
                   R("Own Now", "Input Metrics — Existing Calling", "Total Login duration"),
                   R("Own Now", "Input Metrics — Existing Calling", "Total Talktime"),
                   R("Own Now", "Input Metrics — Existing Calling", "Breaktime", pol=-1),
                   R("Own Now", "Input Metrics — Existing Calling", "AHT", pol=0),
                   R("Own Now", "Input Metrics — Existing Calling", "wrap.timeout", pol=-1),
                   R("Own Now", "Input Metrics — Existing Calling", "TC Count", pol=0)]),
        dict(fn="Onboarding", sub="Placements", owner="Satheesh Kumar J",
             note="Placements = new joins + resurrections + net EIP add-ons. % of total cars = placements ÷ total fleet.",
             rows=[R("On Boarding", "Growth", "Total", "Total placements"), R("On Boarding", "Growth", "New Joins"),
                   R("On Boarding", "Growth", "Resurrection"), R("On Boarding", "Growth", "Net EIP add Ons"),
                   R("On Boarding", "Growth", "% of Total Cars"),
                   R("On Boarding", "Growth", "New Join avg deposit", pol=0)]),
        dict(fn="Collections", sub="Collections and bad debt by product", owner="Yamini A",
             note="From the India Collections dashboard (Chennai city view). Only four weeks are published there.",
             rows=[R("Collection", "Collections — Chennai", f"EoW Collections % — {p}") for p in ("All products", "SINGLE", "EIP", "D2O", "Own Now")]
             + [R("Collection", "Collections — Chennai", f"Bad debts % — {p}", pol=-1) for p in ("All products", "SINGLE", "EIP", "D2O", "Own Now")]
             + [R("Collection", "Collections — Chennai", "Carry Forward OS % — All products", pol=-1)]),
        dict(fn="Recovery", sub="Car recovery", owner="Yamini A",
             note="Recovery % from the Chennai SSOT; the week of 14 Sep is not published yet.",
             rows=[R("Car Recovery", "Recovery %", "Recovery Till Sun %"), R("Car Recovery", "Recovery %", "Recovery Till Wed %")]),
    ]),
    ("Driver Acquisition", "Yamini A", [
        dict(fn="Channels", sub="Conversions by channel", owner="Yamini A",
             note="Conversions = new joins + resurrections. Plan = channel plan (new join + resurrection) in the Chennai SSOT.",
             rows=[R(PM, "Channel Performance", "Total Recruitment"),
                   R(PM, "Channel Performance", "Performance marketing", plan=(PM, "Channel Performance", "New  Join — Plan (New Join + Resurrection)", 0)),
                   R(PM, "Channel Performance", "Vendor", plan=(PM, "Channel Performance", "New  Join — Plan (New Join + Resurrection)", 1)),
                   R(PM, "Channel Performance", "Referrals", plan=(PM, "Channel Performance", "New  Join — Plan (New Join + Resurrection)", 2)),
                   R(PM, "Channel Performance", "Field Sales Executive", plan=None),
                   R(PM, "Channel Performance", "New  Join", "Perf marketing — New Join", plan=None),
                   R(PM, "Channel Performance", "Resurrection", "Perf marketing — Resurrection", plan=None),
                   R(PM, "Channel Performance", "New  Join", "Vendor — New Join", occ=2, plan=None),
                   R(PM, "Channel Performance", "Resurrection", "Vendor — Resurrection", occ=1, plan=None)]),
        dict(fn="Performance Marketing", sub="Funnel", owner="Sri Kavitha",
             note="Stages are % of unique leads for the lead week (Recruitment Channel Funnel, % ToF view).",
             rows=[R(PM, "Funnel Perf_Marketing", x) for x in ("Unique Leads", "Total Uploads", "Attempted Leads", "Average Attempts",
                                                              "Connected Leads", "Average Connects", "Pipeline", "Schedules",
                                                              "Walkins", "Security Deposit %", "Allocated Leads")]),
        dict(fn="Performance Marketing", sub="Speed of funnel", owner="Sri Kavitha",
             note="TAT in days from lead creation to each stage; lower is better.",
             rows=[R(PM, "Speed of Funnel", x, pol=-1) for x in ("TAT to Upload", "TAT to Attempt", "TAT to connect", "TAT to Pipeline",
                                                                  "TAT to Schedule", "TAT to Walkin", "TAT to SD payment", "TAT to Allocation")]
             + [R(PM, "Speed of Funnel", "Total Allocation"), R(PM, "Speed of Funnel", "% Leads Alloc within 3 days"),
                R(PM, "Speed of Funnel", "% Leads Allocated after 8 days", pol=-1)]),
        dict(fn="Performance Marketing", sub="Tele-calling productivity", owner="Sri Kavitha",
             note="Per agent per day, Agent Performance Report (Chennai).",
             rows=[R(PM, "Agent Performance — Perf Marketing", "Total_call per agent day", "Calls per agent day"),
                   R(PM, "Agent Performance — Perf Marketing", "Total_connected_calls per agent day", "Connected calls per agent day"),
                   R(PM, "Agent Performance — Perf Marketing", "Interested / agent date", "Interested per agent day"),
                   R(PM, "Agent Performance — Perf Marketing", "sch_count / agent date", "Schedules per agent day"),
                   R(PM, "Agent Performance — Perf Marketing", "walking_count [total walkins / number of agent days]", "Walk-ins per agent day"),
                   R(PM, "Agent Performance — Perf Marketing", "Avg Conversion Per Agent Per Day"),
                   R(PM, "Agent Performance — Perf Marketing", "total_user_talk_time / per agent day", "Talk time per agent day"),
                   R(PM, "Agent Performance — Perf Marketing", "login duration / per agent day", "Login per agent day"),
                   R(PM, "Agent Performance — Perf Marketing", "break duration / per agent day", "Break per agent day", pol=-1),
                   R(PM, "Agent Performance — Perf Marketing", "Average wrap.timeout %", pol=-1),
                   R(PM, "Agent Performance — Perf Marketing", "Total TC", pol=0)]),
        dict(fn="Performance Marketing", sub="Inbound calls", owner="Sri Kavitha",
             note="ABD = abandoned inbound call. Net ABD = abandoned and never reconnected.",
             rows=[R(PM, "Inbound Report — Perf Marketing — panel 1", "Unique Inbound calls"),
                   R(PM, "Inbound Report — Perf Marketing — panel 1", "Unique ANS calls"),
                   R(PM, "Inbound Report — Perf Marketing — panel 1", "Unique ABD calls", pol=-1),
                   R(PM, "Inbound Report — Perf Marketing — panel 1", "Uniq ABD Reconnected"),
                   R(PM, "Inbound Report — Perf Marketing — panel 1", "Net ABD Leads", pol=-1),
                   R(PM, "Inbound Report — Perf Marketing — panel 1", "Avg attempt on ABD"),
                   R(PM, "Inbound Report — Perf Marketing — panel 2", "% Unique ANS calls"),
                   R(PM, "Inbound Report — Perf Marketing — panel 2", "% ABD Reconnected"),
                   R(PM, "Inbound Report — Perf Marketing — panel 2", "Net ABD %", pol=-1)]),
        dict(fn="Offline growth", sub="Vendor channel", owner="Yamini A",
             note="Vendor conversions from the Chennai SSOT channel view; Plan = vendor plan (new join + resurrection).",
             rows=[R(PM, "Channel Performance", "Vendor", "Vendor conversions", plan=(PM, "Channel Performance", "New  Join — Plan (New Join + Resurrection)", 1)),
                   R(PM, "Channel Performance", "New  Join", "Vendor — New Join", occ=2, plan=None),
                   R(PM, "Channel Performance", "Resurrection", "Vendor — Resurrection", occ=1, plan=None)]),
        dict(fn="Rejoining", sub="Funnel (1–60 days)", owner="Yamini A",
             note="Rejoins from the Chennai SSOT; tele-calling metrics per TC from the Central Rejoining dashboard.",
             rows=[R(AR, RR, "Rejoins + Temp Rejoin"), R(AR, RR, "Rejoins"), R(AR, RR, "Temp Rejoin")]
             + [R(AR, "Rejoin — TC Metrics", x, pol=p) for x, p in (("Total Calls / TC", 1), ("Total Connected Calls / TC", 1),
                                                                   ("Total Talk Time / TC", 1), ("Scheduled Count / TC", 1),
                                                                   ("Allocation Count / TC", 1), ("Total Breaktime / TC", -1),
                                                                   ("Fatal_count", -1), ("Quality_Score", 1))]),
        dict(fn="Winback", sub="Resurrection funnel (60+ days)", owner="Yamini A",
             note="Resurrections from the Chennai SSOT; tele-calling metrics per TC from the Central Resurrection dashboard.",
             rows=[R("On Boarding", "Growth", "Resurrection", "Resurrections")]
             + [R(AR, "Resurrection — TC Metrics", x, pol=p) for x, p in (("Total Calls / TC", 1), ("Total Connected Calls / TC", 1),
                                                                         ("Connected call outbound / TC", 1), ("Connected call inbound / TC", 1),
                                                                         ("Total Talk Time / TC", 1), ("Total Login hrs / TC", 1),
                                                                         ("Total Breaktime / TC", -1), ("Scheduled Count / TC", 1),
                                                                         ("Wrap.Timeout / TC", -1), ("Count of TC", 0))]),
        dict(fn="Referral", sub="Referral funnel", owner="Sri Kavitha",
             note="Conversions = new joins + resurrections from referrals; Plan = referral plan in the Chennai SSOT.",
             rows=[R("Referral Channel", "Referrals", "Conversions (New + Ress)", plan=(PM, "Channel Performance", "New  Join — Plan (New Join + Resurrection)", 2)),
                   R("Referral Channel", "Referrals", "Active Pilots"),
                   R("Referral Channel", "Referrals", "Conversion / Active Pilot")]),
    ]),
    ("Vehicle Management", "Nagappan S", [
        dict(fn="Vehicle management", sub="Yard reconciliation", owner="Nagappan S", snapshot="parking",
             note="Parking reco city-wise summary for CNG as of 19 Sep; the source keeps one snapshot, not a weekly series."),
        dict(fn="Vehicle management", sub="Driver-wanted branding", owner="Nagappan S", snapshot="branding",
             note="Driver Wanted Sticker dashboard, current status; the source keeps one snapshot, not a weekly series."),
    ]),
    ("Workshop", "Hamish Joel", [
        dict(fn="R&M - CNG", sub="Total downtime (not on road, not ready to allot)", owner="Hamish Joel",
             note="Share of the Chennai fleet in each status at week end (Chennai SSOT, Car Status). Alloted % is the on-road share.",
             rows=[R(VM, CS, x, pol=-1) for x in ("Garage%", "Repair %", "RTA%", "Misc%", "Fitness Parking%", "Insurance%", "Audit_failed%")]
             + [R(VM, CS, "Alloted %")]),
        dict(fn="R&M - CNG", sub="RTA by model and year", owner="Hamish Joel",
             note="RTA % = share of cars off road for road-traffic accidents, by model and model year (Chennai SSOT).",
             rows=[R("Workshop Overview", "RTA%", "Wagon R", "Wagon R — all", pol=-1)]
             + [R("Workshop Overview", "RTA%", y, f"Wagon R — {y}", pol=-1) for y in ("2026", "2025", "2024", "2023", "2022")]
             + [R("Workshop Overview", "RTA%", "Dzire", "Dzire — all", pol=-1), R("Workshop Overview", "RTA%", "2024", "Dzire — 2024", occ=1, pol=-1)]),
    ]),
]


# ---------------------------------------------------------------- analytics
def row_series(spec, weeks):
    vals = ROWS[spec["key"]]["vals"]
    return [vals.get(w, "") for w in weeks]


def slide_weeks(sd):
    ws = set()
    for r in sd["rows"]:
        ws |= {w for w, v in ROWS[r["key"]]["vals"].items() if w and w <= CUTOFF and parse(v)[0] is not None}
    return sorted(ws)[-NW:]


def move(spec, weeks):
    """WoW move between the last two weeks (both must exist)."""
    s = row_series(spec, weeks)
    cur, kc = parse(s[-1])
    prev, kp = parse(s[-2]) if len(s) > 1 else (None, None)
    if cur is None or prev is None:
        return None
    kind = kc if kc == kp else kc
    d = cur - prev
    if spec["pol"] == 0 or d == 0:
        good = None
    else:
        good = (d > 0) == (spec["pol"] > 0)
    if kind == "pct":
        score = abs(d)
    else:
        score = abs(d) / max(abs(prev), 20) * 100 / 3
    big = (abs(d) >= 0.5) if kind == "pct" else (abs(d) / max(abs(prev), 1) >= 0.05 and (kind == "time" or abs(d) >= 3 or abs(prev) < 20 and abs(d) >= 2))
    return dict(d=d, kind=kind, good=good, score=score, big=big, a=fmt_cell(s[-2]), b=fmt_cell(s[-1]),
                txt=fmt_delta(d, kind, max(abs(cur), abs(prev)) >= 3600), growth="growth" in spec["disp"].lower())


def vs_plan(spec, weeks):
    p = plan_of(spec)
    if not p:
        return None, None, None
    pv = p["vals"].get(weeks[-1], "")
    pn, pk = parse(pv)
    cn, ck = parse(row_series(spec, weeks)[-1])
    if pn is None or cn is None:
        return fmt_cell(pv) if pn is not None else None, None, None
    if ck == "pct":
        gap = cn - pn
        txt = f"{gap:+.1f}pp".replace(".0pp", "pp")
    else:
        if abs(pn) < 20 or (pn < 0) != (cn < 0):
            gap = cn - pn
            txt = ("+" if gap >= 0 else "") + fmt_num(gap)
        else:
            gap = (cn - pn) / abs(pn) * 100
            txt = f"{gap:+.0f}%"
    good = None if gap == 0 or spec["pol"] == 0 else ((gap > 0) == (spec["pol"] > 0))
    return fmt_cell(pv), txt, good


def heat(values, pol):
    nums = [parse(v)[0] for v in values]
    ok = [n for n in nums if n is not None]
    out = []
    for n in nums:
        if n is None or pol == 0 or len(ok) < 2 or max(ok) == min(ok):
            out.append(WHITE if n is None or pol == 0 else H_AMB)
            continue
        t = (n - min(ok)) / (max(ok) - min(ok))
        if pol < 0:
            t = 1 - t
        a, b, u = (H_RED, H_AMB, t * 2) if t < 0.5 else (H_AMB, H_GRN, (t - 0.5) * 2)
        out.append(tuple(round(a[i] + (b[i] - a[i]) * u, 3) for i in range(3)))
    return out


# ---------------------------------------------------------------- slides API helpers
_ctr = [0]


def nid(page, tag):
    _ctr[0] += 1
    return f"{page}_{tag}{_ctr[0]}"


def rgb(c):
    return {"red": c[0], "green": c[1], "blue": c[2]}


def box(x, y, w, h):
    return {"size": {"width": {"magnitude": w * EMU, "unit": "EMU"}, "height": {"magnitude": h * EMU, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x * EMU, "translateY": y * EMU, "unit": "EMU"}}


def text(reqs, page, x, y, w, h, runs, size=7, align="START", valign="TOP", tag="t"):
    """runs: list of (text, dict(bold, color, link)) or a plain string."""
    if isinstance(runs, str):
        runs = [(runs, {})]
    oid = nid(page, tag)
    reqs.append({"createShape": {"objectId": oid, "shapeType": "TEXT_BOX", "elementProperties": dict(pageObjectId=page, **box(x, y, w, h))}})
    full = "".join(r[0] for r in runs)
    reqs.append({"insertText": {"objectId": oid, "text": full}})
    reqs.append({"updateShapeProperties": {"objectId": oid, "fields": "contentAlignment",
                                           "shapeProperties": {"contentAlignment": valign}}})
    reqs.append({"updateParagraphStyle": {"objectId": oid, "textRange": {"type": "ALL"}, "fields": "alignment,lineSpacing,spaceAbove,spaceBelow",
                                          "style": {"alignment": align, "lineSpacing": 100, "spaceAbove": {"magnitude": 0, "unit": "PT"},
                                                    "spaceBelow": {"magnitude": 0, "unit": "PT"}}}})
    pos = 0
    for t, st in runs:
        if not t:
            continue
        style = {"fontFamily": FONT, "fontSize": {"magnitude": st.get("size", size), "unit": "PT"}, "bold": st.get("bold", False),
                 "foregroundColor": {"opaqueColor": {"rgbColor": rgb(st.get("color", BLACK))}}}
        fields = "fontFamily,fontSize,bold,foregroundColor"
        if st.get("link"):
            style["link"] = {"url": st["link"]}
            style["underline"] = True
            fields += ",link,underline"
        reqs.append({"updateTextStyle": {"objectId": oid, "textRange": {"type": "FIXED_RANGE", "startIndex": pos, "endIndex": pos + len(t)},
                                         "fields": fields, "style": style}})
        pos += len(t)
    return oid


def rect(reqs, page, x, y, w, h, fill=None, outline=None, weight=1.0):
    oid = nid(page, "r")
    reqs.append({"createShape": {"objectId": oid, "shapeType": "RECTANGLE", "elementProperties": dict(pageObjectId=page, **box(x, y, w, h))}})
    sp = {}
    fields = []
    if fill:
        sp["shapeBackgroundFill"] = {"solidFill": {"color": {"rgbColor": rgb(fill)}}}
    else:
        sp["shapeBackgroundFill"] = {"propertyState": "NOT_RENDERED"}
    fields.append("shapeBackgroundFill")
    if outline:
        sp["outline"] = {"outlineFill": {"solidFill": {"color": {"rgbColor": rgb(outline)}}}, "weight": {"magnitude": weight, "unit": "PT"}}
    else:
        sp["outline"] = {"propertyState": "NOT_RENDERED"}
    fields.append("outline")
    reqs.append({"updateShapeProperties": {"objectId": oid, "fields": ",".join(fields), "shapeProperties": sp}})
    return oid


def hline(reqs, page, x, y, w, weight=1.5, color=BLACK):
    oid = nid(page, "l")
    reqs.append({"createLine": {"objectId": oid, "lineCategory": "STRAIGHT",
                                "elementProperties": dict(pageObjectId=page, **box(x, y, w, 0))}})
    reqs.append({"updateLineProperties": {"objectId": oid, "fields": "weight,lineFill",
                                          "lineProperties": {"weight": {"magnitude": weight, "unit": "PT"},
                                                             "lineFill": {"solidFill": {"color": {"rgbColor": rgb(color)}}}}}})


def table(reqs, page, x, y, colw, rowh, cells):
    """cells[r][c] = dict(t, fill, bold, color, align, size)."""
    oid = nid(page, "tb")
    nr, nc = len(cells), len(colw)
    reqs.append({"createTable": {"objectId": oid, "rows": nr, "columns": nc,
                                 "elementProperties": dict(pageObjectId=page, **box(x, y, sum(colw), sum(rowh)))}})
    for c, w in enumerate(colw):
        reqs.append({"updateTableColumnProperties": {"objectId": oid, "columnIndices": [c], "fields": "columnWidth",
                                                     "tableColumnProperties": {"columnWidth": {"magnitude": w * EMU, "unit": "EMU"}}}})
    for r, h in enumerate(rowh):
        reqs.append({"updateTableRowProperties": {"objectId": oid, "rowIndices": [r], "fields": "minRowHeight",
                                                  "tableRowProperties": {"minRowHeight": {"magnitude": h * EMU, "unit": "EMU"}}}})
    reqs.append({"updateTableBorderProperties": {"objectId": oid, "borderPosition": "ALL", "fields": "tableBorderFill,weight",
                                                 "tableRange": {"location": {"rowIndex": 0, "columnIndex": 0}, "rowSpan": nr, "columnSpan": nc},
                                                 "tableBorderProperties": {"tableBorderFill": {"solidFill": {"color": {"rgbColor": rgb(WHITE)}}},
                                                                           "weight": {"magnitude": 1.5, "unit": "PT"}}}})
    for r in range(nr):
        for c in range(nc):
            cd = cells[r][c]
            loc = {"rowIndex": r, "columnIndex": c}
            reqs.append({"updateTableCellProperties": {"objectId": oid, "tableRange": {"location": loc, "rowSpan": 1, "columnSpan": 1},
                                                       "fields": "tableCellBackgroundFill,contentAlignment",
                                                       "tableCellProperties": {"tableCellBackgroundFill": {"solidFill": {"color": {"rgbColor": rgb(cd.get("fill", WHITE))}}},
                                                                               "contentAlignment": "MIDDLE"}}})
            t = cd.get("t") or " "
            reqs.append({"insertText": {"objectId": oid, "cellLocation": loc, "text": t}})
            reqs.append({"updateTextStyle": {"objectId": oid, "cellLocation": loc, "textRange": {"type": "ALL"},
                                             "fields": "fontFamily,fontSize,bold,foregroundColor",
                                             "style": {"fontFamily": FONT, "fontSize": {"magnitude": cd.get("size", 7), "unit": "PT"},
                                                       "bold": cd.get("bold", False),
                                                       "foregroundColor": {"opaqueColor": {"rgbColor": rgb(cd.get("color", BLACK))}}}}})
            reqs.append({"updateParagraphStyle": {"objectId": oid, "cellLocation": loc, "textRange": {"type": "ALL"}, "fields": "alignment",
                                                  "style": {"alignment": cd.get("align", "CENTER")}}})
    return oid


def new_slide(reqs, page):
    reqs.append({"createSlide": {"objectId": page, "slideLayoutReference": {"predefinedLayout": "BLANK"}}})


def chrome(reqs, page, crumb, headline, pno, hsize=14):
    text(reqs, page, 0.5, 0.17, 9.0, 0.17, [(crumb, {"bold": True, "color": GREY_TXT, "size": 9})])
    text(reqs, page, 0.5, 0.35, 9.0, 0.5, [(headline, {"bold": True, "size": hsize})], valign="MIDDLE")
    hline(reqs, page, 0.5, 0.86, 9.0)
    text(reqs, page, 0.5, 5.39, 7.78, 0.17, [(FOOT, {"color": GREY_TXT})])
    text(reqs, page, 9.03, 5.39, 0.47, 0.17, [(str(pno), {"color": GREY_TXT})], align="END")


# ---------------------------------------------------------------- slide builders
def build_metric_slide(page, dept, sd, pno, nxt):
    reqs = []
    new_slide(reqs, page)
    weeks = slide_weeks(sd)
    last_ok = weeks[-1] == CUTOFF
    rows = [r for r in sd["rows"] if any(parse(v)[0] is not None for v in row_series(r, weeks))]
    sd["rows"] = rows
    has_plan = any(plan_of(r) for r in rows)
    lead = rows[0]
    s = row_series(lead, weeks)
    m = move(lead, weeks)
    wk = dlabel(weeks[-1])
    head = f"{lead['disp']}: {fmt_cell(s[-1])} in the week of {wk}"
    if m:
        head += f", {m['txt'].replace(' pp', ' pp')} WoW"
    pv, ptxt, _ = vs_plan(lead, weeks)
    if ptxt:
        head += f", {ptxt.replace('pp', ' pp')} vs plan"
    if not last_ok:
        head += f" (week of {WK} not final yet)"
    crumb = f"{CITY}  ·  {dept}  ›  {sd['fn']}  ›  {sd['sub']}   ·   Owner: {sd['owner']}"
    chrome(reqs, page, crumb, head, pno)
    url, name = SRC[sd["rows"][0]["key"][:2]]
    text(reqs, page, 0.5, 0.88, 9.0, 0.19, [
        (f"Week of {wk} and {len(weeks) - 1} weeks before; plan for week of {wk}. Cells: green better, red worse, per row. "
         "WoW Δ, vs plan: green favourable, red unfavourable.  ", {"color": GREY_TXT}),
        ("Backing sheet ↗", {"color": LINK, "link": url})], valign="MIDDLE")
    # table
    nwk = len(weeks)
    fixed = [0.53] * nwk + [0.6, 0.55, 0.55]
    colw = [7.6 - sum(fixed)] + fixed
    hdr = ["Metric"] + [wlabel(w) for w in weeks] + ["WoW Δ", "Plan", "vs Plan"]
    cells = [[dict(t=h, fill=BLACK, color=WHITE, bold=True, size=7 if i == 0 else 6, align="START" if i == 0 else "CENTER") for i, h in enumerate(hdr)]]
    concerns, wins = [], []
    for r in rows:
        ser = row_series(r, weeks)
        hc = heat(ser, r["pol"])
        mv = move(r, weeks)
        pv, ptxt, pgood = vs_plan(r, weeks)
        line = [dict(t=r["disp"], fill=LIGHT, bold=True, align="START")]
        line += [dict(t=fmt_cell(v), fill=hc[i]) for i, v in enumerate(ser)]
        wf = WHITE if not mv or mv["good"] is None else (T_GRN if mv["good"] else T_RED)
        line.append(dict(t=mv["txt"] if mv else "–", fill=wf, bold=True))
        line.append(dict(t=pv or "–"))
        line.append(dict(t=ptxt or "–", fill=WHITE if pgood is None else (T_GRN if pgood else T_RED)))
        cells.append(line)
        if mv and mv["good"] is not None and mv["big"]:
            item = dict(disp=r["disp"], a=mv["a"], b=mv["b"], txt=mv["txt"], score=mv["score"], fn=sd["fn"], growth=mv["growth"])
            (wins if mv["good"] else concerns).append(item)
    table(reqs, page, 0.5, 1.08, colw, [0.22] + [0.24] * len(rows), cells)
    concerns.sort(key=lambda i: -i["score"])
    wins.sort(key=lambda i: -i["score"])
    sd["_concerns"], sd["_wins"] = concerns, wins
    # FLAGS panel
    rect(reqs, page, 8.19, 1.08, 1.31, 0.25, fill=BLACK)
    text(reqs, page, 8.26, 1.08, 1.2, 0.25, [("FLAGS", {"bold": True, "color": WHITE, "size": 8})], valign="MIDDLE")
    rect(reqs, page, 8.19, 1.33, 1.31, 3.56, outline=BLACK, weight=1)
    y = 1.44
    nc = 3 if wins else 4
    shown_c, shown_w = concerns[:nc], wins[:max(2, 5 - len(concerns[:nc]))][:3]
    if not shown_c and not shown_w:
        text(reqs, page, 8.26, y, 1.17, 0.5, [("No week-on-week move to flag.", {})])
    for label, items, col in (("CONCERNS", shown_c, RED), ("DOING WELL", shown_w, GREEN)):
        if not items:
            continue
        text(reqs, page, 8.26, y, 1.17, 0.17, [(label, {"bold": True, "color": col, "size": 7.5})])
        y += 0.22
        for it in items:
            t = f"{it['disp']}: {it['a']} → {it['b']} ({it['txt']})"
            h = 0.14 * (1 + len(t) // 24) + 0.06
            text(reqs, page, 8.26, y, 1.17, h, [(t, {})])
            y += h + 0.08
        y += 0.06
    # how to read + bottom line
    rect(reqs, page, 0.5, 4.94, 9.0, 0.22, fill=LIGHT)
    text(reqs, page, 0.6, 4.94, 8.8, 0.22, [(f"How to read:  WoW Δ = week of {wk} vs {dlabel(weeks[-2]) if len(weeks) > 1 else '-'} (pp for %). "
                                             f"Plan = weekly plan from the {SS} for the week of {wk}; – = no plan / no data. Source: {name}. {sd['note']}",
                                             {"color": DARK_TXT, "size": 5.5})], valign="MIDDLE")
    if concerns:
        c = concerns[0]
        bl = f"Concern: {c['disp']}: {c['a']} → {c['b']} ({c['txt']})."
    elif wins:
        c = wins[0]
        bl = f"Doing well: {c['disp']}: {c['a']} → {c['b']} ({c['txt']})."
    else:
        bl = "No week-on-week move to flag."
    if nxt:
        bl += f"  Next: {nxt}"
    text(reqs, page, 0.5, 5.18, 9.0, 0.18, [(bl, {"bold": True, "size": 7.5})])
    return reqs


def snapshot_rows(kind):
    if kind == "parking":
        raw = next(r for t, r, u, n in D["T"]["VMT Overview"] if t.startswith("Parking"))
        u, n = next((u, n) for t, r, u, n in D["T"]["VMT Overview"] if t.startswith("Parking"))
        rows = [[r[0], fmt_cell(r[1]), r[2].strip() or "–"] for r in raw[1:]]
        return ["Metric", "Count (19 Sep)", "% of parking"], rows, u, n, \
            f"Parking cars (Hawkeye): {rows[0][1]} on 19 Sep; {rows[1][1]} photos uploaded ({rows[1][2]})", \
            [("CONCERNS", [f"Exceptions: {rows[2][1]} ({rows[2][2]})", f"Missing cars: {rows[4][1]}", f"Police custody: {rows[3][1]}"], RED)]
    raw = next(r for t, r, u, n in D["T"]["Workshop Overview"] if t.startswith("Driver Wanted"))
    u, n = next((u, n) for t, r, u, n in D["T"]["Workshop Overview"] if t.startswith("Driver Wanted"))
    cnt, pct = raw[1], raw[2]
    names = raw[0][1:]
    rows = [[names[i], fmt_cell(cnt[i + 1]), pct[i + 1] if "%" in pct[i + 1] else "–"] for i in range(len(names))]
    return ["Metric", "Cars", "% of group"], rows, u, n, \
        f"Driver-wanted branding: {rows[1][1]} of {rows[0][1]} cars branded ({rows[1][2]}); {rows[2][1]} still blank", \
        [("CONCERNS", [f"Blank cars: {rows[2][1]} ({rows[2][2]})", f"Allotted blank cars: {rows[5][1]} ({rows[5][2]})"], RED),
         ("DOING WELL", [f"Allotted cars branded: {rows[4][1]} ({rows[4][2]})"], GREEN)]


def build_snapshot_slide(page, dept, sd, pno, nxt):
    reqs = []
    new_slide(reqs, page)
    hdr, rows, url, name, head, flags = snapshot_rows(sd["snapshot"])
    chrome(reqs, page, f"{CITY}  ·  {dept}  ›  {sd['fn']}  ›  {sd['sub']}   ·   Owner: {sd['owner']}", head, pno)
    text(reqs, page, 0.5, 0.88, 9.0, 0.19, [("Latest snapshot in the source; no weekly history is kept there, so no WoW column.  ", {"color": GREY_TXT}),
                                            ("Backing sheet ↗", {"color": LINK, "link": url})], valign="MIDDLE")
    cells = [[dict(t=h, fill=BLACK, color=WHITE, bold=True, align="START" if i == 0 else "CENTER") for i, h in enumerate(hdr)]]
    for r in rows:
        cells.append([dict(t=r[0], fill=LIGHT, bold=True, align="START"), dict(t=r[1]), dict(t=r[2])])
    table(reqs, page, 0.5, 1.08, [4.2, 1.6, 1.6], [0.22] + [0.24] * len(rows), cells)
    rect(reqs, page, 8.19, 1.08, 1.31, 0.25, fill=BLACK)
    text(reqs, page, 8.26, 1.08, 1.2, 0.25, [("FLAGS", {"bold": True, "color": WHITE, "size": 8})], valign="MIDDLE")
    rect(reqs, page, 8.19, 1.33, 1.31, 3.56, outline=BLACK, weight=1)
    y = 1.44
    for label, items, col in flags:
        text(reqs, page, 8.26, y, 1.17, 0.17, [(label, {"bold": True, "color": col, "size": 7.5})])
        y += 0.22
        for t in items:
            text(reqs, page, 8.26, y, 1.17, 0.3, [(t, {})])
            y += 0.36
        y += 0.06
    rect(reqs, page, 0.5, 4.94, 9.0, 0.22, fill=LIGHT)
    text(reqs, page, 0.6, 4.94, 8.8, 0.22, [(f"How to read:  Source: {name}. {sd['note']}", {"color": DARK_TXT, "size": 5.5})], valign="MIDDLE")
    bl = f"Concern: {flags[0][1][0]}." + (f"  Next: {nxt}" if nxt else "")
    text(reqs, page, 0.5, 5.18, 9.0, 0.18, [(bl, {"bold": True, "size": 7.5})])
    sd["_concerns"], sd["_wins"] = [], []
    return reqs


def build_owner_slide(page, dept, owner, pno, nxt):
    reqs = []
    new_slide(reqs, page)
    chrome(reqs, page, f"{CITY}  ·  {dept}  ·  Owner's view", f"{dept}: owner's view for the week of {WK}  ·  {owner}", pno, hsize=16)
    for i, (lab, col) in enumerate((("WHAT WORKED", GREEN), ("WHAT DIDN'T", RED), ("WHERE I NEED HELP", BLACK))):
        x = 0.5 + i * 3.055
        rect(reqs, page, x, 1.03, 2.89, 0.31, fill=col)
        text(reqs, page, x, 1.03, 2.89, 0.31, [(lab, {"bold": True, "color": WHITE, "size": 10})], align="CENTER", valign="MIDDLE")
        rect(reqs, page, x, 1.33, 2.89, 3.47, outline=OUTL, weight=1)
        text(reqs, page, x + 0.11, 1.42, 2.67, 0.5, [("Owner fills this before the review.", {"color": GREY_TXT, "size": 8})])
    if nxt:
        text(reqs, page, 0.5, 5.15, 9.0, 0.19, [(f"Next: {nxt}", {"bold": True, "size": 7.5})])
    return reqs


def build_cover(page):
    reqs = []
    new_slide(reqs, page)
    text(reqs, page, 0.5, 1.2, 9.0, 0.6, [(f"{CITY} — Weekly City Review", {"bold": True, "size": 28})], valign="BOTTOM")
    hline(reqs, page, 0.5, 1.95, 9.0)
    text(reqs, page, 0.5, 2.05, 9.0, 0.25, [("Everest Fleet  ·  Week starting 14 Sep ending on 20 Sep 2026  ·  Weekly review vs last week and plan", {"size": 12})])
    text(reqs, page, 0.5, 2.35, 9.0, 0.25, [("Prepared by Strategy & Planning", {"size": 11, "color": GREY_TXT})])
    return reqs


def kra_val(key, weeks_back=0):
    vals = ROWS[key]["vals"]
    ws = sorted(w for w in vals if w and w <= CUTOFF)
    return vals.get(ws[-1 - weeks_back], "") if len(ws) > weeks_back else ""


def build_kra(page, pno):
    reqs = []
    new_slide(reqs, page)
    on = (CO, EOW, "On Road Cars", 0)
    onv, onp = parse(kra_val(on))[0], parse(kra_val((CO, EOW, "On Road Cars — Plan", 0)))[0]
    chrome(reqs, page, f"{CITY}  ·  City KRA  ·  Owner: Vigneshwar Munuswamy",
           f"{fmt_num(onv)} cars on road in the week of {WK} vs a plan of {fmt_num(onp)}: {fmt_num(onp - onv)} short", pno)
    left = [("Cars on road", "Vignesh", on, (CO, EOW, "On Road Cars — Plan", 0), 1),
            ("D2O cars", "Vignesh", (CO, EOW, "D20 Cars", 0), (CO, EOW, "D20 Cars — Plan", 0), 1),
            ("Own Now cars", "Sarathy", (CO, EOW, "Own_Now cars", 0), (CO, EOW, "Own_Now cars — Plan", 0), 1),
            ("EIP cars", "Yamini", (CO, EOW, "EIP Cars", 0), (CO, EOW, "EIP Cars — Plan", 0), 1),
            ("Fleet (total cars)", "Vignesh", (CO, EOW, "Total Cars", 0), (CO, EOW, "Total Cars — Plan", 0), 1),
            ("Utilisation %", "Vignesh", (CN, UT, "Utilisation", 0), (CN, UT, "Utilisation — Plan", 0), 1),
            ("WagonR utilisation %", "Vignesh", (CN, UT, "WagonR Util", 0), (CN, UT, "WagonR Util — Plan", 0), 1)]
    right = [("Net attrition %", "Vignesh", (AR, RR, "Net Attrition %", 0), (AR, RR, "Net Attrition % — Plan", 0), -1),
             ("Net attrition (cars)", "Vignesh", (AR, RR, "Net Attrition", 0), None, 1),
             ("Rejoins + temp rejoins", "Vignesh", (AR, RR, "Rejoins + Temp Rejoin", 0), None, 1),
             ("Total recruitment", "Yamini", (PM, "Channel Performance", "Total Recruitment", 0), (PM, "Channel Performance", "Total Recruitment — Plan (Total Recruitment)", 0), 1),
             ("Collected vs owed % (EoW)", "Yamini", ("Collection", "Collections — Chennai", "EoW Collections % — All products", 0), None, 1),
             ("Bad debt % of outstanding", "Yamini", ("Collection", "Collections — Chennai", "Bad debts % — All products", 0), None, -1),
             ("Garage % of fleet", "Hamish", (VM, CS, "Garage%", 0), None, -1)]
    colw = [1.3, 0.6, 0.5, 0.5, 0.5, 0.64]
    for side, rows_ in enumerate((left, right)):
        hdr = ["KRA", "Owner", "Plan", "Last wk", "This wk", "Gap"]
        cells = [[dict(t=h, fill=BLACK, color=WHITE, bold=True, align="START" if i == 0 else "CENTER") for i, h in enumerate(hdr)]]
        for lab, own, k, pk, pol in rows_:
            cur, last = kra_val(k), kra_val(k, 1)
            plan = kra_val(pk) if pk else ""
            cn, ck = parse(cur)
            pn, _ = parse(plan)
            gap, fill = "–", WHITE
            if cn is not None and pn is not None:
                g = cn - pn
                gap = f"{g:+.1f} pp" if ck == "pct" else ("+" if g >= 0 else "") + fmt_num(g)
                good = (g >= 0) == (pol > 0) if g != 0 else True
                fill = T_GRN if good else T_RED
            cells.append([dict(t=lab, fill=LIGHT, bold=True, align="START"), dict(t=own), dict(t=fmt_cell(plan) if pk else "–"),
                          dict(t=fmt_cell(last)), dict(t=fmt_cell(cur), bold=True, fill=fill), dict(t=gap, fill=fill)])
        table(reqs, page, 0.5 + side * 4.6, 1.03, colw, [0.3] + [0.3] * len(rows_), cells)
    rect(reqs, page, 0.5, 4.89, 9.0, 0.25, fill=LIGHT)
    text(reqs, page, 0.6, 4.89, 8.8, 0.25, [(f"Plan = weekly plan rows in the {SS}. Actuals: week of {WK} (week-end stocks); last wk = week of {PWK}. "
                                             "Gap = this wk − plan. Collections from the India Collections dashboard (Chennai). – = no plan in the source.",
                                             {"color": DARK_TXT, "size": 5.5})], valign="MIDDLE")
    return reqs


def build_actions(page, pno):
    reqs = []
    new_slide(reqs, page)
    chrome(reqs, page, f"{CITY}  ·  Review", "Action items — Chennai Weekly City Review", pno, hsize=16)
    text(reqs, page, 0.5, 0.9, 9.0, 0.2, [("Filled from this week's review. Owners update the status column before Thursday; we review it Friday.", {"color": GREY_TXT, "size": 8})])
    cells = [[dict(t=h, fill=BLACK, color=WHITE, bold=True, align="START" if i == 1 else "CENTER") for i, h in enumerate(["#", "Action item", "Owner", "Due", "Status / update"])]]
    for i in range(1, 12):
        cells.append([dict(t=str(i), fill=LIGHT), dict(t=" ", align="START"), dict(t=" "), dict(t=" "), dict(t=" ")])
    table(reqs, page, 0.5, 1.2, [0.45, 4.6, 1.4, 0.9, 1.65], [0.26] + [0.29] * 11, cells)
    return reqs


def build_contents(page, pno, entries):
    """entries: list of (dept, [(page no, label)])"""
    reqs = []
    new_slide(reqs, page)
    chrome(reqs, page, f"{CITY}  ·  Contents", "Business overview first, then each department by function and sub-function", pno, hsize=16)
    sizes = [len(e[1]) + 1.5 for e in entries]
    n = len(entries)
    best = None
    for a in range(1, n - 1):
        for b in range(a + 1, n):
            h = max(sum(sizes[:a]), sum(sizes[a:b]), sum(sizes[b:]))
            if best is None or h < best[0]:
                best = (h, a, b)
    _, a, b = best
    cols = [entries[:a], entries[a:b], entries[b:]]
    for ci, col in enumerate(cols):
        x, y = 0.5 + ci * 3.03, 1.03
        for dept, items in col:
            rect(reqs, page, x, y, 2.86, 0.22, fill=SECT)
            text(reqs, page, x + 0.09, y, 2.7, 0.22, [(dept, {"bold": True, "size": 8})], valign="MIDDLE")
            y += 0.3
            for pn_, lab in items:
                text(reqs, page, x + 0.09, y, 0.3, 0.24, [(str(pn_), {"color": GREY_TXT, "size": 7})], valign="MIDDLE")
                text(reqs, page, x + 0.48, y, 2.35, 0.24, [(lab, {"size": 7})], valign="MIDDLE")
                y += 0.265
            y += 0.08
    return reqs


def build_summary(page, pno, working, notworking):
    reqs = []
    new_slide(reqs, page)
    chrome(reqs, page, f"{CITY}  ·  Summary", f"What is working, what is not: biggest moves, week of {WK} vs {PWK}", pno, hsize=16)
    for i, (lab, col, items) in enumerate((("WORKING", GREEN, working), ("NOT WORKING", RED, notworking))):
        x = 0.5 + i * 4.61
        rect(reqs, page, x, 1.03, 4.39, 0.31, fill=col)
        text(reqs, page, x + 0.09, 1.03, 4.2, 0.31, [(lab, {"bold": True, "color": WHITE, "size": 10})], valign="MIDDLE")
        rect(reqs, page, x, 1.33, 4.39, 3.62, outline=OUTL, weight=1)
        y = 1.43
        for it in items[:8]:
            text(reqs, page, x + 0.2, y, 4.0, 0.36, [(f"{it['fn']} › {it['disp']}\n", {"size": 7.5}),
                                                     (f"{PWK} {it['a']} → {WK} {it['b']} ({it['txt']})", {"size": 7.5})])
            y += 0.44
    return reqs


ANNEX = [
    ("Workshop", "Workshop throughput (SDD %, inward, outward)", "Chennai SSOT CORE_WBR stops at the week of 24 Aug ('-' after)"),
    ("Workshop", "DSA revisit buckets / Quality-TA (<7D)", "Chennai SSOT CORE_WBR shows YTM / '-' for recent weeks"),
    ("Workshop", "Repair pendency / Service pendency", "blank ('-') and #N/A for Chennai in SSOT CORE_WBR"),
    ("Workshop", "EFG review, Revisit analysis", "sources are Bangalore-only files"),
    ("Workshop", "Service due plan-wise, Urgent service, Washing, Saturday reco, Petrol funnel", "source sheets not shared with this account (403)"),
    ("Workshop", "City-wise weekly budget tracking", "'EFG - Pan India Budget New' has no Chennai rows"),
    ("Vehicle Management", "Fitness status / Vehicles movement", "'VM reports' has no Chennai data"),
    ("Driver Operations", "Helpdesk dash, Support weekly trend and input metrics", "no Chennai rows; Zoho dashboard city dropdown set to Bangalore (shared sheet, not changed)"),
    ("Driver Operations", "Car recovery agent / vendor-wise", "'Central Car Recovery Dash' dropdown set to Pune (shared sheet, not changed)"),
    ("Driver Operations", "Onboarding city deck / agent-level OB", "no Chennai rows; agent-level sheet not shared (403)"),
    ("Driver Operations", "EV utilisation / EV SSOT", "no Chennai EV data"),
    ("Driver Acquisition", "Vendor level, Allocation split (perf marketing)", "source sheets not shared with this account (403)"),
    ("Driver Acquisition", "Referral funnel / new referral dash", "'Referral Process - V2' dropdown set to Pune (shared sheet, not changed)"),
]


def build_annex(page, pno):
    reqs = []
    new_slide(reqs, page)
    chrome(reqs, page, f"{CITY}  ·  Annexure", "Metrics asked for that have no weekly Chennai source yet", pno, hsize=16)
    text(reqs, page, 0.5, 0.9, 9.0, 0.2, [("Share access or the Chennai view for these and they get their own slide. Shared sheets were not changed.", {"color": GREY_TXT, "size": 8})])
    cells = [[dict(t=h, fill=BLACK, color=WHITE, bold=True, align="START") for h in ("Department", "Metric", "Why it is not in the deck")]]
    for d_, m_, w_ in ANNEX:
        cells.append([dict(t=d_, fill=LIGHT, bold=True, align="START", size=6.5), dict(t=m_, align="START", size=6.5),
                      dict(t=w_, align="START", color=DARK_TXT, size=6.5)])
    table(reqs, page, 0.5, 1.15, [1.4, 3.4, 4.2], [0.22] + [0.2] * len(ANNEX), cells)
    return reqs


# ---------------------------------------------------------------- assemble
plan = [("cover", None), ("kra", None), ("actions", None), ("contents", None)]
for dept, owner, subs in DEPTS:
    if owner:
        plan.append(("owner", (dept, owner)))
    for sd in subs:
        plan.append(("metric", (dept, sd)))
plan += [("summary", None), ("annex", None)]


def label_of(p):
    k, a = p
    if k == "owner":
        return "Owner's view"
    if k == "metric":
        return f"{a[1]['fn']} › {a[1]['sub']}"
    return None


contents = []
for i, (k, a) in enumerate(plan):
    if k == "kra":
        contents.append(["Business overview", [(i + 1, "City › City KRA")]])
    elif k in ("owner", "metric"):
        dept = a[0]
        if contents[-1][0] != dept:
            contents.append([dept, []])
        contents[-1][1].append((i + 1, "Owner's view › what worked / didn't / help" if k == "owner" else label_of((k, a))))

reqs_all, order = [], []
all_c, all_w = [], []
for i, (k, a) in enumerate(plan):
    pno = i + 1
    page = f"{PFX}s{pno:02d}"
    nxt = label_of(plan[i + 1]) if i + 1 < len(plan) and plan[i + 1][0] in ("owner", "metric") else None
    if nxt == "Owner's view":
        nxt = f"{plan[i + 1][1][0]} › Owner's view"
    if k == "cover":
        r = build_cover(page)
    elif k == "kra":
        r = build_kra(page, pno)
    elif k == "actions":
        r = build_actions(page, pno)
    elif k == "contents":
        r = build_contents(page, pno, contents)
    elif k == "owner":
        r = build_owner_slide(page, a[0], a[1], pno, nxt)
    elif k == "metric":
        sd = a[1]
        r = (build_snapshot_slide if sd.get("snapshot") else build_metric_slide)(page, a[0], sd, pno, nxt)
        all_c += sd["_concerns"]
        all_w += sd["_wins"]
    elif k == "summary":
        seen = set()

        def uniq(lst):
            out = []
            for it in sorted(lst, key=lambda i: -i["score"]):
                key = (it["a"], it["b"], it["txt"])
                if key not in seen:
                    seen.add(key)
                    out.append(it)
            return out
        r = build_summary(page, pno, uniq([i for i in all_w if not i["growth"]]), uniq([i for i in all_c if not i["growth"]]))
    elif k == "annex":
        r = build_annex(page, pno)
    reqs_all += r
    order.append(page)

print("slides:", len(order), "requests:", len(reqs_all))
if "--dry" in sys.argv:
    sys.exit(0)

old = [s["objectId"] for s in slides.presentations().get(presentationId=CPRES, fields="slides.objectId").execute().get("slides", [])]
for i in range(0, len(reqs_all), 400):
    slides.presentations().batchUpdate(presentationId=CPRES, body={"requests": reqs_all[i:i + 400]}).execute()
    print("submitted", min(i + 400, len(reqs_all)), "/", len(reqs_all))
old = [o for o in old if o not in order]
if old:
    slides.presentations().batchUpdate(presentationId=CPRES, body={"requests": [{"deleteObject": {"objectId": o}} for o in old]}).execute()
slides.presentations().batchUpdate(presentationId=CPRES, body={"requests": [
    {"updateSlidesPosition": {"slideObjectIds": order, "insertionIndex": 0}}]}).execute()
json.dump({"pres": CPRES, "order": order}, open(SP + "chennai_deck.json", "w"))
print("done:", f"https://docs.google.com/presentation/d/{CPRES}/edit")
