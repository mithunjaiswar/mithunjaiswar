"""Build the Lakshya 15,000 weekly supply plan workbook (1 Inputs tab + 7 city tabs).

Source of targets: Lakshya_15000_Model_v4.xlsx (the AOP does not match it, so it is not used).
Opening position: reporting DB, analytics.ssot_scorecard_agg, CNG, Sun 20 Sep 2026.
City tab layout follows the existing Weekly Supply Plan sheet (columns A-Z), with the
Lakshya build-up (the logic behind each weekly number) to the right of it.

Every number on a city tab is a formula that reads from the Inputs tab.

Usage: python3 build_weekly_supply_plan.py <output.xlsx> <raw.json> [--v2]
  --v2 builds "Lakshya as given": every Own Now and L+DTO number is Lakshya v4's (see LK_WEEKLY).
  raw.json = {"hdr": [...], "data": [[...], ...]}: the SSOT query output (see SSOT_URL).
"""
import datetime as dt
import json
import re
import sys

from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.utils import column_index_from_string, get_column_letter

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from lakshya_cmp import LK_CMP
from plan_history import ALIGNED, ATTR_TREND, CAPACITY, SEASON_CHANGE, SEASON_OFFSETS  # noqa: E402

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
# Own Now new-car share of driver acquisition (Lakshya Inputs sec 5); utilisation ceiling (sec 7)
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
# Lakshya v4 new cars by month (Sep, Oct, Nov, Dec): 2,300 in all, landed by 30 Nov
LAKSHYA_ADDS_M = {"Mumbai": (0, 234, 233, 0), "Delhi NCR": (0, 0, 0, 0), "Bangalore": (0, 317, 316, 0),
                  "Hyderabad": (0, 317, 316, 0), "Chennai": (0, 242, 241, 0), "Kolkata": (0, 0, 0, 0),
                  "Pune": (0, 42, 42, 0)}
LAKSHYA_ADDS = {c: sum(v) for c, v in LAKSHYA_ADDS_M.items()}
# New cars bought and waiting at the stock yard (New Car Stock Report, 27 Sep 2026), by RTO status:
# (RTO process not started, under RTO process, registration done, ready for delivery)
NEW_CAR_STOCK = {"Mumbai": (0, 0, 0, 8), "Delhi NCR": (0, 0, 0, 1), "Bangalore": (102, 0, 12, 50),
                 "Hyderabad": (0, 56, 0, 125), "Chennai": (0, 203, 0, 0), "Kolkata": (0, 0, 0, 0),
                 "Pune": (0, 0, 0, 25)}
# When each status reaches the fleet: (status, first plan week, last plan week); spread evenly in between.
# Plan week 1 = w/c 28 Sep, week 8 = w/c 16 Nov: all 582 cars land within 8 weeks.
DELIVERY_WINDOWS = [("RTO process not started", 5, 8), ("Under RTO process", 3, 6),
                    ("Registration done", 2, 3), ("Ready for delivery", 1, 2)]
# Cars sold by month (Oct, Nov, Dec): Lakshya's 721, even over Oct-Dec
SALES = {"Mumbai": (50, 50, 51), "Delhi NCR": (70, 70, 69), "Bangalore": (17, 17, 16),
         "Hyderabad": (17, 17, 16), "Chennai": (17, 17, 16), "Kolkata": (17, 17, 16),
         "Pune": (54, 54, 53)}
LAKSHYA_SALES = {"Mumbai": 151, "Delhi NCR": 209, "Bangalore": 50, "Hyderabad": 50, "Chennai": 50,
                 "Kolkata": 50, "Pune": 161}

N_WEEKS = 13  # the current week w/c 28 Sep ... w/c 21 Dec (w/e 27 Dec, Lakshya's last week)
# Season block of each plan week, aligned on Diwali (Sun 8 Nov 2026; Bhai Dooj week = w/c 9 Nov). The same
# blocks are measured in 2024 and 2025 (plan_history.py) and only applied where both years agree.
SEASONS = ["Pre-Diwali", "Diwali", "Recovery", "December"]
WEEK_SEASON = ["Pre-Diwali"] * 5 + ["Diwali"] * 2 + ["Recovery"] * 3 + ["December"] * 3   # history blocks (reference)
# The plan uses only two festivals: Diwali (every city, w/c 2 and 9 Nov) and Durga Puja (Kolkata only). Durga Puja 2026
# (Saptami Sat 17 Oct - Dashami Tue 20 Oct) falls across w/c 12 and 19 Oct, so each week takes half of the one-week dip.
FESTIVALS = ["Diwali", "Durga Puja"]
WEEK_FESTIVAL = ["", "", "Durga Puja", "Durga Puja", "", "Diwali", "Diwali", "", "", "", "", "", ""]
# Kolkata, Durga Puja week vs the 4 weeks before: (hiring change, attrition-rate change) in 2024 (w/c 7 Oct) and 2025 (w/c 29 Sep)
DURGA_PUJA = {"Kolkata": ((-0.593, 0.463), (-0.563, -0.102))}
PUJA_WEEK_SHARE = 0.5
EVENTS_ALL = {
    1: "Gandhi Jayanti (Fri 2 Oct)",
    4: "Dussehra (Tue 20 Oct)",
    6: "Diwali (Sun 8 Nov)",
    7: "Bali Pratipada, Bhai Dooj",
    9: "Guru Nanak Jayanti (Tue 24 Nov)",
    13: "Christmas (Fri 25 Dec); last plan week, ends Sun 27 Dec as in Lakshya",
}
EVENTS_CITY = {
    ("Bangalore", 5): "Kannada Rajyotsava (Sun 1 Nov)",
    ("Hyderabad", 7): "GHMC election (Sun 15 Nov)",
    ("Kolkata", 12): "KMC election (Tue 15 Dec)",
}

# AOP FY27 by city, month-end Sep, Oct, Nov, Dec: cars on road incl. EIP, EIP, driver recruitment in the month
AOP = {
    "Mumbai": dict(onroad=(2935, 2628, 2785, 3116), eip=(1029, 929, 1029, 1099), rec=(1212, 772, 681, 1015)),
    "Delhi NCR": dict(onroad=(2584, 2417, 2572, 2845), eip=(82, 65, 64, 82), rec=(831, 676, 807, 1021)),
    "Bangalore": dict(onroad=(2231, 2112, 2105, 2468), eip=(391, 341, 291, 321), rec=(803, 763, 716, 868)),
    "Hyderabad": dict(onroad=(1918, 1871, 2036, 2215), eip=(312, 306, 340, 333), rec=(898, 825, 881, 916)),
    "Chennai": dict(onroad=(2065, 2112, 2112, 2163), eip=(446, 420, 457, 458), rec=(687, 841, 689, 698)),
    "Kolkata": dict(onroad=(793, 711, 770, 815), eip=(81, 71, 78, 88), rec=(320, 264, 297, 313)),
    "Pune": dict(onroad=(1069, 1002, 1066, 1196), eip=(60, 64, 64, 72), rec=(535, 453, 506, 598)),
}

LAKSHYA_URL = "https://docs.google.com/spreadsheets/d/1Bu8NkgNVcakYondqbyK_jW4nFuFDBqEk"
AOP_URL = "https://docs.google.com/spreadsheets/d/1yK2NRIK1B7U-K9wSqGvoFgcl3arVB-Ozybl_St0Z_PA"
SUPPLY_URL = "https://docs.google.com/spreadsheets/d/1Cxg6qsZr6I9nr9OdORAYJVlRc5iB6r0Vnu6k9LKWcjE"
SSOT_URL = "https://docs.google.com/document/d/1UIKW0voWgrUu2HDonBR4GsWdFz8XLVgWq7r5UoaYMpc"
V2_URL = "https://docs.google.com/spreadsheets/d/1mYh3raKeU-taJxLsObbOfNbJpDx4wtx_2OPdJhQZjbY/edit?gid=352333344#gid=352333344"
SOURCES = [
    ("Lakshya source (targets)", LAKSHYA_URL, "Lakshya_15000_Model_v4.xlsx - the December targets and month-end books"),
    ("AOP FY27", AOP_URL, "AOP FY27 - month-end on road, EIP and recruitment (baseline); recruitment channel mix"),
    ("Weekly Supply Plan (format)", SUPPLY_URL, "Weekly Supply Plan - city tab layout"),
    ("SSOT query (raw data)", SSOT_URL, "SSOT query - its output is the raw_performance tab (actuals, run rate, last year)"),
    ("New Car Stock Report", None, "New Car Stock Report, 27 Sep 2026 - 582 cars bought, by city and RTO status (Inputs A6)"),
    ("History 2024-2026", None, "Reporting DB, weekly by city, Jan 2024 - Sep 2026 (plan_history.py): seasonality and hiring capacity"),
]
DIFF_FMT = "+#,##0;-#,##0;0"
SEAS_TAB = "Seasonality Check"
SQ = f"'{SEAS_TAB}'"
R_SU_H = 8                           # 1. used seasonal changes (group header row above); city rows follow
R_SU0 = R_SU_H + 1
R_CK_H = R_SU0 + 8 + 10              # 2. the check (group header above); 2 rows per city (hiring, attrition)
R_CK0 = R_CK_H + 1
R_AT_H = R_CK0 + 16 + 5              # 3. attrition this year vs last (group header above), 12 weeks
R_WK_H = R_AT_H + 12 + 3 + 6         # 4. week by week, aligned on Diwali (first city block header)


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
# The tab reads top to bottom in two parts:
#   PART A  what the plan starts from and what you set
#           A1 dates & switches, A2 city start/targets/rates, A3 current run rate (last 8 weeks),
#           A4 Lakshya month-end targets, A5 AOP month-end, A6 new cars (stock, delivery, pending),
#           A7 cars sold, A8 weekly calendar
#   PART C  output and sources: C1 plan summary, C2 sources
# Seasonality (validated against 2024 and 2025) lives on its own tab (SEAS_TAB).
# Each section is: title row, one "what it does" row, (group header row), header row, data.
_r = 9                     # PART A banner row
N_GLOBAL = 8               # settings in A1
R_GLOBAL = _r + 4          # A1 header row; values start next row
R_CITY_H = R_GLOBAL + N_GLOBAL + 5   # A2 header (group header row above it)
R_CITY0 = R_CITY_H + 1
R_RR_H = R_CITY0 + 8 + 5      # A3 current run rate header (group header row above it)
R_RR0 = R_RR_H + 1
R_MS_H = R_RR0 + 8 + 5        # A4 Lakshya month-end header (group header row above it)
R_MS0 = R_MS_H + 1
R_AOP_H = R_MS0 + 8 + 5       # A5 AOP header (group header row above it)
R_AOP0 = R_AOP_H + 1
R_STK_H = R_AOP0 + 8 + 5      # A6 new-car stock header (group header row above it)
R_STK0 = R_STK_H + 1
R_WIN_H = R_STK0 + 8 + 4      # A6 delivery windows header
R_WIN0 = R_WIN_H + 1
R_FUT_H = R_WIN0 + len(DELIVERY_WINDOWS) + 4   # A6 future purchases header
R_FUT0 = R_FUT_H + 1
R_ADD_H = R_FUT0 + 8 + 4      # A6 weekly deliveries header
R_ADD0 = R_ADD_H + 1
R_SALE_H = R_ADD0 + 8 + 4     # A7 header
R_SALE0 = R_SALE_H + 1
R_CAL_H = R_SALE0 + 8 + 4     # A8 header
R_CAL0 = R_CAL_H + 1
R_SUM_H = R_CAL0 + N_WEEKS + 1 + 7   # C1 header (PART C banner above the title)
R_SUM0 = R_SUM_H + 1
R_SRC_H = R_SUM0 + 8 + 4      # C2 header

MONTHS = ["Sep", "Oct", "Nov", "Dec"]          # Lakshya month-ends (Sep = 27 Sep, now the opening actual)
PLAN_MONTHS = ["Oct", "Nov", "Dec"]            # months with plan weeks
WEEK_MONTH = ["Oct"] * 4 + ["Nov"] * 5 + ["Dec"] * 4   # Lakshya month each plan week rolls up to
MS_WEEKS = (0, 4, 9, 13)  # plan weeks elapsed at each Lakshya month-end (27 Sep, 25 Oct, 29 Nov, 27 Dec)

G_OPEN_DATE = f"Inputs!$B${R_GLOBAL + 1}"
G_PLAN_END = f"Inputs!$B${R_GLOBAL + 3}"
G_WPM = f"Inputs!$B${R_GLOBAL + 4}"
G_LAST = f"Inputs!$B${R_GLOBAL + 6}"    # actuals used up to (input: 26 Sep)
G_CAP = f"Inputs!$B${R_GLOBAL + 7}"     # December target: "Lakshya" (steady hiring ramp) or "Run rate"
G_SEAS = f"Inputs!$B${R_GLOBAL + 8}"    # a seasonal change is used only if both years show at least this

# City-input columns on the Inputs tab (A2)
CI = {k: i + 1 for i, k in enumerate([
    "city", "fleet", "onroad", "eip", "own", "ldto", "t_eip", "t_own", "t_ldto", "t_onroad",
    "r_ldto", "r_own", "r_roll", "newshare", "ceiling", "fse", "vendor", "referral", "perf",
    "lk_fleet"])}
# Current run-rate columns (A3)
RR = {k: i + 1 for i, k in enumerate([
    "city", "rec", "rec_ly", "rec_yoy", "na", "na_rate", "na_rate_ly", "na_yoy", "eip_wk", "own_wk",
    "cap", "cap_from", "u_rec", "u_rate", "u_eip", "u_own"])}


def ci(key, city_idx):
    return f"Inputs!${get_column_letter(CI[key])}${R_CITY0 + city_idx}"


def rr(key, city_idx):
    return f"Inputs!${get_column_letter(RR[key])}${R_RR0 + city_idx}"


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
    ("AF", "Season block", 9), ("AG", "EIP net add (run rate)", 8),
    ("AH", "Own Now book - WB", 8), ("AI", "Drivers for new cars (Own Now)", 9), ("AJ", "Own Now net add", 8),
    ("AK", "Own Now churn (Lakshya rate)", 8), ("AL", "Own Now purchase rollover", 9),
    ("AM", "Own Now driver acquisition", 9), ("AN", "of which new cars", 8),
    ("AO", "of which existing cars", 8),
    ("AP", "L+DTO book - WB", 8), ("AQ", "Net attrition, all drivers (rate x season)", 9), ("AR", "L+DTO net add", 8),
    ("AS", "L+DTO churn (the rest)", 8), ("AT", "L+DTO driver acquisition", 9),
    ("AU", "Total driver acquisition (Own Now + L+DTO)", 10), ("AV", "Check: on road = EIP + L+DTO + Own Now", 9),
    ("AW", "Util headroom", 8), ("AX", "", 2),
    ("AY", "LY week (same week last year)", 9), ("AZ", "LY active partners - WB", 9),
    ("BA", "LY recruitment (new joins + resurrections)", 10), ("BB", "LY net attrition (abs)", 9),
    ("BC", "LY net attrition %", 8), ("BD", "LY attrition index (1 = average week)", 9),
    ("BE", "Hiring: seasonal change (validated)", 9), ("BF", "Attrition: seasonal change (validated)", 9),
    ("BG", "", 2),
    ("BH", "Current hiring run rate (a week, A3)", 10),
    ("BI", "Proven hiring capacity (best 4 weeks, a week)", 10), ("BJ", "New cars going on road (landed last week)", 10),
    ("BK", "Run-rate hiring this week (x season)", 10),
    ("BL", "Extra hiring to reach Lakshya (step x week #)", 11),
    ("BM", "Planned on-road add = EIP + hiring + new-car drivers - attrition", 11), ("BN", "Planned weekly growth %", 8),
    ("BO", "Organic growth % (without new cars)", 8), ("BP", "Driver acquisition vs proven capacity", 10),
    ("BQ", "Gap to Lakshya Dec (week end)", 10),
    ("BR", "Net attrition rate this week (A3 x season)", 9), ("BS", "Run-rate path: cars on road (no extra hiring)", 10),
    ("BT", "Run-rate path: drivers (Own Now + L+DTO)", 10),
    ("BU", "Lakshya month-end this week counts to", 8), ("BV", "EIP month-end target", 8),
    ("BW", "Own Now month-end target (Lakshya)", 9), ("BX", "L+DTO month-end target (Lakshya)", 9),
    ("BY", "On road month-end target (Lakshya)", 9), ("BZ", "AOP month-end on road", 9),
    ("CA", "Plan - Lakshya month-end", 9), ("CB", "Plan - AOP month-end", 9),
    ("CC", "Share of this week's hires still driving on 27 Dec", 9), ("CD", "Share of drivers kept this week", 8),
    ("CE", "Extra hiring within proven capacity", 9), ("CF", "Within-capacity path: drivers", 9),
    ("CG", "Within-capacity path: cars on road", 10),
    ("CH", "Cars short: on road above fleet x max utilisation", 10),
]
LY_BLOCK = ("AY", "AZ", "BA", "BB", "BC", "BD", "BE", "BF")
PACE_BLOCK = ("BH", "BI", "BJ", "BK", "BL", "BM", "BN", "BO", "BP", "BQ", "BR", "BS", "BT")
MS_BLOCK = ("BU", "BV", "BW", "BX", "BY", "BZ", "CA", "CB", "CC", "CD", "CE", "CF", "CG", "CH")
TEAL = "FF1F6F5F"
N_ACTUAL = 4                   # actual weeks shown above the plan (rows 2-5)
FIRST = 2 + N_ACTUAL           # first plan week row
OPEN_ROW = FIRST - 1           # last actual week = opening position
LAST = FIRST + N_WEEKS - 1     # 19
R_TOT = LAST + 2               # totals row
STEP_CELL = f"$BL${R_TOT + 2}"  # city tab: extra hiring step (drivers a week, added once more each week)

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
            color = TEAL if letter in LY_BLOCK else ("FF7F3F00" if letter in PACE_BLOCK else (
                "FF3F3F7F" if letter in MS_BLOCK else (GREY_HDR if grey else NAVY)))
            hdr(ws, 1, column_index_from_string(newcol(letter)), text, color)
    ws.row_dimensions[1].height = 54
    ws.freeze_panes = "F2"

    ev_col = get_column_letter(7 + idx)  # events columns on Inputs calendar: G..M

    # ---- actual weeks (rows 2-5): straight from raw_performance
    def day(col, r, offset):   # value on one date (week start + offset days; a week end not yet loaded -> latest day)
        d = f"MIN($D{r}+{offset},{G_LAST})" if offset > 0 else f"$D{r}+{offset}"
        return (f"SUMIFS(raw_performance!${rc(col)}:${rc(col)},raw_performance!$D:$D,$A{r},"
                f"raw_performance!$E:$E,$B{r},raw_performance!$C:$C,{d})").replace("+-", "-")

    def week(col, r):          # sum over the Mon-Sun week; a week not fully loaded is scaled up to 7 days
        return (f"SUMIFS(raw_performance!${rc(col)}:${rc(col)},raw_performance!$D:$D,$A{r},"
                f"raw_performance!$E:$E,$B{r},raw_performance!$B:$B,$D{r})*7/MIN(7,{G_LAST}-$D{r}+1)")

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
            "I": f"=K{r}+P{r}+U{r}", "J": f"=K{r}+P{r}", "K": f"=SUM(L{r}:O{r})",
            "L": "=" + week("ni_fse_cnt", r) + "+" + week("resurrection_fse_cnt", r),
            "M": "=" + week("ni_vendor_cnt", r) + "+" + week("resurrection_vendor_cnt", r),
            "N": "=" + week("ni_driver_referral_cnt", r) + "+" + week("resurrection_driver_referral_cnt", r),
            "O": "=" + week("ni_perf_mktg_cnt", r) + "+" + week("resurrection_perf_mktg_cnt", r),
            "P": "=" + week("Net EIP Add-ons", r),
            "Q": f'=IF({G_LAST}-$D{r}+1<7,"ACTUAL - "&({G_LAST}-$D{r}+1)&" of 7 days loaded, flows scaled to a week","ACTUAL - raw_performance")',
            "R": "=" + day("eip_vehicles_cnt", r, 6),
            "U": "=-(" + week("attrition_cnt", r) + "+" + week("temp_attrition_cnt", r) + "-" + week("rejoin_cnt", r)
                 + "-" + week("temp_rejoin_cnt", r) + ")",
            "V": f"=IF(H{r}=0,0,-U{r}/H{r})",
            "W": f"=Y{r}-R{r}-X{r}",
            "X": "=" + day("own_now_cars_eod", r, 6),
            "Y": "=" + day("allotted_cars_eod", r, 6),
            "Z": f"=Y{r}/E{r}", "AA": f"={ci('ceiling', idx)}",
            "AC": 7, "AU": f"=K{r}",
            "AV": f"=Y{r}-(R{r}+W{r}+X{r})", "AW": f"=AA{r}-Z{r}",
        }
        for letter, _, _ in COLS:
            if letter in ("AB", "AX", "BG") or letter in MS_BLOCK:
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
    L = get_column_letter
    wim = {m: WEEK_MONTH.count(m) for m in PLAN_MONTHS}
    for w in range(N_WEEKS):
        r = FIRST + w
        p = r - 1
        cal = R_CAL0 + w
        m = PLAN_MONTHS.index(WEEK_MONTH[w])
        f = {
            "A": f"=$A$2", "B": f"=$B$2", "C": f"=EOMONTH(D{r},-1)+1", "D": f"=Inputs!$B${cal}",
            "E": f"=E{p}+AD{r}-AE{r}", "F": f"=E{r}-E{p}", "G": f"=Y{p}", "H": f"=W{p}+X{p}",
            "I": f"=K{r}+P{r}+U{r}", "J": f"=K{r}+P{r}", "K": f"=SUM(L{r}:O{r})",
            "L": f"=AU{r}*{ci('fse', idx)}", "M": f"=AU{r}*{ci('vendor', idx)}",
            "N": f"=AU{r}*{ci('referral', idx)}", "O": f"=AU{r}*{ci('perf', idx)}",
            "P": f"=AG{r}", "Q": f"=Inputs!${ev_col}${cal}", "R": f"=R{p}+P{r}",
            "U": f"=(AJ{r}+AR{r})-(AM{r}+AT{r})", "V": f"=IF(H{r}=0,0,-U{r}/H{r})",
            "W": f"=W{p}+AR{r}", "X": f"=X{p}+AJ{r}", "Y": f"=G{r}+I{r}", "Z": f"=Y{r}/E{r}",
            "AA": f"={ci('ceiling', idx)}",
            "AC": f"=Inputs!$E${cal}",
            # cars reaching the fleet this week (Inputs A6) and cars sold (A7)
            "AD": f"=Inputs!${L(2 + w)}${R_ADD0 + idx}",
            "AE": f"=Inputs!${L(2 + m)}${R_SALE0 + idx}/{wim[WEEK_MONTH[w]]}",
            "AF": f"=Inputs!$F${cal}",
            # layers: EIP at its run rate; Own Now = drivers for new cars + its existing-car trend; L+DTO = the rest
            "AG": f"={rr('u_eip', idx)}*AC{r}/7",
            "AH": f"=X{p}",
            "AI": f"=BJ{r}",
            "AJ": f"=AI{r}+{rr('u_own', idx)}*AC{r}/7",
            "AK": f"=AH{r}*{ci('r_own', idx)}/{G_WPM}*AC{r}/7",
            "AL": f"=AH{r}*{ci('r_roll', idx)}/{G_WPM}*AC{r}/7",
            "AM": f"=AJ{r}+AK{r}+AL{r}",
            "AN": f"=AI{r}",
            "AO": f"=AM{r}-AN{r}",
            "AP": f"=W{p}",
            "AQ": f"=(AH{r}+AP{r})*BR{r}*AC{r}/7",
            "AR": f"=(BK{r}+BL{r}-AQ{r})-AJ{r}",
            "AS": f"=AQ{r}-AK{r}-AL{r}",
            "AT": f"=AR{r}+AS{r}",
            "AU": f"=AM{r}+AT{r}",
            "AV": f"=Y{r}-(R{r}+W{r}+X{r})", "AW": f"=AA{r}-Z{r}",
            # last year, for reference
            "AY": f"=D{r}-364",
            "AZ": "=" + raw_on("uniq_partners_dt_beginning", r),
            "BA": "=" + raw_wk("newjoin_cnt", r) + "+" + raw_wk("resurrection_cnt", r),
            "BB": "=" + raw_wk("attrition_cnt", r) + "+" + raw_wk("temp_attrition_cnt", r) + "-"
                  + raw_wk("rejoin_cnt", r) + "-" + raw_wk("temp_rejoin_cnt", r),
            "BC": f"=IFERROR(BB{r}/(AZ{r}+BA{r}),0)",
            "BD": f"=IFERROR(BC{r}/AVERAGE($BC${FIRST}:$BC${LAST}),1)",
            # seasonal changes that showed in both 2024 and 2025 (Seasonality Check tab), else 0
            "BE": f"=IFERROR(INDEX({SQ}!$B${R_SU0 + idx}:$E${R_SU0 + idx},MATCH(AF{r},{SQ}!$B${R_SU_H}:$E${R_SU_H},0)),0)",
            "BF": f"=IFERROR(INDEX({SQ}!$F${R_SU0 + idx}:$I${R_SU0 + idx},MATCH(AF{r},{SQ}!$F${R_SU_H}:$I${R_SU_H},0)),0)",
            # driver acquisition: one line = the 8-week run rate + a steady ramp, dipping only for festivals; new-car drivers come out of it
            "BH": f"={rr('u_rec', idx)}",
            "BI": f"={rr('cap', idx)}",
            "BJ": "=0" if w == 0 else f"=AD{p}",
            "BK": f"=BH{r}*(1+BE{r})*AC{r}/7",
            # the plan's extra hiring: the steady ramp to Lakshya, the same ramp kept within proven capacity, or none
            "BL": f'=IF({G_CAP}="Lakshya",{STEP_CELL}*{w + 1}*(1+BE{r})*AC{r}/7,IF({G_CAP}="Capacity",CE{r},0))',
            "CE": f"=MIN({STEP_CELL}*{w + 1}*(1+BE{r})*AC{r}/7,BI{r}*(1+BE{r})*AC{r}/7-BK{r})",  # total acquisition never above proven capacity (x festival dip)
            "CF": (f"=AH{r}+AP{r}+BK{r}+CE{r}-(AH{r}+AP{r})*BR{r}*AC{r}/7" if w == 0
                   else f"=CF{p}+BK{r}+CE{r}-CF{p}*BR{r}*AC{r}/7"),
            "CG": f"=R{r}+CF{r}",
            "CH": f"=MAX(0,Y{r}-E{r}*AA{r})",
            "BM": f"=AG{r}+BK{r}+BL{r}-AQ{r}",
            "BN": f"=BM{r}/G{r}",
            "BO": f"=(BM{r}-AI{r})/G{r}",
            "BP": f'=IF(AU{r}>BI{r}*AC{r}/7+0.5,"Above capacity","Within capacity")',
            "BQ": f"={ci('t_onroad', idx)}-Y{r}",
            "BR": f"={rr('u_rate', idx)}*(1+BF{r})",
            # run-rate path: same EIP, hiring at the 8-week run rate (festival dips only), no extra ramp
            "BT": (f"=AH{r}+AP{r}+BK{r}-(AH{r}+AP{r})*BR{r}*AC{r}/7" if w == 0
                   else f"=BT{p}+BK{r}-BT{p}*BR{r}*AC{r}/7"),
            "BS": f"=R{r}+BT{r}",
            # Lakshya and AOP month-ends (Inputs A4, A5)
            "BU": f"=Inputs!$N${cal}",
            "BV": f"=INDEX(Inputs!$B${R_MS0 + idx}:$E${R_MS0 + idx},MATCH(BU{r},Inputs!$B${R_MS_H}:$E${R_MS_H},0))",
            "BW": f"=INDEX(Inputs!$F${R_MS0 + idx}:$I${R_MS0 + idx},MATCH(BU{r},Inputs!$F${R_MS_H}:$I${R_MS_H},0))",
            "BX": f"=INDEX(Inputs!$J${R_MS0 + idx}:$M${R_MS0 + idx},MATCH(BU{r},Inputs!$J${R_MS_H}:$M${R_MS_H},0))",
            "BY": f"=BV{r}+BW{r}+BX{r}",
            "BZ": f"=INDEX(Inputs!$B${R_AOP0 + idx}:$E${R_AOP0 + idx},MATCH(BU{r},Inputs!$B${R_AOP_H}:$E${R_AOP_H},0))",
            "CA": f"=Y{r}-BY{r}", "CB": f"=Y{r}-BZ{r}",
            "CC": "=1" if w == N_WEEKS - 1 else f"=PRODUCT(CD{r + 1}:CD{LAST})",
            "CD": f"=1-BR{r}*AC{r}/7",
        }
        if V2:
            f.update(v2_city_overrides(idx, w, r, p))
        for letter, _, _ in COLS:
            if letter in ("AB", "AX", "BG"):
                continue
            v = f.get(letter)
            fmt = NUM
            if letter in ("C", "D", "AY"):
                fmt = DATE
            elif letter in ("V", "Z", "AA", "AW", "BC", "BE", "BF", "BN", "BO", "BR", "CC", "CD"):
                fmt = PCT
            elif letter in ("AF", "BP", "BU", "A", "B", "Q"):
                fmt = None
            elif letter == "BD":
                fmt = "0.00"
            elif letter in ("CA", "CB", "BM"):
                fmt = DIFF_FMT
            bg = None
            if letter in ("L", "M", "N", "O", "P", "AU"):
                bg = YELLOW
            elif letter == "K":
                bg = GREEN
            cput(ws, r, letter, v, fmt, bg=bg)

    # ---- totals row
    r = R_TOT
    put(ws, r, 1, "Total w/c 28 Sep - 27 Dec", bold=True)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    for letter in ["F", "I", "J", "K", "L", "M", "N", "O", "P", "U", "AD", "AE", "AG", "AI", "AJ", "AK",
                   "AL", "AM", "AN", "AO", "AQ", "AR", "AS", "AT", "AU", "BJ", "BK", "BL", "BM", "CE"]:
        cput(ws, r, letter, f"=SUM({letter}{FIRST}:{letter}{LAST})", NUM, bold=True, bg=LIGHT)
    cput(ws, r, "BP", f'=COUNTIF(BP{FIRST}:BP{LAST},"Above capacity")&" weeks above capacity"', bold=True, bg=LIGHT)
    cput(ws, r, "Q", "Closing stock on 27 Dec is the last week row", font=F_NOTE)
    # the extra hiring step: the same extra added every week (1x in week 1, 2x in week 2, ...) so that 27 Dec lands on
    # Lakshya. Solved in one go: each extra hire made in week k is still driving on 27 Dec with the share in CC.
    r = R_TOT + 2
    cput(ws, r, "BH", "Extra hiring step (drivers a week, added once more each week)", bold=True)
    ws.merge_cells(f"BH{r}:BK{r}")
    rng = lambda c: f"${c}${FIRST}:${c}${LAST}"
    cput(ws, r, "BL", (f'=({ci("t_onroad", idx)}-BS{LAST})/SUMPRODUCT((ROW({rng("BE")})-{FIRST - 1})'
                       f'*(1+{rng("BE")})*{rng("AC")}/7*{rng("CC")})'), "0.0", bold=True, bg=INPUT)
    cput(ws, r, "BM", "Step = (Lakshya 27 Dec - run-rate path in BS) spread as a steady ramp (negative = hire a little below the run rate). Inputs A1 decides how much of it the plan "
                      "uses: all (Lakshya), only within proven capacity (Capacity, column CE), or none (Run rate).", font=F_NOTE)

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
    ws.conditional_formatting.add(f"BP{FIRST}:BP{LAST}", FormulaRule(formula=[f'BP{FIRST}="Above capacity"'], font=red,
                                                                     fill=fill("FFFFC7CE")))
    ws.conditional_formatting.add(f"BP{FIRST}:BP{LAST}", FormulaRule(formula=[f'BP{FIRST}="Within capacity"'],
                                                                     font=Font(name="Calibri", size=10, color="FF006100"),
                                                                     fill=fill("FFC6EFCE")))
    for c_ in ("CA", "CB"):
        ws.conditional_formatting.add(f"{c_}{FIRST}:{c_}{LAST}", FormulaRule(formula=[f"{c_}{FIRST}<-0.5"], font=red))
    ws.sheet_view.zoomScale = 90
    return ws


