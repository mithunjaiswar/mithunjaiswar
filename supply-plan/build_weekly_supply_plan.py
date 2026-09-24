"""Build the Lakshya 15,000 weekly supply plan workbook (1 Inputs tab + 7 city tabs).

Source of targets: Lakshya_15000_Model_v4.xlsx (the AOP does not match it, so it is not used).
Opening position: reporting DB, analytics.ssot_scorecard_agg, CNG, Sun 20 Sep 2026.
City tab layout follows the existing Weekly Supply Plan sheet (columns A-Z), with the
Lakshya build-up (the logic behind each weekly number) to the right of it.

Every number on a city tab is a formula that reads from the Inputs tab.

Usage: python3 build_weekly_supply_plan.py <output.xlsx> <raw.json>
  raw.json = {"hdr": [...], "data": [[...], ...]}: the SSOT query output (see SSOT_URL).
"""
import datetime as dt
import json
import re
import sys

from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import column_index_from_string, get_column_letter

# ---------------------------------------------------------------- data
CITIES = ["Mumbai", "Delhi NCR", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune"]

# Lakshya v4 December targets: EIP, Own Now, L+DTO
TARGET = {
    "Mumbai":    (1150, 1006, 1225),
    "Delhi NCR": (83, 850, 1535),
    "Bangalore": (493, 1075, 1201),
    "Hyderabad": (604, 700, 1112),
    "Chennai":   (577, 725, 1004),
    "Kolkata":   (61, 305, 233),
    "Pune":      (70, 442, 631),
}
# L+DTO net churn / month (Lakshya Inputs sec 6); Own Now churn and purchase rollover
# per calendar month (derived from Lakshya Weekly Own Now: exits / book-weeks x 52/12);
# Own Now new-car share of placements (Lakshya Inputs sec 5); utilisation ceiling (sec 7)
RATES = {
    "Mumbai":    (0.58, 0.071, 0.031, 382 / 747, 0.75),
    "Delhi NCR": (0.49, 0.094, 0.0, 45 / 444, 0.62),
    "Bangalore": (0.54, 0.099, 0.0, 418 / 699, 0.795),
    "Hyderabad": (0.65, 0.039, 0.066, 323 / 581, 0.795),
    "Chennai":   (0.56, 0.101, 0.0, 334 / 490, 0.795),
    "Kolkata":   (0.73, 0.094, 0.0, 0 / 200, 0.60),
    "Pune":      (0.68, 0.098, 0.0, 84 / 294, 0.70),
}
# Channel mix FSE, Vendor, Referral (Perf marketing = remainder): AOP Sep-Dec 2026
CHANNEL = {
    "Mumbai":    (0.0, 0.264, 0.095),
    "Delhi NCR": (0.321, 0.192, 0.086),
    "Bangalore": (0.010, 0.277, 0.132),
    "Hyderabad": (0.035, 0.370, 0.090),
    "Chennai":   (0.0, 0.448, 0.095),
    "Kolkata":   (0.0, 0.339, 0.079),
    "Pune":      (0.0, 0.370, 0.150),
}
LAKSHYA_FLEET_DEC = {"Mumbai": 4508, "Delhi NCR": 3981, "Bangalore": 3599, "Hyderabad": 3143,
                     "Chennai": 2972, "Kolkata": 1046, "Pune": 1664}
# New cars by month (Sep 21-30, Oct, Nov, Dec). All land by 30 Nov.
ADDS = {"Mumbai": (0, 234, 233, 0), "Delhi NCR": (0, 0, 0, 0), "Bangalore": (0, 317, 316, 0),
        "Hyderabad": (0, 317, 316, 0), "Chennai": (0, 242, 241, 0), "Kolkata": (0, 0, 0, 0),
        "Pune": (0, 42, 42, 0)}
LAKSHYA_ADDS = {"Mumbai": 467, "Delhi NCR": 0, "Bangalore": 633, "Hyderabad": 633, "Chennai": 483,
                "Kolkata": 0, "Pune": 84}
SALES = {"Mumbai": (0, 50, 50, 51), "Delhi NCR": (0, 70, 70, 69), "Bangalore": (0, 17, 17, 16),
         "Hyderabad": (0, 17, 17, 16), "Chennai": (0, 17, 17, 16), "Kolkata": (0, 17, 17, 16),
         "Pune": (0, 54, 54, 53)}
LAKSHYA_SALES = {"Mumbai": 151, "Delhi NCR": 209, "Bangalore": 50, "Hyderabad": 50, "Chennai": 50,
                 "Kolkata": 50, "Pune": 161}

N_WEEKS = 14  # w/c 21 Sep ... w/c 21 Dec (w/e 27 Dec), the same 14 weeks as Lakshya v4
W_EIP = [5, 5, 8, 8, 8, 8, 4, 4, 8, 8, 8, 9, 9, 8]
# Own Now / L+DTO base profiles are relative weights before seasonality (they need not sum to 100):
# Own Now builds up as new cars land in Oct-Nov; L+DTO is flat and gets its shape from seasonality.
W_OWN = [4, 5, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 8, 7]
W_LDTO = [1] * 14
# Event impact on recruitment by city (Mumbai, Delhi NCR, Bangalore, Hyderabad, Chennai, Kolkata, Pune):
# "Rec Avg" (2024-25 average) from the seasonality_Impect tab of the Weekly Supply Plan. City-only events
# are 0 in the other cities.
SEASON_REC = {
    "Mahatma Gandhi Jayanti": (-0.245, -0.12, -0.13, -0.305, -0.025, -0.67, 0.005),
    "Dussehra": (-0.075, -0.09, -0.17, -0.475, -0.075, -1.37, -0.025),
    "Kannada Rajyotsava": (0, 0, -0.19, 0, 0, 0, 0),
    "Diwali (Laxmi Pujan)": (-0.415, -1.625, -0.385, -0.095, -0.315, -0.205, -0.61),
    "Bhai Dooj": (-0.415, -1.625, -0.385, -0.095, -0.315, -0.205, -0.61),
    "Guru Nanak Jayanti": (0.085, 0.06, 0.08, 0.01, -0.055, -0.01, 0.075),
    "GHMC/MMC/CMC Election Hyderabad 2026": (0, 0, 0, 0, 0, 0, 0),
    "KMC Election Kolkata 2026": (0, 0, 0, 0, 0, 0, 0),
    "Christmas": (0.125, -0.005, -0.06, -0.03, -0.075, -0.295, -0.085),
}
# Event used for the impact lookup in each plan week (week 8 = Bali Pratipada + Bhai Dooj, same impact)
WEEK_EVENT = {2: "Mahatma Gandhi Jayanti", 5: "Dussehra", 6: "Kannada Rajyotsava", 7: "Diwali (Laxmi Pujan)",
              8: "Bhai Dooj", 10: "Guru Nanak Jayanti", 13: "KMC Election Kolkata 2026", 14: "Christmas"}
EVENTS_ALL = {
    2: "Gandhi Jayanti (Fri 2 Oct)",
    5: "Dussehra (Tue 20 Oct)",
    7: "Diwali (Sun 8 Nov) - low week",
    8: "Bali Pratipada, Bhai Dooj - low week",
    10: "Guru Nanak Jayanti (Tue 24 Nov)",
    11: "Last week new cars can land (30 Nov)",
    14: "Christmas (Fri 25 Dec); last plan week, ends Sun 27 Dec as in Lakshya",
}
EVENTS_CITY = {
    ("Bangalore", 6): "Kannada Rajyotsava (Sun 1 Nov)",
    ("Hyderabad", 8): "GHMC election (Sun 15 Nov)",
    ("Kolkata", 13): "KMC election (Tue 15 Dec)",
}

LAKSHYA_URL = "https://docs.google.com/spreadsheets/d/1Bu8NkgNVcakYondqbyK_jW4nFuFDBqEk"
AOP_URL = "https://docs.google.com/spreadsheets/d/1yK2NRIK1B7U-K9wSqGvoFgcl3arVB-Ozybl_St0Z_PA"
SUPPLY_URL = "https://docs.google.com/spreadsheets/d/1Cxg6qsZr6I9nr9OdORAYJVlRc5iB6r0Vnu6k9LKWcjE"
SSOT_URL = "https://docs.google.com/document/d/1UIKW0voWgrUu2HDonBR4GsWdFz8XLVgWq7r5UoaYMpc"
SOURCES = [
    ("Lakshya source (targets)", LAKSHYA_URL, "Lakshya_15000_Model_v4.xlsx - source of every target in this plan"),
    ("AOP (reference only)", AOP_URL, "AOP FY27 - does not match Lakshya; used only for the recruitment channel mix"),
    ("Weekly Supply Plan (format)", SUPPLY_URL, "Weekly Supply Plan - city tab layout"),
    ("SSOT query (raw data)", SSOT_URL, "SSOT query - run from 1 Aug 2026; its output is the raw_performance tab"),
]


def link(url, text):
    return f'=HYPERLINK("{url}","{text}")'


# ---------------------------------------------------------------- styles
NAVY = "FF1F3864"
GREY_HDR = "FF404040"
YELLOW = "FFFFFF00"
INPUT = "FFFFF2CC"
GREEN = "FFA2D9BE"
LIGHT = "FFF2F2F2"
ACTUAL = "FFDDEBF7"
BLUE_TXT = "FF0000FF"
F_HDR = Font(name="Calibri", size=10, bold=True, color="FFFFFFFF")
F_BODY = Font(name="Calibri", size=10)
F_BOLD = Font(name="Calibri", size=10, bold=True)
F_INPUT = Font(name="Calibri", size=10, color=BLUE_TXT)
F_TITLE = Font(name="Calibri", size=14, bold=True, color=NAVY)
F_SECTION = Font(name="Calibri", size=11, bold=True, color=NAVY)
F_NOTE = Font(name="Calibri", size=9, italic=True, color="FF595959")
THIN = Side(style="thin", color="FFBFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
NUM = "#,##0"
PCT = "0.0%"
DATE = "dd-mmm"


def fill(c):
    return PatternFill("solid", fgColor=c)


def hdr(ws, row, col, text, color=NAVY):
    c = ws.cell(row, col, text)
    c.font = F_HDR
    c.fill = fill(color)
    c.alignment = CENTER
    c.border = BOX
    return c


def put(ws, row, col, value, fmt=None, font=F_BODY, bg=None, bold=False):
    if isinstance(value, str) and value.startswith("=") and "'!" in value and ws.title not in CITIES:
        value = _shift_refs(value, own_sheet=False)
    c = ws.cell(row, col, value)
    c.font = F_BOLD if bold else font
    if fmt:
        c.number_format = fmt
    if bg:
        c.fill = fill(bg)
    c.border = BOX
    return c


def inp(ws, row, col, value, fmt=None):
    return put(ws, row, col, value, fmt, font=F_INPUT, bg=INPUT)


RAW_HDR = []  # filled from the raw data file at build time


def rc(name):
    """Column letter of a raw_performance field."""
    return get_column_letter(RAW_HDR.index(name) + 1)


def q(sheet):
    return f"'{sheet}'"


# ---------------------------------------------------------------- Inputs tab layout
R_GLOBAL = 5          # header row of global settings; values start next row
R_SUM_H = 18          # summary header row
R_SUM0 = R_SUM_H + 1  # first city row in summary
R_CITY_H = 31         # city inputs header row
R_CITY0 = R_CITY_H + 1
R_ADD_H = 45          # new cars header
R_ADD0 = R_ADD_H + 1
R_SALE_H = 57         # sales header
R_SALE0 = R_SALE_H + 1
R_CAL_H = 69          # calendar header
R_CAL0 = R_CAL_H + 1
R_SEAS_H = 91         # seasonality table header
R_SEAS0 = R_SEAS_H + 1
R_SEAS1 = R_SEAS0 + len(SEASON_REC) - 1

G_OPEN_DATE = f"Inputs!$B${R_GLOBAL + 1}"
G_PLAN_END = f"Inputs!$B${R_GLOBAL + 3}"
G_WPM = f"Inputs!$B${R_GLOBAL + 4}"
G_FLOOR = f"Inputs!$B${R_GLOBAL + 6}"

# City-input columns on the Inputs tab
CI = {k: i + 1 for i, k in enumerate([
    "city", "fleet", "onroad", "eip", "own", "ldto", "t_eip", "t_own", "t_ldto", "t_onroad",
    "r_ldto", "r_own", "r_roll", "newshare", "ceiling", "fse", "vendor", "referral", "perf",
    "lk_fleet"])}


def ci(key, city_idx):
    return f"Inputs!${get_column_letter(CI[key])}${R_CITY0 + city_idx}"


# ---------------------------------------------------------------- City tab layout
COLS = [  # (letter, header, width)
    ("A", "City", 10), ("B", "Fuel Type", 7), ("C", "Month", 8), ("D", "Week", 8),
    ("E", "Total Cars [week ending]", 9), ("F", "nULP", 7), ("G", "cars on Road - WB", 9),
    ("H", "active partners - WB", 9), ("I", "Net Allocations", 9), ("J", "Total Allocations", 9),
    ("K", "Total Channel", 9), ("L", "Field Sales Executive", 8), ("M", "Vendor", 8),
    ("N", "Referrals", 8), ("O", "Performance marketing", 9), ("P", "EIP Net add-on", 8),
    ("Q", "seasonality", 24), ("R", "EIP cars", 8), ("S", "Rejoin %", 6),
    ("T", "Attrition + Temp Attrition", 8), ("U", "Net Attrition (Abs)", 9),
    ("V", "Net Attrition %", 8), ("W", "Leasing + DTO cars on Road - WE", 10),
    ("X", "Own Now cars on Road - WE", 9), ("Y", "Week-ending cars on Road", 9),
    ("Z", "Week ending Util", 8), ("AA", "Util ceiling (Lakshya)", 8), ("AB", "", 2),
    ("AC", "Days in plan", 6), ("AD", "Total buy (new cars)", 8), ("AE", "Total sold", 8),
    ("AF", "EIP weight", 7), ("AG", "EIP net add", 8),
    ("AH", "Own Now book - WB", 8), ("AI", "Own Now share of placements", 8), ("AJ", "Own Now net add", 8),
    ("AK", "Own Now churn (LY-shaped)", 8), ("AL", "Own Now purchase rollover", 9),
    ("AM", "Own Now placements", 9), ("AN", "of which new cars", 8),
    ("AO", "of which existing cars", 8),
    ("AP", "L+DTO book - WB", 8), ("AQ", "L+DTO share of placements", 8), ("AR", "L+DTO net add", 8),
    ("AS", "L+DTO churn (LY-shaped)", 8), ("AT", "L+DTO placements", 9),
    ("AU", "Total placements (Own Now + L+DTO)", 10), ("AV", "Check: on road = EIP + L+DTO + Own Now", 9),
    ("AW", "Util headroom", 8), ("AX", "", 2),
    ("AY", "LY week (same week last year)", 9), ("AZ", "LY active partners - WB", 9),
    ("BA", "LY recruitment (new joins + resurrections)", 10), ("BB", "LY net attrition (abs)", 9),
    ("BC", "LY net attrition %", 8), ("BD", "LY attrition index (1 = average week)", 9),
    ("BE", "Festival impact on recruitment", 9), ("BF", "Seasonality factor", 8),
    ("BG", "Own Now base profile", 8), ("BH", "L+DTO base profile", 8),
    ("BI", "Own Now straight-line book - WB", 9), ("BJ", "L+DTO straight-line book - WB", 9),
]
LY_BLOCK = ("AY", "AZ", "BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BI", "BJ")
TEAL = "FF1F6F5F"
N_ACTUAL = 4                   # actual weeks shown above the plan (rows 2-5)
FIRST = 2 + N_ACTUAL           # first plan week row
OPEN_ROW = FIRST - 1           # last actual week = opening position
LAST = FIRST + N_WEEKS - 1     # 19
R_TOT = LAST + 2               # 19
R_MON_T = R_TOT + 3            # 22 monthly block title
R_MON_H = R_MON_T + 1          # 23
R_MON0 = R_MON_H + 1           # 24..27
R_MON_TOT = R_MON0 + 4         # 28
R_NOTES = R_MON_TOT + 3        # 31

# The formulas below are written against the logical column letters in COLS. On the sheet,
# "New cars added" (AD) and "Cars sold" (AE) sit right after nULP as G and H ("Total buy",
# "Total sold"), so logical G..AC move two columns right; AF onwards stay where they are.
_MOVED = {"AD": "G", "AE": "H"}


def newcol(old):
    if old in _MOVED:
        return _MOVED[old]
    i = column_index_from_string(old)
    return get_column_letter(i + 2) if 7 <= i <= 29 else old


_REF = re.compile(r"(?<![A-Za-z0-9_])((?:'[^']+'|[A-Za-z_][A-Za-z0-9_]*)!)?(\$?)([A-Z]{1,3})(\$?)(\d*)"
                  r"(?::(\$?)([A-Z]{1,3})(\$?)(\d*))?")
_CITY_PREFIXES = {f"'{c}'!" for c in CITIES}


def _shift_refs(formula, own_sheet):
    """Map logical city-tab column letters to their sheet position.
    own_sheet=True: shift refs with no sheet prefix (formula lives on a city tab).
    own_sheet=False: shift refs prefixed with a city tab name (formula lives elsewhere)."""
    def sub(m):
        prefix, d1, c1, d2, r1, d3, c2, d4, r2 = m.groups()
        is_ref = bool(r1) or c2 is not None
        if not is_ref:
            return m.group(0)
        if own_sheet and prefix is not None:
            return m.group(0)
        if not own_sheet and prefix not in _CITY_PREFIXES:
            return m.group(0)
        out = f"{prefix or ''}{d1}{newcol(c1)}{d2}{r1}"
        if c2 is not None:
            out += f":{d3}{newcol(c2)}{d4}{r2}"
        return out
    return _REF.sub(sub, formula)


def cput(ws, r, old_letter, value, fmt=None, **kw):
    """put() on a city tab, addressed by logical column letter; formulas get shifted."""
    if isinstance(value, str) and value.startswith("="):
        value = _shift_refs(value, own_sheet=True)
    return put(ws, r, column_index_from_string(newcol(old_letter)), value, fmt, **kw)


def build_city(wb, idx, city):
    ws = wb.create_sheet(city)
    for letter, text, width in COLS:
        ws.column_dimensions[newcol(letter)].width = width
        if text:
            grey = letter >= "AC" and len(letter) == 2 and letter not in ("AA", "AD", "AE")
            color = TEAL if letter in LY_BLOCK else (GREY_HDR if grey else NAVY)
            hdr(ws, 1, column_index_from_string(newcol(letter)), text, color)
    ws.row_dimensions[1].height = 54
    ws.freeze_panes = "F2"

    ev_col = get_column_letter(9 + idx)  # events columns on Inputs calendar: I..O

    # ---- actual weeks (rows 2-5): straight from raw_performance
    def day(col, r, offset):   # value on one date (week start + offset days)
        return (f"SUMIFS(raw_performance!${rc(col)}:${rc(col)},raw_performance!$D:$D,$A{r},"
                f"raw_performance!$E:$E,$B{r},raw_performance!$C:$C,$D{r}+{offset})").replace("+-", "-")

    def week(col, r):          # sum over the Mon-Sun week
        return (f"SUMIFS(raw_performance!${rc(col)}:${rc(col)},raw_performance!$D:$D,$A{r},"
                f"raw_performance!$E:$E,$B{r},raw_performance!$B:$B,$D{r})")

    for k in range(N_ACTUAL):
        r = 2 + k
        f = {
            "A": city if k == 0 else "=$A$2", "B": "CNG" if k == 0 else "=$B$2",
            "C": f"=EOMONTH(D{r},-1)+1",
            "D": f"={G_OPEN_DATE}-{7 * N_ACTUAL - 1}" if k == 0 else f"=D{r - 1}+7",
            "E": "=" + day("fleet_total_cars_cnt", r, 6),
            "F": f"=E{r}-" + day("fleet_total_cars_cnt", r, -1),
            "G": "=" + day("allotted_cars_eod", r, -1),
            "H": "=" + day("allotted_cars_eod", r, -1) + "-" + day("eip_vehicles_cnt", r, -1),
            "I": f"=Y{r}-G{r}", "J": f"=K{r}+P{r}", "K": f"=SUM(L{r}:O{r})",
            "L": "=" + week("ni_fse_cnt", r) + "+" + week("resurrection_fse_cnt", r),
            "M": "=" + week("ni_vendor_cnt", r) + "+" + week("resurrection_vendor_cnt", r),
            "N": "=" + week("ni_driver_referral_cnt", r) + "+" + week("resurrection_driver_referral_cnt", r),
            "O": "=" + week("ni_perf_mktg_cnt", r) + "+" + week("resurrection_perf_mktg_cnt", r),
            "P": "=" + week("Net EIP Add-ons", r),
            "Q": "ACTUAL - raw_performance",
            "R": "=" + day("eip_vehicles_cnt", r, 6),
            "U": f"=I{r}-J{r}", "V": f"=IF(H{r}=0,0,-U{r}/H{r})",
            "W": f"=Y{r}-R{r}-X{r}",
            "X": "=" + day("own_now_cars_eod", r, 6),
            "Y": "=" + day("allotted_cars_eod", r, 6),
            "Z": f"=Y{r}/E{r}", "AA": f"={ci('ceiling', idx)}",
            "AC": 7, "AU": f"=K{r}",
            "AV": f"=Y{r}-(R{r}+W{r}+X{r})", "AW": f"=AA{r}-Z{r}",
        }
        for letter, _, _ in COLS:
            if letter in ("AB", "AX"):
                continue
            fmt = NUM
            if letter in ("C", "D"):
                fmt = DATE
            elif letter in ("V", "Z", "AA", "AW"):
                fmt = PCT
            elif letter in ("A", "B", "Q", "AC"):
                fmt = None
            cput(ws, r, letter, f.get(letter), fmt, bg=ACTUAL, bold=(letter == "Q"))

    def raw_on(col, r):        # value on the LY week's Monday
        return (f"SUMIFS(raw_performance!${rc(col)}:${rc(col)},raw_performance!$D:$D,$A{r},"
                f"raw_performance!$E:$E,$B{r},raw_performance!$C:$C,$AY{r})")

    def raw_wk(col, r):        # sum over the LY week
        return (f"SUMIFS(raw_performance!${rc(col)}:${rc(col)},raw_performance!$D:$D,$A{r},"
                f"raw_performance!$E:$E,$B{r},raw_performance!$B:$B,$AY{r})")

    # ---- weekly rows
    for w in range(N_WEEKS):
        r = FIRST + w
        p = r - 1
        cal = R_CAL0 + w
        f = {
            "A": f"=$A$2", "B": f"=$B$2", "C": f"=EOMONTH(D{r},-1)+1", "D": f"=Inputs!$B${cal}",
            "E": f"=E{p}+AD{r}-AE{r}", "F": f"=E{r}-E{p}", "G": f"=Y{p}", "H": f"=W{p}+X{p}",
            "I": f"=K{r}+P{r}+U{r}", "J": f"=K{r}+P{r}", "K": f"=SUM(L{r}:O{r})",
            "L": f"=AU{r}*{ci('fse', idx)}", "M": f"=AU{r}*{ci('vendor', idx)}",
            "N": f"=AU{r}*{ci('referral', idx)}", "O": f"=AU{r}*{ci('perf', idx)}",
            "P": f"=AG{r}", "Q": f"=Inputs!${ev_col}${cal}", "R": f"=R{p}+P{r}",
            "U": f"=-(AK{r}+AL{r}+AS{r})", "V": f"=IF(H{r}=0,0,-U{r}/H{r})",
            "W": f"=W{p}+AR{r}", "X": f"=X{p}+AJ{r}", "Y": f"=G{r}+I{r}", "Z": f"=Y{r}/E{r}",
            "AA": f"={ci('ceiling', idx)}",
            "AC": f"=Inputs!$E${cal}",
            "AD": f"=INDEX(Inputs!$B${R_ADD0 + idx}:$E${R_ADD0 + idx},MATCH(C{r},Inputs!$B${R_ADD_H}:$E${R_ADD_H},0))/COUNTIF($C${FIRST}:$C${LAST},C{r})",
            "AE": f"=INDEX(Inputs!$B${R_SALE0 + idx}:$E${R_SALE0 + idx},MATCH(C{r},Inputs!$B${R_SALE_H}:$E${R_SALE_H},0))/COUNTIF($C${FIRST}:$C${LAST},C{r})",
            "AF": f"=Inputs!$F${cal}",
            "AG": f"=({ci('t_eip', idx)}-{ci('eip', idx)})*AF{r}",
            "AH": f"=X{p}",
            "AI": f"=BG{r}*BF{r}/SUMPRODUCT($BG${FIRST}:$BG${LAST},$BF${FIRST}:$BF${LAST})",
            "AJ": f"=AM{r}-AK{r}-AL{r}",
            "AK": f"=BI{r}*{ci('r_own', idx)}/{G_WPM}*AC{r}/7*BD{r}",
            "AL": f"=BI{r}*{ci('r_roll', idx)}/{G_WPM}*AC{r}/7",
            "AM": f"=(({ci('t_own', idx)}-{ci('own', idx)})+SUM($AK${FIRST}:$AL${LAST}))*AI{r}",
            "AN": f"=AM{r}*{ci('newshare', idx)}",
            "AO": f"=AM{r}-AN{r}",
            "AP": f"=W{p}",
            "AQ": f"=BH{r}*BF{r}/SUMPRODUCT($BH${FIRST}:$BH${LAST},$BF${FIRST}:$BF${LAST})",
            "AR": f"=AT{r}-AS{r}",
            "AS": f"=BJ{r}*{ci('r_ldto', idx)}/{G_WPM}*AC{r}/7*BD{r}",
            "AT": f"=(({ci('t_ldto', idx)}-{ci('ldto', idx)})+SUM($AS${FIRST}:$AS${LAST}))*AQ{r}",
            "AU": f"=AM{r}+AT{r}",
            "AV": f"=Y{r}-(R{r}+W{r}+X{r})", "AW": f"=AA{r}-Z{r}",
            # last year and seasonality
            "AY": f"=D{r}-364",
            "AZ": "=" + raw_on("uniq_partners_dt_beginning", r),
            "BA": "=" + raw_wk("newjoin_cnt", r) + "+" + raw_wk("resurrection_cnt", r),
            "BB": "=" + raw_wk("attrition_cnt", r) + "+" + raw_wk("temp_attrition_cnt", r) + "-"
                  + raw_wk("rejoin_cnt", r) + "-" + raw_wk("temp_rejoin_cnt", r),
            "BC": f"=IFERROR(BB{r}/(AZ{r}+BA{r}),0)",
            "BD": f"=IFERROR(BC{r}/AVERAGE($BC${FIRST}:$BC${LAST}),1)",
            "BE": f"=IFERROR(INDEX(Inputs!$B${R_SEAS0}:$H${R_SEAS1},MATCH(Inputs!$P${cal},Inputs!$A${R_SEAS0}:$A${R_SEAS1},0),{idx + 1}),0)",
            "BF": f"=MAX(1+{G_FLOOR},1+BE{r})",
            "BG": f"=Inputs!$G${cal}", "BH": f"=Inputs!$H${cal}",
            "BI": f"={ci('own', idx)}" if w == 0 else f"=BI{p}+({ci('t_own', idx)}-{ci('own', idx)})/COUNT($D${FIRST}:$D${LAST})",
            "BJ": f"={ci('ldto', idx)}" if w == 0 else f"=BJ{p}+({ci('t_ldto', idx)}-{ci('ldto', idx)})/COUNT($D${FIRST}:$D${LAST})",
        }
        for letter, _, _ in COLS:
            if letter in ("AB", "AX"):
                continue
            v = f.get(letter)
            fmt = NUM
            if letter in ("C", "D"):
                fmt = DATE
            elif letter in ("V", "Z", "AA", "AF", "AI", "AQ", "AW", "BC", "BE"):
                fmt = PCT
            elif letter in ("BD", "BF"):
                fmt = "0.00"
            elif letter == "AY":
                fmt = DATE
            elif letter in ("A", "B", "Q"):
                fmt = None
            bg = None
            if letter in ("L", "M", "N", "O", "P"):
                bg = YELLOW
            elif letter == "K":
                bg = GREEN
            elif letter == "AU":
                bg = YELLOW
            cput(ws, r, letter, v, fmt, bg=bg)

    # ---- totals row
    r = R_TOT
    put(ws, r, 1, "Total 21 Sep - 27 Dec", bold=True)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    for letter in ["F", "I", "J", "K", "L", "M", "N", "O", "P", "U", "AD", "AE", "AG", "AJ", "AK",
                   "AL", "AM", "AN", "AO", "AR", "AS", "AT", "AU"]:
        cput(ws, r, letter, f"=SUM({letter}{FIRST}:{letter}{LAST})", NUM, bold=True, bg=LIGHT)
    for letter in ["AF", "AI", "AQ"]:
        cput(ws, r, letter, f"=SUM({letter}{FIRST}:{letter}{LAST})", PCT, bold=True, bg=LIGHT)
    cput(ws, r, "Q", "Closing stock on 27 Dec is the last week row", font=F_NOTE)

    # ---- monthly view
    ws.cell(R_MON_T, 1, "MONTHLY VIEW  -  each week counts in the month its Monday falls in; "
                        "month-end stock = last week of that month").font = F_SECTION
    mon_cols = [
        ("Month", None, DATE), ("Weeks", "count", "0"), ("Total buy (new cars)", "AD", NUM),
        ("Total sold", "AE", NUM), ("Fleet (month end)", "=E", NUM), ("EIP net add", "P", NUM),
        ("Own Now placements", "AM", NUM), ("Own Now churn + rollover", "AKAL", NUM),
        ("Own Now net add", "AJ", NUM), ("L+DTO placements", "AT", NUM), ("L+DTO churn", "AS", NUM),
        ("L+DTO net add", "AR", NUM), ("Total placements (recruitment)", "AU", NUM),
        ("EIP (month end)", "=R", NUM), ("Own Now (month end)", "=X", NUM),
        ("L+DTO (month end)", "=W", NUM), ("On road (month end)", "=Y", NUM),
        ("Util (month end)", "=Z", PCT),
    ]
    for j, (text, _, _) in enumerate(mon_cols):
        hdr(ws, R_MON_H, j + 1, text)
    ws.row_dimensions[R_MON_H].height = 40
    rng = f"$C${FIRST}:$C${LAST}"
    for m in range(4):
        r = R_MON0 + m
        put(ws, r, 1, dt.date(2026, 9 + m, 1), "mmm-yy", bold=True)
        for j, (_, src, fmt) in enumerate(mon_cols[1:], start=2):
            if src == "count":
                v = f"=COUNTIF({rng},$A{r})"
            elif src == "AKAL":
                v = f"=SUMIF({rng},$A{r},AK${FIRST}:AK${LAST})+SUMIF({rng},$A{r},AL${FIRST}:AL${LAST})"
            elif src.startswith("="):
                s = newcol(src[1:])
                v = f"=INDEX({s}${FIRST}:{s}${LAST},MATCH($A{r},{rng},1))"
            else:
                s = newcol(src)
                v = f"=SUMIF({rng},$A{r},{s}${FIRST}:{s}${LAST})"
            put(ws, r, j, v, fmt)
    r = R_MON_TOT
    put(ws, r, 1, "Total", bold=True, bg=LIGHT)
    for j, (_, src, fmt) in enumerate(mon_cols[1:], start=2):
        L = get_column_letter(j)
        if src.startswith("="):
            v = f"={L}{R_MON0 + 3}"
        else:
            v = f"=SUM({L}{R_MON0}:{L}{R_MON0 + 3})"
        put(ws, r, j, v, fmt, bold=True, bg=LIGHT)

    # ---- notes
    notes = [
        "HOW THIS TAB WORKS  (all inputs are on the Inputs tab; nothing on this tab is typed)",
        f"Rows 2-{OPEN_ROW} (blue) are the last {N_ACTUAL} actual weeks, read from the raw_performance tab. The plan (row {FIRST} on) starts from the close of the last actual week, Sun 20 Sep.",
        "EIP: the gap to the December target is spread across the weeks by the EIP weights (AG = gap x weight). No EIP churn is modelled, as in Lakshya v4.",
        "LAST YEAR (AY:BD): same week last year (week start - 364 days) from raw_performance. LY net attrition % = (attrition + temp attrition - rejoins - temp rejoins) / (active partners at week start + new joins + resurrections), as in the Weekly Supply Plan. LY attrition index = that week's LY % / the average over the 14 plan weeks.",
        "SEASONALITY (BE:BF): festival impact on recruitment for the event in that week (Inputs, sections 6-7); seasonality factor = 1 + impact, floored. Share of placements (AI, AQ) = base profile x seasonality factor, over the total.",
        "Churn (AK, AS) = straight-line book (BI, BJ: today's book moving evenly to the December target) x Lakshya monthly rate / 4.33 x LY attrition index. So the Lakshya rate sets the level and last year sets the week-to-week shape. Own Now rollover (AL) is not shaped.",
        "Placements (AM, AT) = (gap to December target + all churn over the plan) x that week's share. Net add = placements - churn (AJ, AR), so the book dips in festival weeks and lands exactly on target on 27 Dec.",
        "Recruitment by channel (N:Q) = total placements (AU) x the city's channel mix on the Inputs tab. Net Attrition (W) = Own Now churn + rollover + L+DTO churn.",
        "Fleet (E) = previous week + Total buy (G) - Total sold (H); each month's cars are split evenly across that month's weeks (Inputs, sections 4 and 5). Buy and sold are blank in actual weeks: raw_performance has fleet only. Util (AB) = week-ending cars on road / fleet; red when above the Lakshya ceiling (AC).",
        "Weights sum to 100%, so the last week (w/e Sun 27 Dec, Lakshya's last week) lands exactly on the Lakshya December target for each layer. Check column AV must be 0.",
    ]
    for k, text in enumerate(notes):
        ws.cell(R_NOTES + k, 1, text).font = F_SECTION if k == 0 else F_NOTE

    # ---- conditional formats
    ws.conditional_formatting.add(
        f"AB2:AB{LAST}", ColorScaleRule(start_type="min", start_color="FFF8696B", mid_type="percentile",
                                      mid_value=50, mid_color="FFFFEB84", end_type="max", end_color="FF63BE7B"))
    ws.conditional_formatting.add(
        f"M{FIRST}:M{LAST}", ColorScaleRule(start_type="min", start_color="FFFFFFFF", end_type="max",
                                            end_color="FF57BB8A"))
    red = Font(name="Calibri", size=10, bold=True, color="FFC00000")
    ws.conditional_formatting.add(f"AW2:AW{LAST}", FormulaRule(formula=[f"AW2<0"], font=red))
    ws.conditional_formatting.add(f"AV2:AV{LAST}", FormulaRule(formula=[f"ROUND(AV2,6)<>0"], font=red,
                                                               fill=fill("FFFFC7CE")))
    ws.conditional_formatting.add(f"AT{FIRST}:AT{LAST}", FormulaRule(formula=[f"AT{FIRST}<0"], font=red))
    ws.conditional_formatting.add(f"AM{FIRST}:AM{LAST}", FormulaRule(formula=[f"AM{FIRST}<0"], font=red))
    ws.sheet_view.zoomScale = 90
    return ws


def build_inputs(wb):
    ws = wb.active
    ws.title = "Inputs"
    widths = [26, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.column_dimensions["I"].width = 24
    for L in "JKLMNO":
        ws.column_dimensions[L].width = 16
    ws["A1"] = "Lakshya 15,000 - Weekly Supply Plan  |  INPUTS"
    ws["A1"].font = F_TITLE
    ws["A2"] = ("Blue-on-cream cells are inputs; everything else is a formula. Every city tab reads from this tab. "
                "Targets: Lakshya_15000_Model_v4 (the AOP does not match it, so it is used for reference only). "
                "Opening: reporting DB analytics.ssot_scorecard_agg, CNG, Sun 20 Sep 2026 "
                "(the raw_performance tab in the Weekly Supply Plan sheet stops at 5 Jul 2026).")
    ws["A2"].font = F_NOTE
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A2:T3")
    ws.row_dimensions[2].height = 20

    # ---- 1. global
    ws.cell(R_GLOBAL - 1, 1, "1.  GLOBAL SETTINGS").font = F_SECTION
    hdr(ws, R_GLOBAL, 1, "Setting")
    hdr(ws, R_GLOBAL, 2, "Value")
    hdr(ws, R_GLOBAL, 3, "Note")
    ws.merge_cells(start_row=R_GLOBAL, start_column=3, end_row=R_GLOBAL, end_column=8)
    rows = [
        ("Opening date (actual, Sunday)", dt.date(2026, 9, 20), DATE, True,
         "Last actual week ends here (close of w/c 14 Sep). Opening values in section 3 and the 4 actual weeks on each city tab are read from raw_performance up to this date."),
        ("First plan week starts (Monday)", f"=B{R_GLOBAL + 1}+1", DATE, False, "Current week, Mon 21 - Sun 27 Sep."),
        ("Plan ends (Sunday)", dt.date(2026, 12, 27), DATE, True,
         "Same end as Lakshya v4: w/e Sun 27 Dec. 28-31 Dec is not planned."),
        ("Weeks per month", "=52/12", "0.00", False, "Turns a monthly churn rate into a weekly one."),
        ("India CNG on-road goal, Dec", 15000, NUM, True, "Lakshya lands at 15,082. ~1,000 EV held flat on top = 16,000."),
        ("Largest recruitment drop in one week", -0.75, "0%", True,
         "Floor on the festival impact (section 7). Some history values are below -100% (e.g. Delhi Diwali -163%)."),
    ]
    for k, (label, val, fmt, is_input, note) in enumerate(rows):
        r = R_GLOBAL + 1 + k
        put(ws, r, 1, label)
        (inp if is_input else put)(ws, r, 2, val, fmt)
        c = put(ws, r, 3, note, font=F_NOTE)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=8)

    # ---- sources
    F_LINK = Font(name="Calibri", size=10, color="FF1155CC", underline="single")
    for k, (label, url, text) in enumerate(SOURCES):
        r = R_GLOBAL + 7 + k
        put(ws, r, 1, label, bold=True)
        put(ws, r, 2, link(url, text), font=F_LINK)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)

    # ---- 2. summary
    ws.cell(R_SUM_H - 1, 1, "2.  PLAN SUMMARY - OUTPUT, DO NOT EDIT  (pulled from the city tabs)").font = F_SECTION
    sum_cols = ["City", "On road 20 Sep", "On road 27 Dec", "Lakshya target", "Gap to target",
                "EIP 27 Dec", "Own Now 27 Dec", "L+DTO 27 Dec", "Fleet 27 Dec", "Lakshya fleet Dec",
                "Util 27 Dec", "Ceiling", "Headroom", "EIP net add", "Own Now placements",
                "L+DTO placements", "Total placements", "Peak week placements", "Check (0 = OK)"]
    for j, t in enumerate(sum_cols, start=1):
        hdr(ws, R_SUM_H, j, t)
    ws.row_dimensions[R_SUM_H].height = 40
    for i, city in enumerate(CITIES):
        r = R_SUM0 + i
        s = q(city)
        vals = [
            (city, None), (f"={s}!Y{OPEN_ROW}", NUM), (f"={s}!Y{LAST}", NUM), (f"={ci('t_onroad', i)}", NUM),
            (f"=C{r}-D{r}", NUM), (f"={s}!R{LAST}", NUM), (f"={s}!X{LAST}", NUM), (f"={s}!W{LAST}", NUM),
            (f"={s}!E{LAST}", NUM), (f"={ci('lk_fleet', i)}", NUM), (f"=C{r}/I{r}", PCT),
            (f"={ci('ceiling', i)}", PCT), (f"=L{r}-K{r}", PCT), (f"={s}!P{R_TOT}", NUM),
            (f"={s}!AM{R_TOT}", NUM), (f"={s}!AT{R_TOT}", NUM), (f"={s}!AU{R_TOT}", NUM),
            (f"=MAX({s}!AU{FIRST}:AU{LAST})", NUM),
            (f"=ROUND(SUMPRODUCT(ABS({s}!AV2:AV{LAST})),6)", "0"),
        ]
        for j, (v, fmt) in enumerate(vals, start=1):
            put(ws, r, j, v, fmt, bold=(j == 1))
    r = R_SUM0 + len(CITIES)
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in range(2, len(sum_cols) + 1):
        L = get_column_letter(j)
        if L == "K":
            v, fmt = f"=C{r}/I{r}", PCT
        elif L in ("L", "M"):
            v, fmt = None, PCT
        else:
            v, fmt = f"=SUM({L}{R_SUM0}:{L}{r - 1})", NUM
        put(ws, r, j, v, fmt, bold=True, bg=LIGHT)
    r_india = r
    ws.cell(r_india + 1, 1, "Headroom below 0 = the city is planned above its Lakshya utilisation ceiling "
                            "(shown red). Fleet uses fleet_total_cars_cnt, the same column the Weekly "
                            "Supply Plan uses; Lakshya's 31-Aug fleet base does not match it.").font = F_NOTE
    red = Font(name="Calibri", size=10, bold=True, color="FFC00000")
    ws.conditional_formatting.add(f"M{R_SUM0}:M{r_india - 1}",
                                  FormulaRule(formula=[f"M{R_SUM0}<0"], font=red, fill=fill("FFFFC7CE")))
    ws.conditional_formatting.add(f"E{R_SUM0}:E{r_india}",
                                  FormulaRule(formula=[f"ROUND(E{R_SUM0},0)<>0"], font=red))
    ws.conditional_formatting.add(f"S{R_SUM0}:S{r_india}",
                                  FormulaRule(formula=[f"S{R_SUM0}<>0"], font=red, fill=fill("FFFFC7CE")))

    # ---- 3. city inputs
    ws.cell(R_CITY_H - 2, 1, "3.  CITY INPUTS - opening position, December targets, rates, ceiling, channel mix").font = F_SECTION
    groups = [(2, 6, "OPENING - actual on the opening date (raw_performance)"), (7, 10, "DECEMBER TARGET - Lakshya v4"),
              (11, 14, "RATES - per calendar month"), (15, 15, "GUARDRAIL"),
              (16, 19, "RECRUITMENT CHANNEL MIX - AOP Sep-Dec"), (20, 20, "REFERENCE")]
    for c1, c2, t in groups:
        hdr(ws, R_CITY_H - 1, c1, t, GREY_HDR)
        if c2 > c1:
            ws.merge_cells(start_row=R_CITY_H - 1, start_column=c1, end_row=R_CITY_H - 1, end_column=c2)
    heads = ["City", "Fleet", "On road", "EIP", "Own Now", "Leasing + DTO (= on road - EIP - Own Now)",
             "EIP", "Own Now", "Leasing + DTO", "On road", "L+DTO net churn", "Own Now churn",
             "Own Now purchase rollover", "Own Now: new-car share of placements", "Utilisation ceiling",
             "FSE", "Vendor", "Referrals", "Perf marketing (= 100% - others)", "Lakshya fleet Dec"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_CITY_H, j, t)
    ws.row_dimensions[R_CITY_H].height = 54
    for i, city in enumerate(CITIES):
        r = R_CITY0 + i
        te, to, tl = TARGET[city]
        rl, ro, rr, ns, ce = RATES[city]
        fse, ven, ref = CHANNEL[city]
        put(ws, r, 1, city, bold=True)
        for j, field in ((2, "fleet_total_cars_cnt"), (3, "allotted_cars_eod"), (4, "eip_vehicles_cnt"),
                         (5, "own_now_cars_eod")):
            put(ws, r, j, f'=SUMIFS(raw_performance!${rc(field)}:${rc(field)},raw_performance!$D:$D,$A{r},'
                          f'raw_performance!$E:$E,"CNG",raw_performance!$C:$C,{G_OPEN_DATE})', NUM, bg=ACTUAL)
        put(ws, r, 6, f"=C{r}-D{r}-E{r}", NUM)
        inp(ws, r, 7, te, NUM)
        inp(ws, r, 8, to, NUM)
        inp(ws, r, 9, tl, NUM)
        put(ws, r, 10, f"=G{r}+H{r}+I{r}", NUM)
        inp(ws, r, 11, rl, "0%")
        inp(ws, r, 12, ro, PCT)
        inp(ws, r, 13, rr, PCT)
        inp(ws, r, 14, round(ns, 3), PCT)
        inp(ws, r, 15, ce, PCT)
        inp(ws, r, 16, fse, PCT)
        inp(ws, r, 17, ven, PCT)
        inp(ws, r, 18, ref, PCT)
        put(ws, r, 19, f"=1-P{r}-Q{r}-R{r}", PCT)
        inp(ws, r, 20, LAKSHYA_FLEET_DEC[city], NUM)
    r = R_CITY0 + len(CITIES)
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in [2, 3, 4, 5, 6, 7, 8, 9, 10, 20]:
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{R_CITY0}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)
    for j in range(11, 20):
        put(ws, r, j, None, bg=LIGHT)
    notes = [
        "Opening (blue) is read from the raw_performance tab on the opening date: allotted_cars_eod (on road), eip_vehicles_cnt, own_now_cars_eod, fleet_total_cars_cnt. Leasing + DTO = on road - EIP - Own Now (EIP sits inside leasing in the source).",
        "L+DTO churn: Lakshya v4 planning rate (net basis: a driver who leaves and returns nets out). Own Now churn and rollover: Lakshya v4 city exits divided by the book they ran on, per calendar month.",
        "New-car share: Lakshya v4 new-car Own Now placements / all Own Now placements (information only; it splits AM into AN and AO on the city tabs).",
    ]
    for k, t in enumerate(notes):
        ws.cell(r + 1 + k, 1, t).font = F_NOTE

    # ---- 4/5. cars added / sold by month
    def month_table(r_h, title, data, lakshya, note):
        ws.cell(r_h - 1, 1, title).font = F_SECTION
        hdr(ws, r_h, 1, "City")
        for m in range(4):
            c = hdr(ws, r_h, 2 + m, dt.date(2026, 9 + m, 1))
            c.number_format = "mmm-yy"
        for j, t in enumerate(["Total", "Lakshya Sep-Dec", "Difference"], start=6):
            hdr(ws, r_h, j, t)
        for i, city in enumerate(CITIES):
            r = r_h + 1 + i
            put(ws, r, 1, city, bold=True)
            for m in range(4):
                inp(ws, r, 2 + m, data[city][m], NUM)
            put(ws, r, 6, f"=SUM(B{r}:E{r})", NUM, bold=True)
            inp(ws, r, 7, lakshya[city], NUM)
            put(ws, r, 8, f"=F{r}-G{r}", NUM)
        r = r_h + 1 + len(CITIES)
        put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
        for j in range(2, 9):
            L = get_column_letter(j)
            put(ws, r, j, f"=SUM({L}{r_h + 1}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)
        ws.cell(r + 1, 1, note).font = F_NOTE
        ws.conditional_formatting.add(f"H{r_h + 1}:H{r}", FormulaRule(formula=[f"H{r_h + 1}<>0"], font=red))

    month_table(R_ADD_H, "4.  NEW CARS ADDED TO FLEET, BY MONTH  (Sep = 21-30 Sep only)", ADDS, LAKSHYA_ADDS,
                "Lakshya: 2,300 cars (WagonR 1,200, Dzire 600, Rumion 500), all landed by 30 Nov. Default phasing 50% Oct / 50% Nov - change to the delivery schedule. Each month's cars are split evenly across that month's weeks.")
    month_table(R_SALE_H, "5.  CARS SOLD, BY MONTH  (Sep = 21-30 Sep only)", SALES, LAKSHYA_SALES,
                "Lakshya: 721 cars (AOP 1,776). Sales come out of idle cars, so they change utilisation, not cars on road. Default phasing: even Oct-Dec. Any sold between 1 and 20 Sep are already in the opening fleet - reduce these rows by them.")

    # ---- 6. calendar
    ws.cell(R_CAL_H - 1, 1, "6.  WEEKLY CALENDAR AND PHASING  -  weeks run Mon-Sun; a week counts in the month its Monday falls in").font = F_SECTION
    cal_heads = ["Week #", "Week start (Mon)", "Week end", "Month", "Days in plan", "EIP weight (sums to 100%)",
                 "Own Now base profile", "L+DTO base profile"] + [f"Events - {c}" for c in CITIES] + [
                 "Event used for impact (section 7)"]
    for j, t in enumerate(cal_heads, start=1):
        hdr(ws, R_CAL_H, j, t)
    ws.row_dimensions[R_CAL_H].height = 40
    for w in range(N_WEEKS):
        r = R_CAL0 + w
        put(ws, r, 1, w + 1, "0", bold=True)
        put(ws, r, 2, f"=$B${R_GLOBAL + 2}" if w == 0 else f"=B{r - 1}+7", DATE)
        put(ws, r, 3, f"=MIN(B{r}+6,{G_PLAN_END})", DATE)
        put(ws, r, 4, f"=EOMONTH(B{r},-1)+1", "mmm-yy")
        put(ws, r, 5, f"=C{r}-B{r}+1", "0")
        inp(ws, r, 6, W_EIP[w] / 100, "0%")
        inp(ws, r, 7, W_OWN[w], "0")
        inp(ws, r, 8, W_LDTO[w], "0")
        for k, city in enumerate(CITIES):
            parts = [x for x in (EVENTS_ALL.get(w + 1), EVENTS_CITY.get((city, w + 1))) if x]
            inp(ws, r, 9 + k, "; ".join(parts) if parts else "")
        inp(ws, r, 16, WEEK_EVENT.get(w + 1, ""))
    r = R_CAL0 + N_WEEKS
    put(ws, r, 1, "Total", bold=True, bg=LIGHT)
    for j in (2, 3, 4):
        put(ws, r, j, None, bg=LIGHT)
    put(ws, r, 5, f"=SUM(E{R_CAL0}:E{r - 1})", "0", bold=True, bg=LIGHT)
    put(ws, r, 6, f"=SUM(F{R_CAL0}:F{r - 1})", "0%", bold=True, bg=LIGHT)
    ws.conditional_formatting.add(f"F{r}", FormulaRule(formula=[f"ROUND(F{r},6)<>1"], font=red,
                                                       fill=fill("FFFFC7CE")))
    for j in (7, 8):
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{R_CAL0}:{L}{r - 1})", "0", bold=True, bg=LIGHT)
    notes = [
        "EIP weight: share of the EIP gap (December target - 20 Sep opening) added each week; must total 100% (turns red if not).",
        "Own Now / L+DTO base profile: relative size of each week's placements before seasonality (any scale). On each city tab, placements = base profile x seasonality factor, scaled so the layer lands on its December target.",
        "Default: L+DTO flat (its shape comes from festival weeks and last year's attrition); Own Now builds up as new cars land in Oct-Nov.",
    ]
    for k, t in enumerate(notes):
        ws.cell(r + 1 + k, 1, t).font = F_NOTE

    # ---- 7. seasonality
    ws.cell(R_SEAS_H - 1, 1, "7.  SEASONALITY - festival impact on recruitment (Weekly Supply Plan, seasonality_Impect tab, 'Rec Avg' 2024-25)").font = F_SECTION
    hdr(ws, R_SEAS_H, 1, "Event")
    for k, city in enumerate(CITIES):
        hdr(ws, R_SEAS_H, 2 + k, city)
    for i, (ev, vals) in enumerate(SEASON_REC.items()):
        r = R_SEAS0 + i
        put(ws, r, 1, ev, bold=True)
        for k, v in enumerate(vals):
            inp(ws, r, 2 + k, v, "0%")
    r = R_SEAS1 + 1
    for k, t in enumerate([
        "Change in recruitment in the event week vs a normal week. A city tab looks up the event named for that week in section 6 (last column), "
        "then seasonality factor = 1 + impact, floored at the global setting. Recruitment lost in festival weeks is picked up in the other weeks, "
        "because the total still has to land on the December target.",
        "Kannada Rajyotsava is a Bangalore-only holiday (0 elsewhere). The Hyderabad and Kolkata civic elections have no measured impact.",
    ]):
        ws.cell(r + k, 1, t).font = F_NOTE
    ws.freeze_panes = "B4"
    ws.sheet_view.zoomScale = 90