F_WHAT = Font(name="Calibri", size=10, italic=True, color="FF404040")
F_HIST = Font(name="Calibri", size=10, italic=True, color="FF595959")
F_BANNER = Font(name="Calibri", size=12, bold=True, color="FFFFFFFF")
HIST = "FFEDEDED"
RED_FONT = Font(name="Calibri", size=10, bold=True, color="FFC00000")
LAST_COL = 20  # banners run across A:T


def note(ws, r, text):
    ws.cell(r, 1, text).font = F_NOTE


def banner(ws, r, text, color):
    for j in range(1, LAST_COL + 1):
        ws.cell(r, j).fill = fill(color)
    ws.cell(r, 1, text).font = F_BANNER
    ws.row_dimensions[r].height = 22


def title(ws, r, code, text, what):
    ws.cell(r, 1, f"{code}   {text}").font = F_SECTION
    ws.cell(r + 1, 1, what).font = F_WHAT


def hist(ws, r, j, v, fmt="0.0%"):
    return put(ws, r, j, v, fmt, font=F_HIST, bg=HIST)


def india_row(ws, r, cols, fmt=NUM):
    """INDIA total of the 7 city rows directly above r."""
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in cols:
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{r - len(CITIES)}:{L}{r - 1})", fmt, bold=True, bg=LIGHT)


def _raw_sum(field, r, ly=False, date=None):
    """SUMIFS over raw_performance for the city in column A of row r (CNG). Default window: the 8 weeks to the
    latest actual date; date= a single day instead. ly=True shifts the window back 364 days."""
    c = rc(field)
    back = "-364" if ly else ""
    base = f"raw_performance!${c}:${c},raw_performance!$D:$D,$A{r},raw_performance!$E:$E,\"CNG\",raw_performance!$C:$C,"
    if date is not None:
        return f"SUMIFS({base}{date}{back})"
    return f"SUMIFS({base}\">\"&({G_OPEN_DATE}-56{back}),raw_performance!$C:$C,\"<=\"&({G_LAST}{back}))"


def _raw_avg(field, r, ly=False):
    c = rc(field)
    back = "-364" if ly else ""
    return (f"AVERAGEIFS(raw_performance!${c}:${c},raw_performance!$D:$D,$A{r},raw_performance!$E:$E,\"CNG\","
            f"raw_performance!$C:$C,\">\"&({G_OPEN_DATE}-56{back}),raw_performance!$C:$C,\"<=\"&({G_LAST}{back}))")


def build_inputs(wb):
    ws = wb.active
    ws.title = "Inputs"
    ws.column_dimensions["A"].width = 30
    for j in range(2, 23):
        ws.column_dimensions[get_column_letter(j)].width = 11
    ws.sheet_properties.tabColor = "FFF1C232"
    L = get_column_letter
    n = len(CITIES)
    WEEKS_RR = f"((({G_LAST})-({G_OPEN_DATE}-56))/7)"   # weeks of actuals in the run-rate window

    # ---- top: what this tab is, colour key, contents
    ws["A1"] = "INPUTS  -  every number the plan is built from"
    ws["A1"].font = F_TITLE
    ws["A2"] = ("The plan starts from the latest actual and runs on today's hiring and attrition. Change a cream cell and "
                "every city tab, the dashboards and the Read Me update.")
    ws["A2"].font = F_WHAT
    ws["A3"] = "Colour key:"
    ws["A3"].font = F_BOLD
    for c1, text, bg, font in ((2, "You can change", INPUT, F_INPUT), (4, "Actual (raw_performance)", ACTUAL, F_BODY),
                               (6, "Formula - leave it", None, F_BODY), (8, "History (reference)", HIST, F_HIST),
                               (10, "Total / output", LIGHT, F_BOLD)):
        c = put(ws, 3, c1, text, font=font, bg=bg)
        c.alignment = CENTER
        put(ws, 3, c1 + 1, None, bg=bg)
        ws.merge_cells(start_row=3, start_column=c1, end_row=3, end_column=c1 + 1)
    parts = [
        ("PART A  What the plan runs on", [("A1", "Dates and switches", R_GLOBAL - 2), ("A2", "City start, Dec targets", R_CITY_H - 3),
                                           ("A3", "Current run rate", R_RR_H - 3), ("A4", "Lakshya month-ends", R_MS_H - 3),
                                           ("A5", "AOP month-ends", R_AOP_H - 3), ("A6", "New cars", R_STK_H - 3),
                                           ("A7", "Cars sold", R_SALE_H - 2), ("A8", "Weekly calendar", R_CAL_H - 2)]),
        ("Seasonality", [("tab", f"Checked city by city against 2024 and 2025: {SEAS_TAB} tab", None)]),
        ("PART C  Output and sources", [("C1", "Plan summary by city", R_SUM_H - 2), ("C2", "Sources", R_SRC_H - 2)]),
    ]
    ws["A5"] = "Contents"
    ws["A5"].font = F_BOLD
    for k, (part, secs) in enumerate(parts):
        r = 6 + k
        put(ws, r, 1, part, bold=True)
        put(ws, r, 2, "   |   ".join(name if row is None else f"{code} {name} (row {row})" for code, name, row in secs))
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=LAST_COL)

    # ================================================================ PART A
    banner(ws, R_GLOBAL - 4, "PART A  -  WHAT THE PLAN RUNS ON  (cream cells can be changed)", NAVY)

    # ---- A1. dates and switches
    title(ws, R_GLOBAL - 2, "A1", "PLAN DATES AND SWITCHES",
          "The plan starts from the actual on the opening Sunday and plans the current week onwards.")
    hdr(ws, R_GLOBAL, 1, "Setting")
    hdr(ws, R_GLOBAL, 2, "Value")
    hdr(ws, R_GLOBAL, 3, "What it does")
    ws.merge_cells(start_row=R_GLOBAL, start_column=3, end_row=R_GLOBAL, end_column=14)
    rows = [
        ("Opening date (last actual Sunday)", dt.date(2026, 9, 27), DATE, True,
         "The plan starts from the actual on this Sunday; the current week (w/c 28 Sep) is plan week 1."),
        ("First plan week starts (Monday)", f"=B{R_GLOBAL + 1}+1", DATE, False, "The current week."),
        ("Plan ends (Sunday)", dt.date(2026, 12, 27), DATE, True, "Same end as Lakshya v4: w/e Sun 27 Dec."),
        ("Weeks per month", "=52/12", "0.00", False, "Turns monthly churn rates into weekly ones."),
        ("India CNG on-road goal, Dec", 15000, NUM, True, "Reference. Lakshya's city targets add up to 15,082."),
        ("Actuals used up to", dt.date(2026, 9, 26), DATE, True,
         "The plan is based on actuals up to this day (Sat 26 Sep): opening numbers, the run rate and the last actual week "
         "(w/c 21 Sep, 6 of 7 days, scaled to a week). Move it on only when newer days are loaded in raw_performance."),
        ("December target", "Capacity", None, True,
         "Capacity (used) = the steady hiring ramp toward Lakshya, but total driver acquisition in a week (run rate + drivers for new "
         "cars + ramp) never above the city's best (proven capacity, Inputs A3) - 27 Dec may land below Lakshya. Lakshya = the full "
         "ramp to Lakshya, even above proven capacity (weeks show red). Run rate = no extra hiring."),
        ("Seasonal change: minimum in both years", 0.05, "0%", True,
         f"History check only ({SEAS_TAB}, section 2). The plan's only seasonal dips are Diwali and Durga Puja (Kolkata)."),
    ]
    for k, (label, val, fmt, is_input, what) in enumerate(rows):
        r = R_GLOBAL + 1 + k
        put(ws, r, 1, label, bold=True)
        (inp if is_input else put)(ws, r, 2, val, fmt)
        put(ws, r, 3, what)
        for j in range(4, 15):
            put(ws, r, j, None)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=14)
    dv = DataValidation(type="list", formula1='"Lakshya,Capacity,Run rate"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(f"B{R_GLOBAL + 7}")

    # ---- A2. city start, targets, rates
    title(ws, R_CITY_H - 3, "A2", "CITY START AND DECEMBER TARGETS",
          "Where each city starts (actual, latest day loaded) and where Lakshya wants it on 27 Dec.")
    groups = [(2, 6, "START - actual (raw_performance)"), (7, 10, "DECEMBER TARGET - Lakshya v4"),
              (11, 14, "LAKSHYA RATES - per month"), (15, 15, "CEILING"),
              (16, 19, "RECRUITMENT CHANNEL MIX - AOP"), (20, 20, "REFERENCE")]
    for c1, c2, t in groups:
        hdr(ws, R_CITY_H - 1, c1, t, GREY_HDR)
        if c2 > c1:
            ws.merge_cells(start_row=R_CITY_H - 1, start_column=c1, end_row=R_CITY_H - 1, end_column=c2)
    heads = ["City", "Fleet", "On road", "EIP", "Own Now", "Leasing + DTO",
             "EIP", "Own Now", "Leasing + DTO", "On road", "L+DTO churn", "Own Now churn",
             "Own Now rollover", "Own Now new-car share", "Max utilisation",
             "FSE", "Vendor", "Referrals", "Perf marketing", "Lakshya fleet Dec"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_CITY_H, j, t)
    ws.row_dimensions[R_CITY_H].height = 30
    ws.row_dimensions[R_CITY_H - 1].height = 30
    for i, city in enumerate(CITIES):
        r = R_CITY0 + i
        te, to, tl = TARGET[city]
        rl, ro, rrl, ns, ce = RATES[city]
        fse, ven, ref = CHANNEL[city]
        put(ws, r, 1, city, bold=True)
        for j, field in ((2, "fleet_total_cars_cnt"), (3, "allotted_cars_eod"), (4, "eip_vehicles_cnt"),
                         (5, "own_now_cars_eod")):
            put(ws, r, j, "=" + _raw_sum(field, r, date=G_LAST), NUM, bg=ACTUAL)
        put(ws, r, 6, f"=C{r}-D{r}-E{r}", NUM)
        inp(ws, r, 7, te, NUM)
        inp(ws, r, 8, to, NUM)
        inp(ws, r, 9, tl, NUM)
        put(ws, r, 10, f"=G{r}+H{r}+I{r}", NUM)
        inp(ws, r, 11, rl, "0%")
        inp(ws, r, 12, ro, PCT)
        inp(ws, r, 13, rrl, PCT)
        inp(ws, r, 14, round(ns, 3), PCT)
        inp(ws, r, 15, ce, PCT)
        inp(ws, r, 16, fse, PCT)
        inp(ws, r, 17, ven, PCT)
        inp(ws, r, 18, ref, PCT)
        put(ws, r, 19, f"=1-P{r}-Q{r}-R{r}", PCT)
        inp(ws, r, 20, LAKSHYA_FLEET_DEC[city], NUM)
    r = R_CITY0 + n
    india_row(ws, r, [2, 3, 4, 5, 6, 7, 8, 9, 10, 20])
    for j in range(11, 20):
        put(ws, r, j, None, bg=LIGHT)
    note(ws, r + 1, "Leasing + DTO = on road - EIP - Own Now. Lakshya's Own Now churn and rollover only split the plan's attrition "
                    "between Own Now and L+DTO; the total comes from the current run rate (A3).")

    # ---- A3. current run rate
    title(ws, R_RR_H - 3, "A3", "CURRENT RUN RATE  -  the last 8 weeks, and the same weeks last year",
          "What the city is doing now (raw_performance, live). The plan's hiring and attrition start from the cream "
          "columns on the right; change them only with a reason.")
    groups = [(2, 4, "DRIVER ACQUISITION a week (new joins + resurrections)"), (5, 8, "NET ATTRITION (attrition + temp - rejoins)"),
              (9, 10, "BOOK CHANGE a week"), (11, 12, "PROVEN HIRING CAPACITY"), (13, 16, "USED IN THE PLAN")]
    for c1, c2, t in groups:
        hdr(ws, R_RR_H - 1, c1, t, GREY_HDR)
        ws.merge_cells(start_row=R_RR_H - 1, start_column=c1, end_row=R_RR_H - 1, end_column=c2)
    heads = ["City", "Last 8 weeks", "Same weeks last year", "This year vs last",
             "Drivers leaving a week", "Rate a week (this year)", "Rate a week (last year)", "This year vs last",
             "EIP", "Own Now", "Best 4 weeks since Sep 2025 (a week)", "Best 4 weeks began",
             "Driver acquisition a week", "Net attrition rate a week", "EIP net add a week", "Own Now net add a week (existing cars)"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_RR_H, j, t)
    ws.row_dimensions[R_RR_H].height = 44
    ws.row_dimensions[R_RR_H - 1].height = 30
    for i, city in enumerate(CITIES):
        r = R_RR0 + i
        put(ws, r, 1, city, bold=True)
        rec = lambda ly=False: f"({_raw_sum('newjoin_cnt', r, ly)}+{_raw_sum('resurrection_cnt', r, ly)})"
        na = lambda ly=False: (f"({_raw_sum('attrition_cnt', r, ly)}+{_raw_sum('temp_attrition_cnt', r, ly)}"
                               f"-{_raw_sum('rejoin_cnt', r, ly)}-{_raw_sum('temp_rejoin_cnt', r, ly)})")
        put(ws, r, 2, f"={rec()}/{WEEKS_RR}", NUM, bg=ACTUAL)
        put(ws, r, 3, f"={rec(True)}/{WEEKS_RR}", NUM, font=F_HIST, bg=HIST)
        put(ws, r, 4, f"=IFERROR(B{r}/C{r}-1,0)", "+0%;-0%;0%")
        put(ws, r, 5, f"={na()}/{WEEKS_RR}", NUM, bg=ACTUAL)
        put(ws, r, 6, f"=IFERROR(E{r}/{_raw_avg('uniq_partners_dt_beginning', r)},0)", PCT, bg=ACTUAL)
        put(ws, r, 7, f"=IFERROR({na(True)}/{WEEKS_RR}/{_raw_avg('uniq_partners_dt_beginning', r, True)},0)", PCT,
            font=F_HIST, bg=HIST)
        put(ws, r, 8, f"=IFERROR(F{r}/G{r}-1,0)", "+0%;-0%;0%")
        for j, field in ((9, "eip_vehicles_cnt"), (10, "own_now_cars_eod")):
            put(ws, r, j, f"=({_raw_sum(field, r, date=G_LAST)}-{_raw_sum(field, r, date=f'({G_OPEN_DATE}-56)')})/{WEEKS_RR}",
                "+#,##0.0;-#,##0.0;0", bg=ACTUAL)
        cap, since = CAPACITY[city]
        put(ws, r, 11, cap, NUM, font=F_HIST, bg=HIST)
        put(ws, r, 12, dt.date.fromisoformat(since), "dd-mmm-yy", font=F_HIST, bg=HIST)
        put(ws, r, 13, f"=B{r}", NUM, font=F_INPUT, bg=INPUT)
        put(ws, r, 14, f"=F{r}", PCT, font=F_INPUT, bg=INPUT)
        inp(ws, r, 15, 0, "+#,##0.0;-#,##0.0;0")
        put(ws, r, 16, f"=J{r}", "+#,##0.0;-#,##0.0;0", font=F_INPUT, bg=INPUT)
    r = R_RR0 + n
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    r0, r1 = R_RR0, R_RR0 + n - 1
    drivers = f"SUMPRODUCT(E{r0}:E{r1}/F{r0}:F{r1})"    # average drivers in the window, from leavers / rate
    for j in (2, 3, 5, 9, 10, 11, 13, 15, 16):
        put(ws, r, j, f"=SUM({L(j)}{r0}:{L(j)}{r1})", NUM if j not in (9, 10, 15, 16) else "+#,##0.0;-#,##0.0;0",
            bold=True, bg=LIGHT)
    put(ws, r, 4, f"=IFERROR(B{r}/C{r}-1,0)", "+0%;-0%;0%", bold=True, bg=LIGHT)
    put(ws, r, 6, f"=E{r}/{drivers}", PCT, bold=True, bg=LIGHT)
    put(ws, r, 7, f"=SUMPRODUCT(G{r0}:G{r1},E{r0}:E{r1}/F{r0}:F{r1})/{drivers}", PCT, bold=True, bg=LIGHT)
    put(ws, r, 8, f"=IFERROR(F{r}/G{r}-1,0)", "+0%;-0%;0%", bold=True, bg=LIGHT)
    put(ws, r, 12, None, bg=LIGHT)
    put(ws, r, 14, f"=SUMPRODUCT(N{r0}:N{r1},E{r0}:E{r1}/F{r0}:F{r1})/{drivers}", PCT, bold=True, bg=LIGHT)
    note(ws, r + 1, "Window: the 8 weeks to 'Actuals used up to' (A1: w/c 3 Aug - Sat 26 Sep), scaled to a week. The plan holds these rates "
                    "flat every week; the only changes are the Diwali and Durga Puja (Kolkata) dips (Seasonality Check, section 1). "
                    "EIP is held flat by default.")

    # ---- A4. Lakshya month-end targets
    title(ws, R_MS_H - 3, "A4", "LAKSHYA MONTH-END TARGETS",
          "Lakshya's book on each month-end Sunday (27 Sep, 25 Oct, 29 Nov, 27 Dec). September is the opening week: compare it with A2.")
    groups = [(2, 5, "EIP - straight line from the actual"), (6, 9, "OWN NOW - Lakshya v4"),
              (10, 13, "LEASING + DTO - Lakshya v4"), (14, 17, "ON ROAD (sum)")]
    for c1, c2, t in groups:
        hdr(ws, R_MS_H - 1, c1, t, GREY_HDR)
        ws.merge_cells(start_row=R_MS_H - 1, start_column=c1, end_row=R_MS_H - 1, end_column=c2)
    hdr(ws, R_MS_H, 1, "City")
    for g in range(4):
        for m, mon in enumerate(MONTHS):
            hdr(ws, R_MS_H, 2 + 4 * g + m, mon)
    for i, city in enumerate(CITIES):
        r = R_MS0 + i
        put(ws, r, 1, city, bold=True)
        for m in range(4):
            put(ws, r, 2 + m, f"={ci('eip', i)}+({ci('t_eip', i)}-{ci('eip', i)})*{MS_WEEKS[m]}/{N_WEEKS}", NUM)
            if m < 3:
                inp(ws, r, 6 + m, LK_OWN_ME[city][m], NUM)
                inp(ws, r, 10 + m, LK_LDTO_ME[city][m], NUM)
            else:
                put(ws, r, 6 + m, f"={ci('t_own', i)}", NUM)
                put(ws, r, 10 + m, f"={ci('t_ldto', i)}", NUM)
            Ls = [L(2 + m), L(6 + m), L(10 + m)]
            put(ws, r, 14 + m, f"={Ls[0]}{r}+{Ls[1]}{r}+{Ls[2]}{r}", NUM, bold=True)
    india_row(ws, R_MS0 + n, range(2, 18))
    note(ws, R_MS0 + n + 1, "December = the targets in A2. Lakshya has no monthly EIP, so EIP is a straight line from the actual to its target.")

    # ---- A5. AOP month-ends
    title(ws, R_AOP_H - 3, "A5", "AOP MONTH-ENDS  -  the baseline before Lakshya",
          "AOP FY27 by city: cars on road (incl. EIP), EIP and driver recruitment in the month. Shown next to the plan and Lakshya.")
    groups = [(2, 5, "ON ROAD incl. EIP (month end)"), (6, 9, "EIP (month end)"), (10, 13, "DRIVER RECRUITMENT in the month")]
    for c1, c2, t in groups:
        hdr(ws, R_AOP_H - 1, c1, t, GREY_HDR)
        ws.merge_cells(start_row=R_AOP_H - 1, start_column=c1, end_row=R_AOP_H - 1, end_column=c2)
    hdr(ws, R_AOP_H, 1, "City")
    for g in range(3):
        for m, mon in enumerate(MONTHS):
            hdr(ws, R_AOP_H, 2 + 4 * g + m, mon)
    for i, city in enumerate(CITIES):
        r = R_AOP0 + i
        put(ws, r, 1, city, bold=True)
        for g, key in enumerate(("onroad", "eip", "rec")):
            for m in range(4):
                inp(ws, r, 2 + 4 * g + m, AOP[city][key][m], NUM)
    india_row(ws, R_AOP0 + n, range(2, 14))
    note(ws, R_AOP0 + n + 1, "AOP September is where AOP expected to be now: compare with the actual in A2 to see the starting gap.")

    # ---- A6. new cars
    title(ws, R_STK_H - 3, "A6", "NEW CARS  -  bought and waiting at the stock yard, when they reach the fleet, and what is still to buy",
          "The plan adds only cars that are bought (New Car Stock Report, 27 Sep). Each car gets a driver the week after it lands; "
          "the rest of Lakshya's 2,300 show as pending until ordered.")
    groups = [(2, 6, "IN STOCK BY RTO STATUS (bought)"), (7, 9, "LAKSHYA PLAN"), (10, 11, "PENDING PURCHASE")]
    for c1, c2, t in groups:
        hdr(ws, R_STK_H - 1, c1, t, GREY_HDR)
        ws.merge_cells(start_row=R_STK_H - 1, start_column=c1, end_row=R_STK_H - 1, end_column=c2)
    heads = ["City"] + [s for s, _, _ in DELIVERY_WINDOWS] + ["Total bought", "Sep-Oct", "Nov", "Total",
                                                               "Sep-Oct plan", "not planned yet"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_STK_H, j, t)
    ws.row_dimensions[R_STK_H].height = 42
    for i, city in enumerate(CITIES):
        r = R_STK0 + i
        put(ws, r, 1, city, bold=True)
        for s in range(4):
            inp(ws, r, 2 + s, NEW_CAR_STOCK[city][s], NUM)
        put(ws, r, 6, f"=SUM(B{r}:E{r})", NUM, bold=True)
        inp(ws, r, 7, LAKSHYA_ADDS_M[city][0] + LAKSHYA_ADDS_M[city][1], NUM)
        inp(ws, r, 8, LAKSHYA_ADDS_M[city][2] + LAKSHYA_ADDS_M[city][3], NUM)
        put(ws, r, 9, f"=G{r}+H{r}", NUM)
        put(ws, r, 10, f"=MAX(0,G{r}-F{r})", NUM, bold=True)
        put(ws, r, 11, f"=MAX(0,I{r}-F{r}-SUM(B{R_FUT0 + i}:D{R_FUT0 + i}))", NUM, bold=True)
    india_row(ws, R_STK0 + n, range(2, 12))
    note(ws, R_STK0 + n + 1, "Lakshya is the December plan, so all of its 2,300 cars are planned: the bought ones by RTO status, the rest "
                             "in the table below (Lakshya's months). 'Not planned yet' should stay 0.")
    # delivery windows
    ws.cell(R_WIN_H - 1, 1, "When each status reaches the fleet (plan weeks; cars spread evenly across the window)").font = F_BOLD
    for j, t in enumerate(["RTO status", "First week", "Last week", "First week starts", "Last week starts", "Cars (India)"], start=1):
        hdr(ws, R_WIN_H, j, t)
    for s, (status, a, b) in enumerate(DELIVERY_WINDOWS):
        r = R_WIN0 + s
        put(ws, r, 1, status, bold=True)
        inp(ws, r, 2, a, "0")
        inp(ws, r, 3, b, "0")
        put(ws, r, 4, f"=INDEX($B${R_CAL0}:$B${R_CAL0 + N_WEEKS - 1},B{r})", DATE)
        put(ws, r, 5, f"=INDEX($B${R_CAL0}:$B${R_CAL0 + N_WEEKS - 1},C{r})", DATE)
        put(ws, r, 6, f"={L(2 + s)}{R_STK0 + n}", NUM)
    # future purchases
    ws.cell(R_FUT_H - 1, 1, "Still to buy for Lakshya - planned to land in Lakshya's months (change to the order dates once placed)").font = F_BOLD
    for j, t in enumerate(["City"] + PLAN_MONTHS + ["Total"], start=1):
        hdr(ws, R_FUT_H, j, t)
    for i, city in enumerate(CITIES):
        r = R_FUT0 + i
        put(ws, r, 1, city, bold=True)
        for m in range(3):
            stk = R_STK0 + i   # Oct = Lakshya's Sep-Oct cars not yet bought; Nov = Lakshya's Nov cars, less any bought beyond Oct
            v = {0: f"=MAX(0,G{stk}-F{stk})", 1: f"=MAX(0,H{stk}-MAX(0,F{stk}-G{stk}))", 2: 0}[m]
            put(ws, r, 2 + m, v, NUM, font=F_INPUT, bg=INPUT)
        put(ws, r, 5, f"=SUM(B{r}:D{r})", NUM, bold=True)
    india_row(ws, R_FUT0 + n, range(2, 6))
    # FLAG: a car ordered now lands in plan week B{R_WIN0} ("RTO process not started") at the earliest
    hdr(ws, R_FUT_H, 6, "FLAG - when these cars must be ordered to land as in Lakshya")
    ws.merge_cells(start_row=R_FUT_H, start_column=6, end_row=R_FUT_H, end_column=14)
    earliest = f'TEXT(INDEX($B${R_CAL0}:$B${R_CAL0 + N_WEEKS - 1},$B${R_WIN0}),"d mmm")'
    for i in range(n + 1):
        r = R_FUT0 + i
        parts = []
        for m, mon in enumerate(PLAN_MONTHS):
            f_wk = WEEK_MONTH.index(mon) + 1
            l_wk = len(WEEK_MONTH) - WEEK_MONTH[::-1].index(mon)
            by_first = f"({G_OPEN_DATE}+1+({f_wk}-$B${R_WIN0})*7)"
            by_last = f"({G_OPEN_DATE}+1+({l_wk}-$B${R_WIN0})*7)"
            x = f"{L(2 + m)}{r}"
            parts.append(
                f'IF({x}<0.5,"",IF({by_last}<{G_OPEN_DATE}+1,TEXT({x},"#,##0")&" {mon} cars not bought yet: a car ordered now lands w/c "'
                f'&{earliest}&" at the earliest, so {mon} only works if they are already ordered. ",'
                f'"Order {mon}\'s "&TEXT({x},"#,##0")&" between "&TEXT(MAX({G_OPEN_DATE}+1,{by_first}),"d mmm")&" and "'
                f'&TEXT({by_last},"d mmm")&". "))')
        allz = "AND(" + ",".join(f"{L(2 + m)}{r}<0.5" for m in range(3)) + ")"
        put(ws, r, 6, f'=IF({allz},"OK - all bought",' + "&".join(parts) + ")",
            font=Font(name="Calibri", size=10, bold=True, color="FFC00000"))
        ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=14)
    note(ws, R_FUT0 + n + 1, "FLAG: cars in this table are not bought yet. A car ordered now takes the 'RTO process not started' "
                             "window above to reach the road, so Lakshya's months only hold if orders go in by the dates shown.")
    # weekly deliveries
    ws.cell(R_ADD_H - 1, 1, "Cars reaching the fleet each plan week (drivers are hired for them the following week)").font = F_BOLD
    hdr(ws, R_ADD_H, 1, "City")
    for w in range(N_WEEKS):
        c = hdr(ws, R_ADD_H, 2 + w, f"=B{R_CAL0 + w}")
        c.number_format = DATE
    hdr(ws, R_ADD_H, 2 + N_WEEKS, "Total")
    wim = {m: WEEK_MONTH.count(m) for m in PLAN_MONTHS}
    for i, city in enumerate(CITIES):
        r = R_ADD0 + i
        put(ws, r, 1, city, bold=True)
        for w in range(N_WEEKS):
            terms = [f"IF(AND({w + 1}>=$B${R_WIN0 + s},{w + 1}<=$C${R_WIN0 + s}),{L(2 + s)}{R_STK0 + i}/($C${R_WIN0 + s}-$B${R_WIN0 + s}+1),0)"
                     for s in range(len(DELIVERY_WINDOWS))]
            m = PLAN_MONTHS.index(WEEK_MONTH[w])
            terms.append(f"{L(2 + m)}{R_FUT0 + i}/{wim[WEEK_MONTH[w]]}")
            put(ws, r, 2 + w, "=" + "+".join(terms), NUM)
        put(ws, r, 2 + N_WEEKS, f"=SUM(B{r}:{L(1 + N_WEEKS)}{r})", NUM, bold=True)
    india_row(ws, R_ADD0 + n, range(2, 3 + N_WEEKS))

    # ---- A7. cars sold
    title(ws, R_SALE_H - 2, "A7", "CARS SOLD, BY MONTH",
          "Cars sold each month, spread evenly over its weeks. They come out of idle cars, so they lower the fleet, not cars on road.")
    for j, t in enumerate(["City"] + PLAN_MONTHS + ["Total", "Lakshya total", "Difference"], start=1):
        hdr(ws, R_SALE_H, j, t)
    for i, city in enumerate(CITIES):
        r = R_SALE0 + i
        put(ws, r, 1, city, bold=True)
        for m in range(3):
            inp(ws, r, 2 + m, SALES[city][m], NUM)
        put(ws, r, 5, f"=SUM(B{r}:D{r})", NUM, bold=True)
        inp(ws, r, 6, LAKSHYA_SALES[city], NUM)
        put(ws, r, 7, f"=E{r}-F{r}", NUM)
    india_row(ws, R_SALE0 + n, range(2, 8))
    note(ws, R_SALE0 + n + 1, "Lakshya: 721 cars Sep-Dec; cars already sold by 27 Sep are out of the opening fleet.")

    # ---- A8. calendar
    title(ws, R_CAL_H - 2, "A8", "WEEKLY CALENDAR",
          "One row per plan week (Mon-Sun). The festival column picks the only seasonal dips in the plan (Seasonality Check, section 1); "
          "the last column is the Lakshya month-end the week counts to.")
    cal_heads = ["Week #", "Week start (Mon)", "Week end", "Month", "Days in plan", "Festival"] + [
        f"Events - {c}" for c in CITIES] + ["Lakshya month-end it counts to"]
    for j, t in enumerate(cal_heads, start=1):
        hdr(ws, R_CAL_H, j, t)
    ws.row_dimensions[R_CAL_H].height = 42
    for w in range(N_WEEKS):
        r = R_CAL0 + w
        put(ws, r, 1, w + 1, "0", bold=True)
        put(ws, r, 2, f"=$B${R_GLOBAL + 2}" if w == 0 else f"=B{r - 1}+7", DATE)
        put(ws, r, 3, f"=MIN(B{r}+6,{G_PLAN_END})", DATE)
        put(ws, r, 4, f"=EOMONTH(B{r},-1)+1", "mmm-yy")
        put(ws, r, 5, f"=C{r}-B{r}+1", "0")
        inp(ws, r, 6, WEEK_FESTIVAL[w])
        for k, city in enumerate(CITIES):
            parts_ = [x for x in (EVENTS_ALL.get(w + 1), EVENTS_CITY.get((city, w + 1))) if x]
            inp(ws, r, 7 + k, "; ".join(parts_) if parts_ else "")
        inp(ws, r, 14, WEEK_MONTH[w])
    r = R_CAL0 + N_WEEKS
    put(ws, r, 1, "Total", bold=True, bg=LIGHT)
    put(ws, r, 5, f"=SUM(E{R_CAL0}:E{r - 1})", "0", bold=True, bg=LIGHT)
    note(ws, r + 1, "Festivals: Diwali (Sun 8 Nov) w/c 2 and 9 Nov, every city; Durga Puja (17-20 Oct) w/c 12 and 19 Oct, Kolkata only. "
                    "No other week has a seasonal change. A week counts in the month its Monday falls in.")

    # ================================================================ PART C
    banner(ws, R_SUM_H - 4, "PART C  -  OUTPUT AND SOURCES  (nothing to type)", GREY_HDR)
    title(ws, R_SUM_H - 2, "C1", "PLAN SUMMARY BY CITY",
          "Where the plan lands on 27 Dec, read from the city tabs, next to the run rate, AOP and Lakshya. Check should be 0.")
    sum_cols = ["City", "On road at start", "On road 27 Dec (plan)", "Lakshya target", "Plan - Lakshya",
                "Run rate 27 Dec", "AOP Dec", "Plan - AOP", "EIP 27 Dec", "Own Now 27 Dec", "L+DTO 27 Dec",
                "Fleet 27 Dec", "Lakshya fleet Dec", "Util 27 Dec", "Max utilisation", "Headroom",
                "Driver acquisition (13 weeks)", "of which for new cars", "Extra hiring step a week",
                "Peak week acquisition", "Proven capacity a week", "Weeks above capacity", "Check (0 = OK)",
                "Within capacity 27 Dec", "Cars short at max utilisation, 27 Dec"]
    for j, t in enumerate(sum_cols, start=1):
        hdr(ws, R_SUM_H, j, t, GREY_HDR)
    ws.row_dimensions[R_SUM_H].height = 44
    for i, city in enumerate(CITIES):
        r = R_SUM0 + i
        s = q(city)
        vals = [
            (city, None), (f"={s}!G{FIRST}", NUM), (f"={s}!Y{LAST}", NUM), (f"={ci('t_onroad', i)}", NUM),
            (f"=ROUND(C{r}-D{r},0)", DIFF_FMT), (f"={s}!BS{LAST}", NUM), (f"=Inputs!$E${R_AOP0 + i}", NUM), (f"=ROUND(C{r}-G{r},0)", DIFF_FMT),
            (f"={s}!R{LAST}", NUM), (f"={s}!X{LAST}", NUM), (f"={s}!W{LAST}", NUM),
            (f"={s}!E{LAST}", NUM), (f"={ci('lk_fleet', i)}", NUM), (f"=C{r}/L{r}", PCT),
            (f"={ci('ceiling', i)}", PCT), (f"=O{r}-N{r}", PCT),
            (f"={s}!AU{R_TOT}", NUM), (f"={s}!AI{R_TOT}", NUM), (f"={s}!{STEP_CELL}", "0.0"),
            (f"=MAX({s}!AU{FIRST}:AU{LAST})", NUM), (f"={rr('cap', i)}", NUM),
            (f'=COUNTIF({s}!BP{FIRST}:BP{LAST},"Above capacity")', "0"),
            (f"=ROUND(SUMPRODUCT(ABS({s}!AV2:AV{LAST})),6)", "0"), (f"={s}!CG{LAST}", NUM), (f"={s}!CH{LAST}", NUM),
        ]
        for j, (v, fmt) in enumerate(vals, start=1):
            put(ws, r, j, v, fmt, bold=(j in (1, 3)))
    r = R_SUM0 + n
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in range(2, len(sum_cols) + 1):
        Lj = L(j)
        if Lj == "N":
            v, fmt = f"=C{r}/L{r}", PCT
        elif Lj in ("O", "P", "T"):
            v, fmt = None, PCT
        elif Lj == "S":
            v, fmt = f"=SUM(S{R_SUM0}:S{r - 1})", "0.0"
        elif Lj in ("E", "H"):
            v, fmt = f"=SUM({Lj}{R_SUM0}:{Lj}{r - 1})", DIFF_FMT
        else:
            v, fmt = f"=SUM({Lj}{R_SUM0}:{Lj}{r - 1})", NUM
        put(ws, r, j, v, fmt, bold=True, bg=LIGHT)
    r_india = r
    note(ws, r_india + 1, "Run rate = today's hiring and attrition (with validated seasonality) plus a driver for every new car. "
                          "Plan = run rate + the extra hiring step (added once more each week) when A1 is set to Lakshya. "
                          "Headroom below 0 (red) = above the city's max utilisation.")
    ws.conditional_formatting.add(f"P{R_SUM0}:P{r_india - 1}",
                                  FormulaRule(formula=[f"P{R_SUM0}<0"], font=RED_FONT, fill=fill("FFFFC7CE")))
    for Lj in ("E", "H"):
        ws.conditional_formatting.add(f"{Lj}{R_SUM0}:{Lj}{r_india}",
                                      FormulaRule(formula=[f"ROUND({Lj}{R_SUM0},0)<0"], font=RED_FONT))
    ws.conditional_formatting.add(f"V{R_SUM0}:V{r_india}", FormulaRule(formula=[f"V{R_SUM0}>0"], font=RED_FONT, fill=fill("FFFFC7CE")))
    ws.conditional_formatting.add(f"W{R_SUM0}:W{r_india}", FormulaRule(formula=[f"W{R_SUM0}<>0"], font=RED_FONT, fill=fill("FFFFC7CE")))

    # ---- C2. sources
    title(ws, R_SRC_H - 2, "C2", "SOURCES", "Where the numbers come from.")
    hdr(ws, R_SRC_H, 1, "Source", GREY_HDR)
    hdr(ws, R_SRC_H, 2, "Link", GREY_HDR)
    ws.merge_cells(start_row=R_SRC_H, start_column=2, end_row=R_SRC_H, end_column=12)
    F_LINK = Font(name="Calibri", size=10, color="FF1155CC", underline="single")
    for k, (label, url, text) in enumerate(SOURCES):
        r = R_SRC_H + 1 + k
        put(ws, r, 1, label, bold=True)
        put(ws, r, 2, link(url, text) if url else text, font=F_LINK if url else F_BODY)
        for j in range(3, 13):
            put(ws, r, j, None)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=12)

    ws.freeze_panes = "B2"
    ws.sheet_view.zoomScale = 90