# ---------------------------------------------------------------- Lakshya v4 as given (for the comparison tab)
LK_UTIL_DEC = {"Mumbai": 0.75, "Delhi NCR": 0.6199, "Bangalore": 0.7694, "Hyderabad": 0.7687,
               "Chennai": 0.7759, "Kolkata": 0.5727, "Pune": 0.6869}
# Placements over the same 14 weeks (w/e 27 Sep - w/e 27 Dec): Weekly L+DTO F:S, Weekly Own Now E:R
LK_LDTO_PL = {"Mumbai": 2258, "Delhi NCR": 2400, "Bangalore": 2054, "Hyderabad": 2284, "Chennai": 1780,
              "Kolkata": 574, "Pune": 1390}
LK_OWN_PL = {"Mumbai": 693, "Delhi NCR": 397, "Bangalore": 653, "Hyderabad": 541, "Chennai": 461,
             "Kolkata": 177, "Pune": 267}
LK_LDTO_WK = [983, 1118, 1070, 923, 777, 522, 442, 603, 1004, 1122, 1096, 1251, 1200, 629]
LK_OWN_WK = [131, 297, 286, 246, 208, 144, 123, 166, 279, 311, 262, 299, 287, 150]
# Month-end books (Lakshya months end on w/e 27 Sep, 25 Oct, 29 Nov, 27 Dec) by city
LK_LDTO_ME = {"Mumbai": (1179, 1183, 1152, 1225), "Delhi NCR": (1488, 1489, 1446, 1535),
              "Bangalore": (1080, 1110, 1109, 1201), "Hyderabad": (1054, 1063, 1041, 1112),
              "Chennai": (925, 943, 933, 1004), "Kolkata": (283, 264, 235, 233),
              "Pune": (678, 656, 612, 631)}