def build_season(wb):
    """Seasonality checked city by city: a season block changes hiring or attrition only if 2024 and 2025 agree."""
    ws = wb.create_sheet(SEAS_TAB)
    ws.sheet_properties.tabColor = TEAL
    ws.column_dimensions["A"].width = 18
    for j in range(2, 20):
        ws.column_dimensions[get_column_letter(j)].width = 10
    L = get_column_letter
    n = len(CITIES)
    rows_all = CITIES + ["INDIA"]
    ws["A1"] = "SEASONALITY CHECK  -  is the change real, city by city?"
    ws["A1"].font = F_TITLE
    ws["A2"] = ("The plan has only two seasonal dips: Diwali in every city and Durga Puja in Kolkata (section 1). Every other week "
                "runs at the flat 8-week run rate. Sections 2-4 are history for reference: how each season moved in 2024 and 2025.")
    ws["A2"].font = F_WHAT

    # ---- 1. what the plan uses: two festivals only
    title(ws, R_SU_H - 3, "1.", "FESTIVAL DIPS USED IN THE PLAN  -  Diwali (every city) and Durga Puja (Kolkata); no other seasonality",
          "Read by every city tab (columns BE and BF) in the festival weeks of Inputs A8. Change = average of 2024 and 2025 vs the 4 weeks before.")
    hdr(ws, R_SU_H - 1, 2, "HIRING (driver acquisition)", GREY_HDR)
    ws.merge_cells(start_row=R_SU_H - 1, start_column=2, end_row=R_SU_H - 1, end_column=5)
    hdr(ws, R_SU_H - 1, 6, "NET ATTRITION RATE", GREY_HDR)
    ws.merge_cells(start_row=R_SU_H - 1, start_column=6, end_row=R_SU_H - 1, end_column=9)
    hdr(ws, R_SU_H, 1, "City")
    for g in range(2):
        for b in range(4):
            hdr(ws, R_SU_H, 2 + 4 * g + b, FESTIVALS[b] if b < len(FESTIVALS) else "")
    dw = SEASONS.index("Diwali")
    R_DP = R_SU0 + n + 5                      # Durga Puja history row (Kolkata)
    for i, city in enumerate(rows_all):
        r = R_SU0 + i
        bg = LIGHT if city == "INDIA" else None
        put(ws, r, 1, city, bold=True, bg=bg)
        for g in range(2):
            ck = R_CK0 + 2 * i + g
            c24, c25 = L(3 + 3 * dw), L(4 + 3 * dw)
            put(ws, r, 2 + 4 * g, f"=AVERAGE({c24}{ck},{c25}{ck})", "+0%;-0%;0%", bold=True, bg=bg)
            puja = (f"=AVERAGE({L(2 + 2 * g)}{R_DP},{L(3 + 2 * g)}{R_DP})*$F${R_DP}" if city in DURGA_PUJA else 0)
            put(ws, r, 3 + 4 * g, puja, "+0%;-0%;0%", bold=True, bg=bg)
            for b in (2, 3):
                put(ws, r, 2 + 4 * g + b, None, bg=bg)
    for rng_ in (f"B{R_SU0}:I{R_SU0 + n}",):
        ws.conditional_formatting.add(rng_, FormulaRule(formula=[f"B{R_SU0}<0"], font=Font(name="Calibri", size=10, bold=True, color="FFC00000")))
        ws.conditional_formatting.add(rng_, FormulaRule(formula=[f"B{R_SU0}>0"], font=Font(name="Calibri", size=10, bold=True, color="FF006100")))
    note(ws, R_SU0 + n + 1, "INDIA is for reference: every city uses its own row. Diwali weeks = w/c 2 and 9 Nov 2026 (Diwali history: section 2). "
                            "Durga Puja weeks = w/c 12 and 19 Oct 2026, Kolkata only, each at the share below. Every other week: no change.")
    # Durga Puja history, Kolkata
    ws.cell(R_DP - 2, 1, "Durga Puja, Kolkata  -  Puja week vs the 4 weeks before").font = F_BOLD
    for j, t in enumerate(["City", "Hiring 2024 (w/c 7 Oct)", "Hiring 2025 (w/c 29 Sep)", "Attrition 2024", "Attrition 2025",
                           "Share a week in 2026"], start=1):
        hdr(ws, R_DP - 1, j, t)
    ws.row_dimensions[R_DP - 1].height = 30
    for city, ((r24, a24), (r25, a25)) in DURGA_PUJA.items():
        put(ws, R_DP, 1, city, bold=True)
        for j, v in ((2, r24), (3, r25), (4, a24), (5, a25)):
            hist(ws, R_DP, j, v, "+0%;-0%;0%")
        inp(ws, R_DP, 6, PUJA_WEEK_SHARE, "0%")
    note(ws, R_DP + 1, "2026: Saptami Sat 17 Oct - Dashami Tue 20 Oct, split across w/c 12 and 19 Oct, so each week takes half of the "
                       "one-week dip (2024 and 2025 fell in a single week). Hiring fell in both years; attrition moved differently (average used).")

    # ---- 2. the check
    title(ws, R_CK_H - 3, "2.", "HISTORY  -  change vs the 4 weeks before, in 2024 and 2025 (reference; the plan uses only the Diwali columns)",
          "Yes = both years moved the same way by at least the minimum (Inputs A1). Grey = history (reporting DB).")
    hdr(ws, R_CK_H - 1, 1, "")
    hdr(ws, R_CK_H - 1, 2, "")
    for b, blk in enumerate(SEASONS):
        hdr(ws, R_CK_H - 1, 3 + 3 * b, blk, GREY_HDR)
        ws.merge_cells(start_row=R_CK_H - 1, start_column=3 + 3 * b, end_row=R_CK_H - 1, end_column=5 + 3 * b)
    hdr(ws, R_CK_H, 1, "City")
    hdr(ws, R_CK_H, 2, "Measure")
    for b in range(4):
        for k, t in enumerate(("2024", "2025", "Seasonal?")):
            hdr(ws, R_CK_H, 3 + 3 * b + k, t)
    for i, city in enumerate(rows_all):
        for g, (key, label) in enumerate((("rec", "Hiring"), ("att", "Attrition rate"))):
            r = R_CK0 + 2 * i + g
            put(ws, r, 1, city if g == 0 else "", bold=True)
            put(ws, r, 2, label)
            for b in range(4):
                y24, y25 = SEASON_CHANGE[city][key][b]
                hist(ws, r, 3 + 3 * b, y24, "+0%;-0%;0%")
                hist(ws, r, 4 + 3 * b, y25, "+0%;-0%;0%")
                a, c = f"{L(3 + 3 * b)}{r}", f"{L(4 + 3 * b)}{r}"
                put(ws, r, 5 + 3 * b, f'=IF(AND({a}*{c}>0,ABS({a})>={G_SEAS},ABS({c})>={G_SEAS}),"Yes","No")', bold=True)
    last_ck = R_CK0 + 2 * len(rows_all) - 1
    for b in range(4):
        v = L(5 + 3 * b)
        ws.conditional_formatting.add(f"{v}{R_CK0}:{v}{last_ck}", FormulaRule(formula=[f'{v}{R_CK0}="Yes"'],
                                      font=Font(name="Calibri", size=10, bold=True, color="FF006100"), fill=fill("FFC6EFCE")))
    note(ws, last_ck + 1, "Hiring = new joins + resurrections a week. Attrition rate = (attrition + temp attrition - rejoins - temp rejoins) "
                          "/ drivers at the start of the week. Aligned on the week with Bhai Dooj: w/c 28 Oct 2024, 20 Oct 2025, 9 Nov 2026.")

    # ---- 3. attrition this year vs last year
    title(ws, R_AT_H - 3, "3.", "ATTRITION  -  this year vs the same weeks last year (last 12 weeks)",
          "Net attrition rate a week. Lower this year in most cities: is it holding? The plan keeps this year's rate (Inputs A3).")
    hdr(ws, R_AT_H - 1, 1, "")
    for i, city in enumerate(rows_all):
        hdr(ws, R_AT_H - 1, 2 + 2 * i, city, GREY_HDR)
        ws.merge_cells(start_row=R_AT_H - 1, start_column=2 + 2 * i, end_row=R_AT_H - 1, end_column=3 + 2 * i)
        hdr(ws, R_AT_H, 2 + 2 * i, "This year")
        hdr(ws, R_AT_H, 3 + 2 * i, "Last year")
    hdr(ws, R_AT_H, 1, "Week (Mon)")
    for k in range(12):
        r = R_AT_H + 1 + k
        put(ws, r, 1, dt.date.fromisoformat(ATTR_TREND["Mumbai"][k][0]), DATE, bold=True)
        for i, city in enumerate(rows_all):
            _, cy, ly = ATTR_TREND[city][k]
            put(ws, r, 2 + 2 * i, cy, PCT, bg=ACTUAL)
            hist(ws, r, 3 + 2 * i, ly, PCT)
    r1, r12 = R_AT_H + 1, R_AT_H + 12
    for k, (label, a, b) in enumerate((("Last 4 weeks", r12 - 3, r12), ("8 weeks before", r1, r12 - 4))):
        r = r12 + 1 + k
        put(ws, r, 1, label, bold=True, bg=LIGHT)
        for i in range(len(rows_all)):
            for j in (2 + 2 * i, 3 + 2 * i):
                put(ws, r, j, f"=AVERAGE({L(j)}{a}:{L(j)}{b})", PCT, bold=True, bg=LIGHT)
    r = r12 + 3
    put(ws, r, 1, "This year vs last", bold=True, bg=LIGHT)
    for i in range(len(rows_all)):
        c, d = L(2 + 2 * i), L(3 + 2 * i)
        put(ws, r, 2 + 2 * i, f'=TEXT({c}{r12 + 1}/{d}{r12 + 1}-1,"+0%;-0%")&" now"', None, bold=True, bg=LIGHT)
        put(ws, r, 3 + 2 * i, f'=TEXT({c}{r12 + 2}/{d}{r12 + 2}-1,"+0%;-0%")&" before"', None, bg=LIGHT)
    note(ws, r + 1, "Last year's rate rose through September while this year's stayed flat, so most of the gap is last year rising, "
                    "not this year falling. The plan keeps this year's level and adds only the seasonal changes both years showed (section 1).")

    # ---- 4. week by week, aligned on Diwali, with 4-week moving averages
    title(ws, R_WK_H - 3, "4.", "WEEK BY WEEK, ALIGNED ON DIWALI  -  4-week moving average vs 2024 and 2025",
          "Offset 0 = the week with Bhai Dooj. 2026 has actuals up to the current week (offset -7); the plan starts at offset -6.")
    heads = ["Offset", "w/c 2024", "w/c 2025", "w/c 2026", "Hiring 2024", "Hiring 2025", "Hiring 2026",
             "Hiring 4-wk avg 2024", "4-wk avg 2025", "4-wk avg 2026", "Attrition 2024", "Attrition 2025", "Attrition 2026",
             "Attrition 4-wk avg 2024", "4-wk avg 2025", "4-wk avg 2026"]
    r = R_WK_H
    for i, city in enumerate(rows_all):
        ws.cell(r - 1, 1, city).font = F_SECTION
        for j, t in enumerate(heads, start=1):
            hdr(ws, r, j, t, TEAL if j >= 5 else NAVY)
        ws.row_dimensions[r].height = 30
        top = r + 1
        for k, row in enumerate(ALIGNED[city]):
            rr_ = top + k
            o, w24, h24, a24, w25, h25, a25, w26, h26, a26 = row
            put(ws, rr_, 1, o, "+0;-0;0", bold=True, bg=LIGHT if -6 <= o else None)
            for j, v in ((2, w24), (3, w25), (4, w26)):
                put(ws, rr_, j, dt.date.fromisoformat(v), DATE)
            for j, v, fmt in ((5, h24, NUM), (6, h25, NUM), (7, h26, NUM), (11, a24, PCT), (12, a25, PCT), (13, a26, PCT)):
                if v is None:
                    put(ws, rr_, j, None)
                elif j in (7, 13):
                    put(ws, rr_, j, v, fmt, bg=ACTUAL)
                else:
                    hist(ws, rr_, j, v, fmt)
            for src, dst in ((5, 8), (6, 9), (7, 10), (11, 14), (12, 15), (13, 16)):
                a = max(top, rr_ - 3)
                col = L(src)
                fmt = NUM if src < 11 else PCT
                put(ws, rr_, dst, f'=IF(COUNT({col}{a}:{col}{rr_})=0,"",AVERAGE({col}{a}:{col}{rr_}))', fmt, bold=(dst in (10, 16)))
        r = top + len(ALIGNED[city]) + 3
    ws.freeze_panes = "B4"
    ws.sheet_view.zoomScale = 90


# ---------------------------------------------------------------- Lakshya v4 as given (for the comparison tab)
# Lakshya v4 starting books: Own Now ~6 Sep (Inputs sec 5), L+DTO 31 Aug (Actuals tab)
LK_OWN_OPEN = {"Mumbai": 511, "Delhi NCR": 661, "Bangalore": 668, "Hyderabad": 281, "Chennai": 428,
               "Kolkata": 185, "Pune": 267}
LK_LDTO_OPEN = {"Mumbai": 1164, "Delhi NCR": 1473, "Bangalore": 1040, "Hyderabad": 1035, "Chennai": 899,
                "Kolkata": 300, "Pune": 694}
# Month-end books (Lakshya months end on w/e 27 Sep, 25 Oct, 29 Nov, 27 Dec) by city
LK_LDTO_ME = {"Mumbai": (1179, 1183, 1152, 1225), "Delhi NCR": (1488, 1489, 1446, 1535),
              "Bangalore": (1080, 1110, 1109, 1201), "Hyderabad": (1054, 1063, 1041, 1112),
              "Chennai": (925, 943, 933, 1004), "Kolkata": (283, 264, 235, 233),
              "Pune": (678, 656, 612, 631)}
LK_OWN_ME = {"Mumbai": (549, 711, 869, 1006), "Delhi NCR": (688, 757, 804, 850),
             "Bangalore": (687, 824, 961, 1075), "Hyderabad": (314, 448, 582, 700),
             "Chennai": (438, 537, 641, 725), "Kolkata": (205, 245, 274, 305),
             "Pune": (287, 345, 395, 442)}

# Lakshya v4 weekly books by city (Weekly L+DTO and Weekly Own Now tabs), used by the v2 workbook.
# ld_pre / own_pre: driver acquisition in the weeks before the plan (L+DTO w/e 6, 13, 20 Sep; Own Now w/e 13, 20 Sep);
# ld_wk / own_wk: the 14 plan weeks (w/e 27 Sep ... 27 Dec); churn and rollover by Lakshya month (Sep, Oct, Nov, Dec).
LK_WEEKLY = {
    "Mumbai": dict(ld_open=1164, ld_pre=(172, 172, 172), ld_wk=(174, 198, 189, 163, 138, 93, 78, 107, 178, 199, 195, 222, 213, 111), ld_churn=(675, 684, 686, 668),
                own_open=511, own_pre=(27, 27), own_wk=(27, 65, 62, 53, 45, 32, 27, 37, 61, 68, 57, 65, 62, 32), own_churn=(30, 44, 47, 55), own_roll=(13, 19, 20, 24)),
    "Delhi NCR": dict(ld_open=1473, ld_pre=(184, 184, 184), ld_wk=(185, 210, 201, 173, 146, 97, 82, 112, 187, 209, 209, 239, 229, 121), ld_churn=(722, 729, 730, 709),
                own_open=661, own_pre=(24, 23), own_wk=(23, 38, 36, 32, 27, 16, 14, 19, 32, 35, 33, 37, 36, 19), own_churn=(43, 64, 69, 79), own_roll=(0, 0, 0, 0)),
    "Bangalore": dict(ld_open=1040, ld_pre=(150, 150, 150), ld_wk=(152, 176, 169, 146, 122, 84, 72, 98, 162, 182, 181, 207, 199, 104), ld_churn=(562, 583, 599, 599),
                own_open=668, own_pre=(23, 23), own_wk=(23, 60, 58, 50, 42, 30, 26, 35, 59, 66, 53, 61, 59, 31), own_churn=(50, 73, 79, 90), own_roll=(0, 0, 0, 0)),
    "Hyderabad": dict(ld_open=1035, ld_pre=(173, 173, 173), ld_wk=(173, 200, 191, 165, 138, 95, 80, 109, 182, 203, 196, 224, 215, 113), ld_churn=(673, 685, 691, 677),
                own_open=281, own_pre=(20, 20), own_wk=(20, 50, 48, 41, 35, 25, 21, 29, 49, 54, 44, 51, 49, 25), own_churn=(10, 15, 16, 19), own_roll=(17, 25, 28, 32)),
    "Chennai": dict(ld_open=899, ld_pre=(132, 132, 132), ld_wk=(133, 154, 147, 127, 108, 73, 62, 84, 141, 158, 156, 178, 170, 89), ld_churn=(503, 518, 528, 522),
                own_open=428, own_pre=(15, 14), own_wk=(14, 42, 41, 35, 29, 22, 19, 25, 42, 48, 38, 43, 41, 22), own_churn=(33, 48, 52, 60), own_roll=(0, 0, 0, 0)),
    "Kolkata": dict(ld_open=300, ld_pre=(50, 50, 50), ld_wk=(52, 54, 52, 45, 37, 23, 20, 27, 45, 49, 45, 51, 49, 25), ld_churn=(219, 207, 193, 172),
                own_open=185, own_pre=(12, 11), own_wk=(11, 17, 17, 14, 12, 7, 6, 8, 14, 15, 15, 17, 16, 8), own_churn=(14, 20, 21, 25), own_roll=(0, 0, 0, 0)),
    "Pune": dict(ld_open=694, ld_pre=(114, 114, 114), ld_wk=(114, 126, 121, 104, 88, 57, 48, 66, 109, 122, 114, 130, 125, 66), ld_churn=(472, 461, 446, 416),
                own_open=267, own_pre=(14, 13), own_wk=(13, 25, 24, 21, 18, 12, 10, 13, 22, 25, 22, 25, 24, 13), own_churn=(20, 30, 32, 37), own_roll=(0, 0, 0, 0)),
}
LK_WEEKS_IN_MONTH = {"ld": (4, 4, 5, 4), "own": (3, 4, 5, 4)}  # Lakshya months: L+DTO from 31 Aug, Own Now from ~6 Sep


# ---------------------------------------------------------------- v2: Lakshya as given
# python3 build_weekly_supply_plan.py out.xlsx raw.json --v2
# Every Own Now and L+DTO number on the city tabs is Lakshya v4's: weekly driver acquisition as given, churn and
# rollover by Lakshya month spread evenly over its weeks, starting from Lakshya's own book on the opening date.
# EIP (not weekly in Lakshya) runs in a straight line from the actual to its December target.
V2 = False
LW_TAB = "Lakshya Weekly"
LW = f"'{LW_TAB}'"
R_LW_LD0 = 5                    # L+DTO driver acquisition, city rows (header row above)
R_LW_OW0 = R_LW_LD0 + 11        # Own Now driver acquisition
R_LW_CH0 = R_LW_OW0 + 11        # churn / rollover by month
R_LW_WK = R_LW_CH0 + 8          # weeks in each Lakshya month
R_LW_ST0 = R_LW_WK + 4          # start book on the opening date


def build_lk_weekly(wb):
    ws = wb.create_sheet(LW_TAB, 2)
    ws.sheet_properties.tabColor = TEAL
    ws.column_dimensions["A"].width = 16
    for j in range(2, 18):
        ws.column_dimensions[get_column_letter(j)].width = 10
    ws["A1"] = "LAKSHYA WEEKLY  -  the Lakshya v4 numbers the v2 city tabs run on"
    ws["A1"].font = F_TITLE
    ws["A2"] = ("Source: Lakshya_15000_Model_v4, Weekly L+DTO and Weekly Own Now tabs. Opening book + weekly driver acquisition "
                "- monthly churn = Lakshya's month-end books, for every city. Cream = Lakshya's figures, typed as given.")
    ws["A2"].font = F_NOTE
    n = len(CITIES)
    week_hdr = [f"w/e {d}" for d in ("4 Oct", "11 Oct", "18 Oct", "25 Oct", "1 Nov", "8 Nov", "15 Nov",
                                     "22 Nov", "29 Nov", "6 Dec", "13 Dec", "20 Dec", "27 Dec")]

    def weekly(r0, title, key):
        ws.cell(r0 - 2, 1, title).font = F_SECTION
        for j, t in enumerate(["City"] + week_hdr + ["Total"], start=1):
            hdr(ws, r0 - 1, j, t)
        for i, c in enumerate(CITIES):
            put(ws, r0 + i, 1, c, bold=True)
            for w in range(N_WEEKS):
                inp(ws, r0 + i, 2 + w, LK_WEEKLY[c][key][w + 1], NUM)   # [0] = w/e 27 Sep, before the plan
            put(ws, r0 + i, 2 + N_WEEKS, f"=SUM(B{r0 + i}:{get_column_letter(1 + N_WEEKS)}{r0 + i})", NUM, bold=True)
        india_row(ws, r0 + n, range(2, 3 + N_WEEKS))

    weekly(R_LW_LD0, "1.  LEASING + DTO - driver acquisition per week", "ld_wk")
    weekly(R_LW_OW0, "2.  OWN NOW - driver acquisition per week (new + existing cars)", "own_wk")
    ws.cell(R_LW_CH0 - 2, 1, "3.  CHURN BY LAKSHYA MONTH - spread evenly over the month's weeks on the city tabs").font = F_SECTION
    for c0, t in ((2, "L+DTO churn"), (6, "Own Now churn"), (10, "Own Now purchase rollover")):
        for m, mon in enumerate(MONTHS):
            hdr(ws, R_LW_CH0 - 1, c0 + m, f"{t} {mon}")
    hdr(ws, R_LW_CH0 - 1, 1, "City")
    ws.row_dimensions[R_LW_CH0 - 1].height = 30
    for i, c in enumerate(CITIES):
        put(ws, R_LW_CH0 + i, 1, c, bold=True)
        for m in range(4):
            inp(ws, R_LW_CH0 + i, 2 + m, LK_WEEKLY[c]["ld_churn"][m], NUM)
            inp(ws, R_LW_CH0 + i, 6 + m, LK_WEEKLY[c]["own_churn"][m], NUM)
            inp(ws, R_LW_CH0 + i, 10 + m, LK_WEEKLY[c]["own_roll"][m], NUM)
    india_row(ws, R_LW_CH0 + n, range(2, 14))
    put(ws, R_LW_WK, 1, "Weeks in the month", bold=True)
    for m in range(4):
        for c0, key in ((2, "ld"), (6, "own"), (10, "own")):
            inp(ws, R_LW_WK, c0 + m, LK_WEEKS_IN_MONTH[key][m], "0")
    ws.cell(R_LW_WK + 1, 1, "Lakshya's September runs from 31 Aug for L+DTO (4 weeks) and from ~6 Sep for Own Now (3 weeks); "
                            "only the week to 27 Sep is in the plan.").font = F_NOTE

    ws.cell(R_LW_ST0 - 2, 1, "4.  START - Lakshya's own book on 27 Sep (its September close: where the v2 plan starts)").font = F_SECTION
    heads = ["City", "", "", "L+DTO on 27 Sep (Lakshya)", "", "", "Own Now on 27 Sep (Lakshya)", "Fleet at start (Lakshya base)",
             "Actual L+DTO", "Actual Own Now", "Start gap (Own Now + L+DTO)"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_LW_ST0 - 1, j, t)
    ws.row_dimensions[R_LW_ST0 - 1].height = 42
    for i, c in enumerate(CITIES):
        r = R_LW_ST0 + i
        put(ws, r, 1, c, bold=True)
        put(ws, r, 4, f"=Inputs!$J${R_MS0 + i}", NUM, bold=True)
        put(ws, r, 7, f"=Inputs!$F${R_MS0 + i}", NUM, bold=True)
        put(ws, r, 8, f"={ci('lk_fleet', i)}-Inputs!$I${R_STK0 + i}+Inputs!$F${R_SALE0 + i}", NUM)
        put(ws, r, 9, f"={ci('ldto', i)}", NUM, bg=ACTUAL)
        put(ws, r, 10, f"={ci('own', i)}", NUM, bg=ACTUAL)
        put(ws, r, 11, f"=I{r}+J{r}-D{r}-G{r}", "+#,##0;-#,##0;0", bold=True)
    india_row(ws, R_LW_ST0 + n, [4, 7, 8, 9, 10, 11])
    ws.cell(R_LW_ST0 + n + 1, 1, "v2 starts every city from Lakshya's own 27 Sep book (Inputs A4, September) and fleet base, not the actual. "
                                 "Start gap = how far the actual is from it: the main plan starts from the actual, v2 assumes the gap away.").font = F_NOTE
    ws.freeze_panes = "B4"


def v2_city_overrides(idx, w, r, p):
    """City-tab formulas that make a plan week equal Lakshya's (logical column letters)."""
    m = MONTHS.index(WEEK_MONTH[w])
    wk = get_column_letter(2 + w)
    f = {
        "AT": f"={LW}!${wk}${R_LW_LD0 + idx}",
        "AS": f"={LW}!${get_column_letter(2 + m)}${R_LW_CH0 + idx}/{LW}!${get_column_letter(2 + m)}${R_LW_WK}",
        "AR": f"=AT{r}-AS{r}",
        "AM": f"={LW}!${wk}${R_LW_OW0 + idx}",
        "AK": f"={LW}!${get_column_letter(6 + m)}${R_LW_CH0 + idx}/{LW}!${get_column_letter(6 + m)}${R_LW_WK}",
        "AL": f"={LW}!${get_column_letter(10 + m)}${R_LW_CH0 + idx}/{LW}!${get_column_letter(10 + m)}${R_LW_WK}",
        "AJ": f"=AM{r}-AK{r}-AL{r}",
        "AQ": f"=AK{r}+AL{r}+AS{r}",
        "AG": f"=({ci('t_eip', idx)}-$R${OPEN_ROW})/{N_WEEKS}",
        "BM": f"=AG{r}+AJ{r}+AR{r}",
        "X": f"=AH{r}+AJ{r}", "W": f"=AP{r}+AR{r}",
        # Lakshya's 2,300 new cars (Inputs A6, Lakshya plan): Oct and Nov, spread evenly over the month's weeks
        "AD": {"Oct": f"=Inputs!$G${R_STK0 + idx}/{WEEK_MONTH.count('Oct')}",
               "Nov": f"=Inputs!$H${R_STK0 + idx}/{WEEK_MONTH.count('Nov')}"}.get(WEEK_MONTH[w], "=0"),
    }
    if w == 0:  # start from Lakshya's own book and fleet on the opening date
        f.update({
            "AH": f"={LW}!$G${R_LW_ST0 + idx}", "AP": f"={LW}!$D${R_LW_ST0 + idx}",
            "G": f"=R{p}+AH{r}+AP{r}", "H": f"=AH{r}+AP{r}",
            "E": f"={LW}!$H${R_LW_ST0 + idx}+AD{r}-AE{r}", "F": f"=E{r}-{LW}!$H${R_LW_ST0 + idx}",
        })
    return f


# ---------------------------------------------------------------- Read Me
def build_readme(wb):
    ws = wb.create_sheet("Read Me", 0)
    ws.column_dimensions["A"].width = 24
    for L_ in "BCDEFGHIJKLM":
        ws.column_dimensions[L_].width = 13
    ws.sheet_view.showGridLines = False
    L = get_column_letter
    n = len(CITIES)
    ws.cell(1, 1, "READ ME - v2: LAKSHYA AS GIVEN" if V2 else "READ ME - from today's run rate to 27 December").font = F_TITLE
    ws.cell(2, 1, "Lakshya 15,000 weekly supply plan. Every number below is a live formula from the city tabs and Inputs.").font = F_NOTE
    ws.cell(3, 1, "Lakshya source:").font = F_BOLD
    c = ws.cell(3, 2, link(LAKSHYA_URL, "Lakshya_15000_Model_v4.xlsx"))
    c.font = Font(name="Calibri", size=10, color="FF1155CC", underline="single")
    if V2:
        c = ws.cell(4, 1, "v2: every Own Now and Leasing + DTO number on the city tabs is Lakshya v4's - weekly driver acquisition as given, "
                          "churn and rollover by month spread evenly, starting from Lakshya's own 27 Sep book and fleet (Lakshya Weekly tab), with "
                          "Lakshya's 2,300 new cars. EIP runs in a straight line to its target. The run-rate, new-car and seasonality logic below "
                          "is NOT used in v2.")
        c.font = Font(name="Calibri", size=10, bold=True, color="FFC00000")
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells("A4:M4")
        ws.row_dimensions[4].height = 42

    def para(row, title_, lines):
        ws.cell(row, 1, title_).font = F_SECTION
        for k, t in enumerate(lines):
            c = ws.cell(row + 1 + k, 1, t)
            c.font = F_BODY
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.merge_cells(start_row=row + 1 + k, start_column=1, end_row=row + 1 + k, end_column=13)
            ws.row_dimensions[row + 1 + k].height = 30
        return row + len(lines) + 2

    r = para(6, "1.  THE PRINCIPLE - a realistic path from today's run rate to the December target", [
        "The plan starts from the actual on the latest day loaded (Inputs A1) and plans the current week onwards. Every week has an "
        "operational basis: drivers are acquired at the last 8 weeks' run rate (Inputs A3) and leave at the last 8 weeks' attrition rate. "
        "New cars get their drivers out of that hiring (city tab AI), not as extra jumps.",
        "Only two seasonal dips: Diwali (w/c 2 and 9 Nov, every city) and Durga Puja (w/c 12 and 19 Oct, Kolkata), each the average of "
        "2024 and 2025 (Seasonality Check, section 1). Every other week is flat.",
        "To move toward Lakshya the plan adds a steady hiring ramp on top of the run rate: the same extra number of drivers every "
        "week (1x in week 1, 2x in week 2, ...), so hiring starts at today's level and rises in a straight line - never up and down. Each city tab shows the step (column BL) and flags weeks where total "
        "driver acquisition is above the city's proven capacity - its best 4 weeks since Sep 2025 (column BP). Inputs A1 picks the plan: "
        "'Capacity' (used: the same ramp, but total driver acquisition in any week never above the city's proven capacity - so 27 Dec lands "
        "below Lakshya where hiring can't get there), 'Lakshya' (the full ramp, even above proven capacity) or 'Run rate' (no extra hiring). "
        "All three paths are shown on the Monthly Dashboard and the LY vs CY vs Plan tab whichever is picked.",
        "The path is shown against AOP (the baseline, Inputs A5) and Lakshya (the target, Inputs A4) on the Monthly Dashboard and the "
        "LY vs CY vs Plan tab.",
    ])

    # ---- 2. the bridge by city
    ws.cell(r, 1, "2.  THE BRIDGE BY CITY - from now to 27 December").font = F_SECTION
    r += 1
    heads = ["City", "On road now", "Run rate 27 Dec", "Drivers placed in new cars (13 wks)",
             "Within proven capacity 27 Dec", "Plan 27 Dec", "AOP Dec", "Lakshya Dec", "Plan - Lakshya",
             "Extra hiring step a week (to Lakshya)", "Run-rate hiring a week", "Peak week acquisition", "Proven capacity a week"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, r, j, t)
    ws.row_dimensions[r].height = 54
    first = r + 1
    for i, city in enumerate(CITIES + ["INDIA"]):
        r += 1
        s_ = R_SUM0 + i
        put(ws, r, 1, city, bold=True, bg=LIGHT if city == "INDIA" else None)
        vals = [(2, f"=Inputs!$B${s_}", NUM), (3, f"=Inputs!$F${s_}", NUM), (4, f"=Inputs!$R${s_}", NUM),
                (5, f"=Inputs!$X${s_}", NUM), (6, f"=Inputs!$C${s_}", NUM), (7, f"=Inputs!$G${s_}", NUM),
                (8, f"=Inputs!$D${s_}", NUM), (9, f"=ROUND(F{r}-H{r},0)", DIFF_FMT), (10, f"=Inputs!$S${s_}", "0.0"),
                (11, f"=Inputs!${L(RR['u_rec'])}${R_RR0 + i}", NUM),
                (12, f"=Inputs!$T${s_}" if city != "INDIA" else None, NUM), (13, f"=Inputs!$U${s_}", NUM)]
        for j, v, fmt in vals:
            put(ws, r, j, v, fmt, bold=(j in (6, 9)), bg=LIGHT if city == "INDIA" else None)
    ws.conditional_formatting.add(f"L{first}:L{r - 1}", FormulaRule(formula=[f"L{first}>M{first}+0.5"], font=RED_FONT,
                                                                     fill=fill("FFFFC7CE")))
    r += 1
    ws.cell(r, 1, "Run rate = the last 8 weeks' hiring and attrition, flat except the festival dips. Within capacity = + the "
                  "extra ramp, total driver acquisition never above proven capacity. Plan = the option in Inputs A1. Peak week above proven capacity (red) = hiring the city has not shown in the last year.").font = F_NOTE
    r += 3

    r = para(r, "3.  NEW CARS - linked to drivers", [
        "The 582 cars already bought (New Car Stock Report, 27 Sep) are planned by RTO status. Ready for delivery "
        "reach the fleet in weeks 1-2, registration done in weeks 2-3, under RTO in weeks 3-6, RTO not started in weeks 5-8 (Inputs A6; "
        "change the windows there). Each car gets a driver (Own Now) the week after it lands, taken out of the week's hiring - city tab columns AD, BJ and AI.",
        "Lakshya is the December plan, so all of its 2,300 new cars are in the plan: the cars still to buy land in Lakshya's months "
        "(Sep-Oct cars in October, Nov cars in November; Inputs A6). Change the months to the real "
        "order dates once orders are placed.",
    ])
    r = para(r, "4.  FESTIVALS AND ATTRITION", [
        "The plan uses only the Diwali and Durga Puja (Kolkata) dips (Seasonality Check, section 1). Sections 2-4 of that tab show how "
        "every season moved in 2024 and 2025, for reference only.",
        "Attrition this year is lower than the same weeks last year in most cities, but this year's rate has been flat for 12 weeks while "
        "last year's rose through September (Seasonality Check, section 3). The plan keeps this year's 8-week rate (Inputs A3), "
        "changed only in the festival weeks.",
    ])
    r = para(r, "5.  HOW TO READ A CITY TAB", [
        "Rows 2-5 are actual weeks from raw_performance; plan weeks start at row 6 (the current week). Columns A-AC follow the Weekly Supply "
        "Plan layout. Layers: AG EIP, AH-AO Own Now, AP-AT Leasing + DTO, AU total driver acquisition.",
        "Operational basis BH-BT: BH run rate, BI proven capacity, BJ new cars going on road, BK run-rate hiring x festival dip, BL extra hiring "
        "step x week, BM planned on-road add, BP acquisition vs capacity, BR attrition rate this week, BS-BT the run-rate path. "
        "BU-CB: Lakshya and AOP month-ends and the gaps. Last year for reference: AY-BD. Check column AV must be 0.",
    ])
    r = para(r, "6.  UPDATING EACH WEEK", [
        "Paste a fresh SSOT query result (link on Inputs C2) into raw_performance, then set 'Actuals used up to' (Inputs A1) to the "
        "last full day loaded (now Sat 26 Sep). The run rate, opening numbers and actual weeks update. "
        "To move the plan on a week, also set the opening date (Inputs A1) to the latest Sunday.",
        "Update the stock report numbers and delivery windows in Inputs A6 as cars move through RTO, and add orders as they are placed.",
    ])
    ws.freeze_panes = "A5"
    return ws


# ---------------------------------------------------------------- Monthly Dashboard
DASH = "Monthly Dashboard"


def _bu(s):
    return f"{s}!$BU${FIRST}:$BU${LAST}"


def _flow(s, col, mon):
    """Sum of a weekly city-tab column over the plan weeks of one Lakshya month."""
    return f"SUMIFS({s}!${col}${FIRST}:${col}${LAST},{_bu(s)},{mon})"


def _stock(s, col, mon):
    """City-tab column in the last plan week of one Lakshya month (months are contiguous)."""
    return f"INDEX({s}!${col}${FIRST}:${col}${LAST},MATCH({mon},{_bu(s)},0)+COUNTIF({_bu(s)},{mon})-1)"


def _lk_month(city, key_list, mon):
    """Lakshya v4 per city in one plan month: weekly driver acquisition (summed over the month's plan weeks)."""
    return sum(LK_WEEKLY[city][k][w + 1] for k in key_list for w in range(N_WEEKS) if WEEK_MONTH[w] == mon)


def _lk_churn(city, mon):
    m = MONTHS.index(mon)
    return LK_WEEKLY[city]["ld_churn"][m] + LK_WEEKLY[city]["own_churn"][m] + LK_WEEKLY[city]["own_roll"][m]


# Lakshya's driver acquisition over the 13 plan weeks, India
LK_HIRES_ALL = round(sum(sum(v["ld_wk"][1:N_WEEKS + 1]) + sum(v["own_wk"][1:N_WEEKS + 1]) for v in LK_WEEKLY.values()))