LK_OWN_ME = {"Mumbai": (549, 711, 869, 1006), "Delhi NCR": (688, 757, 804, 850),
             "Bangalore": (687, 824, 961, 1075), "Hyderabad": (314, 448, 582, 700),
             "Chennai": (438, 537, 641, 725), "Kolkata": (205, 245, 274, 305),
             "Pune": (287, 345, 395, 442)}
ME_WEEK_ROWS = (FIRST, FIRST + 4, FIRST + 9, FIRST + 13)  # plan weeks ending 27 Sep, 25 Oct, 29 Nov, 27 Dec


def all_cities(cell):
    return "=" + "+".join(f"{q(c)}!{cell}" for c in CITIES)


def build_compare(wb):
    ws = wb.create_sheet("Lakshya vs Plan", 0)
    widths = [22, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.column_dimensions["P"].width = 60
    ws["A1"] = "Lakshya 15,000 - the plan we were given vs the weekly plan we built"
    ws["A1"].font = F_TITLE
    ws["A2"] = ("Grey headers = Lakshya_15000_Model_v4 as given (typed from the model). Navy headers = this "
                "workbook's weekly plan (live formulas from the city tabs). Weekly plan starts from the actual "
                "position on Sun 20 Sep 2026 and runs to Sun 27 Dec, the same end week as Lakshya.")
    ws["A2"].font = F_NOTE
    ws.merge_cells("A2:P2")
    ws["A3"] = "Lakshya source:"
    ws["A3"].font = F_BOLD
    ws["B3"] = link(LAKSHYA_URL, "Lakshya_15000_Model_v4.xlsx (Google Drive)")
    ws["B3"].font = Font(name="Calibri", size=10, color="FF1155CC", underline="single")
    ws.merge_cells("B3:H3")
    ok_fill, diff_fill = fill("FFC6EFCE"), fill("FFFFEB9C")
    ok_font = Font(name="Calibri", size=10, bold=True, color="FF006100")
    diff_font = Font(name="Calibri", size=10, bold=True, color="FF9C5700")

    def status_rules(rng, first_cell):
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'LEFT({first_cell},1)="M"'], font=ok_font, fill=ok_fill))
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'LEFT({first_cell},1)="D"'], font=diff_font, fill=diff_fill))

    def section(row, text):
        ws.cell(row, 1, text).font = F_SECTION

    def status(diff_cell, tol=0.5):
        return f'=IF(ABS({diff_cell})<{tol},"Match","Differs")'

    # ---- 1. headline
    r = 4
    section(r, "1.  HEADLINE - INDIA")
    r += 1
    for j, (t, col) in enumerate([("Metric", NAVY), ("Lakshya v4", GREY_HDR), ("Weekly plan", NAVY),
                                  ("Difference", NAVY), ("Status", NAVY)], start=1):
        hdr(ws, r, j, t, col)
    hdr(ws, r, 6, "Why", NAVY)
    ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=16)
    rows = [
        ("CNG cars on road, 27 Dec", 15082, all_cities(f"Y{LAST}"), NUM, 0.5,
         "Every city lands on its Lakshya December number."),
        ("EIP, 27 Dec", 3038, all_cities(f"R{LAST}"), NUM, 0.5, ""),
        ("Own Now, 27 Dec", 5103, all_cities(f"X{LAST}"), NUM, 0.5, ""),
        ("Leasing + DTO, 27 Dec", 6941, all_cities(f"W{LAST}"), NUM, 0.5, ""),
        ("New cars added, Sep-Dec", 2300, all_cities(f"AD{R_TOT}"), NUM, 0.5,
         "Same 2,300 cars; phased 50% Oct / 50% Nov, all landed by 30 Nov."),
        ("Cars sold, Sep-Dec", 721, all_cities(f"AE{R_TOT}"), NUM, 0.5, "Same 721 cars; phased evenly Oct-Dec."),
        ("Fleet, 27 Dec", 20913, all_cities(f"E{LAST}"), NUM, 0.5,
         f"Opening fleet differs: weekly plan starts from the DB fleet_total_cars_cnt on 20 Sep (19,167), the "
         f"column the Weekly Supply Plan uses; Lakshya started from 19,334 on 31 Aug."),
        ("Utilisation, 27 Dec", 0.7212, None, PCT, 0.0005, "Same cars on road on a slightly smaller fleet (see fleet line)."),
        ("Starting point - cars on road", 11718, "=" + "+".join(f"{q(c)}!Y{OPEN_ROW}" for c in CITIES), NUM, None,
         "Lakshya starts from the 31 Aug actual; the weekly plan starts from the 20 Sep actual (reporting DB)."),
    ]
    first = r + 1
    for k, (label, lk, plan, fmt, tol, why) in enumerate(rows):
        r += 1
        put(ws, r, 1, label, bold=True)
        put(ws, r, 2, lk, fmt)
        if plan is None:  # utilisation
            plan = f"=C{first}/C{first + 6}"
        put(ws, r, 3, plan, fmt)
        put(ws, r, 4, f"=C{r}-B{r}", fmt)
        put(ws, r, 5, status(f"D{r}", tol) if tol is not None else "Info")
        put(ws, r, 6, why, font=F_NOTE)
        ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=16)
    status_rules(f"E{first}:E{r}", f"E{first}")

    # ---- 2. December landing by city and layer
    r += 3
    section(r, "2.  31 DECEMBER BY CITY - each layer, Lakshya v4 vs weekly plan")
    r += 1
    heads = [("City", NAVY), ("EIP - Lakshya", GREY_HDR), ("EIP - plan", NAVY), ("Own Now - Lakshya", GREY_HDR),
             ("Own Now - plan", NAVY), ("L+DTO - Lakshya", GREY_HDR), ("L+DTO - plan", NAVY),
             ("On road - Lakshya", GREY_HDR), ("On road - plan", NAVY), ("Difference", NAVY), ("Status", NAVY)]
    for j, (t, col) in enumerate(heads, start=1):
        hdr(ws, r, j, t, col)
    ws.row_dimensions[r].height = 32
    first = r + 1
    for city in CITIES:
        r += 1
        s = q(city)
        te, to, tl = TARGET[city]
        put(ws, r, 1, city, bold=True)
        put(ws, r, 2, te, NUM)
        put(ws, r, 3, f"={s}!R{LAST}", NUM)
        put(ws, r, 4, to, NUM)
        put(ws, r, 5, f"={s}!X{LAST}", NUM)
        put(ws, r, 6, tl, NUM)
        put(ws, r, 7, f"={s}!W{LAST}", NUM)
        put(ws, r, 8, f"=B{r}+D{r}+F{r}", NUM)
        put(ws, r, 9, f"={s}!Y{LAST}", NUM)
        put(ws, r, 10, f"=ABS(C{r}-B{r})+ABS(E{r}-D{r})+ABS(G{r}-F{r})", NUM)
        put(ws, r, 11, status(f"J{r}"))
    r += 1
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in range(2, 11):
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{first}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)
    put(ws, r, 11, status(f"J{r}"), bold=True, bg=LIGHT)
    status_rules(f"K{first}:K{r}", f"K{first}")
    ws.cell(r + 1, 1, "Difference = sum of the absolute gaps across the three layers, so 0 means every layer matches.").font = F_NOTE

    # ---- 3. fleet and utilisation
    r += 4
    section(r, "3.  FLEET AND UTILISATION BY CITY - 27 December")
    r += 1
    heads = [("City", NAVY), ("New cars - Lakshya", GREY_HDR), ("New cars - plan", NAVY),
             ("Sold - Lakshya", GREY_HDR), ("Sold - plan", NAVY), ("Fleet - Lakshya", GREY_HDR),
             ("Fleet - plan", NAVY), ("Fleet difference", NAVY), ("Util - Lakshya", GREY_HDR),
             ("Util - plan", NAVY), ("Ceiling", NAVY), ("Within ceiling?", NAVY)]
    for j, (t, col) in enumerate(heads, start=1):
        hdr(ws, r, j, t, col)
    ws.row_dimensions[r].height = 32
    first = r + 1
    for i, city in enumerate(CITIES):
        r += 1
        s = q(city)
        put(ws, r, 1, city, bold=True)
        put(ws, r, 2, LAKSHYA_ADDS[city], NUM)
        put(ws, r, 3, f"={s}!AD{R_TOT}", NUM)
        put(ws, r, 4, LAKSHYA_SALES[city], NUM)
        put(ws, r, 5, f"={s}!AE{R_TOT}", NUM)
        put(ws, r, 6, LAKSHYA_FLEET_DEC[city], NUM)
        put(ws, r, 7, f"={s}!E{LAST}", NUM)
        put(ws, r, 8, f"=G{r}-F{r}", NUM)
        put(ws, r, 9, LK_UTIL_DEC[city], PCT)
        put(ws, r, 10, f"={s}!Z{LAST}", PCT)
        put(ws, r, 11, f"={ci('ceiling', i)}", PCT)
        put(ws, r, 12, f'=IF(J{r}<=K{r}+0.00005,"Match - yes","Differs - above by "&TEXT(J{r}-K{r},"0.0%"))')
    r += 1
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in (2, 3, 4, 5, 6, 7, 8):
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{first}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)
    put(ws, r, 9, 0.7212, PCT, bold=True, bg=LIGHT)
    put(ws, r, 10, f"=({all_cities(f'Y{LAST}')[1:]})/G{r}", PCT, bold=True, bg=LIGHT)
    put(ws, r, 11, None, bg=LIGHT)
    put(ws, r, 12, None, bg=LIGHT)
    status_rules(f"L{first}:L{r - 1}", f"L{first}")
    ws.cell(r + 1, 1, "New cars and sales match Lakshya city by city. Fleet differs only because of the opening fleet "
                      "(see section 1); a city above its ceiling needs more fleet, fewer sales, or a lower target.").font = F_NOTE

    # ---- 4. placements over the same 14 weeks
    r += 4
    section(r, "4.  PLACEMENTS OVER THE SAME 14 WEEKS (w/e 27 Sep - w/e 27 Dec)  -  where the plans differ, and why")
    r += 1
    heads = [("City", NAVY), ("L+DTO - Lakshya", GREY_HDR), ("L+DTO - plan", NAVY), ("Difference", NAVY),
             ("Own Now - Lakshya", GREY_HDR), ("Own Now - plan", NAVY), ("Difference", NAVY),
             ("Total - Lakshya", GREY_HDR), ("Total - plan", NAVY), ("Difference", NAVY)]
    for j, (t, col) in enumerate(heads, start=1):
        hdr(ws, r, j, t, col)
    ws.row_dimensions[r].height = 40
    first = r + 1
    for city in CITIES:
        r += 1
        s = q(city)
        put(ws, r, 1, city, bold=True)
        put(ws, r, 2, LK_LDTO_PL[city], NUM)
        put(ws, r, 3, f"=SUM({s}!AT{FIRST}:AT{LAST})", NUM)
        put(ws, r, 4, f"=C{r}-B{r}", NUM)
        put(ws, r, 5, LK_OWN_PL[city], NUM)
        put(ws, r, 6, f"=SUM({s}!AM{FIRST}:AM{LAST})", NUM)
        put(ws, r, 7, f"=F{r}-E{r}", NUM)
        put(ws, r, 8, f"=B{r}+E{r}", NUM)
        put(ws, r, 9, f"=C{r}+F{r}", NUM)
        put(ws, r, 10, f"=I{r}-H{r}", NUM)
    r += 1
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in range(2, 11):
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{first}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)
    notes = [
        "Why the numbers are close: the weekly plan starts from the actual 20 Sep book (L+DTO 6,271), about 400 below where "
        "Lakshya's path had it, so it needs a bigger net add (+670 vs Lakshya's +261 over these weeks). But a smaller book "
        "loses fewer drivers to churn, which offsets most of it - total placements end up within about 2% of Lakshya's.",
        "Both plans let the book dip in the festival weeks and recover later. Lakshya sets that dip by hand; the weekly plan "
        "takes it from last year's weekly attrition and the festival impact on recruitment (Inputs, sections 6-7; city tabs AY:BJ).",
    ]
    for k, t in enumerate(notes):
        c = ws.cell(r + 1 + k, 1, t)
        c.font = F_NOTE

    # ---- 5. month-end path, India
    r += 5
    section(r, "5.  THE PATH TO DECEMBER - India books on Lakshya's month-end Sundays")
    r += 1
    heads = [("Week ending", NAVY), ("Own Now - Lakshya", GREY_HDR), ("Own Now - plan", NAVY), ("Difference", NAVY),
             ("L+DTO - Lakshya", GREY_HDR), ("L+DTO - plan", NAVY), ("Difference", NAVY), ("Status", NAVY)]
    for j, (t, col) in enumerate(heads, start=1):
        hdr(ws, r, j, t, col)
    ws.row_dimensions[r].height = 32
    first = r + 1
    for m, (d, wrow) in enumerate(zip([dt.date(2026, 9, 27), dt.date(2026, 10, 25), dt.date(2026, 11, 29),
                                       dt.date(2026, 12, 27)], ME_WEEK_ROWS)):
        r += 1
        put(ws, r, 1, d, "dd-mmm-yy", bold=True)
        put(ws, r, 2, sum(LK_OWN_ME[c][m] for c in CITIES), NUM)
        put(ws, r, 3, all_cities(f"X{wrow}"), NUM)
        put(ws, r, 4, f"=C{r}-B{r}", NUM)
        put(ws, r, 5, sum(LK_LDTO_ME[c][m] for c in CITIES), NUM)
        put(ws, r, 6, all_cities(f"W{wrow}"), NUM)
        put(ws, r, 7, f"=F{r}-E{r}", NUM)
        put(ws, r, 8, f'=IF(AND(ABS(D{r})<0.5,ABS(G{r})<0.5),"Match","Differs - catching up")')
    status_rules(f"H{first}:H{r}", f"H{first}")
    ws.cell(r + 1, 1, "We start behind Lakshya's path in September and October, and the weekly plan closes the gap by "
                      "the last week, w/e 27 Dec, where both land on the same December number.").font = F_NOTE

    # ---- 6. weekly India
    r += 4
    section(r, "6.  WEEK BY WEEK - INDIA  (placements = drivers to place in Own Now and Leasing + DTO that week)")
    r += 1
    heads = [("Week (Mon)", NAVY), ("Week end", NAVY), ("L+DTO placements - Lakshya", GREY_HDR),
             ("L+DTO placements - plan", NAVY), ("Difference", NAVY), ("Own Now placements - Lakshya", GREY_HDR),
             ("Own Now placements - plan", NAVY), ("Difference", NAVY), ("EIP net add - plan", NAVY),
             ("Total placements - plan", NAVY), ("On road, week end - plan", NAVY), ("Fleet - plan", NAVY),
             ("Util - plan", NAVY)]
    for j, (t, col) in enumerate(heads, start=1):
        hdr(ws, r, j, t, col)
    ws.row_dimensions[r].height = 40
    first = r + 1
    for w in range(N_WEEKS):
        r += 1
        pr = FIRST + w
        cal = R_CAL0 + w
        put(ws, r, 1, f"=Inputs!B{cal}", DATE, bold=True)
        put(ws, r, 2, f"=Inputs!C{cal}", DATE)
        if w < len(LK_LDTO_WK):
            put(ws, r, 3, LK_LDTO_WK[w], NUM)
            put(ws, r, 6, LK_OWN_WK[w], NUM)
            put(ws, r, 5, f"=D{r}-C{r}", NUM)
            put(ws, r, 8, f"=G{r}-F{r}", NUM)
        else:
            put(ws, r, 3, "not in Lakshya", font=F_NOTE)
            put(ws, r, 6, "not in Lakshya", font=F_NOTE)
            put(ws, r, 5, None)
            put(ws, r, 8, None)
        put(ws, r, 4, all_cities(f"AT{pr}"), NUM)
        put(ws, r, 7, all_cities(f"AM{pr}"), NUM)
        put(ws, r, 9, all_cities(f"P{pr}"), NUM)
        put(ws, r, 10, all_cities(f"AU{pr}"), NUM, bg=YELLOW)
        put(ws, r, 11, all_cities(f"Y{pr}"), NUM)
        put(ws, r, 12, all_cities(f"E{pr}"), NUM)
        put(ws, r, 13, f"=K{r}/L{r}", PCT)
    r += 1
    put(ws, r, 1, "Total", bold=True, bg=LIGHT)
    put(ws, r, 2, None, bg=LIGHT)
    for j in range(3, 11):
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{first}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)
    for j in (11, 12, 13):
        put(ws, r, j, None, bg=LIGHT)
    ws.conditional_formatting.add(
        f"M{first}:M{r - 1}", ColorScaleRule(start_type="min", start_color="FFF8696B", mid_type="percentile",
                                             mid_value=50, mid_color="FFFFEB84", end_type="max", end_color="FF63BE7B"))
    ws.freeze_panes = "B4"
    ws.sheet_view.zoomScale = 90