def build_dashboard(wb):
    """Month by month for India or a picked city: plan vs run rate, AOP and Lakshya, why they differ, and insights.
    Months are Lakshya's: each plan week counts to the month-end in Inputs A8 (city tab column BU)."""
    ws = wb.create_sheet(DASH, 2)
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = NAVY
    ws.column_dimensions["A"].width = 18
    for j in range(2, 28):
        ws.column_dimensions[get_column_letter(j)].width = 11
    L = get_column_letter
    cities = [q(c) for c in CITIES]
    n = len(CITIES)
    SIGNED = DIFF_FMT
    PP = "+0.0%;-0.0%;0.0%"

    def red_if(rng, cond):
        ws.conditional_formatting.add(rng, FormulaRule(formula=[cond], font=RED_FONT, fill=fill("FFFFC7CE")))

    # ---- layout
    R_MV_T = 5                     # 1. month by month
    R_MV_H = R_MV_T + 1
    R_MV_S = R_MV_H + 1            # start row (27 Sep actual)
    R_MV0 = R_MV_S + 1             # Oct..Dec
    R_MV_TOT = R_MV0 + 3
    R_LV_T = R_MV_TOT + 3          # 2. AOP and Lakshya vs plan
    R_LV_G = R_LV_T + 1
    R_LV_H = R_LV_G + 1
    R_LV_S = R_LV_H + 1
    R_LV0 = R_LV_S + 1
    R_LV_TOT = R_LV0 + 3
    R_PB_T = R_LV_TOT + 3          # 3. why driver acquisition differs from Lakshya
    R_PB_H = R_PB_T + 2
    R_PB0 = R_PB_H + 1
    R_PB_TOT = R_PB0 + 3
    R_IN_T = R_PB_TOT + 3          # 4. insights (India)
    PICK = "$B$3"
    city_list = f"Inputs!$A${R_SUM0}:$A${R_SUM0 + n - 1}"   # city names in Inputs C1

    def pick(exprs, india=None):
        india = india or "+".join(exprs)
        return f'=IF({PICK}="India",{india},CHOOSE(MATCH({PICK},{city_list},0),{",".join(exprs)}))'

    # ---- top
    ws["A1"] = "MONTHLY DASHBOARD  -  India and every city, month by month" + ("  (v2: LAKSHYA AS GIVEN)" if V2 else "")
    ws["A1"].font = F_TITLE
    ws["A3"] = "Show (pick):"
    ws["A3"].font = F_BOLD
    c = ws["B3"]
    c.value = "India"
    c.font = Font(name="Calibri", size=11, bold=True, color=BLUE_TXT)
    c.fill = fill(INPUT)
    c.border = BOX
    dv = DataValidation(type="list", formula1='"' + ",".join(["India"] + CITIES) + '"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add("B3")
    if not V2:  # link to the v2 sheet (added by the user on the live sheet)
        c = ws["D3"]
        c.value = link(V2_URL, "V2 Exact Match with Lakshya_15000_Model_v4.xlsx")
        c.font = Font(name="Calibri", size=10, color="FF1155CC", underline="single")

    # ---- 1. month by month (picked)
    mv = [  # (header, kind, source)
        ("Weeks", "weeks", None), ("New cars reaching the fleet", "flow", ["AD"]), ("Cars sold", "flow", ["AE"]),
        ("New cars put on road", "flow", ["BJ"]), ("Hiring at run rate", "flow", ["BK"]),
        ("Drivers for new cars", "flow", ["AI"]), ("Extra hiring to reach Lakshya", "flow", ["BL"]),
        ("Total driver acquisition", "flow", ["AU"]), ("Drivers leaving (net attrition)", "flow", ["AQ"]),
        ("Attrition % a month", "attr", None), ("EIP net add", "flow", ["AG"]), ("Net add on road", "netadd", None),
        ("Fleet (month end)", "stock", "E"), ("EIP (month end)", "stock", "R"), ("Own Now (month end)", "stock", "X"),
        ("L+DTO (month end)", "stock", "W"), ("On road - plan", "stock", "Y"), ("On road - run rate", "stock", "BS"),
        ("On road - within capacity", "stock", "CG"),
        ("On road - AOP", "aop", None), ("On road - Lakshya", "lakshya", None), ("Plan - AOP", "d_aop", None),
        ("Plan - Lakshya", "d_lk", None), ("Util (month end)", "util", None),
    ]
    col = {h: L(2 + k) for k, (h, _, _) in enumerate(mv)}
    ONR, FLT, OWN, LD = col["On road - plan"], col["Fleet (month end)"], col["Own Now (month end)"], col["L+DTO (month end)"]
    AOPC, LKC = col["On road - AOP"], col["On road - Lakshya"]
    put(ws, R_MV_T, 1, f'="1.  MONTH BY MONTH  -  "&UPPER({PICK})', font=F_SECTION).border = Border()
    hdr(ws, R_MV_H, 1, "Month")
    for h, c_ in col.items():
        hdr(ws, R_MV_H, column_index_from_string(c_), h)
    ws.row_dimensions[R_MV_H].height = 44
    start = {  # the first plan week's opening: the actual (Lakshya's own book in v2)
        "E": lambda s_: f"{s_}!$E${FIRST}-{s_}!$F${FIRST}", "R": lambda s_: f"{s_}!$R${OPEN_ROW}",
        "X": lambda s_: f"{s_}!$AH${FIRST}", "W": lambda s_: f"{s_}!$AP${FIRST}", "Y": lambda s_: f"{s_}!$G${FIRST}",
        "BS": lambda s_: f"{s_}!$G${FIRST}", "CG": lambda s_: f"{s_}!$G${FIRST}",
    }
    r = R_MV_S
    put(ws, r, 1, f'="Start ("&TEXT({G_LAST},"d mmm")&")"' if not V2 else "Start (Lakshya 27 Sep)", bold=True, bg=ACTUAL)
    for h, kind, src in mv:
        j = column_index_from_string(col[h])
        if kind == "stock":
            v, fmt = pick([start[src](s_) for s_ in cities]), NUM
        elif kind == "aop":
            v, fmt = pick([f"Inputs!$B${R_AOP0 + i}" for i in range(n)], f"Inputs!$B${R_AOP0 + n}"), NUM
        elif kind == "lakshya":
            v, fmt = pick([f"Inputs!$N${R_MS0 + i}" for i in range(n)], f"Inputs!$N${R_MS0 + n}"), NUM
        elif kind == "d_aop":
            v, fmt = f"=ROUND({ONR}{r}-{AOPC}{r},0)", SIGNED
        elif kind == "d_lk":
            v, fmt = f"=ROUND({ONR}{r}-{LKC}{r},0)", SIGNED
        elif kind == "util":
            v, fmt = f"={ONR}{r}/{FLT}{r}", PCT
        else:
            v, fmt = None, None
        put(ws, r, j, v, fmt, bg=ACTUAL)
    for m, mon in enumerate(PLAN_MONTHS):
        r = R_MV0 + m
        mi = MONTHS.index(mon)
        put(ws, r, 1, mon, bold=True)
        mref = f"$A{r}"
        for h, kind, src in mv:
            j = column_index_from_string(col[h])
            if kind == "weeks":
                v, fmt = f"=COUNTIF({_bu(cities[0])},{mref})", "0"
            elif kind == "flow":
                v, fmt = pick(["+".join(_flow(s, x, mref) for x in src) for s in cities]), NUM
            elif kind == "attr":
                v, fmt = (f"={col['Drivers leaving (net attrition)']}{r}/{col['Weeks']}{r}*{G_WPM}"
                          f"/AVERAGE({OWN}{r - 1}+{LD}{r - 1},{OWN}{r}+{LD}{r})"), PCT
            elif kind == "stock":
                v, fmt = pick([_stock(s, src, mref) for s in cities]), NUM
            elif kind == "netadd":
                v, fmt = f"={ONR}{r}-{ONR}{r - 1}", SIGNED
            elif kind == "aop":
                v, fmt = pick([f"Inputs!${L(2 + mi)}${R_AOP0 + i}" for i in range(n)], f"Inputs!${L(2 + mi)}${R_AOP0 + n}"), NUM
            elif kind == "lakshya":
                v, fmt = pick([f"Inputs!${L(14 + mi)}${R_MS0 + i}" for i in range(n)], f"Inputs!${L(14 + mi)}${R_MS0 + n}"), NUM
            elif kind == "d_aop":
                v, fmt = f"=ROUND({ONR}{r}-{AOPC}{r},0)", SIGNED
            elif kind == "d_lk":
                v, fmt = f"=ROUND({ONR}{r}-{LKC}{r},0)", SIGNED
            else:
                v, fmt = f"={ONR}{r}/{FLT}{r}", PCT
            put(ws, r, j, v, fmt, bold=(kind in ("netadd", "d_lk", "d_aop") or h == "On road - plan"))
    r = R_MV_TOT
    put(ws, r, 1, "Total / 27 Dec", bold=True, bg=LIGHT)
    for h, kind, src in mv:
        c_ = col[h]
        if kind in ("stock", "aop", "lakshya", "d_aop", "d_lk", "util"):
            v = f"={c_}{R_MV0 + 2}"
        elif kind == "attr":
            v = (f"={col['Drivers leaving (net attrition)']}{r}/{N_WEEKS}*{G_WPM}"
                 f"/AVERAGE({OWN}{R_MV_S}+{LD}{R_MV_S},{OWN}{R_MV0 + 2}+{LD}{R_MV0 + 2})")
        else:
            v = f"=SUM({c_}{R_MV0}:{c_}{R_MV0 + 2})"
        fmt = PCT if kind in ("util", "attr") else (SIGNED if kind in ("netadd", "d_aop", "d_lk") else NUM)
        put(ws, r, column_index_from_string(c_), v, fmt, bold=True, bg=LIGHT)
    for k_ in ("Plan - AOP", "Plan - Lakshya"):
        red_if(f"{col[k_]}{R_MV_S}:{col[k_]}{R_MV_TOT}", f"{col[k_]}{R_MV_S}<-0.5")
    ws.cell(R_MV_TOT + 1, 1, "Driver acquisition = hiring at the current run rate (x validated season) + a driver for every new car + the "
                             "extra hiring step (Inputs A1). Run rate = the same without the extra step. Red = below AOP or Lakshya.").font = F_NOTE

    # ---- 2. AOP and Lakshya vs plan (picked)
    put(ws, R_LV_T, 1, f'="2.  AOP AND LAKSHYA vs OUR PLAN  -  "&UPPER({PICK})', font=F_SECTION).border = Border()
    groups = [("ON ROAD (month end)", ["AOP", "Lakshya", "Plan", "Plan - AOP", "Plan - Lakshya"]),
              ("OWN NOW + L+DTO BOOK (month end)", ["Lakshya", "Plan", "Plan - Lakshya"]),
              ("DRIVER ACQUISITION in the month", ["AOP", "Lakshya", "Plan", "Plan - Lakshya"]),
              ("ATTRITION % A MONTH", ["Lakshya", "Plan", "Plan - Lakshya"])]
    hdr(ws, R_LV_G, 1, "")
    hdr(ws, R_LV_H, 1, "Month")
    gc, c0 = {}, 2
    for gt, heads in groups:
        hdr(ws, R_LV_G, c0, gt, GREY_HDR)
        ws.merge_cells(start_row=R_LV_G, start_column=c0, end_row=R_LV_G, end_column=c0 + len(heads) - 1)
        for k, t in enumerate(heads):
            hdr(ws, R_LV_H, c0 + k, t)
            gc[(gt, t)] = L(c0 + k)
        c0 += len(heads)
    WHY = c0
    hdr(ws, R_LV_G, WHY, "")
    hdr(ws, R_LV_H, WHY, "Why the plan differs from Lakshya")
    ws.merge_cells(start_row=R_LV_G, start_column=WHY, end_row=R_LV_G, end_column=WHY + 5)
    ws.merge_cells(start_row=R_LV_H, start_column=WHY, end_row=R_LV_H, end_column=WHY + 5)
    ws.row_dimensions[R_LV_G].height = 30
    ws.row_dimensions[R_LV_H].height = 30
    G1, G2, G3, G4 = (g for g, _ in groups)
    lk_book = lambda mi: pick([f"Inputs!${L(6 + mi)}${R_MS0 + i}+Inputs!${L(10 + mi)}${R_MS0 + i}" for i in range(n)],
                             f"Inputs!${L(6 + mi)}${R_MS0 + n}+Inputs!${L(10 + mi)}${R_MS0 + n}")
    for key, r in [("start", R_LV_S)] + [(m, R_LV0 + m) for m in range(3)] + [("total", R_LV_TOT)]:
        bg = ACTUAL if key == "start" else (LIGHT if key == "total" else None)
        mvr = {"start": R_MV_S, "total": R_MV_TOT}.get(key, R_MV0 + key if isinstance(key, int) else None)
        mon = None if key in ("start", "total") else PLAN_MONTHS[key]
        mi = 0 if key == "start" else (3 if key == "total" else MONTHS.index(mon))
        put(ws, r, 1, {"start": f'="Start ("&TEXT({G_LAST},"d mmm")&")"', "total": "Total / 27 Dec"}.get(key, mon), bold=True, bg=bg)
        cells = {
            (G1, "AOP"): f"={AOPC}{mvr}", (G1, "Lakshya"): f"={LKC}{mvr}", (G1, "Plan"): f"={ONR}{mvr}",
            (G1, "Plan - AOP"): f"=ROUND({gc[(G1, 'Plan')]}{r}-{gc[(G1, 'AOP')]}{r},0)",
            (G1, "Plan - Lakshya"): f"=ROUND({gc[(G1, 'Plan')]}{r}-{gc[(G1, 'Lakshya')]}{r},0)",
            (G2, "Lakshya"): lk_book(mi), (G2, "Plan"): f"={OWN}{mvr}+{LD}{mvr}",
            (G2, "Plan - Lakshya"): f"=ROUND({gc[(G2, 'Plan')]}{r}-{gc[(G2, 'Lakshya')]}{r},0)",
        }
        if key != "start":
            if key == "total":
                cells[(G3, "AOP")] = f"=SUM({gc[(G3, 'AOP')]}{R_LV0}:{gc[(G3, 'AOP')]}{R_LV0 + 2})"
                cells[(G3, "Lakshya")] = f"=SUM({gc[(G3, 'Lakshya')]}{R_LV0}:{gc[(G3, 'Lakshya')]}{R_LV0 + 2})"
                wk_, prev = N_WEEKS, R_LV_S
            else:
                cells[(G3, "AOP")] = pick([f"Inputs!${L(10 + mi)}${R_AOP0 + i}" for i in range(n)], f"Inputs!${L(10 + mi)}${R_AOP0 + n}")
                cells[(G3, "Lakshya")] = pick([str(_lk_month(c_, ("ld_wk", "own_wk"), mon)) for c_ in CITIES])
                wk_, prev = WEEK_MONTH.count(mon), r - 1
            cells[(G3, "Plan")] = f"={col['Total driver acquisition']}{mvr}"
            cells[(G3, "Plan - Lakshya")] = f"=ROUND({gc[(G3, 'Plan')]}{r}-{gc[(G3, 'Lakshya')]}{r},0)"
            # Lakshya churn = its monthly churn + rollover (Lakshya Weekly figures), as % of its average book
            if key == "total":
                lk_ch = pick([str(sum(_lk_churn(c_, m_) for m_ in PLAN_MONTHS)) for c_ in CITIES])[1:]
            else:
                lk_ch = pick([str(_lk_churn(c_, mon)) for c_ in CITIES])[1:]
            bk = gc[(G2, "Lakshya")]
            cells[(G4, "Lakshya")] = f"=({lk_ch})/{wk_}*{G_WPM}/AVERAGE({bk}{prev},{bk}{r})"
            cells[(G4, "Plan")] = f"={col['Attrition % a month']}{mvr}"
            cells[(G4, "Plan - Lakshya")] = f"={gc[(G4, 'Plan')]}{r}-{gc[(G4, 'Lakshya')]}{r}"
        for (g, t), c_ in gc.items():
            v = cells.get((g, t))
            fmt = PCT if g == G4 and t != "Plan - Lakshya" else (PP if g == G4 else (SIGNED if t.startswith("Plan -") else NUM))
            put(ws, r, column_index_from_string(c_), v, fmt, bold=t.startswith("Plan -"), bg=bg)
        d_on, d_bk = f"{gc[(G1, 'Plan - Lakshya')]}{r}", f"{gc[(G2, 'Plan - Lakshya')]}{r}"
        if key == "start":
            why = (f'="Actual on "&TEXT({G_LAST},"d mmm")&": "&TEXT({d_on},"+#,##0;-#,##0;0")&" vs Lakshya\'s 27 Sep and "'
                   f'&TEXT({gc[(G1, "Plan - AOP")]}{r},"+#,##0;-#,##0;0")&" vs AOP September - the plan starts from here."')
        else:
            acq = gc[(G3, "Plan")]
            why = (f'=IF(ABS({d_on})<0.5,"On Lakshya.",TEXT({d_on},"+#,##0;-#,##0;0")&" vs Lakshya.")&" Plan hires "'
                   f'&TEXT({acq}{r},"#,##0")&" vs Lakshya "&TEXT({gc[(G3, "Lakshya")]}{r},"#,##0")&"; attrition "'
                   f'&TEXT({gc[(G4, "Plan")]}{r},"0%")&" a month vs Lakshya "&TEXT({gc[(G4, "Lakshya")]}{r},"0%")&"."')
        c = put(ws, r, WHY, why, bg=bg)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=WHY, end_row=r, end_column=WHY + 5)
        ws.row_dimensions[r].height = 30
    for (g, t), c_ in gc.items():
        if t.startswith("Plan -") and g != G4:
            red_if(f"{c_}{R_LV_S}:{c_}{R_LV_TOT}", f"AND(ISNUMBER({c_}{R_LV_S}),{c_}{R_LV_S}<-0.5)")
    ws.cell(R_LV_TOT + 1, 1, "AOP = AOP FY27 (Inputs A5); Lakshya = Lakshya v4 month-ends (A4) and its weekly driver acquisition by city "
                             "(Lakshya Weekly figures). Attrition % a month = drivers leaving / weeks x 52/12 / average Own Now + L+DTO book.").font = F_NOTE

    # ---- 3. why driver acquisition differs from Lakshya (picked): acquisition = book change + drivers leaving
    put(ws, R_PB_T, 1, f'="3.  WHY DRIVER ACQUISITION DIFFERS FROM LAKSHYA  -  "&UPPER({PICK})&"  (acquisition = book at month end - book at start + drivers leaving)"',
        font=F_SECTION).border = Border()
    pb_groups = [("BOOK AT START (Own Now + L+DTO)", 2), ("BOOK AT MONTH END", 4), ("NET ADD", 6),
                 ("DRIVERS LEAVING", 8), ("DRIVER ACQUISITION", 10)]
    hdr(ws, R_PB_T + 1, 1, "")
    hdr(ws, R_PB_H, 1, "Month")
    for gt, c0 in pb_groups:
        hdr(ws, R_PB_T + 1, c0, gt, GREY_HDR)
        ws.merge_cells(start_row=R_PB_T + 1, start_column=c0, end_row=R_PB_T + 1, end_column=c0 + 1)
        hdr(ws, R_PB_H, c0, "Lakshya")
        hdr(ws, R_PB_H, c0 + 1, "Plan")
    hdr(ws, R_PB_T + 1, 12, "", GREY_HDR)
    hdr(ws, R_PB_H, 12, "Plan - Lakshya")
    hdr(ws, R_PB_T + 1, 13, "", GREY_HDR)
    hdr(ws, R_PB_H, 13, "Why")
    ws.merge_cells(start_row=R_PB_T + 1, start_column=13, end_row=R_PB_T + 1, end_column=22)
    ws.merge_cells(start_row=R_PB_H, start_column=13, end_row=R_PB_H, end_column=22)
    ws.row_dimensions[R_PB_T + 1].height = 30
    ws.row_dimensions[R_PB_H].height = 30
    lvr = lambda rr_: rr_ - R_PB0 + R_LV0
    for m, mon in enumerate(PLAN_MONTHS):
        r = R_PB0 + m
        put(ws, r, 1, mon, bold=True)
        vals = [(2, f"={gc[(G2, 'Lakshya')]}{lvr(r) - 1}"), (3, f"={gc[(G2, 'Plan')]}{lvr(r) - 1}"),
                (4, f"={gc[(G2, 'Lakshya')]}{lvr(r)}"), (5, f"={gc[(G2, 'Plan')]}{lvr(r)}"),
                (6, f"=D{r}-B{r}"), (7, f"=E{r}-C{r}"),
                (8, f"=J{r}-F{r}"), (9, f"=K{r}-G{r}"),
                (10, f"={gc[(G3, 'Lakshya')]}{lvr(r)}"), (11, f"={gc[(G3, 'Plan')]}{lvr(r)}"), (12, f"=K{r}-J{r}")]
        for j, v in vals:
            put(ws, r, j, v, SIGNED if j in (6, 7, 12) else NUM, bold=(j == 12))
        why = (f'=TEXT(L{r},"+#,##0;-#,##0;0")&" = book growth "&TEXT(G{r}-F{r},"+#,##0;-#,##0;0")&" (plan "&TEXT(C{r},"#,##0")'
               f'&" to "&TEXT(E{r},"#,##0")&", Lakshya "&TEXT(B{r},"#,##0")&" to "&TEXT(D{r},"#,##0")&") + drivers leaving "'
               f'&TEXT(I{r}-H{r},"+#,##0;-#,##0;0")&" (attrition "&TEXT({gc[(G4, "Plan")]}{lvr(r)},"0%")&" a month vs Lakshya "'
               f'&TEXT({gc[(G4, "Lakshya")]}{lvr(r)},"0%")&")."')
        c = put(ws, r, 13, why)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=13, end_row=r, end_column=22)
        ws.row_dimensions[r].height = 30
    r = R_PB_TOT
    put(ws, r, 1, "Total", bold=True, bg=LIGHT)
    for j in range(2, 13):
        c_ = L(j)
        v = f"={c_}{R_PB0}" if j in (2, 3) else (f"={c_}{R_PB0 + 2}" if j in (4, 5) else f"=SUM({c_}{R_PB0}:{c_}{R_PB0 + 2})")
        put(ws, r, j, v, SIGNED if j in (6, 7, 12) else NUM, bold=True, bg=LIGHT)
    c = put(ws, r, 13, (f'=TEXT(L{r},"+#,##0;-#,##0;0")&" = book growth "&TEXT(G{r}-F{r},"+#,##0;-#,##0;0")'
                        f'&" (the plan starts "&TEXT(C{r}-B{r},"+#,##0;-#,##0;0")&" vs Lakshya\'s 27 Sep book) + drivers leaving "'
                        f'&TEXT(I{r}-H{r},"+#,##0;-#,##0;0")&"."'), bold=True, bg=LIGHT)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=r, start_column=13, end_row=r, end_column=22)
    ws.row_dimensions[r].height = 30
    red_if(f"L{R_PB0}:L{R_PB_TOT}", f"L{R_PB0}<-0.5")
    ws.cell(R_PB_TOT + 1, 1, "Lakshya's drivers leaving = its driver acquisition - its book growth. The plan's = the current attrition rate "
                             "(Inputs A3) x the validated seasonal change, on the plan's own book.").font = F_NOTE

    # ---- 4. insights (India, live)
    put(ws, R_IN_T, 1, "4.  INSIGHTS  -  India (live; update with the plan)", font=F_SECTION).border = Border()
    ri = R_SUM0 + n                                    # INDIA row of Inputs C1
    c1 = lambda c_: f"Inputs!${c_}${ri}"
    c1r = lambda c_: f"Inputs!${c_}${R_SUM0}:${c_}${ri - 1}"
    rri = lambda k: f"Inputs!${L(RR[k])}${R_RR0 + n}"
    allc = lambda expr: "(" + "+".join(expr(s) for s in cities) + ")"
    step_cities = "&".join(f'IF(ABS({q(c_)}!{STEP_CELL})>=0.5,"{c_} "&TEXT({q(c_)}!{STEP_CELL},"0;-0")&", ","")' for c_ in CITIES)
    above = "&".join(f'IF(Inputs!$P${R_SUM0 + i}<0,"{c_} "&TEXT(Inputs!$N${R_SUM0 + i},"0.0%")&" vs max "&TEXT(Inputs!$O${R_SUM0 + i},"0.0%")&", ","")'
                     for i, c_ in enumerate(CITIES))
    over_cap = "&".join(f'IF(Inputs!$V${R_SUM0 + i}>0,"{c_} ("&Inputs!$V${R_SUM0 + i}&" wks), ","")' for i, c_ in enumerate(CITIES))
    ins = [
        # where we start
        (f'="Where we start: "&TEXT({c1("B")},"#,##0")&" cars on road ("&TEXT({G_LAST},"d mmm")&"): "'
         f'&TEXT(ABS({c1("B")}-Inputs!$B${R_AOP0 + n}),"#,##0")&IF({c1("B")}<Inputs!$B${R_AOP0 + n}," below"," above")&" AOP September and "'
         f'&TEXT(ABS({c1("B")}-Inputs!$N${R_MS0 + n}),"#,##0")&IF({c1("B")}<Inputs!$N${R_MS0 + n}," below"," above")&" Lakshya\'s 27 Sep book."'),
        # current run rate
        (f'="Current run rate (last 8 weeks): "&TEXT({rri("rec")},"#,##0")&" drivers acquired a week ("&TEXT({rri("rec_yoy")},"+0%;-0%")'
         f'&" vs the same weeks last year) and "&TEXT({rri("na_rate")},"0.0%")&" of drivers leaving a week ("&TEXT({rri("na_yoy")},"+0%;-0%")'
         f'&" vs last year). If that continues flat (festival dips only), 27 Dec lands at "&TEXT({c1("F")},"#,##0")&"."'),
        # new cars
        (f'="New cars: "&TEXT(Inputs!$F${R_STK0 + n},"#,##0")&" bought and at the stock yard reach the fleet between "'
         f'&TEXT(Inputs!$D${R_WIN0 + len(DELIVERY_WINDOWS) - 1},"d mmm")&" and "&TEXT(Inputs!$E${R_WIN0},"d mmm")'
         f'&"; the other "&TEXT(Inputs!$E${R_FUT0 + n},"#,##0")&" of Lakshya\'s cars are still to buy and planned in Oct-Nov as in Lakshya. "'
         f'&"FLAG: a car ordered now lands w/c "&TEXT(INDEX(Inputs!$B${R_CAL0}:$B${R_CAL0 + N_WEEKS - 1},Inputs!$B${R_WIN0}),"d mmm")'
         f'&" at the earliest, so the "&TEXT(Inputs!$B${R_FUT0 + n},"#,##0")&" October cars only land if already ordered, and November\'s "'
         f'&TEXT(Inputs!$C${R_FUT0 + n},"#,##0")&" must be ordered from this week (dates by city: Inputs A6). "'
         f'&TEXT({c1("R")},"#,##0")&" drivers are needed for new cars in all."'),
        # seasonality
        (f'="Seasonality: only two festival dips. Diwali (w/c 2 and 9 Nov, every city; India): hiring "'
         f'&TEXT({SQ}!$B${R_SU0 + n},"+0%;-0%;0%")&", attrition "&TEXT({SQ}!$F${R_SU0 + n},"+0%;-0%;0%")'
         f'&". Durga Puja (w/c 12 and 19 Oct, Kolkata only): hiring "&TEXT({SQ}!$C${R_SU0 + CITIES.index("Kolkata")},"+0%;-0%;0%")'
         f'&" a week. Every other week runs at the flat 8-week rate (Seasonality Check, section 1)."'),
        # three paths
        (f'="27 Dec: run rate "&TEXT({c1("F")},"#,##0")&", within proven hiring capacity "&TEXT({c1("X")},"#,##0")&", Lakshya ramp "'
         f'&TEXT({c1("D")},"#,##0")&" (AOP "&TEXT({c1("G")},"#,##0")&"). The plan uses: "&{G_CAP}&" (Inputs A1) and lands at "'
         f'&TEXT({c1("C")},"#,##0")&"."'),
        # what Lakshya takes
        (f'="To reach Lakshya: hiring rises by "&TEXT({c1("S")},"#,##0")&" drivers a week, every week, on top of the run rate (by city: "'
         f'&IF(({step_cities})="","none",LEFT({step_cities},LEN({step_cities})-2))&"); with the ramp, driver acquisition in the last week is "'
         f'&TEXT({allc(lambda s: f"{s}!BK{LAST}+{s}!{STEP_CELL}*{N_WEEKS}*(1+{s}!BE{LAST})")},"#,##0")'
         f'&" a week vs "&TEXT({rri("rec")},"#,##0")&" today and "&TEXT({rri("cap")},"#,##0")&" at best in the last year."'),
        # capacity
        (f'="Above proven hiring capacity (best 4 weeks since Sep 2025): "&IF(({over_cap})="","no city.",LEFT({over_cap},LEN({over_cap})-2)'
         f'&" - these weeks need hiring the city has not delivered in the last year.")'),
        # AOP
        (f'="Vs AOP: plan "&TEXT({c1("H")},"+#,##0;-#,##0;0")&" on 27 Dec (plan "&TEXT({c1("C")},"#,##0")&", AOP "&TEXT({c1("G")},"#,##0")'
         f'&"); AOP recruitment Oct-Dec "&TEXT(SUM(Inputs!$K${R_AOP0 + n}:$M${R_AOP0 + n}),"#,##0")&" vs plan "&TEXT({c1("Q")},"#,##0")&"."'),
        # utilisation
        (f'=IF({c1("Y")}<0.5,"Cars: the fleet carries the plan within every city\'s max utilisation.","Cars: at max utilisation the fleet is "'
         f'&TEXT({c1("Y")},"#,##0")&" cars short of the plan on 27 Dec ("&IF(({above})="","",LEFT({above},LEN({above})-2))&") - the plan needs '
         f'more cars or fewer cars sold.")'),
        # the gap to Lakshya: what it is made of (LY vs CY vs Plan, section 3)
        (f'=IF({c1("E")}>-0.5,"Plan reaches Lakshya on 27 Dec.","Gap to Lakshya on 27 Dec: "&TEXT({c1("E")},"+#,##0;-#,##0")&" = start "'
         f'&TEXT({c1("B")}-Inputs!$N${R_MS0 + n},"+#,##0;-#,##0")&", EIP flat "&TEXT({c1("I")}-Inputs!$E${R_MS0 + n},"+#,##0;-#,##0")'
         f'&", more hiring than Lakshya "&TEXT({c1("Q")}-{LK_HIRES_ALL},"+#,##0;-#,##0")&", more drivers leaving "'
         f'&TEXT({c1("E")}-({c1("B")}-Inputs!$N${R_MS0 + n})-({c1("I")}-Inputs!$E${R_MS0 + n})-({c1("Q")}-{LK_HIRES_ALL}),"+#,##0;-#,##0")'
         f'&" (attrition "&TEXT({rri("na_rate")},"0.0%")&" a week vs Lakshya\'s lower rate). What closes it: {BRIDGE_TAB} tab, section 3.")'),
    ]
    for k, f in enumerate(ins):
        r = R_IN_T + 1 + k
        c = put(ws, r, 1, f)
        c.border = Border()
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=22)
        ws.row_dimensions[r].height = 30
    ws.freeze_panes = "B4"
    return ws


# ---------------------------------------------------------------- LY vs CY vs Plan (consolidated comparison)
BRIDGE_TAB = "LY vs CY vs Plan"


def build_bridge(wb):
    """Last year, this year, current run rate, plan, AOP and Lakshya side by side, week on week (India or a picked city)."""
    ws = wb.create_sheet(BRIDGE_TAB, 3)
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = TEAL
    ws.column_dimensions["A"].width = 16
    for j in range(2, 24):
        ws.column_dimensions[get_column_letter(j)].width = 11
    L = get_column_letter
    n = len(CITIES)
    cities = [q(c) for c in CITIES]
    PICK = "$B$3"
    city_list = f"Inputs!$A${R_SUM0}:$A${R_SUM0 + n - 1}"

    def pick(exprs, india=None):
        india = india or "+".join(exprs)
        return f'=IF({PICK}="India",{india},CHOOSE(MATCH({PICK},{city_list},0),{",".join(exprs)}))'

    def raw(field, city, crit_col, crit):
        c = rc(field)
        return (f'SUMIFS(raw_performance!${c}:${c},raw_performance!$D:$D,"{city}",raw_performance!$E:$E,"CNG",'
                f'raw_performance!${crit_col}:${crit_col},{crit})')

    ws["A1"] = "LY vs CY vs PLAN  -  last year, this year, the run rate, the plan, AOP and Lakshya"
    ws["A1"].font = F_TITLE
    ws["A2"] = ("Is the planned growth supported by what we did last year and what we are doing now? Last year = the same week "
                "364 days earlier (raw_performance).")
    ws["A2"].font = F_NOTE
    ws["A3"] = "Show (pick):"
    ws["A3"].font = F_BOLD
    c = ws["B3"]
    c.value = "India"
    c.font = Font(name="Calibri", size=11, bold=True, color=BLUE_TXT)
    c.fill = fill(INPUT)
    c.border = BOX
    dv = DataValidation(type="list", formula1='"' + ",".join(["India"] + CITIES) + '"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add("B3")

    # ---- 2. week by week (built first so the bridge can sum it)
    R_W_T = 20
    R_W_H = R_W_T + 2
    R_W0 = R_W_H + 1
    rows = list(range(2, LAST + 1))                   # city-tab rows: 4 actual weeks + the plan weeks
    me_rows = {OPEN_ROW: 0, FIRST + 3: 1, FIRST + 8: 2, FIRST + 12: 3}   # month-end weeks: 27 Sep, 25 Oct, 29 Nov, 27 Dec
    put(ws, R_W_T, 1, f'="2.  WEEK BY WEEK  -  "&UPPER({PICK})', font=F_SECTION).border = Border()
    groups = [("", 1, 2), ("CARS ON ROAD (week end)", 3, 12), ("DRIVER ACQUISITION a week", 13, 15),
              ("NET ATTRITION % a week", 16, 17)]
    for t, a_, b_ in groups:
        hdr(ws, R_W_T + 1, a_, t, GREY_HDR)
        if b_ > a_:
            ws.merge_cells(start_row=R_W_T + 1, start_column=a_, end_row=R_W_T + 1, end_column=b_)
    heads = ["Week (w/c)", "Actual / Plan", "Last year", "LY WoW", "This year / Plan", "WoW", "Run rate path",
             "Within capacity", "AOP (month end)", "Lakshya (month end)", "vs last year", "vs Lakshya (month end)",
             "Last year", "This year / Plan", "vs last year", "Last year", "This year / Plan"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_W_H, j, t)
    ws.row_dimensions[R_W_H].height = 42
    for k, cr in enumerate(rows):
        r = R_W0 + k
        actual = cr < FIRST
        bg = ACTUAL if actual else None
        wk = f"{cities[0]}!$D${cr}"
        put(ws, r, 1, f"={wk}", DATE, bold=True, bg=bg)
        put(ws, r, 2, "Actual" if actual else "Plan", None, bg=bg)
        put(ws, r, 3, pick([raw("allotted_cars_eod", c_, "C", f"{wk}+6-364") for c_ in CITIES]), NUM, bg=HIST, font=F_HIST)
        put(ws, r, 4, f"=C{r}-" + (pick([raw("allotted_cars_eod", c_, "C", f"{wk}-1-364") for c_ in CITIES])[1:] if k == 0 else f"C{r - 1}"),
            DIFF_FMT, bg=HIST, font=F_HIST)
        put(ws, r, 5, pick([f"{s}!$Y${cr}" for s in cities]), NUM, bold=True, bg=bg)
        put(ws, r, 6, f"=E{r}-" + (pick([f"{s}!$G${cr}" for s in cities])[1:] if k == 0 else f"E{r - 1}"), DIFF_FMT, bold=True, bg=bg)
        put(ws, r, 7, None if actual else pick([f"{s}!$BS${cr}" for s in cities]), NUM, bg=bg)
        put(ws, r, 8, None if actual else pick([f"{s}!$CG${cr}" for s in cities]), NUM, bg=bg)
        if cr in me_rows:
            m = me_rows[cr]
            put(ws, r, 9, pick([f"Inputs!${L(2 + m)}${R_AOP0 + i}" for i in range(n)], f"Inputs!${L(2 + m)}${R_AOP0 + n}"), NUM, bg=bg)
            put(ws, r, 10, pick([f"Inputs!${L(14 + m)}${R_MS0 + i}" for i in range(n)], f"Inputs!${L(14 + m)}${R_MS0 + n}"), NUM, bg=bg)
            put(ws, r, 12, f"=E{r}-J{r}", DIFF_FMT, bold=True, bg=bg)
        else:
            for j in (9, 10, 12):
                put(ws, r, j, None, bg=bg)
        put(ws, r, 11, f"=IFERROR(E{r}/C{r}-1,0)", "+0%;-0%;0%", bg=bg)
        rec_ly = pick([f"{raw('newjoin_cnt', c_, 'B', f'{wk}-364')}+{raw('resurrection_cnt', c_, 'B', f'{wk}-364')}" for c_ in CITIES])
        put(ws, r, 13, rec_ly, NUM, bg=HIST, font=F_HIST)
        put(ws, r, 14, pick([f"{s}!$AU${cr}" for s in cities]), NUM, bold=True, bg=bg)
        put(ws, r, 15, f"=IFERROR(N{r}/M{r}-1,0)", "+0%;-0%;0%", bg=bg)
        na_ly = [f"({raw('attrition_cnt', c_, 'B', f'{wk}-364')}+{raw('temp_attrition_cnt', c_, 'B', f'{wk}-364')}"
                 f"-{raw('rejoin_cnt', c_, 'B', f'{wk}-364')}-{raw('temp_rejoin_cnt', c_, 'B', f'{wk}-364')})" for c_ in CITIES]
        dr_ly = [raw("uniq_partners_dt_beginning", c_, "C", f"{wk}-364") for c_ in CITIES]
        put(ws, r, 16, f'=IFERROR({pick([f"{a}/{b}" for a, b in zip(na_ly, dr_ly)], "(" + "+".join(na_ly) + ")/(" + "+".join(dr_ly) + ")")[1:]},0)',
            PCT, bg=HIST, font=F_HIST)
        put(ws, r, 17, f'=IFERROR({pick([f"-{s}!$U${cr}" for s in cities])[1:]}/{pick([f"{s}!$H${cr}" for s in cities])[1:]},0)',
            PCT, bold=True, bg=bg)
    last_w = R_W0 + len(rows) - 1
    for c_ in ("K", "L", "O"):
        ws.conditional_formatting.add(f"{c_}{R_W0}:{c_}{last_w}", FormulaRule(formula=[f"{c_}{R_W0}<-0.005"], font=RED_FONT))
    ws.cell(last_w + 1, 1, "WoW = change on the week before. This year's attrition % = drivers leaving / drivers at the start of the week "
                           "(actual weeks: from raw_performance; plan weeks: the plan's rate).").font = F_NOTE
    fp, lp = R_W0 + N_ACTUAL, last_w                    # plan rows on this tab
    now = R_W0 + N_ACTUAL - 1                           # last actual week

    # ---- 1. the bridge
    put(ws, 5, 1, f'="1.  THE BRIDGE  -  "&UPPER({PICK})&": last year -> now -> run rate -> within capacity -> plan -> AOP -> Lakshya"',
        font=F_SECTION).border = Border()
    heads = ["", "Last year, same weeks", "This year: now", "Run rate (if nothing changes)", "Within proven capacity", "Plan",
             "AOP", "Lakshya", "Plan vs last year", "Plan vs AOP", "Plan vs Lakshya"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, 6, j, t)
    ws.row_dimensions[6].height = 42
    lk_acq = pick([str(sum(LK_WEEKLY[c_]["ld_wk"][1:]) + sum(LK_WEEKLY[c_]["own_wk"][1:])) for c_ in CITIES])[1:]
    per_wk = lambda expr: "=(" + expr + f")/{N_WEEKS}"
    lines = [
        ("Cars on road, 27 Dec (now: latest actual)", f"=C{lp}", f"=E{now}", f"=G{lp}", f"=H{lp}", f"=E{lp}",
         pick([f"Inputs!$E${R_AOP0 + i}" for i in range(n)], f"Inputs!$E${R_AOP0 + n}"),
         pick([f"Inputs!$Q${R_MS0 + i}" for i in range(n)], f"Inputs!$Q${R_MS0 + n}"), NUM),
        ("Growth to 27 Dec (cars on road)", f"=C{lp}-C{now}", f"=E{now}-E{R_W0}+F{R_W0}", f"=D7-C7", f"=E7-C7",
         f"=F7-C7", f"=G7-C7", f"=H7-C7", DIFF_FMT),
        ("Driver acquisition a week", f"=AVERAGE(M{fp}:M{lp})", pick([rr("u_rec", i) for i in range(n)]),
         per_wk(pick([f"{s}!$BK${R_TOT}+{s}!$BJ${R_TOT}" for s in cities])[1:]),
         per_wk(pick([f"{s}!$BK${R_TOT}+{s}!$BJ${R_TOT}+{s}!$CE${R_TOT}" for s in cities])[1:]),
         f"=AVERAGE(N{fp}:N{lp})",
         per_wk(pick([f"SUM(Inputs!$K${R_AOP0 + i}:$M${R_AOP0 + i})" for i in range(n)])[1:]),
         per_wk(lk_acq), NUM),
        ("Net attrition % a week", f"=AVERAGE(P{fp}:P{lp})", pick([rr("u_rate", i) for i in range(n)],
         f"Inputs!${L(RR['u_rate'])}${R_RR0 + n}"), None, None, f"=AVERAGE(Q{fp}:Q{lp})", None, None, PCT),
    ]
    for k, (label, ly, cy, rr_, cap, plan, aop, lk, fmt) in enumerate(lines):
        r = 7 + k
        put(ws, r, 1, label, bold=True)
        for j, v in ((2, ly), (3, cy), (4, rr_), (5, cap), (6, plan), (7, aop), (8, lk)):
            put(ws, r, j, v, fmt, bold=(j == 6), bg=HIST if j == 2 else (ACTUAL if j == 3 else None),
                font=F_HIST if j == 2 else F_BODY)
        if fmt == PCT:
            put(ws, r, 9, f"=F{r}-B{r}", "+0.0%;-0.0%;0.0%")
            put(ws, r, 10, None)
            put(ws, r, 11, None)
        elif k == 1:
            for j in (9, 10, 11):
                put(ws, r, j, None)
        else:
            put(ws, r, 9, f"=IFERROR(F{r}/B{r}-1,0)", "+0%;-0%;0%", bold=True)
            put(ws, r, 10, f"=F{r}-G{r}", DIFF_FMT, bold=True)
            put(ws, r, 11, f"=F{r}-H{r}", DIFF_FMT, bold=True)
    ws.row_dimensions[7].height = 30
    notes = [
        "Last year, same weeks: cars on road on the same Sunday of 2025; driver acquisition and attrition averaged over the plan's weeks a year earlier.",
        "Run rate: the last 8 weeks' hiring and attrition, flat except the Diwali and Durga Puja dips - no extra hiring.",
        "Within proven capacity: the steady extra ramp, but total driver acquisition never above the city's best 4 weeks since Sep 2025. Plan: the option chosen in Inputs A1.",
    ]
    for k, t in enumerate(notes):
        ws.cell(11 + k, 1, t).font = F_NOTE
    for c_ in ("J", "K"):
        ws.conditional_formatting.add(f"{c_}7:{c_}9", FormulaRule(formula=[f"{c_}7<-0.5"], font=RED_FONT))

    # ---- 3. the gap to Lakshya on 27 Dec: what it is made of, and what closes it (by city)
    R_G_T = R_W0 + len(rows) + 3
    R_G_H = R_G_T + 2
    put(ws, R_G_T, 1, "3.  GAP TO LAKSHYA ON 27 DEC  -  what it is made of, and what would close it (by city)",
        font=F_SECTION).border = Border()
    groups = [("", 1, 1), ("CARS ON ROAD 27 DEC", 2, 4), ("THE GAP IS MADE OF", 5, 8), ("ATTRITION A WEEK", 9, 10),
              ("WHAT CLOSES IT", 11, 14)]
    for t, a_, b_ in groups:
        hdr(ws, R_G_T + 1, a_, t, GREY_HDR)
        if b_ > a_:
            ws.merge_cells(start_row=R_G_T + 1, start_column=a_, end_row=R_G_T + 1, end_column=b_)
    heads = ["City", "Plan", "Lakshya", "Plan - Lakshya", "Start: actual vs Lakshya's 27 Sep", "EIP: plan flat vs Lakshya's growth",
             "Hiring: plan vs Lakshya (13 wks)", "Drivers leaving: plan vs Lakshya", "Plan (last 8 weeks)", "Lakshya (implied)",
             "Each 1 pt lower attrition a week adds", "Each +10 hires a week adds", "Attrition cut that closes the gap (pts a week)",
             "or extra hires a week that close it"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_G_H, j, t)
    ws.row_dimensions[R_G_H].height = 56
    for i, city in enumerate(CITIES + ["INDIA"]):
        r = R_G_H + 1 + i
        india = city == "INDIA"
        bg = LIGHT if india else None
        sr, mr = R_SUM0 + i, R_MS0 + i
        put(ws, r, 1, city, bold=True, bg=bg)
        lk_h = (sum(sum(LK_WEEKLY[c]["ld_wk"][1:N_WEEKS + 1]) + sum(LK_WEEKLY[c]["own_wk"][1:N_WEEKS + 1]) for c in CITIES)
                if india else sum(LK_WEEKLY[city]["ld_wk"][1:N_WEEKS + 1]) + sum(LK_WEEKLY[city]["own_wk"][1:N_WEEKS + 1]))
        bk0, bk1 = f"(Inputs!$F${mr}+Inputs!$J${mr})", f"(Inputs!$I${mr}+Inputs!$M${mr})"   # Lakshya book 27 Sep, 27 Dec
        if india:
            k_ = f"=SUM(K{R_G_H + 1}:K{r - 1})"          # 1 pt lower in every city
            l_ = f"=AVERAGE(L{R_G_H + 1}:L{r - 1})"      # 10 more hires a week for India as a whole
        else:
            sh_ = q(city)
            rg = lambda c_: f"{sh_}!${c_}${FIRST}:${c_}${LAST}"
            k_ = f"=0.01*SUMPRODUCT(({rg('AH')}+{rg('AP')})*{rg('AC')}/7*{rg('CC')})"
            l_ = f"=10*SUMPRODUCT({rg('AC')}/7*{rg('CC')})"
        vals = [
            (2, f"=Inputs!$C${sr}", NUM), (3, f"=Inputs!$D${sr}", NUM), (4, f"=Inputs!$E${sr}", DIFF_FMT),
            (5, f"=ROUND(Inputs!$B${sr}-Inputs!$N${mr},0)", DIFF_FMT), (6, f"=ROUND(Inputs!$I${sr}-Inputs!$E${mr},0)", DIFF_FMT),
            (7, f"=ROUND(Inputs!$Q${sr}-{lk_h},0)", DIFF_FMT), (8, f"=D{r}-E{r}-F{r}-G{r}", DIFF_FMT),
            (9, f"=Inputs!${L(RR['u_rate'])}${R_RR0 + i}", PCT),
            (10, f"=({lk_h}-({bk1}-{bk0}))/{N_WEEKS}/AVERAGE({bk0},{bk1})", PCT),
            (11, k_, NUM), (12, l_, NUM),
            (13, f"=IF(D{r}>=0,0,-D{r}/K{r})", "0.0"), (14, f"=IF(D{r}>=0,0,-D{r}/L{r}*10)", NUM),
        ]
        for j, v, fmt in vals:
            put(ws, r, j, v, fmt, bold=(j in (4, 13, 14)), bg=bg)
    r_end = R_G_H + 1 + len(CITIES)
    for c_ in ("D", "E", "F", "G", "H"):
        ws.conditional_formatting.add(f"{c_}{R_G_H + 1}:{c_}{r_end}", FormulaRule(formula=[f"{c_}{R_G_H + 1}<-0.5"], font=RED_FONT))
    notes3 = [
        "Plan - Lakshya = start + EIP + hiring + drivers leaving. Start: the actual on 26 Sep vs Lakshya's 27 Sep book. EIP: the plan holds "
        "EIP flat (Inputs A3); Lakshya grows it (Inputs A4). Hiring: the plan's 13 weeks vs Lakshya's weekly driver acquisition. "
        "Drivers leaving: the rest - the plan's attrition (last 8 weeks) is above Lakshya's.",
        "What closes it: each lever alone, on 27 Dec. Attrition: one point lower every week (e.g. 10.9% -> 9.9%). Hires: 10 more drivers "
        "every week from w/c 28 Sep. Growing EIP as Lakshya does would also close the EIP column.",
    ]
    for k, t in enumerate(notes3):
        c = ws.cell(r_end + 2 + k, 1, t)
        c.font = F_NOTE
    ws.freeze_panes = "B4"
    ws.sheet_view.zoomScale = 90
    return ws


# ---------------------------------------------------------------- Combined All
# Same columns (and letters) as the Weekly Supply Plan's "Combined All" for A:Z and AH:AI, so its
# Summary View formulas read the same way. Wagon R / S-Presso util and realisation are not in the
# Lakshya plan; the Lakshya layers take AA:AG instead.
COMBINED = [  # (header, logical city-tab column or special)
    ("City", "A"), ("Fuel Type", "B"), ("Month", "C"), ("Week", "D"), ("Total Cars [week ending]", "E"),
    ("nULP", "F"), ("Week-beginning cars on Road", "G"), ("Week beginning active partners", "H"),
    ("Net Allocations", "I"), ("Total Allocations", "J"), ("Channel Sourcing", "K"),
    ("Field Sales Executive", "L"), ("Vendor", "M"), ("Referrals", "N"), ("Performance marketing", "O"),
    ("EIP Net add-on", "P"), ("seasonality", "Q"), ("EIP cars", "R"), ("Rejoin %", None),
    ("Attrition + Temp Attrition", None), ("Net Attrition %", "V"),
    ("Leasing + DTO cars on Road - WE", "W"), ("Week-ending cars on Road", "Y"), ("Week ending Util", "Z"),
    ("Net Attrition (Abs)", "U"), ("Own Now cars on Road - WE", "X"),
    ("Total buy (new cars)", "AD"), ("Total sold", "AE"), ("Util ceiling (Lakshya)", "AA"),
    ("Own Now driver acquisition", "AM"), ("L+DTO driver acquisition", "AT"), ("Total driver acquisition (Own Now + L+DTO)", "AU"),
    ("Actual / Plan", "TYPE"), ("Net Attrition", "NETATTR"), ("WE Active Pilots", "PILOTS"),
]
CB_ROWS = LAST - 1  # rows per city (actual + plan weeks)
# City-tab columns that are empty in the Lakshya plan but kept so the Combined All letters match
_CB_EMPTY = {"Rejoin %": "S", "Attrition + Temp Attrition": "T"}


def combined_query():
    """One QUERY that stacks every city tab's weekly rows (actual + plan)."""
    stack = ";".join(f"{q(c)}!A2:AU{LAST}" for c in CITIES)
    cols = []
    for h, col in COMBINED:
        if col in ("TYPE", "NETATTR", "PILOTS"):
            continue
        col = col or _CB_EMPTY[h]
        cols.append(f"Col{column_index_from_string(newcol(col))}")
    return f'=QUERY({{{stack}}},"select {",".join(cols)} where Col2 is not null",0)'


# ---------------------------------------------------------------- Lakshya vs Plan vs LY (attrition, recruitment, util)
CMP_TAB = "Lakshya vs Plan vs LY"


def build_cmp(wb):
    """Attrition %, driver recruitment and util: Lakshya vs plan vs the same week last year vs the last 8 weeks' average."""
    ws = wb.create_sheet(CMP_TAB, 4)
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = TEAL
    ws.column_dimensions["A"].width = 22
    for j in range(2, 16):
        ws.column_dimensions[get_column_letter(j)].width = 11
    L = get_column_letter
    n = len(CITIES)
    PICK, CF = "$B$3", "$E$3"
    city_list = f"Inputs!$A${R_SUM0}:$A${R_SUM0 + n - 1}"
    ATT, RATE, UT = "0.0%", "0.0%", "0.0%"
    NW = N_WEEKS + 1                                   # w/c 21 Sep (actual) + the 13 plan weeks

    def pick(exprs, india):
        return f'=IF({PICK}="India",{india},CHOOSE(MATCH({PICK},{city_list},0),{",".join(exprs)}))'

    def rs(field, crit_col, crit, city=CF):
        c = rc(field)
        return (f'SUMIFS(raw_performance!${c}:${c},raw_performance!$D:$D,{city},raw_performance!$E:$E,"CNG",'
                f'raw_performance!${crit_col}:${crit_col},{crit})')

    def na(crit_col, crit, city=CF):
        return (f"({rs('attrition_cnt', crit_col, crit, city)}+{rs('temp_attrition_cnt', crit_col, crit, city)}"
                f"-{rs('rejoin_cnt', crit_col, crit, city)}-{rs('temp_rejoin_cnt', crit_col, crit, city)})")

    def rec(crit_col, crit, city=CF):
        return f"({rs('newjoin_cnt', crit_col, crit, city)}+{rs('resurrection_cnt', crit_col, crit, city)})"

    # Lakshya v4 week by week (lakshya_cmp.py, from the v2 sheet); India = sum of the cities
    lk = {c: LK_CMP[c] for c in CITIES}
    lk["INDIA"] = {k: [sum(LK_CMP[c][k][w] for c in CITIES) for w in range(NW)] for k in LK_CMP[CITIES[0]]}
    lk_att = {c: [v["leave"][w] / v["book"][w] for w in range(NW)] for c, v in lk.items()}
    lk_ut = {c: [v["onroad"][w] / v["fleet"][w] for w in range(NW)] for c, v in lk.items()}

    ws["A1"] = "LAKSHYA vs PLAN vs LAST YEAR vs LAST 8 WEEKS  -  attrition, driver recruitment, util"
    ws["A1"].font = F_TITLE
    ws["A2"] = ("Attrition % = drivers leaving in the week (attrition + temp - rejoins) / drivers at the start of the week, the same way "
                "for all four. Recruitment = new joins + resurrections a week. Util = cars on road / total cars at week end.")
    ws["A2"].font = F_NOTE
    ws["A3"] = "Show (pick):"
    ws["A3"].font = F_BOLD
    c = ws["B3"]
    c.value = "India"
    c.font = Font(name="Calibri", size=11, bold=True, color=BLUE_TXT)
    c.fill = fill(INPUT)
    c.border = BOX
    dv = DataValidation(type="list", formula1='"' + ",".join(["India"] + CITIES) + '"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add("B3")
    ws["D3"] = "City filter:"
    ws["D3"].font = F_NOTE
    ws["E3"] = f'=IF({PICK}="India","*",{PICK})'
    ws["E3"].font = F_NOTE

    # ---- 3 first (the other sections read its averages): the last 8 weeks, actual, by city
    R8_T = 7 + NW + 6 + len(CITIES) + 1 + 6          # below sections 1 and 2
    blocks = [("att", "ATTRITION % a week", ATT), ("rec", "DRIVER RECRUITMENT a week", NUM), ("ut", "UTIL % (week end)", UT)]
    avg8 = {}
    put(ws, R8_T, 1, "3.  THE LAST 8 WEEKS, ACTUAL  -  where the 'last 8 weeks' columns come from (w/c 21 Sep: days loaded, scaled to a week)",
        font=F_SECTION).border = Border()
    cols8 = CITIES + ["INDIA"]
    r = R8_T + 2
    for key, label, fmt in blocks:
        hdr(ws, r, 1, label, GREY_HDR)
        for j, c_ in enumerate(cols8, start=2):
            hdr(ws, r, j, c_)
        for k in range(8):
            rr_ = r + 1 + k
            put(ws, rr_, 1, f"={G_OPEN_DATE}-55+{7 * k}", 'dd" "mmm', bold=True)
            d = f"$A{rr_}"
            scale = f"7/MIN(7,{G_LAST}-{d}+1)"
            for j, c_ in enumerate(cols8, start=2):
                city = '"*"' if c_ == "INDIA" else f'"{c_}"'
                if key == "att":
                    v = f"=IFERROR({na('B', d, city)}*{scale}/{rs('uniq_partners_dt_beginning', 'C', d, city)},\"\")"
                elif key == "rec":
                    v = f"={rec('B', d, city)}*{scale}"
                else:
                    day = f"MIN({d}+6,{G_LAST})"
                    v = (f"=IFERROR({rs('allotted_cars_eod', 'C', day, city)}/{rs('fleet_total_cars_cnt', 'C', day, city)},\"\")")
                put(ws, rr_, j, v, fmt, bg=LIGHT if c_ == "INDIA" else None)
        ra = r + 9
        put(ws, ra, 1, "Average", bold=True, bg=LIGHT)
        for j, c_ in enumerate(cols8, start=2):
            put(ws, ra, j, f"=AVERAGE({L(j)}{r + 1}:{L(j)}{r + 8})", fmt, bold=True, bg=LIGHT)
        avg8[key] = (r, ra)                          # header row, average row
        r = ra + 3
    note(ws, r - 2, "A week's attrition = drivers leaving that week / drivers at its Monday start. Util on the week's Sunday "
                    "(Sat 26 Sep for w/c 21 Sep). INDIA = the seven cities.")

    def a8(key, city_cell):                          # the 8-week average for a city name (or India)
        h, ra = avg8[key]
        return f"INDEX($B${ra}:${L(1 + len(cols8))}${ra},MATCH({city_cell},$B${h}:${L(1 + len(cols8))}${h},0))"

    # ---- 1. week by week, for the pick
    R1_T = 5
    put(ws, R1_T, 1, f'="1.  WEEK BY WEEK  -  "&UPPER({PICK})', font=F_SECTION).border = Border()
    groups = [("ATTRITION % a week", 2), ("DRIVER RECRUITMENT a week", 6), ("UTIL % (week end)", 10)]
    heads = ["Lakshya", "Plan", "Last year (same week)", "Last 8 weeks avg"]
    hdr(ws, R1_T + 1, 1, "", GREY_HDR)
    hdr(ws, R1_T + 2, 1, "Week (w/c)")
    for t, c0 in groups:
        hdr(ws, R1_T + 1, c0, t, GREY_HDR)
        ws.merge_cells(start_row=R1_T + 1, start_column=c0, end_row=R1_T + 1, end_column=c0 + 3)
        for k, h in enumerate(heads):
            hdr(ws, R1_T + 2, c0 + k, h)
    ws.row_dimensions[R1_T + 2].height = 30
    sheets_ = [q(c) for c in CITIES]
    for w in range(NW):
        r = R1_T + 3 + w
        cr = OPEN_ROW + w                            # city-tab row: w/c 21 Sep = the actual opening week
        d = f"$A{r}"
        ly = f"({d}-364)"
        if w == 0:
            put(ws, r, 1, f"={G_OPEN_DATE}-6", 'dd" "mmm" (actual)"', bold=True, bg=ACTUAL)
        else:
            put(ws, r, 1, f"=Inputs!$B${R_CAL0 + w - 1}", 'dd" "mmm', bold=True)
        # Lakshya
        put(ws, r, 2, pick([str(round(lk_att[c][w], 5)) for c in CITIES], str(round(lk_att["INDIA"][w], 5))), ATT)
        put(ws, r, 6, pick([str(round(lk[c]["rec"][w], 1)) for c in CITIES], str(round(lk["INDIA"]["rec"][w], 1))), NUM)
        put(ws, r, 10, pick([str(round(lk_ut[c][w], 5)) for c in CITIES], str(round(lk_ut["INDIA"][w], 5))), UT)
        # Plan (w/c 21 Sep = the actual, from raw_performance, scaled to a week)
        if w == 0:
            scale = f"7/MIN(7,{G_LAST}-{d}+1)"
            put(ws, r, 3, f"=IFERROR({na('B', d)}*{scale}/{rs('uniq_partners_dt_beginning', 'C', d)},\"\")", ATT, bg=ACTUAL)
            put(ws, r, 7, f"={rec('B', d)}*{scale}", NUM, bg=ACTUAL)
            put(ws, r, 11, f"=IFERROR({rs('allotted_cars_eod', 'C', G_LAST)}/{rs('fleet_total_cars_cnt', 'C', G_LAST)},\"\")", UT, bg=ACTUAL)
        else:
            put(ws, r, 3, pick([f"{s_}!AQ{cr}/({s_}!AH{cr}+{s_}!AP{cr})" for s_ in sheets_],
                               "(" + "+".join(f"{s_}!AQ{cr}" for s_ in sheets_) + ")/("
                               + "+".join(f"{s_}!AH{cr}+{s_}!AP{cr}" for s_ in sheets_) + ")"), ATT, bold=True)
            put(ws, r, 7, pick([f"{s_}!AU{cr}" for s_ in sheets_], "+".join(f"{s_}!AU{cr}" for s_ in sheets_)), NUM, bold=True)
            put(ws, r, 11, pick([f"{s_}!Y{cr}/{s_}!E{cr}" for s_ in sheets_],
                                "(" + "+".join(f"{s_}!Y{cr}" for s_ in sheets_) + ")/(" + "+".join(f"{s_}!E{cr}" for s_ in sheets_) + ")"),
                UT, bold=True)
        # last year, same week
        put(ws, r, 4, f"=IFERROR({na('B', ly)}/{rs('uniq_partners_dt_beginning', 'C', ly)},\"\")", ATT, font=F_HIST, bg=HIST)
        put(ws, r, 8, f"={rec('B', ly)}", NUM, font=F_HIST, bg=HIST)
        put(ws, r, 12, f"=IFERROR({rs('allotted_cars_eod', 'C', f'{ly}+6')}/{rs('fleet_total_cars_cnt', 'C', f'{ly}+6')},\"\")", UT,
            font=F_HIST, bg=HIST)
        # last 8 weeks (section 3)
        for c0, key, fmt in ((5, "att", ATT), (9, "rec", NUM), (13, "ut", UT)):
            put(ws, r, c0, f"={a8(key, PICK)}", fmt)
    r = R1_T + 3 + NW
    put(ws, r, 1, "Average 28 Sep - 21 Dec", bold=True, bg=LIGHT)
    for j in range(2, 14):
        fmt = NUM if 6 <= j <= 9 else ATT
        put(ws, r, j, f"=AVERAGE({L(j)}{R1_T + 4}:{L(j)}{r - 1})", fmt, bold=True, bg=LIGHT)
    for c0 in (2, 6, 10):
        ws.conditional_formatting.add(f"{L(c0 + 1)}{R1_T + 3}:{L(c0 + 1)}{r}",
                                      FormulaRule(formula=[f"ABS({L(c0 + 1)}{R1_T + 3}-{L(c0)}{R1_T + 3})>0.1*{L(c0)}{R1_T + 3}"],
                                                  font=RED_FONT))
    note(ws, r + 1, "Plan = the city tabs (Inputs A1: the plan in use). Lakshya = Lakshya v4 week by week as the v2 sheet runs it. "
                    "Last year = the same week 364 days earlier. Red = plan more than 10% away from Lakshya.")

    # ---- 2. by city
    R2_T = r + 4
    put(ws, R2_T, 1, "2.  BY CITY  -  attrition and recruitment: average of the 13 plan weeks; util: w/c 21 Dec (27 Dec)",
        font=F_SECTION).border = Border()
    hdr(ws, R2_T + 1, 1, "", GREY_HDR)
    hdr(ws, R2_T + 2, 1, "City")
    for t, c0 in groups:
        hdr(ws, R2_T + 1, c0, t, GREY_HDR)
        ws.merge_cells(start_row=R2_T + 1, start_column=c0, end_row=R2_T + 1, end_column=c0 + 3)
        for k, h in enumerate(heads):
            hdr(ws, R2_T + 2, c0 + k, h.replace(" (same week)", " (same weeks)"))
    ws.row_dimensions[R2_T + 2].height = 30
    ly0, ly1 = f"({G_OPEN_DATE}+1-364)", f"({G_PLAN_END}-364)"
    rng = lambda s_, c_: f"{s_}!{c_}{FIRST}:{c_}{LAST}"
    for i, c_ in enumerate(cols8):
        r = R2_T + 3 + i
        india = c_ == "INDIA"
        bg = LIGHT if india else None
        put(ws, r, 1, c_, bold=True, bg=bg)
        v = lk[c_]
        put(ws, r, 2, sum(v["leave"][1:]) / sum(v["book"][1:]), ATT, bg=bg)
        put(ws, r, 6, sum(v["rec"][1:]) / N_WEEKS, NUM, bg=bg)
        put(ws, r, 10, v["onroad"][N_WEEKS] / v["fleet"][N_WEEKS], UT, bg=bg)
        ss = sheets_ if india else [q(c_)]
        put(ws, r, 3, "=(" + "+".join(f"SUM({rng(s_, 'AQ')})" for s_ in ss) + ")/("
            + "+".join(f"SUM({rng(s_, 'AH')})+SUM({rng(s_, 'AP')})" for s_ in ss) + ")", ATT, bold=True, bg=bg)
        put(ws, r, 7, "=(" + "+".join(f"SUM({rng(s_, 'AU')})" for s_ in ss) + f")/{N_WEEKS}", NUM, bold=True, bg=bg)
        put(ws, r, 11, "=(" + "+".join(f"{s_}!Y{LAST}" for s_ in ss) + ")/(" + "+".join(f"{s_}!E{LAST}" for s_ in ss) + ")",
            UT, bold=True, bg=bg)
        city = '"*"' if india else f'"{c_}"'
        dates = f'raw_performance!$C:$C,">="&{ly0},raw_performance!$C:$C,"<="&{ly1}'
        def rsr(field):
            cc = rc(field)
            return (f'SUMIFS(raw_performance!${cc}:${cc},raw_performance!$D:$D,{city},raw_performance!$E:$E,"CNG",{dates})')
        mondays = "+".join(f"{rs('uniq_partners_dt_beginning', 'C', f'{ly0}+{7 * k}', city)}" for k in range(N_WEEKS))
        put(ws, r, 4, f"=IFERROR(({rsr('attrition_cnt')}+{rsr('temp_attrition_cnt')}-{rsr('rejoin_cnt')}-{rsr('temp_rejoin_cnt')})/({mondays}),\"\")",
            ATT, font=F_HIST, bg=HIST)
        put(ws, r, 8, f"=({rsr('newjoin_cnt')}+{rsr('resurrection_cnt')})/{N_WEEKS}", NUM, font=F_HIST, bg=HIST)
        put(ws, r, 12, f"=IFERROR({rs('allotted_cars_eod', 'C', ly1, city)}/{rs('fleet_total_cars_cnt', 'C', ly1, city)},\"\")", UT,
            font=F_HIST, bg=HIST)
        for c0, key, fmt in ((5, "att", ATT), (9, "rec", NUM), (13, "ut", UT)):
            put(ws, r, c0, f'={a8(key, f"$A{r}")}', fmt, bg=bg)
    r_end = R2_T + 3 + n
    for c0 in (2, 6, 10):
        ws.conditional_formatting.add(f"{L(c0 + 1)}{R2_T + 3}:{L(c0 + 1)}{r_end}",
                                      FormulaRule(formula=[f"ABS({L(c0 + 1)}{R2_T + 3}-{L(c0)}{R2_T + 3})>0.1*{L(c0)}{R2_T + 3}"],
                                                  font=RED_FONT))
    assert r_end + 3 < R8_T, "section 3 overlaps section 2"
    ws.freeze_panes = "B4"
    ws.sheet_view.zoomScale = 90
    return ws


def build_combined(wb):
    ws = wb.create_sheet("Combined All")
    for j, (h, _) in enumerate(COMBINED, start=1):
        hdr(ws, 1, j, h)
        ws.column_dimensions[get_column_letter(j)].width = 22 if h == "seasonality" else 10
    ws.row_dimensions[1].height = 54
    # Everything below the header comes from two kinds of formula: one QUERY (A:AF) that stacks the
    # city tabs, and three array formulas (AG:AI). No cell-by-cell links.
    ws["A2"] = combined_query()
    n = len(COMBINED)
    type_col, net_col, pil_col = (get_column_letter(n - 2), get_column_letter(n - 1), get_column_letter(n))
    # Written as array formulas; Google Sheets opens them as ARRAYFORMULA over rows 2-1000.
    A = "A2:A1000"

    def rng(name):
        L = cb(name)
        return f"{L}2:{L}1000"

    ws[f"{type_col}2"] = ArrayFormula(f"{type_col}2:{type_col}1000",
                                      f'=IF({A}="","",IF(D2:D1000<={G_OPEN_DATE}-6,"Actual","Plan"))')
    ws[f"{net_col}2"] = ArrayFormula(f"{net_col}2:{net_col}1000",
                                     f'=IF({A}="","",{rng("Net Attrition (Abs)")})')
    ws[f"{pil_col}2"] = ArrayFormula(f"{pil_col}2:{pil_col}1000",
                                     f'=IF({A}="","",{rng("Week beginning active partners")}+{rng("Channel Sourcing")})')
    rows = CB_ROWS * len(CITIES) + 1
    for j, (h, col) in enumerate(COMBINED, start=1):
        fmt = NUM
        if col in ("C", "D"):
            fmt = DATE
        elif col in ("V", "Z", "AA"):
            fmt = PCT
        elif col in ("A", "B", "Q", "TYPE"):
            fmt = None
        for r in range(2, rows + 1):
            c = ws.cell(r, j)
            c.font = F_BODY
            if fmt:
                c.number_format = fmt
    ws.conditional_formatting.add(f"A2:{get_column_letter(n)}{rows}",
                                  FormulaRule(formula=[f'${type_col}2="Actual"'], fill=fill(ACTUAL)))
    ws.freeze_panes = "E2"
    ws.sheet_view.zoomScale = 90


def cb(name):
    """Column letter of a Combined All header."""
    return get_column_letter([h for h, _ in COMBINED].index(name) + 1)


# ---------------------------------------------------------------- Summary View
SV_WEEKS = N_ACTUAL + N_WEEKS   # 18 columns: 4 actual + 14 plan weeks
SV_FIRST_BLOCK = 8


def build_summary(wb):
    ws = wb.create_sheet("Summary View", 1)
    last_col = get_column_letter(1 + SV_WEEKS)
    ws.column_dimensions["A"].width = 30
    for j in range(2, 2 + SV_WEEKS):
        ws.column_dimensions[get_column_letter(j)].width = 9

    ws["A1"] = "City"
    ws["A1"].font = F_BOLD
    c = ws["B1"]
    c.value = "India"
    c.font = Font(name="Calibri", size=11, bold=True, color=BLUE_TXT)
    c.fill = fill(INPUT)
    ws["A2"] = "Fuel Type"
    ws["A2"].font = F_BOLD
    c = ws["B2"]
    c.value = "CNG"
    c.font = Font(name="Calibri", size=11, bold=True, color=BLUE_TXT)
    c.fill = fill(INPUT)
    dv = DataValidation(type="list", formula1='"' + ",".join(["India"] + CITIES) + '"', allow_blank=False)
    dv2 = DataValidation(type="list", formula1='"CNG"', allow_blank=False)
    ws.add_data_validation(dv)
    ws.add_data_validation(dv2)
    dv.add("B1")
    dv2.add("B2")
    ws["D1"] = "Pick a city (or India) in B1. Plan = this workbook; actual and last year = raw_performance."
    ws["D1"].font = F_NOTE
    ws["D2"] = "City filter:"
    ws["D2"].font = F_NOTE
    ws["E2"] = '=IF($B$1="India","*",$B$1)'
    ws["E2"].font = F_NOTE
    ws["G2"] = "Raw data up to:"
    ws["G2"].font = F_NOTE
    ws["I2"] = "=MAX(raw_performance!$C:$C)"
    ws["I2"].number_format = "dd-mmm-yy"
    ws["I2"].font = F_NOTE
    CITY = "$E$2"
    FUEL = "$B$2"
    RAWMAX = "$I$2"

    ws["A3"] = "Week"
    ws["A3"].font = F_BOLD
    ws["A4"] = "2026"
    ws["A5"] = "2025 (same week LY)"
    ws["A6"] = ""
    for k in range(SV_WEEKS):
        col = get_column_letter(2 + k)
        c = ws[f"{col}3"]
        c.value = f'=IF({col}4<={G_OPEN_DATE}-6,"Actual","Plan")'
        c.font = F_BOLD
        c.alignment = CENTER
        c = ws[f"{col}4"]
        c.value = f"={G_OPEN_DATE}-{7 * N_ACTUAL - 1}" if k == 0 else f"={get_column_letter(1 + k)}4+7"
        c.number_format = "mmm-dd"
        c.font = F_BOLD
        c = ws[f"{col}5"]
        c.value = f"={col}4-364"
        c.number_format = "mmm-dd"
        c.font = F_BOLD
        c = ws[f"{col}6"]
        c.value = f'=IF(AND(TODAY()>={col}4,TODAY()<{col}4+7),"We are here","")'
        c.font = F_BOLD
        c.alignment = CENTER
    ws.conditional_formatting.add(f"B6:{last_col}6", FormulaRule(formula=['B6="We are here"'], fill=fill("FFFFFF00")))
    ws.conditional_formatting.add(f"B3:{last_col}3", FormulaRule(formula=['B3="Actual"'], fill=fill(ACTUAL)))

    CA = "'Combined All'"

    def ca(col, wk):
        return (f"SUMIFS({CA}!${col}:${col},{CA}!$A:$A,{CITY},{CA}!$B:$B,{FUEL},{CA}!$D:$D,{wk})")

    def raw_day(field, wk):   # on the week's last day (Sunday)
        L = rc(field)
        return (f"SUMIFS(raw_performance!${L}:${L},raw_performance!$D:$D,{CITY},raw_performance!$E:$E,{FUEL},"
                f"raw_performance!$C:$C,{wk}+6)")

    def raw_mon(field, wk):   # on the week's Monday
        L = rc(field)
        return (f"SUMIFS(raw_performance!${L}:${L},raw_performance!$D:$D,{CITY},raw_performance!$E:$E,{FUEL},"
                f"raw_performance!$C:$C,{wk})")

    def raw_wk(field, wk):    # sum over the week
        L = rc(field)
        return (f"SUMIFS(raw_performance!${L}:${L},raw_performance!$D:$D,{CITY},raw_performance!$E:$E,{FUEL},"
                f"raw_performance!$B:$B,{wk})")

    def raw_attr_pct(wk):
        abs_ = (raw_wk("attrition_cnt", wk) + "+" + raw_wk("temp_attrition_cnt", wk) + "-"
                + raw_wk("rejoin_cnt", wk) + "-" + raw_wk("temp_rejoin_cnt", wk))
        base = raw_mon("uniq_partners_dt_beginning", wk) + "+" + raw_wk("newjoin_cnt", wk) + "+" + raw_wk("resurrection_cnt", wk)
        return f"IFERROR(({abs_})/({base}),\"\")"

    # (title, plan formula(wk), raw formula(wk) or None, number format)
    blocks = [
        ("Util", lambda w: f"IFERROR({ca(cb('Week-ending cars on Road'), w)}/{ca(cb('Total Cars [week ending]'), w)},\"\")",
         lambda w: f"IFERROR({raw_day('allotted_cars_eod', w)}/{raw_day('fleet_total_cars_cnt', w)},\"\")", "0%"),
        ("On Road Cars", lambda w: ca(cb("Week-ending cars on Road"), w), lambda w: raw_day("allotted_cars_eod", w), "#,##0"),
        ("On road growth % (week on week)",
         lambda w: f"IFERROR({ca(cb('Week-ending cars on Road'), w)}/{ca(cb('Week-ending cars on Road'), w + '-7')}-1,\"\")",
         lambda w: f"IFERROR({raw_day('allotted_cars_eod', w)}/{raw_day('allotted_cars_eod', w + '-7')}-1,\"\")", "0.0%"),
        ("Recruitment", lambda w: ca(cb("Channel Sourcing"), w),
         lambda w: raw_wk("newjoin_cnt", w) + "+" + raw_wk("resurrection_cnt", w), "#,##0"),
        ("Net Attrition %", lambda w: f"IFERROR(-{ca(cb('Net Attrition'), w)}/{ca(cb('WE Active Pilots'), w)},\"\")",
         raw_attr_pct, "0.0%"),
        ("EIP Growth", lambda w: ca(cb("EIP Net add-on"), w), lambda w: raw_wk("Net EIP Add-ons", w), "#,##0"),
        ("Field Sales Executive", lambda w: ca(cb("Field Sales Executive"), w),
         lambda w: raw_wk("ni_fse_cnt", w) + "+" + raw_wk("resurrection_fse_cnt", w), "#,##0"),
        ("Vendor", lambda w: ca(cb("Vendor"), w),
         lambda w: raw_wk("ni_vendor_cnt", w) + "+" + raw_wk("resurrection_vendor_cnt", w), "#,##0"),
        ("Referrals", lambda w: ca(cb("Referrals"), w),
         lambda w: raw_wk("ni_driver_referral_cnt", w) + "+" + raw_wk("resurrection_driver_referral_cnt", w), "#,##0"),
        ("Performance marketing", lambda w: ca(cb("Performance marketing"), w),
         lambda w: raw_wk("ni_perf_mktg_cnt", w) + "+" + raw_wk("resurrection_perf_mktg_cnt", w), "#,##0"),
        ("EIP %", lambda w: f"IFERROR({ca(cb('EIP cars'), w)}/{ca(cb('Week-ending cars on Road'), w)},\"\")",
         lambda w: f"IFERROR({raw_day('eip_vehicles_cnt', w)}/{raw_day('allotted_cars_eod', w)},\"\")", "0%"),
        ("Total car", lambda w: ca(cb("Total Cars [week ending]"), w), lambda w: raw_day("fleet_total_cars_cnt", w), "#,##0"),
        ("Total buy", lambda w: ca(cb("Total buy (new cars)"), w), None, "#,##0"),
        ("Total Sold", lambda w: ca(cb("Total sold"), w), None, "#,##0"),
        ("On Road Cars EIP", lambda w: ca(cb("EIP cars"), w), lambda w: raw_day("eip_vehicles_cnt", w), "#,##0"),
        ("On Road Cars Own Now", lambda w: ca(cb("Own Now cars on Road - WE"), w), lambda w: raw_day("own_now_cars_eod", w), "#,##0"),
        ("On Road Cars Leasing + DTO", lambda w: ca(cb("Leasing + DTO cars on Road - WE"), w),
         lambda w: raw_day("allotted_cars_eod", w) + "-" + raw_day("own_now_cars_eod", w) + "-" + raw_day("eip_vehicles_cnt", w), "#,##0"),
        ("Driver Acquisition (Own Now + L+DTO)", lambda w: ca(cb("Total driver acquisition (Own Now + L+DTO)"), w), None, "#,##0"),
    ]
    r = SV_FIRST_BLOCK
    for title, plan_f, raw_f, fmt in blocks:
        ws.cell(r, 1, title).font = F_HDR
        ws.cell(r, 1).fill = fill(NAVY)
        labels = ["2026 plan", "2026 actual", "2025 actual (same week LY)"]
        for k in range(SV_WEEKS):
            col = get_column_letter(2 + k)
            h = ws[f"{col}{r}"]
            h.value = f"={col}$4"
            h.number_format = 'dd" "mmm'
            h.font = F_HDR
            h.fill = fill(NAVY)
            h.alignment = CENTER
            wk, ly = f"{col}$4", f"{col}$5"
            vals = [
                "=" + plan_f(wk),
                (f'=IF({wk}+6<={RAWMAX},{raw_f(wk)},"")' if raw_f else None),
                (f'=IF({ly}+6<={RAWMAX},{raw_f(ly)},"")' if raw_f else None),
            ]
            for i, v in enumerate(vals):
                c = ws.cell(r + 1 + i, 2 + k, v)
                c.number_format = fmt
                c.font = F_BOLD if i == 0 else F_BODY
                c.border = BOX
        for i, lab in enumerate(labels):
            c = ws.cell(r + 1 + i, 1, lab if (raw_f or i == 0) else lab + " - n/a")
            c.font = F_BOLD if i == 0 else F_BODY
            c.border = BOX
        if title == "Recruitment":   # FLAG row (the block's blank row): drivers for Lakshya cars not bought yet
            c = ws.cell(r + 4, 1, "FLAG: of which for cars not bought yet")
            c.font = Font(name="Calibri", size=10, bold=True, color="FFC00000")
            fut_row = (f'MATCH(IF($B$1="India","INDIA",$B$1),Inputs!$A${R_FUT0}:$A${R_FUT0 + len(CITIES)},0)')
            wim = {m: WEEK_MONTH.count(m) for m in PLAN_MONTHS}
            for k in range(SV_WEEKS):
                pw = k - N_ACTUAL + 1          # plan week (1 = current week); drivers follow cars landing a week earlier
                if pw < 2:
                    continue
                m = PLAN_MONTHS.index(WEEK_MONTH[pw - 2])
                c = ws.cell(r + 4, 2 + k, f"=IFERROR(INDEX(Inputs!${get_column_letter(2 + m)}${R_FUT0}:${get_column_letter(2 + m)}${R_FUT0 + len(CITIES)},"
                                          f"{fut_row})/{wim[WEEK_MONTH[pw - 2]]},0)")
                c.number_format = '#,##0;-#,##0;""'
                c.font = Font(name="Calibri", size=10, bold=True, color="FFC00000")
        if title in ("Util", "Recruitment", "Net Attrition %"):
            for i in range(2):
                ws.conditional_formatting.add(
                    f"B{r + 1 + i * 2}:{last_col}{r + 1 + i * 2}",
                    ColorScaleRule(start_type="min", start_color="FFE67C73", mid_type="percentile", mid_value=50,
                                   mid_color="FFFFFFFF", end_type="max", end_color="FF57BB8A"))
        r += 5
    ws.cell(r, 1, "Plan row = Combined All (4 actual weeks, then the plan). Actual row fills in once raw_performance "
                  "covers the whole week - paste a fresh SSOT query into raw_performance to track plan vs actual. "
                  "Last year = same week 364 days earlier.").font = F_NOTE
    ws.freeze_panes = "B7"
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
    build_season(wb)
    if V2:
        build_lk_weekly(wb)
    for i, city in enumerate(CITIES):
        build_city(wb, i, city)
    build_summary(wb)
    build_dashboard(wb)
    build_bridge(wb)
    build_cmp(wb)
    build_combined(wb)
    build_readme(wb)
    build_raw(wb, raw)
    order = ["Read Me", "Summary View", DASH, BRIDGE_TAB, CMP_TAB, "Inputs", SEAS_TAB, LW_TAB] + CITIES + ["Combined All", "raw_performance"]
    wb._sheets.sort(key=lambda ws: order.index(ws.title))
    wb.active = 0
    wb.save(out)


if __name__ == "__main__":
    V2 = "--v2" in sys.argv[3:]
    main(sys.argv[1], sys.argv[2])