def build_raw(wb, raw):
    """raw_performance: the SSOT query output, one row per date x city x fuel type."""
    ws = wb.create_sheet("raw_performance")
    date_cols = {"month", "Week", "date", "current_year_week"}
    for j, h in enumerate(raw["hdr"], start=1):
        c = ws.cell(1, j, h)
        c.font = F_HDR
        c.fill = fill(NAVY)
        c.alignment = CENTER
        ws.column_dimensions[get_column_letter(j)].width = 12
    ws.row_dimensions[1].height = 40
    for i, row in enumerate(raw["data"], start=2):
        for j, (h, v) in enumerate(zip(raw["hdr"], row), start=1):
            if v in ("", "NULL", "None"):
                val = None
            elif h in date_cols:
                val = dt.date.fromisoformat(v)
            elif h in ("city", "fuel_type", "short_month", "updated_at"):
                val = v
            else:
                val = float(v) if "." in v else int(v)
            c = ws.cell(i, j, val)
            if h in date_cols:
                c.number_format = "yyyy-mm-dd"
    ws.freeze_panes = "F2"


def main(out, raw_path):
    raw = json.load(open(raw_path))
    RAW_HDR[:] = raw["hdr"]
    wb = Workbook()
    build_inputs(wb)
    for i, city in enumerate(CITIES):
        build_city(wb, i, city)
    build_compare(wb)
    build_raw(wb, raw)
    wb.save(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
