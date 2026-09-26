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
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.formula import ArrayFormula
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
# Season of each plan week (Diwali: Sun 8 Nov 2026)
SEASONS = ["Pre-Diwali", "Diwali", "Post-Diwali"]
WEEK_SEASON = ["Pre-Diwali"] * 6 + ["Diwali"] * 2 + ["Post-Diwali"] * 6
# Proven weekly pace: best 4-week average weekly growth in cars on road (allotted_cars_eod, Sunday to
# Sunday) in the same season of 2024 or 2025, whichever is higher, floored at 0. Order: Pre-Diwali,
# Diwali, Post-Diwali. Seasons: 2024 Diwali 1 Nov, 2025 Diwali 20 Oct.
PACE = {
    "Mumbai":    (0.025, 0.0, 0.052),
    "Delhi NCR": (0.0, 0.0, 0.048),
    "Bangalore": (0.026, 0.004, 0.014),
    "Hyderabad": (0.008, 0.010, 0.024),
    "Chennai":   (0.023, 0.047, 0.047),
    "Kolkata":   (0.007, 0.050, 0.049),
    "Pune":      (0.023, 0.012, 0.054),
}
PACE_INDIA = (0.015, 0.0, 0.029)
# Diwali dip: change in cars on road (allotted_cars_eod, Sunday to Sunday) around Diwali.
# Run-up week = the week before the week with Bhai Dooj; Diwali week = the week with Bhai Dooj;
# Recovery = the week after. 2024: w/e 27 Oct, 3 Nov, 10 Nov (Diwali Fri 1 Nov).
# 2025: w/e 19 Oct, 26 Oct, 2 Nov (Diwali Mon 20 Oct). 2026: w/c 2 Nov, 9 Nov, 16 Nov (Diwali Sun 8 Nov).
DIWALI_WEEK = {7: "Run-up week", 8: "Diwali week", 9: "Recovery week"}
DIWALI_CARS = {  # cars on road on the Sundays: (week before run-up, run-up, Diwali, recovery) for 2024, 2025
    "Mumbai":    ((3023, 2910, 2716, 2645), (2517, 2340, 2228, 2211)),
    "Delhi NCR": ((2005, 1917, 1761, 1772), (2197, 2150, 2029, 2038)),
    "Bangalore": ((1745, 1810, 1686, 1741), (2087, 1989, 1930, 1937)),
    "Hyderabad": ((1039, 1071, 1001, 1004), (1463, 1422, 1395, 1409)),
    "Chennai":   ((1143, 1111, 892, 1001), (1409, 1259, 1321, 1422)),
    "Kolkata":   ((516, 543, 533, 545), (513, 503, 473, 498)),
    "Pune":      ((1154, 1128, 998, 1073), (903, 827, 773, 833)),
}
DIWALI_SUNDAYS = (("20 Oct 24", "27 Oct 24", "3 Nov 24", "10 Nov 24"), ("12 Oct 25", "19 Oct 25", "26 Oct 25", "2 Nov 25"))
# Same measure per year, for reference: (2024, 2025) x (Pre, Diwali, Post)
PACE_HIST = {
    "Mumbai":    ((0.025, -0.020, 0.052), (0.009, -0.025, 0.048)),
    "Delhi NCR": ((0.000, -0.012, 0.048), (-0.012, -0.002, 0.040)),
    "Bangalore": ((0.026, 0.004, 0.014), (0.012, -0.018, 0.013)),
    "Hyderabad": ((0.008, 0.007, 0.024), (-0.001, 0.010, 0.022)),
    "Chennai":   ((0.023, -0.018, 0.034), (0.014, 0.047, 0.047)),
    "Kolkata":   ((0.007, 0.050, 0.021), (-0.008, 0.013, 0.049)),
    "Pune":      ((0.023, -0.004, 0.032), (0.001, 0.012, 0.054)),
    "INDIA":     ((0.015, -0.012, 0.029), (-0.001, -0.001, 0.027)),
}
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
# The tab reads top to bottom in three parts:
#   PART A  what you set          A1 dates & switches, A2 city start/targets/rates, A3 month-end targets,
#                                 A4 new cars bought, A5 cars sold, A6 weekly calendar
#   PART B  learnt from last year B1 festival impact
#   PART C  output and sources    C1 plan summary, C2 sources
# Proven pace and the Diwali dip live on their own tab (DIP_TAB).
# Each section is: title row, one "what it does" row, (group header row), header row, data.
_r = 9                     # PART A banner row
R_GLOBAL = _r + 4          # A1 header row; values start next row (7 settings)
R_CITY_H = R_GLOBAL + 7 + 5   # A2 header (group header row above it)
R_CITY0 = R_CITY_H + 1
R_MS_H = R_CITY0 + 8 + 5      # A3 header (group header row above it)
R_MS0 = R_MS_H + 1
R_ADD_H = R_MS0 + 8 + 4       # A4 header
R_ADD0 = R_ADD_H + 1
R_SALE_H = R_ADD0 + 8 + 4     # A5 header
R_SALE0 = R_SALE_H + 1
R_CAL_H = R_SALE0 + 8 + 4     # A6 header
R_CAL0 = R_CAL_H + 1
R_SEAS_H = R_CAL0 + N_WEEKS + 1 + 6   # B1 header (PART B banner above the title)
R_SEAS0 = R_SEAS_H + 1
R_SEAS1 = R_SEAS0 + len(SEASON_REC) - 1
R_SUM_H = R_SEAS1 + 7         # C1 header (PART C banner above the title)
R_SUM0 = R_SUM_H + 1
R_SRC_H = R_SUM0 + 8 + 4      # C2 header

# ---------------------------------------------------------------- Diwali dip / pace tab layout
DIP_TAB = "Diwali_Dip Analysis"
DQ = f"'{DIP_TAB}'"
R_PACE_H = 7                  # 1. proven pace header
R_PACE0 = R_PACE_H + 1
R_DIP_H = R_PACE0 + 8 + 4     # 2. Diwali dip header
R_DIP0 = R_DIP_H + 1
R_DIPC_H = R_DIP0 + 8 + 4     # 3. history table header
R_DIPC0 = R_DIPC_H + 1
MONTHS = ["Sep", "Oct", "Nov", "Dec"]
WEEK_MONTH = ["Sep"] + ["Oct"] * 4 + ["Nov"] * 5 + ["Dec"] * 4   # Lakshya month each plan week rolls up to
MS_WEEKS = (1, 5, 10, 14)  # plan weeks elapsed at each Lakshya month-end (27 Sep, 25 Oct, 29 Nov, 27 Dec)

G_OPEN_DATE = f"Inputs!$B${R_GLOBAL + 1}"
G_PLAN_END = f"Inputs!$B${R_GLOBAL + 3}"
G_WPM = f"Inputs!$B${R_GLOBAL + 4}"
G_FLOOR = f"Inputs!$B${R_GLOBAL + 6}"
G_CAP = f"Inputs!$B${R_GLOBAL + 7}"

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
    ("AF", "Season", 9), ("AG", "EIP net add", 8),
    ("AH", "Own Now book - WB", 8), ("AI", "Own Now need this week (to Lakshya month-end)", 9), ("AJ", "Own Now net add", 8),
    ("AK", "Own Now churn (LY-shaped)", 8), ("AL", "Own Now purchase rollover", 9),
    ("AM", "Own Now driver acquisition", 9), ("AN", "of which new cars", 8),
    ("AO", "of which existing cars", 8),
    ("AP", "L+DTO book - WB", 8), ("AQ", "L+DTO need this week (to Lakshya month-end)", 9), ("AR", "L+DTO net add", 8),
    ("AS", "L+DTO churn (LY-shaped)", 8), ("AT", "L+DTO driver acquisition", 9),
    ("AU", "Total driver acquisition (Own Now + L+DTO)", 10), ("AV", "Check: on road = EIP + L+DTO + Own Now", 9),
    ("AW", "Util headroom", 8), ("AX", "", 2),
    ("AY", "LY week (same week last year)", 9), ("AZ", "LY active partners - WB", 9),
    ("BA", "LY recruitment (new joins + resurrections)", 10), ("BB", "LY net attrition (abs)", 9),
    ("BC", "LY net attrition %", 8), ("BD", "LY attrition index (1 = average week)", 9),
    ("BE", "Festival impact on recruitment", 9), ("BF", "Seasonality factor", 8),
    ("BG", "", 2),
    ("BH", "Proven weekly pace (best 4 weeks, same season 2024/25)", 10),
    ("BI", "Organic capacity (cars on road WB x pace)", 10), ("BJ", "New cars going on road (bought last week)", 10),
    ("BK", "Max achievable add (new cars + organic capacity)", 10),
    ("BL", "Organic add needed (gap after new cars, spread over weeks left)", 11),
    ("BM", "Planned on-road add = new cars + MIN(needed, capacity)", 11), ("BN", "Planned weekly growth %", 8),
    ("BO", "Organic growth %", 8), ("BP", "Organic need within last year's pace?", 10),
    ("BQ", "Gap to Lakshya still open (week end)", 10),
    ("BR", "Diwali dip % (2024/25 avg, Diwali_Dip Analysis tab)", 9), ("BS", "Diwali dip (cars)", 8),
    ("BT", "New cars still to go on road (incl. this week)", 10),
    ("BU", "Lakshya month-end this week counts to", 8), ("BV", "EIP month-end target", 8),
    ("BW", "Own Now month-end target (Lakshya)", 9), ("BX", "L+DTO month-end target (Lakshya)", 9),
    ("BY", "On road month-end target", 9), ("BZ", "Weeks left in the month (weighted)", 8),
    ("CA", "EIP need this week", 8), ("CB", "Needs not covered by the plan (shared out)", 9),
    ("CC", "Positive needs", 8),
]
LY_BLOCK = ("AY", "AZ", "BA", "BB", "BC", "BD", "BE", "BF")
PACE_BLOCK = ("BH", "BI", "BJ", "BK", "BL", "BM", "BN", "BO", "BP", "BQ", "BR", "BS", "BT")
MS_BLOCK = ("BU", "BV", "BW", "BX", "BY", "BZ", "CA", "CB", "CC")
TEAL = "FF1F6F5F"
CAPPED, ABOVE = "Capped at LY pace", "Above LY pace (cap off)"  # BP labels with the pace switch on Yes / No


def stretch_count(bp_range):
    """Weeks whose organic need is above last year's pace: capped (switch Yes) or planned anyway (switch No)."""
    return f'(COUNTIF({bp_range},"{CAPPED}")+COUNTIF({bp_range},"{ABOVE}"))'
N_ACTUAL = 4                   # actual weeks shown above the plan (rows 2-5)
FIRST = 2 + N_ACTUAL           # first plan week row
OPEN_ROW = FIRST - 1           # last actual week = opening position
LAST = FIRST + N_WEEKS - 1     # 19
R_TOT = LAST + 2               # 19

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
            "U": f"=(AJ{r}+AR{r})-(AM{r}+AT{r})", "V": f"=IF(H{r}=0,0,-U{r}/H{r})",
            "W": f"=W{p}+AR{r}", "X": f"=X{p}+AJ{r}", "Y": f"=G{r}+I{r}", "Z": f"=Y{r}/E{r}",
            "AA": f"={ci('ceiling', idx)}",
            "AC": f"=Inputs!$E${cal}",
            "AD": f"=INDEX(Inputs!$B${R_ADD0 + idx}:$E${R_ADD0 + idx},MATCH(C{r},Inputs!$B${R_ADD_H}:$E${R_ADD_H},0))/COUNTIF($C${FIRST}:$C${LAST},C{r})",
            "AE": f"=INDEX(Inputs!$B${R_SALE0 + idx}:$E${R_SALE0 + idx},MATCH(C{r},Inputs!$B${R_SALE_H}:$E${R_SALE_H},0))/COUNTIF($C${FIRST}:$C${LAST},C{r})",
            "AF": f"=Inputs!$F${cal}",
            # the planned on-road add (BM) is split across the three layers by their share of the gap
            # each layer gets its own need to the Lakshya month-end; anything the pace cap (or new cars) moves
            # away from the total need is shared out over the layers with a positive need
            "AG": f"=CA{r}-IFERROR(CB{r}*MAX(CA{r},0)/CC{r},0)",
            "AH": f"=X{p}",
            "AI": f'=IF(AF{r}="Diwali",0,IFERROR((BW{r}-AH{r})*BF{r}/BZ{r},0))',
            "AJ": f"=AI{r}-IFERROR(CB{r}*MAX(AI{r},0)/CC{r},0)",
            "AK": f"=AH{r}*{ci('r_own', idx)}/{G_WPM}*AC{r}/7*BD{r}",
            "AL": f"=AH{r}*{ci('r_roll', idx)}/{G_WPM}*AC{r}/7",
            "AM": f"=MAX(0,AJ{r}+AK{r}+AL{r})",
            "AN": f"=AM{r}*{ci('newshare', idx)}",
            "AO": f"=AM{r}-AN{r}",
            "AP": f"=W{p}",
            "AQ": f'=IF(AF{r}="Diwali",BS{r},IFERROR((BX{r}-AP{r}-G{r}*SUMIFS(BR{r}:$BR${LAST},BU{r}:$BU${LAST},BU{r}))*BF{r}/BZ{r},0))',
            "AR": f"=BM{r}-AG{r}-AJ{r}",
            "AS": f"=AP{r}*{ci('r_ldto', idx)}/{G_WPM}*AC{r}/7*BD{r}",
            "AT": f"=MAX(0,AR{r}+AS{r})",
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
            "BE": f"=IFERROR(INDEX(Inputs!$B${R_SEAS0}:$H${R_SEAS1},MATCH(Inputs!$N${cal},Inputs!$A${R_SEAS0}:$A${R_SEAS1},0),{idx + 1}),0)",
            "BF": f"=MAX(1+{G_FLOOR},1+BE{r})",
            # realism: never grow faster than the city's proven pace for the season, plus new cars
            "BH": f"=INDEX({DQ}!$B${R_PACE0 + idx}:$D${R_PACE0 + idx},MATCH(AF{r},{DQ}!$B${R_PACE_H}:$D${R_PACE_H},0))",
            "BI": f"=G{r}*BH{r}",
            # new cars bought so far and not yet on road go on road this week, unless it is a Diwali week
            "BJ": "=0" if w == 0 else f'=IF(Inputs!$P${cal}="No",0,MIN(Inputs!$I${R_ADD0 + idx},SUM($AD${FIRST}:AD{p})-SUM($BJ${FIRST}:BJ{p})))',
            "BK": f"=BI{r}+BJ{r}",
            # Diwali weeks: organic change = last two years' average dip. Other weeks: the gap left after
            # new cars and the Diwali dips still to come, spread over the non-Diwali weeks left
            "BL": (f'=IF(AF{r}="Diwali",BS{r},IFERROR(((BY{r}-G{r})-SUMIFS(BJ{r}:$BJ${LAST},BU{r}:$BU${LAST},BU{r})'
                   f'-G{r}*SUMIFS(BR{r}:$BR${LAST},BU{r}:$BU${LAST},BU{r}))*BF{r}/BZ{r},0))'),
            "BM": f'=BJ{r}+IF(AF{r}="Diwali",BL{r},IF({G_CAP}="No",BL{r},MIN(BL{r},BI{r})))',
            "BN": f"=BM{r}/G{r}",
            "BO": f"=(BM{r}-BJ{r})/G{r}",
            "BP": f'=IF(AF{r}="Diwali","Diwali dip (2024/25 avg)",IF(BL{r}<=BI{r}+0.5,"Yes",IF({G_CAP}="No","Above LY pace (cap off)","Capped at LY pace")))',
            "BQ": f"={ci('t_onroad', idx)}-Y{r}",
            "BR": f'=IF(AF{r}="Diwali",IFERROR(INDEX({DQ}!$B${R_DIP0 + idx}:$C${R_DIP0 + idx},MATCH(Inputs!$O${cal},{DQ}!$B${R_DIP_H}:$C${R_DIP_H},0)),0),0)',
            "BS": f"=G{r}*BR{r}",
            "BT": (f"=SUM($AD${FIRST}:$AD${LAST - 1})" if w == 0 else f"=SUM($AD${FIRST}:$AD${LAST - 1})-SUM($BJ${FIRST}:BJ{p})"),
            # Lakshya month-end targets (Inputs A3)
            "BU": f"=Inputs!$Q${cal}",
            "BV": f"=INDEX(Inputs!$B${R_MS0 + idx}:$E${R_MS0 + idx},MATCH(BU{r},Inputs!$B${R_MS_H}:$E${R_MS_H},0))",
            "BW": f"=INDEX(Inputs!$F${R_MS0 + idx}:$I${R_MS0 + idx},MATCH(BU{r},Inputs!$F${R_MS_H}:$I${R_MS_H},0))",
            "BX": f"=INDEX(Inputs!$J${R_MS0 + idx}:$M${R_MS0 + idx},MATCH(BU{r},Inputs!$J${R_MS_H}:$M${R_MS_H},0))",
            "BY": f"=BV{r}+BW{r}+BX{r}",
            "BZ": f'=SUMIFS(BF{r}:$BF${LAST},AF{r}:$AF${LAST},"<>Diwali",BU{r}:$BU${LAST},BU{r})',
            "CA": f'=IF(AF{r}="Diwali",0,IFERROR((BV{r}-R{p})*BF{r}/BZ{r},0))',
            "CB": f"=(CA{r}+AI{r}+AQ{r})-BM{r}",
            "CC": f"=MAX(CA{r},0)+MAX(AI{r},0)+MAX(AQ{r},0)",
        }
        for letter, _, _ in COLS:
            if letter in ("AB", "AX", "BG"):
                continue
            v = f.get(letter)
            fmt = NUM
            if letter in ("C", "D"):
                fmt = DATE
            elif letter in ("V", "Z", "AA", "AW", "BC", "BE", "BH", "BN", "BO", "BR"):
                fmt = PCT
            elif letter in ("AF", "BP", "BU"):
                fmt = None
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
    for letter in ["BI", "BJ", "BK", "BL", "BM"]:
        cput(ws, r, letter, f"=SUM({letter}{FIRST}:{letter}{LAST})", NUM, bold=True, bg=LIGHT)
    cput(ws, r, "BP", "=" + stretch_count(f"BP{FIRST}:BP{LAST}") + '&" weeks above LY pace"', bold=True, bg=LIGHT)
    cput(ws, r, "Q", "Closing stock on 27 Dec is the last week row", font=F_NOTE)

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
    ws.conditional_formatting.add(f"BP{FIRST}:BP{LAST}", FormulaRule(formula=[f'OR(BP{FIRST}="{CAPPED}",BP{FIRST}="{ABOVE}")'], font=red,
                                                                     fill=fill("FFFFC7CE")))
    ws.conditional_formatting.add(f"BP{FIRST}:BP{LAST}", FormulaRule(formula=[f'LEFT(BP{FIRST},6)="Diwali"'],
                                                                     font=Font(name="Calibri", size=10, bold=True, color="FF9C5700"),
                                                                     fill=fill("FFFFEB9C")))
    ws.conditional_formatting.add(f"BP{FIRST}:BP{LAST}", FormulaRule(formula=[f'BP{FIRST}="Yes"'],
                                                                     font=Font(name="Calibri", size=10, color="FF006100"),
                                                                     fill=fill("FFC6EFCE")))
    ws.conditional_formatting.add(f"AM{FIRST}:AM{LAST}", FormulaRule(formula=[f"AM{FIRST}<0"], font=red))
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


def build_inputs(wb):
    ws = wb.active
    ws.title = "Inputs"
    ws.column_dimensions["A"].width = 30
    for j in range(2, 22):
        ws.column_dimensions[get_column_letter(j)].width = 11
    for L in "GHIJKLM":  # calendar event columns
        ws.column_dimensions[L].width = 14
    ws.column_dimensions["N"].width = 16
    ws.sheet_properties.tabColor = "FFF1C232"
    # ---- top: what this tab is, colour key, contents
    ws["A1"] = "INPUTS  -  every number the plan is built from"
    ws["A1"].font = F_TITLE
    ws["A2"] = ("Change a cream cell and all 7 city tabs, Summary View and Lakshya vs Plan update. "
                "Nothing else on this tab needs typing.")
    ws["A2"].font = F_WHAT
    ws["A3"] = "Colour key:"
    ws["A3"].font = F_BOLD
    for c1, text, bg, font in ((2, "You can change", INPUT, F_INPUT), (4, "Actual (raw_performance)", ACTUAL, F_BODY),
                               (6, "Formula - leave it", None, F_BODY), (8, "Last year (history)", HIST, F_HIST),
                               (10, "Total / output", LIGHT, F_BOLD)):
        c = put(ws, 3, c1, text, font=font, bg=bg)
        c.alignment = CENTER
        put(ws, 3, c1 + 1, None, bg=bg)
        ws.merge_cells(start_row=3, start_column=c1, end_row=3, end_column=c1 + 1)
    parts = [
        ("PART A  What you set", [("A1", "Dates and switches", R_GLOBAL - 2), ("A2", "City start, Dec targets, rates", R_CITY_H - 3),
                                  ("A3", "Lakshya month-end targets", R_MS_H - 3), ("A4", "New cars bought", R_ADD_H - 2),
                                  ("A5", "Cars sold", R_SALE_H - 2), ("A6", "Weekly calendar", R_CAL_H - 2)]),
        ("PART B  Learnt from last year", [("B1", "Festival impact on recruitment", R_SEAS_H - 2),
                                           ("tab", f"Proven weekly pace and Diwali dip: {DIP_TAB} tab", None)]),
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
    banner(ws, R_GLOBAL - 4, "PART A  -  WHAT YOU SET  (cream cells)", NAVY)

    # ---- A1. dates and switches
    title(ws, R_GLOBAL - 2, "A1", "PLAN DATES AND SWITCHES",
          "When the plan starts and ends, and two switches that change how it behaves.")
    hdr(ws, R_GLOBAL, 1, "Setting")
    hdr(ws, R_GLOBAL, 2, "Value")
    hdr(ws, R_GLOBAL, 3, "What it does")
    ws.merge_cells(start_row=R_GLOBAL, start_column=3, end_row=R_GLOBAL, end_column=12)
    rows = [
        ("Opening date (last actual Sunday)", dt.date(2026, 9, 20), DATE, True,
         "The plan starts from the actual on this date (A2 and the 4 actual weeks on each city tab, from raw_performance)."),
        ("First plan week starts (Monday)", f"=B{R_GLOBAL + 1}+1", DATE, False, "Current week, Mon 21 Sep."),
        ("Plan ends (Sunday)", dt.date(2026, 12, 27), DATE, True, "Same end as Lakshya v4: w/e Sun 27 Dec."),
        ("Weeks per month", "=52/12", "0.00", False, "Turns the monthly churn rates in A2 into weekly ones."),
        ("India CNG on-road goal, Dec", 15000, NUM, True, "Reference. Lakshya's city targets (A2) add up to 15,082."),
        ("Largest recruitment drop in one week", -0.75, "0%", True,
         "Floor on the festival impact (B1), so no festival week plans recruitment below 25% of normal."),
        ("Hold weekly growth to last year's pace?", "No", None, True,
         "Yes = no week grows faster than the city did last year (Diwali_Dip Analysis tab). No = every week takes whatever Lakshya's month-end needs."),
    ]
    for k, (label, val, fmt, is_input, what) in enumerate(rows):
        r = R_GLOBAL + 1 + k
        put(ws, r, 1, label, bold=True)
        (inp if is_input else put)(ws, r, 2, val, fmt)
        put(ws, r, 3, what)
        for j in range(4, 13):
            put(ws, r, j, None)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=12)

    # ---- A2. city inputs
    title(ws, R_CITY_H - 3, "A2", "CITY START, DECEMBER TARGETS AND RATES",
          "Where each city starts (actual), where Lakshya wants it on 27 Dec, and the rates each week uses.")
    groups = [(2, 6, "START - actual on the opening date"), (7, 10, "DECEMBER TARGET - Lakshya v4"),
              (11, 14, "RATES - per month (Lakshya v4)"), (15, 15, "CEILING"),
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
    india_row(ws, r, [2, 3, 4, 5, 6, 7, 8, 9, 10, 20])
    for j in range(11, 20):
        put(ws, r, j, None, bg=LIGHT)
    note(ws, r + 1, "Leasing + DTO = on road - EIP - Own Now. Perf marketing = 100% - the other channels. "
                "New-car share only splits driver acquisition into new and existing cars on the city tabs.")

    # ---- A3. Lakshya month-end targets
    title(ws, R_MS_H - 3, "A3", "LAKSHYA MONTH-END TARGETS",
          "Lakshya's book on each month-end Sunday (27 Sep, 25 Oct, 29 Nov, 27 Dec). "
          "Each plan week works towards the month-end it counts to (A6, last column).")
    groups = [(2, 5, "EIP - straight line (not monthly in Lakshya)"), (6, 9, "OWN NOW - Lakshya v4"),
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
            # EIP: straight line from the opening to the December target
            put(ws, r, 2 + m, f"={ci('eip', i)}+({ci('t_eip', i)}-{ci('eip', i)})*{MS_WEEKS[m]}/{N_WEEKS}", NUM)
            if m < 3:
                inp(ws, r, 6 + m, LK_OWN_ME[city][m], NUM)
                inp(ws, r, 10 + m, LK_LDTO_ME[city][m], NUM)
            else:  # December = the Lakshya December target in A2
                put(ws, r, 6 + m, f"={ci('t_own', i)}", NUM)
                put(ws, r, 10 + m, f"={ci('t_ldto', i)}", NUM)
            L = [get_column_letter(2 + m), get_column_letter(6 + m), get_column_letter(10 + m)]
            put(ws, r, 14 + m, f"={L[0]}{r}+{L[1]}{r}+{L[2]}{r}", NUM, bold=True)
    india_row(ws, R_MS0 + len(CITIES), range(2, 18))
    note(ws, R_MS0 + len(CITIES) + 1, "December = the targets in A2. If a month-end can't be reached within last year's pace, "
                                  "the rest rolls into the next month (Lakshya vs Plan tab, section 5 shows why).")

    # ---- A4 / A5. cars bought / sold by month
    def month_table(r_h, code, name, what, data, lakshya, note_text, cap_col=False):
        title(ws, r_h - 2, code, name, what)
        hdr(ws, r_h, 1, "City")
        for m in range(4):
            c = hdr(ws, r_h, 2 + m, dt.date(2026, 9 + m, 1))
            c.number_format = "mmm-yy"
        for j, t in enumerate(["Total", "Lakshya total", "Difference"], start=6):
            hdr(ws, r_h, j, t)
        if cap_col:
            hdr(ws, r_h, 9, "Max on road per week")
        ws.row_dimensions[r_h].height = 30
        for i, city in enumerate(CITIES):
            r = r_h + 1 + i
            put(ws, r, 1, city, bold=True)
            for m in range(4):
                inp(ws, r, 2 + m, data[city][m], NUM)
            put(ws, r, 6, f"=SUM(B{r}:E{r})", NUM, bold=True)
            inp(ws, r, 7, lakshya[city], NUM)
            put(ws, r, 8, f"=F{r}-G{r}", NUM)
            if cap_col:  # 1.5 x the busiest month's weekly arrivals; type over to change
                put(ws, r, 9, f"=ROUNDUP(MAX(C{r}/4,D{r}/5)*1.5,0)", NUM, font=F_INPUT, bg=INPUT)
        r = r_h + 1 + len(CITIES)
        india_row(ws, r, range(2, 9))
        note(ws, r + 1, note_text)
        ws.conditional_formatting.add(f"H{r_h + 1}:H{r}", FormulaRule(formula=[f"H{r_h + 1}<>0"], font=RED_FONT))

    month_table(R_ADD_H, "A4", "NEW CARS BOUGHT, BY MONTH",
                "Cars arriving each month, split evenly over the month's weeks. They go on road the week after they arrive, "
                "at most column I a week (cars held back over Diwali catch up this way).",
                ADDS, LAKSHYA_ADDS,
                "Lakshya: 2,300 cars (WagonR 1,200, Dzire 600, Rumion 500), all landed by 30 Nov. Sep = 21-30 Sep only. "
                "Column I = 1.5 x normal weekly arrivals; type a number to change it.", cap_col=True)
    month_table(R_SALE_H, "A5", "CARS SOLD, BY MONTH",
                "Cars sold each month. They come out of idle cars, so they lower the fleet (and raise utilisation), not cars on road.",
                SALES, LAKSHYA_SALES,
                "Lakshya: 721 cars. Sep = 21-30 Sep only; cars sold 1-20 Sep are already out of the opening fleet.")

    # ---- A6. calendar
    title(ws, R_CAL_H - 2, "A6", "WEEKLY CALENDAR",
          "One row per plan week (Mon-Sun). The cream columns tell each week which season, festival and Diwali dip apply, "
          "and whether new cars go on road.")
    cal_heads = ["Week #", "Week start (Mon)", "Week end", "Month", "Days in plan", "Season (picks pace)"] + [
        f"Events - {c}" for c in CITIES] + ["Festival used (picks impact, B1)", "Diwali week (picks dip)",
                                             "New cars go on road? (No = hold)", "Month-end it counts to (A3)"]
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
        inp(ws, r, 6, WEEK_SEASON[w])
        for k, city in enumerate(CITIES):
            parts_ = [x for x in (EVENTS_ALL.get(w + 1), EVENTS_CITY.get((city, w + 1))) if x]
            inp(ws, r, 7 + k, "; ".join(parts_) if parts_ else "")
        inp(ws, r, 14, WEEK_EVENT.get(w + 1, ""))
        inp(ws, r, 15, DIWALI_WEEK.get(w + 1, ""))
        inp(ws, r, 16, "No" if WEEK_SEASON[w] == "Diwali" else "Yes")
        inp(ws, r, 17, WEEK_MONTH[w])
    r = R_CAL0 + N_WEEKS
    put(ws, r, 1, "Total", bold=True, bg=LIGHT)
    for j in (2, 3, 4):
        put(ws, r, j, None, bg=LIGHT)
    put(ws, r, 5, f"=SUM(E{R_CAL0}:E{r - 1})", "0", bold=True, bg=LIGHT)
    note(ws, r + 1, "Seasons: Pre-Diwali w/c 21 Sep - 26 Oct, Diwali w/c 2 and 9 Nov (Diwali Sun 8 Nov), Post-Diwali w/c 16 Nov - 21 Dec. "
                "A week counts in the month its Monday falls in. Events columns are for reading; only the festival column is used.")

    # ================================================================ PART B
    banner(ws, R_SEAS_H - 4, "PART B  -  LEARNT FROM LAST YEAR  (change only if you disagree with history)", TEAL)

    # ---- B1. festival impact on recruitment
    title(ws, R_SEAS_H - 2, "B1", "FESTIVAL IMPACT ON RECRUITMENT",
          "Change in recruitment in a festival week vs a normal week (2024-25 average). "
          "A festival week is asked to grow less: factor = 1 + impact.")
    hdr(ws, R_SEAS_H, 1, "Festival", TEAL)
    for k, city in enumerate(CITIES):
        hdr(ws, R_SEAS_H, 2 + k, city, TEAL)
    for i, (ev, vals) in enumerate(SEASON_REC.items()):
        r = R_SEAS0 + i
        put(ws, r, 1, ev, bold=True)
        for k, v in enumerate(vals):
            inp(ws, r, 2 + k, v, "0%")
    note(ws, R_SEAS1 + 1, "Source: Weekly Supply Plan, seasonality_Impect tab ('Rec Avg'). Floored at the A1 'largest drop'. "
                      "Weeks with no festival: factor 1. Kannada Rajyotsava is Bangalore only.")

    # ================================================================ PART C
    banner(ws, R_SUM_H - 4, "PART C  -  OUTPUT AND SOURCES  (nothing to type)", GREY_HDR)

    # ---- C1. summary
    title(ws, R_SUM_H - 2, "C1", "PLAN SUMMARY BY CITY",
          "Where the plan lands on 27 Dec, read from the city tabs. Gap to target and Check should be 0. "
          "Fleet 27 Dec differs from Lakshya only by the start fleet difference (column L).")
    sum_cols = ["City", "On road at start", "On road 27 Dec", "Lakshya target", "Gap to target",
                "EIP 27 Dec", "Own Now 27 Dec", "L+DTO 27 Dec", "Fleet 27 Dec", "Lakshya fleet Dec",
                "Lakshya start fleet (31 Aug)", "Start fleet difference (plan start - Lakshya start)",
                "Util 27 Dec", "Max utilisation", "Headroom", "EIP net add", "Own Now driver acquisition",
                "L+DTO driver acquisition", "Total driver acquisition", "Peak week driver acquisition", "Check (0 = OK)",
                "Weeks needing more than LY pace", "Top weekly growth %"]
    for j, t in enumerate(sum_cols, start=1):
        hdr(ws, R_SUM_H, j, t, GREY_HDR)
    ws.row_dimensions[R_SUM_H].height = 54
    for i, city in enumerate(CITIES):
        r = R_SUM0 + i
        s = q(city)
        vals = [
            (city, None), (f"={s}!Y{OPEN_ROW}", NUM), (f"={s}!Y{LAST}", NUM), (f"={ci('t_onroad', i)}", NUM),
            (f"=C{r}-D{r}", NUM), (f"={s}!R{LAST}", NUM), (f"={s}!X{LAST}", NUM), (f"={s}!W{LAST}", NUM),
            (f"={s}!E{LAST}", NUM), (f"={ci('lk_fleet', i)}", NUM),
            # Lakshya's start = its Dec fleet less its new cars plus its cars sold (A4 / A5, column G)
            (f"=J{r}-Inputs!$G${R_ADD0 + i}+Inputs!$G${R_SALE0 + i}", NUM),
            (f"={ci('fleet', i)}-K{r}", NUM),
            (f"=C{r}/I{r}", PCT), (f"={ci('ceiling', i)}", PCT), (f"=N{r}-M{r}", PCT), (f"={s}!P{R_TOT}", NUM),
            (f"={s}!AM{R_TOT}", NUM), (f"={s}!AT{R_TOT}", NUM), (f"={s}!AU{R_TOT}", NUM),
            (f"=MAX({s}!AU{FIRST}:AU{LAST})", NUM),
            (f"=ROUND(SUMPRODUCT(ABS({s}!AV2:AV{LAST})),6)", "0"),
            ("=" + stretch_count(f"{s}!BP{FIRST}:BP{LAST}"), "0"),
            (f"=MAX({s}!BN{FIRST}:BN{LAST})", "0.0%"),
        ]
        for j, (v, fmt) in enumerate(vals, start=1):
            put(ws, r, j, v, fmt, bold=(j == 1))
    r = R_SUM0 + len(CITIES)
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in range(2, len(sum_cols) + 1):
        L = get_column_letter(j)
        if L == "M":
            v, fmt = f"=C{r}/I{r}", PCT
        elif L in ("N", "O"):
            v, fmt = None, PCT
        elif L == "W":
            v, fmt = f"=MAX(W{R_SUM0}:W{r - 1})", "0.0%"
        else:
            v, fmt = f"=SUM({L}{R_SUM0}:{L}{r - 1})", NUM
        put(ws, r, j, v, fmt, bold=True, bg=LIGHT)
    r_india = r
    note(ws, r_india + 1, "Start fleet difference: the plan starts from the actual fleet on the opening date (A2, fleet_total_cars_cnt, "
                          "as in the Weekly Supply Plan); Lakshya started from its own 31 Aug base. Same cars bought and sold on both sides, "
                          "so the gap carries to 27 Dec. Headroom below 0 (red) = planned above the city's max utilisation.")
    ws.conditional_formatting.add(f"O{R_SUM0}:O{r_india - 1}",
                                  FormulaRule(formula=[f"O{R_SUM0}<0"], font=RED_FONT, fill=fill("FFFFC7CE")))
    ws.conditional_formatting.add(f"E{R_SUM0}:E{r_india}",
                                  FormulaRule(formula=[f"ROUND(E{R_SUM0},0)<>0"], font=RED_FONT))
    ws.conditional_formatting.add(f"U{R_SUM0}:U{r_india}",
                                  FormulaRule(formula=[f"U{R_SUM0}<>0"], font=RED_FONT, fill=fill("FFFFC7CE")))

    # ---- C2. sources
    title(ws, R_SRC_H - 2, "C2", "SOURCES", "Where the numbers come from.")
    hdr(ws, R_SRC_H, 1, "Source", GREY_HDR)
    hdr(ws, R_SRC_H, 2, "Link", GREY_HDR)
    ws.merge_cells(start_row=R_SRC_H, start_column=2, end_row=R_SRC_H, end_column=12)
    F_LINK = Font(name="Calibri", size=10, color="FF1155CC", underline="single")
    for k, (label, url, text) in enumerate(SOURCES):
        r = R_SRC_H + 1 + k
        put(ws, r, 1, label, bold=True)
        put(ws, r, 2, link(url, text), font=F_LINK)
        for j in range(3, 13):
            put(ws, r, j, None)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=12)

    ws.freeze_panes = "B2"
    ws.sheet_view.zoomScale = 90


def build_dip(wb):
    """Last year's proven weekly pace and Diwali dip: the history the plan is held to."""
    ws = wb.create_sheet(DIP_TAB)
    ws.column_dimensions["A"].width = 30
    for j in range(2, 13):
        ws.column_dimensions[get_column_letter(j)].width = 12
    ws.sheet_properties.tabColor = TEAL
    ws["A1"] = "DIWALI DIP AND LAST YEAR'S PACE  -  what 2024 and 2025 showed"
    ws["A1"].font = F_TITLE
    ws["A2"] = ("The city tabs read the cream cells here: the two Diwali weeks fall by section 2; section 1 caps weekly growth when the "
                "Inputs A1 switch is Yes, and flags the weeks above it when No. Grey = last year's history. Type over a cream cell to change it.")
    ws["A2"].font = F_WHAT

    # ---- 1. proven weekly pace
    title(ws, R_PACE_H - 2, "1.", "PROVEN WEEKLY PACE",
          "The fastest each city's cars on road grew per week, over its best 4 weeks, in the same season of 2024 or 2025. "
          "Columns B:D are used; with the Inputs A1 switch on Yes, no week grows faster than them.")
    for j, t in enumerate(["City"] + SEASONS +
                          ["2024 Pre", "2024 Diwali", "2024 Post", "2025 Pre", "2025 Diwali", "2025 Post"], start=1):
        hdr(ws, R_PACE_H, j, t, TEAL if j <= 4 else GREY_HDR)
    ws.row_dimensions[R_PACE_H].height = 30
    for i, city in enumerate(CITIES + ["INDIA (reference)"]):
        r = R_PACE0 + i
        key = city if city in PACE else "INDIA"
        vals = PACE.get(city, PACE_INDIA)
        put(ws, r, 1, city, bold=True, bg=None if city in PACE else LIGHT)
        for k in range(3):
            if city in PACE:
                inp(ws, r, 2 + k, vals[k], "0.0%")
            else:
                put(ws, r, 2 + k, vals[k], "0.0%", bold=True, bg=LIGHT)
        for y in range(2):
            for k in range(3):
                hist(ws, r, 5 + 3 * y + k, PACE_HIST[key][y][k])
    note(ws, R_PACE0 + len(CITIES) + 1,
         "Used = the better of 2024 and 2025, never below 0%. New cars are extra on top of this pace. "
         "The Diwali column is for reference: the two Diwali weeks follow section 2 instead.")

    # ---- 2. Diwali dip
    title(ws, R_DIP_H - 2, "2.", "DIWALI DIP",
          "How much cars on road fell in the Diwali weeks of 2024 and 2025. The plan's w/c 2 and 9 Nov fall by the "
          "two-year average (columns B and C).")
    heads = ["City", "Run-up week", "Diwali week", "Two weeks together", "Recovery week (info)",
             "2024 run-up", "2024 Diwali", "2024 recovery", "2025 run-up", "2025 Diwali", "2025 recovery"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_DIP_H, j, t, TEAL if j <= 5 else GREY_HDR)
    ws.row_dimensions[R_DIP_H].height = 30
    cc = R_DIPC0  # history table rows, same city order
    for i, city in enumerate(CITIES + ["INDIA (reference)"]):
        r = R_DIP0 + i
        is_city = city in CITIES
        put(ws, r, 1, city, bold=True, bg=None if is_city else LIGHT)
        cr = cc + i
        # history from the table below: (run-up, Diwali, recovery) = weeks 2/1, 3/2, 4/3 of each year
        for k, f in enumerate([f"=C{cr}/B{cr}-1", f"=D{cr}/C{cr}-1", f"=E{cr}/D{cr}-1",
                               f"=G{cr}/F{cr}-1", f"=H{cr}/G{cr}-1", f"=I{cr}/H{cr}-1"]):
            hist(ws, r, 6 + k, f)
        avg_ru, avg_dw = f"=AVERAGE(F{r},I{r})", f"=AVERAGE(G{r},J{r})"
        if is_city:  # typed as the formula so it stays live; type a number over it to override
            put(ws, r, 2, avg_ru, "0.0%", font=F_INPUT, bg=INPUT)
            put(ws, r, 3, avg_dw, "0.0%", font=F_INPUT, bg=INPUT)
        else:
            put(ws, r, 2, avg_ru, "0.0%", bold=True, bg=LIGHT)
            put(ws, r, 3, avg_dw, "0.0%", bold=True, bg=LIGHT)
        put(ws, r, 4, f"=(1+B{r})*(1+C{r})-1", "0.0%", bold=True, bg=None if is_city else LIGHT)
        put(ws, r, 5, f"=AVERAGE(H{r},K{r})", "0.0%", bg=None if is_city else LIGHT)
    note(ws, R_DIP0 + len(CITIES) + 1,
         "Diwali week = the week with Bhai Dooj; run-up = the week before; recovery = the week after (not forced, follows section 1). "
         "2024: w/e 27 Oct, 3 Nov, 10 Nov. 2025: w/e 19 Oct, 26 Oct, 2 Nov.")
    title(ws, R_DIPC_H - 2, "3.", "HISTORY - CARS ON ROAD ON THE SUNDAYS AROUND DIWALI",
          "The numbers section 2 is worked out from (allotted_cars_eod, CNG).")
    heads = ["City"] + [f"{d}" for d in DIWALI_SUNDAYS[0]] + [f"{d}" for d in DIWALI_SUNDAYS[1]]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_DIPC_H, j, t, GREY_HDR)
    for i, city in enumerate(CITIES):
        r = R_DIPC0 + i
        put(ws, r, 1, city, bold=True)
        for y in range(2):
            for k in range(4):
                hist(ws, r, 2 + 4 * y + k, DIWALI_CARS[city][y][k], NUM)
    india_row(ws, R_DIPC0 + len(CITIES), range(2, 10))
    note(ws, R_DIPC0 + len(CITIES) + 1, "2024 Diwali: Fri 1 Nov. 2025 Diwali: Mon 20 Oct. 2026 Diwali: Sun 8 Nov.")

    ws.freeze_panes = "B2"
    ws.sheet_view.zoomScale = 90


# ---------------------------------------------------------------- Lakshya v4 as given (for the comparison tab)
# Lakshya v4 starting books: Own Now ~6 Sep (Inputs sec 5), L+DTO 31 Aug (Actuals tab)
LK_OWN_OPEN = {"Mumbai": 511, "Delhi NCR": 661, "Bangalore": 668, "Hyderabad": 281, "Chennai": 428,
               "Kolkata": 185, "Pune": 267}
LK_LDTO_OPEN = {"Mumbai": 1164, "Delhi NCR": 1473, "Bangalore": 1040, "Hyderabad": 1035, "Chennai": 899,
                "Kolkata": 300, "Pune": 694}
LK_UTIL_DEC = {"Mumbai": 0.75, "Delhi NCR": 0.6199, "Bangalore": 0.7694, "Hyderabad": 0.7687,
               "Chennai": 0.7759, "Kolkata": 0.5727, "Pune": 0.6869}
# Driver Acquisition over the same 14 weeks (w/e 27 Sep - w/e 27 Dec): Weekly L+DTO F:S, Weekly Own Now E:R
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
    ws.sheet_state = "hidden"  # kept for reference; the Monthly Dashboard shows Lakshya vs plan
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
         "Each week works to Lakshya's month-end. Inputs A1 switch: No = match Lakshya every month-end; Yes = hold growth to the city's best 2024/25 pace, so it may land short - see Read Me."),
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
    put(ws, r, 11, f"=AVERAGE(K{first}:K{r - 1})", PCT, bold=True, bg=LIGHT)
    put(ws, r, 12, None, bg=LIGHT)
    status_rules(f"L{first}:L{r - 1}", f"L{first}")
    ws.cell(r + 1, 1, "New cars and sales match Lakshya city by city. Fleet differs only because of the opening fleet "
                      "(see section 1); a city above its ceiling needs more fleet, fewer sales, or a lower target.").font = F_NOTE

    # ---- 4. driver acquisition over the same 14 weeks
    r += 4
    section(r, "4.  DRIVER ACQUISITION OVER THE SAME 14 WEEKS (w/e 27 Sep - w/e 27 Dec)  -  where the plans differ, and why")
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
        "loses fewer drivers to churn, which offsets most of it - total driver acquisition ends up within about 2% of Lakshya's.",
        "Both plans let the book dip in the festival weeks and recover later. Lakshya sets that dip by hand; the weekly plan "
        "takes it from last year's weekly attrition and the festival impact on recruitment (Inputs A6 and B1; city tabs AY:BJ).",
    ]
    for k, t in enumerate(notes):
        c = ws.cell(r + 1 + k, 1, t)
        c.font = F_NOTE

    # ---- 5. month-end path, India
    r += 5
    section(r, "5.  THE PATH TO DECEMBER - India books on Lakshya's month-end Sundays")
    r += 1
    heads = [("Week ending", NAVY), ("Own Now - Lakshya", GREY_HDR), ("Own Now - plan", NAVY), ("Difference", NAVY),
             ("L+DTO - Lakshya", GREY_HDR), ("L+DTO - plan", NAVY), ("Difference", NAVY), ("Status", NAVY),
             ("Why", NAVY)]
    for j, (t, col) in enumerate(heads, start=1):
        hdr(ws, r, j, t, col)
    ws.column_dimensions["I"].width = 11
    ws.row_dimensions[r].height = 32
    first = r + 1
    s5_rows = []
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
        s5_rows.append(r)
    status_rules(f"H{first}:H{r}", f"H{first}")
    ws.cell(r + 1, 1, "Each plan week works towards Lakshya's next month-end book (Inputs A3). September has only one plan week (from the 20 Sep actual), "
                      "so it cannot close; later months miss only where last year's pace or the Diwali dip does not allow it. City detail below.").font = F_NOTE

    # ---- 5b. month-end by city, with the actual starting point
    r += 4
    section(r, "5b.  BY CITY - where each plan started (actual vs Lakshya), and Lakshya's month-end books vs the plan")
    r += 1
    heads = [("City", NAVY), ("Date", NAVY), ("Point", NAVY),
             ("Own Now - Lakshya", GREY_HDR), ("Own Now - plan", NAVY), ("Own Now - actual", TEAL), ("Own Now diff", NAVY),
             ("L+DTO - Lakshya", GREY_HDR), ("L+DTO - plan", NAVY), ("L+DTO - actual", TEAL), ("L+DTO diff", NAVY),
             ("Status", NAVY), ("Why", NAVY)]
    for j, (t, col) in enumerate(heads, start=1):
        hdr(ws, r, j, t, col)
    ws.row_dimensions[r].height = 32
    first = r + 1
    b_rows = {}
    dates = [dt.date(2026, 9, 27), dt.date(2026, 10, 25), dt.date(2026, 11, 29), dt.date(2026, 12, 27)]
    rawmax = "MAX(raw_performance!$C:$C)"

    def raw(field, city_cell, date_expr):
        L = rc(field)
        return (f"SUMIFS(raw_performance!${L}:${L},raw_performance!$D:$D,{city_cell},raw_performance!$E:$E,\"CNG\","
                f"raw_performance!$C:$C,{date_expr})")

    def raw_ldto(city_cell, date_expr):
        return (raw("allotted_cars_eod", city_cell, date_expr) + "-" + raw("own_now_cars_eod", city_cell, date_expr)
                + "-" + raw("eip_vehicles_cnt", city_cell, date_expr))

    city_blocks = []
    for i, city in enumerate(CITIES):
        s_ = q(city)
        cc = f'"{city}"'
        top = r + 1
        # 1. Lakshya's own starting point
        r += 1
        put(ws, r, 1, city, bold=True)
        put(ws, r, 2, "31 Aug / 6 Sep")
        put(ws, r, 3, "Lakshya start", font=F_NOTE)
        put(ws, r, 4, LK_OWN_OPEN[city], NUM)
        put(ws, r, 5, None)
        put(ws, r, 6, "=" + raw("own_now_cars_eod", cc, "DATE(2026,9,6)"), NUM)
        put(ws, r, 7, f"=F{r}-D{r}", NUM)
        put(ws, r, 8, LK_LDTO_OPEN[city], NUM)
        put(ws, r, 9, None)
        put(ws, r, 10, "=" + raw_ldto(cc, "DATE(2026,8,31)"), NUM)
        put(ws, r, 11, f"=J{r}-H{r}", NUM)
        put(ws, r, 12, "Start")
        put(ws, r, 13, f'="Actual vs Lakshya start: Own Now "&TEXT(G{r},"+#,##0;-#,##0;0")&", L+DTO "&TEXT(K{r},"+#,##0;-#,##0;0")')
        lk_row = r
        # 2. our plan start (20 Sep actual) vs where Lakshya's path was that day
        r += 1
        put(ws, r, 2, f"={G_OPEN_DATE}", "dd-mmm")
        put(ws, r, 3, "Plan start", font=F_NOTE)
        put(ws, r, 4, f"=D{lk_row}+(Inputs!F{R_MS0 + i}-D{lk_row})*2/3", NUM)   # 6 Sep -> 27 Sep, 2 of 3 weeks
        put(ws, r, 5, f"={ci('own', i)}", NUM)
        put(ws, r, 6, "=" + raw("own_now_cars_eod", cc, G_OPEN_DATE), NUM)
        put(ws, r, 7, f"=F{r}-D{r}", NUM)
        put(ws, r, 8, f"=H{lk_row}+(Inputs!J{R_MS0 + i}-H{lk_row})*3/4", NUM)  # 31 Aug -> 27 Sep, 3 of 4 weeks
        put(ws, r, 9, f"={ci('ldto', i)}", NUM)
        put(ws, r, 10, "=" + raw_ldto(cc, G_OPEN_DATE), NUM)
        put(ws, r, 11, f"=J{r}-H{r}", NUM)
        put(ws, r, 12, "Start")
        put(ws, r, 13, f'="Plan starts from the actual; Lakshya path that day: Own Now "&TEXT(G{r},"+#,##0;-#,##0;0")&", L+DTO "&TEXT(K{r},"+#,##0;-#,##0;0")')
        # 3-6. Lakshya month-ends
        for m, (d, wrow) in enumerate(zip(dates, ME_WEEK_ROWS)):
            r += 1
            put(ws, r, 2, d, "dd-mmm")
            put(ws, r, 3, "Month-end", font=F_NOTE)
            put(ws, r, 4, f"=Inputs!{get_column_letter(6 + m)}{R_MS0 + i}", NUM)
            put(ws, r, 5, f"={s_}!X{wrow}", NUM)
            put(ws, r, 6, f'=IF(B{r}<={rawmax},' + raw("own_now_cars_eod", cc, f"B{r}") + ',"")', NUM)
            put(ws, r, 7, f"=E{r}-D{r}", NUM)
            put(ws, r, 8, f"=Inputs!{get_column_letter(10 + m)}{R_MS0 + i}", NUM)
            put(ws, r, 9, f"={s_}!W{wrow}", NUM)
            put(ws, r, 10, f'=IF(B{r}<={rawmax},' + raw_ldto(cc, f"B{r}") + ',"")', NUM)
            put(ws, r, 11, f"=I{r}-H{r}", NUM)
            put(ws, r, 12, f'=IF(AND(ABS(G{r})<0.5,ABS(K{r})<0.5),"Match","Differs")')
            b_rows[(i, m)] = r
            mon = MONTHS[m]
            bu, bp, af = (f"{s_}!$BU${FIRST}:$BU${LAST}", f"{s_}!$BP${FIRST}:$BP${LAST}", f"{s_}!$AF${FIRST}:$AF${LAST}")
            pace = f"{DQ}!$B${R_PACE0 + i}" if m < 2 else f"{DQ}!$D${R_PACE0 + i}"
            if m == 0:
                reason = '"only 1 week after the 20 Sep actual"'
            else:
                reason = f'"growth held to last year\'s pace ("&TEXT({pace},"0.0%")&"/wk)"'
                if m == 2:
                    reason += f'&" + Diwali dip "&TEXT({DQ}!$D${R_DIP0 + i},"0%")'
            why = (f'=IF(L{r}="Match","",IF(G{r}+K{r}>0,"Above Lakshya by "&TEXT(G{r}+K{r},"#,##0"),'
                   f'TEXT(-(G{r}+K{r}),"#,##0")&" short - "&{reason}))')
            put(ws, r, 13, why)
        city_blocks.append(top)
    # INDIA block: sum of the city blocks row by row
    r += 1
    labels = [("31 Aug / 6 Sep", "Lakshya start"), (f"={G_OPEN_DATE}", "Plan start")] + [(d, "Month-end") for d in dates]
    for k, (d, pt) in enumerate(labels):
        r += 1
        put(ws, r, 1, "INDIA" if k == 0 else "", bold=True, bg=LIGHT)
        put(ws, r, 2, d, "dd-mmm", bg=LIGHT)
        put(ws, r, 3, pt, font=F_NOTE, bg=LIGHT)
        for j in (4, 5, 6, 8, 9, 10):
            L = get_column_letter(j)
            cells = ",".join(f"{L}{t + k}" for t in city_blocks)
            if k < 2 and j in (5, 9) and k == 0:
                put(ws, r, j, None, bg=LIGHT)
            elif j in (6, 10) and k >= 2:
                put(ws, r, j, f'=IF(COUNT({cells})=0,"",SUM({cells}))', NUM, bold=True, bg=LIGHT)
            else:
                put(ws, r, j, f"=SUM({cells})", NUM, bold=True, bg=LIGHT)
        if k < 2:
            put(ws, r, 7, f"=F{r}-D{r}", NUM, bold=True, bg=LIGHT)
            put(ws, r, 11, f"=J{r}-H{r}", NUM, bold=True, bg=LIGHT)
            put(ws, r, 12, "Start", bg=LIGHT)
        else:
            put(ws, r, 7, f"=E{r}-D{r}", NUM, bold=True, bg=LIGHT)
            put(ws, r, 11, f"=I{r}-H{r}", NUM, bold=True, bg=LIGHT)
            put(ws, r, 12, f'=IF(AND(ABS(G{r})<0.5,ABS(K{r})<0.5),"Match","Differs")', bg=LIGHT)
        put(ws, r, 13, None, bg=LIGHT)
    status_rules(f"L{first}:L{r}", f"L{first}")
    ws.conditional_formatting.add(f"A{first}:M{r}", FormulaRule(formula=[f'$C{first}<>"Month-end"'], fill=fill(ACTUAL)))
    # India reasons in section 5: which cities are short at each month-end
    for m, r5 in enumerate(s5_rows):
        terms = "&".join(f'IF(ABS(G{b_rows[(i, m)]}+K{b_rows[(i, m)]})>=0.5,"{c} "&TEXT(G{b_rows[(i, m)]}+K{b_rows[(i, m)]},"+#,##0;-#,##0")&"  ","")'
                         for i, c in enumerate(CITIES))
        lead = ['"Only 1 week after the 20 Sep actual. "', '"Growth held to last year\'s pace. "',
                '"Diwali dip + last year\'s pace. "', '""'][m]
        put(ws, r5, 9, f'=IF(H{r5}="Match","",{lead}&"Short: "&{terms})', font=F_NOTE)
    ws.cell(r + 1, 1, "Start rows (blue): Lakshya started from Own Now on ~6 Sep and L+DTO on 31 Aug; the plan starts from the actual on 20 Sep. "
                      "'Plan start' Lakshya = where Lakshya's path was on 20 Sep (straight line to its 27 Sep book). Diff on start rows = actual - Lakshya; on month-ends = plan - Lakshya. "
                      "Actual columns fill in from raw_performance once a month-end has passed.").font = F_NOTE
    r += 1
    ws.cell(r + 1, 1, "Inputs A1 'Hold weekly growth to last year's pace?' = No: every month-end matches Lakshya; weeks that need more than last year's pace show red in city tab column BP. "
                      "Set it to Yes and growth is held to that pace: September (one week from the 20 Sep actual) and months hit by the pace or the Diwali dip can then fall short.").font = F_NOTE

    # ---- 6. weekly India
    r += 4
    section(r, "6.  WEEK BY WEEK - INDIA  (driver acquisition = drivers to acquire for Own Now and Leasing + DTO that week)")
    r += 1
    heads = [("Week (Mon)", NAVY), ("Week end", NAVY), ("L+DTO driver acquisition - Lakshya", GREY_HDR),
             ("L+DTO driver acquisition - plan", NAVY), ("Difference", NAVY), ("Own Now driver acquisition - Lakshya", GREY_HDR),
             ("Own Now driver acquisition - plan", NAVY), ("Difference", NAVY), ("EIP net add - plan", NAVY),
             ("Total driver acquisition - plan", NAVY), ("On road, week end - plan", NAVY), ("Fleet - plan", NAVY),
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


# ---------------------------------------------------------------- Read Me
def build_readme(wb):
    ws = wb.create_sheet("Read Me", 0)
    ws.column_dimensions["A"].width = 24
    for L in "BCDEFGHIJKL":
        ws.column_dimensions[L].width = 13
    ws.sheet_view.showGridLines = False
    r = 1
    ws.cell(r, 1, "READ ME - how this plan gets from today to 27 December").font = F_TITLE
    r += 1
    ws.cell(r, 1, "Lakshya 15,000 weekly supply plan. Numbers in the tables below are live formulas from the city tabs.").font = F_NOTE
    ws.cell(r + 1, 1, "Lakshya source:").font = F_BOLD
    c = ws.cell(r + 1, 2, link(LAKSHYA_URL, "Lakshya_15000_Model_v4.xlsx"))
    c.font = Font(name="Calibri", size=10, color="FF1155CC", underline="single")

    def para(row, title, lines):
        ws.cell(row, 1, title).font = F_SECTION
        for k, t in enumerate(lines):
            c = ws.cell(row + 1 + k, 1, t)
            c.font = F_BODY
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.merge_cells(start_row=row + 1 + k, start_column=1, end_row=row + 1 + k, end_column=12)
            ws.row_dimensions[row + 1 + k].height = 30
        return row + len(lines) + 2

    r = para(5, "1.  HOW EACH WEEK IS PLANNED", [
        "New cars go on road the week after they arrive (2,300 cars, Oct-Nov, Inputs A4) - supply we did not have last year. Everything else is organic growth from recruitment net of churn.",
        "Organic growth: each week is asked for its share of the gap to Lakshya's next month-end (Own Now and L+DTO books on 27 Sep, 25 Oct, 29 Nov, 27 Dec - Inputs A3), after the new cars due in that month, less in festival weeks. "
        "The two Diwali weeks follow the dip seen in 2024 and 2025 instead of growing (section 4).",
        "Inputs A1 'Hold weekly growth to last year's pace?': No = every week takes what Lakshya's month-end needs, so the plan matches Lakshya at every month-end; weeks that need more than the city's best 4-week pace of 2024/25 "
        "(Diwali_Dip Analysis tab, section 1) are flagged red in city tab column BP. Yes = growth is capped at that pace and the rest rolls into the next month, so month-ends can fall short.",
        f'=IF({G_CAP}="No","CURRENT SETTING: MATCH LAKSHYA - "&({"+".join(stretch_count(f"{q(c)}!BP{FIRST}:BP{LAST}") for c in CITIES)})&" of {len(CITIES) * N_WEEKS} city-weeks need more organic growth than last year showed. Those are the weeks to watch.",'
        f'"CURRENT SETTING: LAST YEAR\'S PACE - no week plans more organic growth than 2024/25 showed; "&({"+".join(stretch_count(f"{q(c)}!BP{FIRST}:BP{LAST}") for c in CITIES)})&" city-weeks are capped.")',
    ])

    # ---- 2. the bridge
    ws.cell(r, 1, "2.  THE BRIDGE - from 20 Sep to 27 Dec, by season").font = F_SECTION
    r += 1
    heads = ["City", "On road 20 Sep", "Pre-Diwali organic (w/c 21 Sep-26 Oct)", "Diwali organic (w/c 2-9 Nov)",
             "Post-Diwali organic (w/c 16 Nov-21 Dec)", "New cars put on road", "On road 27 Dec (plan)",
             "Lakshya target", "Short of Lakshya", "Weeks needing more than LY pace"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, r, j, t)
    ws.row_dimensions[r].height = 45
    first = r + 1
    rng = lambda s, col: f"{s}!${col}${FIRST}:${col}${LAST}"
    for i, city in enumerate(CITIES):
        r += 1
        s = q(city)
        put(ws, r, 1, city, bold=True)
        put(ws, r, 2, f"={s}!Y{OPEN_ROW}", NUM)
        for j, season in enumerate(SEASONS):
            put(ws, r, 3 + j, f'=SUMIF({rng(s, "AF")},"{season}",{rng(s, "BM")})-SUMIF({rng(s, "AF")},"{season}",{rng(s, "BJ")})', NUM)
        put(ws, r, 6, f"=SUM({rng(s, 'BJ')})", NUM)
        put(ws, r, 7, f"={s}!Y{LAST}", NUM, bold=True)
        put(ws, r, 8, f"={ci('t_onroad', i)}", NUM)
        put(ws, r, 9, f"=H{r}-G{r}", NUM)
        put(ws, r, 10, "=" + stretch_count(rng(s, "BP")), "0")
    r += 1
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in range(2, 11):
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{first}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)
    red = Font(name="Calibri", size=10, bold=True, color="FFC00000")
    ws.conditional_formatting.add(f"I{first}:I{r}", FormulaRule(formula=[f"I{first}>0.5"], font=red, fill=fill("FFFFC7CE")))
    r += 1
    ws.cell(r, 1, "Organic = growth from recruitment net of churn. On road 27 Dec = on road 20 Sep + the three organic columns + new cars. "
                  "Short of Lakshya > 0 (only with the Inputs A1 switch on Yes) means last year's pace cannot carry the city all the way: that gap needs something last year did not have (more cars earlier, more EIP, lower churn). "
                  "New cars: 2,300 over nine weeks is 250-290 a week going on road - confirm deliveries and onboarding; if a delivery slips, change Inputs A4 and the plan re-spreads.").font = F_NOTE
    r += 3

    # ---- 3. week by week, India
    ws.cell(r, 1, "3.  WEEK BY WEEK - INDIA: planned growth vs what we have done before").font = F_SECTION
    r += 1
    heads = ["Week (Mon)", "Season", "Festival in the week", "Planned growth % (India)", "Organic growth %",
             "Proven India pace (season)", "Same week last year", "On road week end (plan)", "Of which new cars"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, r, j, t)
    ws.row_dimensions[r].height = 40
    wfirst = r + 1
    for w in range(N_WEEKS):
        r += 1
        pr = FIRST + w
        cal = R_CAL0 + w
        allc = lambda col, row=pr: "+".join(f"{q(c)}!{col}{row}" for c in CITIES)
        put(ws, r, 1, f"=Inputs!B{cal}", DATE, bold=True)
        put(ws, r, 2, f"=Inputs!F{cal}")
        put(ws, r, 3, f"=Inputs!N{cal}")
        put(ws, r, 4, f"=({allc('BM')})/({allc('G')})", "0.0%", bold=True)
        put(ws, r, 5, f"=(({allc('BM')})-({allc('BJ')}))/({allc('G')})", "0.0%")
        put(ws, r, 6, f"=INDEX({DQ}!$B${R_PACE0 + len(CITIES)}:$D${R_PACE0 + len(CITIES)},MATCH(B{r},{DQ}!$B${R_PACE_H}:$D${R_PACE_H},0))", "0.0%")
        put(ws, r, 7, (f'=IFERROR(SUMIFS(raw_performance!${rc("allotted_cars_eod")}:${rc("allotted_cars_eod")},raw_performance!$E:$E,"CNG",raw_performance!$C:$C,A{r}-364+6)'
                       f'/SUMIFS(raw_performance!${rc("allotted_cars_eod")}:${rc("allotted_cars_eod")},raw_performance!$E:$E,"CNG",raw_performance!$C:$C,A{r}-364-1)-1,"")'), "0.0%")
        put(ws, r, 8, f"={allc('Y')}", NUM)
        put(ws, r, 9, f"={allc('BJ')}", NUM)
    ws.conditional_formatting.add(f"E{wfirst}:E{r}", FormulaRule(formula=[f"E{wfirst}>F{wfirst}+0.0005"], font=red, fill=fill("FFFFC7CE")))
    r += 1
    ws.cell(r, 1, "Red = organic growth above India's proven pace for the season. With Inputs A1 on No these are weeks Lakshya's month-ends need; with Yes each city stays within its own pace. "
                  "Last year's column is India cars on road, same week of 2025 (Diwali 2025 fell on 20 Oct, three weeks earlier than 2026).").font = F_NOTE
    r += 3

    # ---- Diwali check
    ws.cell(r, 1, "4.  DIWALI CHECK - what happened in the two Diwali weeks of 2024 and 2025, and what the plan assumes for w/c 2 and 9 Nov").font = F_SECTION
    r += 1
    heads = ["City", "2024: two Diwali weeks", "2025: two Diwali weeks", "Average (used)", "Plan: organic change",
             "Plan: total change (new cars held back)", "Plan: recovery week", "History: recovery week"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, r, j, t)
    ws.row_dimensions[r].height = 45
    dfirst = r + 1
    pre, dw2, rec = FIRST + 5, FIRST + 7, FIRST + 8  # weeks ending 1 Nov, 15 Nov, 22 Nov
    for i, city in enumerate(CITIES + ["INDIA"]):
        r += 1
        d = R_DIP0 + i
        put(ws, r, 1, city, bold=True, bg=LIGHT if city == "INDIA" else None)
        put(ws, r, 2, f"=(1+{DQ}!F{d})*(1+{DQ}!G{d})-1", "0.0%")
        put(ws, r, 3, f"=(1+{DQ}!I{d})*(1+{DQ}!J{d})-1", "0.0%")
        put(ws, r, 4, f"={DQ}!D{d}", "0.0%", bold=True)
        if city in CITIES:
            s_ = q(city)
            put(ws, r, 5, f"=({s_}!BS{pre + 1}+{s_}!BS{dw2})/{s_}!Y{pre}", "0.0%")
            put(ws, r, 6, f"={s_}!Y{dw2}/{s_}!Y{pre}-1", "0.0%", bold=True)
            put(ws, r, 7, f"={s_}!Y{rec}/{s_}!Y{dw2}-1", "0.0%")
        else:
            allc = lambda col, row: "+".join(f"{q(c)}!{col}{row}" for c in CITIES)
            put(ws, r, 5, f"=({allc('BS', pre + 1)}+{allc('BS', dw2)})/({allc('Y', pre)})", "0.0%", bg=LIGHT)
            put(ws, r, 6, f"=({allc('Y', dw2)})/({allc('Y', pre)})-1", "0.0%", bold=True, bg=LIGHT)
            put(ws, r, 7, f"=({allc('Y', rec)})/({allc('Y', dw2)})-1", "0.0%", bg=LIGHT)
        put(ws, r, 8, f"={DQ}!E{d}", "0.0%", bg=LIGHT if city == "INDIA" else None)
    r += 1
    ws.cell(r, 1, "The plan's two Diwali weeks now fall by each city's two-year average dip (Diwali_Dip Analysis tab) - India about -9%, as in 2024 (-9.8%) and 2025 (-8.5%). "
                  "New cars that arrive in those weeks wait, then go on road from the recovery week at up to 1.5x the normal weekly rate (Inputs A4), so the recovery week is also lifted by new cars. "
                  "The Summary View shows the same weeks against last year's week of the same date (Diwali 2025 fell three weeks earlier).").font = F_NOTE
    r += 3

    r = para(r, "5.  WHERE THE PLAN DROPS, WHERE IT GAINS, AND THE WEEKS IN BETWEEN", [
        "PRE-DIWALI (w/c 21 Sep - 26 Oct): last year cars on road fell in these weeks (India -0.1% at best, weeks of -2.6% to -5.4%); in 2024 the best was +1.5% a week. The plan allows each city its better of the two years "
        "and adds the October new cars the week after they land. Last year's attrition peaks here (LY attrition index up to 1.2-1.4), so more driver acquisition is needed just to hold the book.",
        "DIWALI (w/c 2 and 9 Nov): cars on road fell in these weeks in both years - India -9.8% in 2024 and -8.5% in 2025 over the two weeks (drivers go home; recruitment stops). "
        "The plan now falls by each city's two-year average (section 4 above; Diwali_Dip Analysis tab), all of it from the Leasing + DTO book, and holds new cars back until the recovery week. This is where the plan dips.",
        "POST-DIWALI (w/c 16 Nov - 21 Dec): the season where we have shown real recovery - India +2.7% to +2.9% a week at best, Mumbai and Pune above 5%. Most of the remaining gap is closed here, "
        "but no city goes above its own best 4-week pace.",
        "WEEKS WITH NO FESTIVAL (the middle of each season): no seasonality is applied - the factor is 1, so the week is simply asked for an equal share of the gap still open, capped by the season's pace. "
        "Only last year's attrition shape (city tab column BD) changes how much driver acquisition such a week needs.",
    ])
    r = para(r, "6.  HOW TO READ A CITY TAB", [
        "Rows 2-5 are actual weeks from raw_performance. Plan weeks start at row 6. Columns A-AC follow the Weekly Supply Plan layout; the Lakshya build-up is AF-AW.",
        "Brown block BH-BQ is the realism check: BH proven pace, BI organic capacity, BJ new cars going on road, BK most we can add, BL organic add needed, BM what we plan (new cars + the smaller of BL and BI), "
        "BN/BO planned and organic growth %, BP 'Yes' / 'Capped at LY pace' / 'Diwali dip', BQ gap to the Lakshya number still open, BR:BS the Diwali dip, BT new cars still to go on road.",
        "BM is split into EIP / Own Now / Leasing+DTO by each layer's share of the gap it still has to its Lakshya number (the Diwali dip is taken from Leasing+DTO, which then wins it back). Driver acquisition = that layer's net add + churn. Recruitment by channel = driver acquisition x the city's channel mix.",
        "Last year (AY:BF): the same week last year (week start - 364 days) from raw_performance. LY net attrition % = (attrition + temp attrition - rejoins - temp rejoins) / (active partners at week start + new joins + resurrections), as in the Weekly Supply Plan; "
        "LY attrition index = that week's % / the 14-week average. Churn (AK, AS) = last week's book x Lakshya monthly rate / 4.33 x that index. Festival factor (BF) = 1 + festival impact (Inputs B1).",
        "Fleet (E) = previous week + Total buy (G) - Total sold (H); each month's cars are split evenly over its weeks (Inputs A4, A5). Util (AB) = cars on road / fleet, red above the Lakshya ceiling (AC). "
        "Net Attrition (W) = net adds - driver acquisition. Check column AV must be 0. Month by month, by city: Monthly Dashboard tab.",
    ])
    r = para(r, "7.  UPDATING EACH WEEK", [
        "Paste a fresh SSOT query result (link on the Inputs tab, C2) into raw_performance. The Summary View 'actual' rows fill in for finished weeks. "
        "To re-plan from a later week, move the opening date on Inputs to the latest Sunday and extend the calendar.",
        "Change what the plan may assume on the Inputs tab: month-end targets (A3), new cars and sales by month (A4, A5), churn rates and targets (A2), festival impacts (B1); proven pace and Diwali dip on the Diwali_Dip Analysis tab.",
    ])
    ws.freeze_panes = "A4"
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


def build_dashboard(wb):
    """Month by month for India or a picked city, city-by-month tables and live insights.
    Months are Lakshya's: each plan week counts to the month-end in Inputs A6 (city tab column BU)."""
    ws = wb.create_sheet(DASH, 2)
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = NAVY
    ws.column_dimensions["A"].width = 18
    for j in range(2, 23):
        ws.column_dimensions[get_column_letter(j)].width = 11
    L = get_column_letter
    cities = [q(c) for c in CITIES]
    F_WHAT = Font(name="Calibri", size=10, italic=True, color="FF404040")

    def red_if(rng, cond):
        ws.conditional_formatting.add(rng, FormulaRule(formula=[cond], font=RED_FONT, fill=fill("FFFFC7CE")))

    # ---- layout
    R_MV_T = 5                     # 1. month by month
    R_MV_H = R_MV_T + 1
    R_MV_S = R_MV_H + 1            # start row
    R_MV0 = R_MV_S + 1             # Sep..Dec
    R_MV_TOT = R_MV0 + 4
    R_LV_T = R_MV_TOT + 3          # 2. Lakshya plan vs our plan
    R_LV_G = R_LV_T + 1            # group header
    R_LV_H = R_LV_G + 1            # Lakshya / Plan / Diff
    R_LV_S = R_LV_H + 1            # start row
    R_LV0 = R_LV_S + 1             # Sep..Dec
    R_LV_TOT = R_LV0 + 4
    R_PB_T = R_LV_TOT + 3          # 2b. driver acquisition bridge (India)
    R_PB_H = R_PB_T + 2
    R_PB0 = R_PB_H + 1             # Sep..Dec
    R_PB_TOT = R_PB0 + 4
    R_IN_T = R_PB_TOT + 3          # 3. insights
    N_INS = 10
    PICK = "$B$3"
    city_list = f"Inputs!$A${R_SUM0}:$A${R_SUM0 + len(CITIES) - 1}"   # city names in Inputs C1

    def pick(exprs, india=None):
        india = india or "+".join(exprs)
        return f'=IF({PICK}="India",{india},CHOOSE(MATCH({PICK},{city_list},0),{",".join(exprs)}))'

    # ---- top
    ws["A1"] = "MONTHLY DASHBOARD  -  India and every city, month by month"
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

    # ---- 1. month by month (picked)
    mv = [  # (header, kind, source)
        ("Weeks", "weeks", None), ("New cars bought", "flow", ["AD"]), ("Cars sold", "flow", ["AE"]),
        ("New cars put on road", "flow", ["BJ"]), ("EIP net add", "flow", ["P"]),
        ("Own Now driver acquisition", "flow", ["AM"]), ("Own Now churn + rollover", "flow", ["AK", "AL"]),
        ("Own Now net add", "flow", ["AJ"]), ("L+DTO driver acquisition", "flow", ["AT"]), ("L+DTO churn", "flow", ["AS"]),
        ("L+DTO net add", "flow", ["AR"]), ("Total driver acquisition", "flow", ["AU"]), ("Net add on road", "netadd", None),
        ("Fleet (month end)", "stock", "E"), ("EIP (month end)", "stock", "R"), ("Own Now (month end)", "stock", "X"),
        ("L+DTO (month end)", "stock", "W"), ("On road (month end)", "stock", "Y"),
        ("Lakshya on road (month end)", "lakshya", None), ("Plan - Lakshya", "diff", None), ("Util (month end)", "util", None),
    ]
    col = {h: L(2 + k) for k, (h, _, _) in enumerate(mv)}
    ONR, FLT, LKC, DIF = col["On road (month end)"], col["Fleet (month end)"], col["Lakshya on road (month end)"], col["Plan - Lakshya"]
    put(ws, R_MV_T, 1, f'="1.  MONTH BY MONTH  -  "&UPPER({PICK})', font=F_SECTION).border = Border()
    hdr(ws, R_MV_H, 1, "Month")
    for h, c_ in col.items():
        hdr(ws, R_MV_H, column_index_from_string(c_), h)
    ws.row_dimensions[R_MV_H].height = 42
    # start row
    r = R_MV_S
    put(ws, r, 1, f'="Start ("&TEXT({G_OPEN_DATE},"d mmm")&")"', bold=True, bg=ACTUAL)
    for h, kind, src in mv:
        j = column_index_from_string(col[h])
        if kind == "stock":
            put(ws, r, j, pick([f"{s}!${src}${OPEN_ROW}" for s in cities]), NUM, bg=ACTUAL)
        elif kind == "util":
            put(ws, r, j, f"={ONR}{r}/{FLT}{r}", PCT, bg=ACTUAL)
        else:
            put(ws, r, j, None, bg=ACTUAL)
    for m, mon in enumerate(MONTHS):
        r = R_MV0 + m
        put(ws, r, 1, mon, bold=True)
        mref = f"$A{r}"
        for h, kind, src in mv:
            j = column_index_from_string(col[h])
            if kind == "weeks":
                v, fmt = f"=COUNTIF({_bu(cities[0])},{mref})", "0"
            elif kind == "flow":
                v, fmt = pick(["+".join(_flow(s, x, mref) for x in src) for s in cities]), NUM
            elif kind == "stock":
                v, fmt = pick([_stock(s, src, mref) for s in cities]), NUM
            elif kind == "netadd":
                v, fmt = f"={ONR}{r}-{ONR}{r - 1}", NUM
            elif kind == "lakshya":
                v, fmt = pick([f"Inputs!${L(14 + m)}${R_MS0 + i}" for i in range(len(CITIES))]), NUM
            elif kind == "diff":
                v, fmt = f"={ONR}{r}-{LKC}{r}", NUM
            else:
                v, fmt = f"={ONR}{r}/{FLT}{r}", PCT
            put(ws, r, j, v, fmt, bold=(kind in ("netadd", "diff") or h == "On road (month end)"))
    r = R_MV_TOT
    put(ws, r, 1, "Total / 27 Dec", bold=True, bg=LIGHT)
    for h, kind, src in mv:
        c_ = col[h]
        if kind in ("stock", "lakshya", "diff", "util"):
            v = f"={c_}{R_MV0 + 3}"
        else:
            v = f"=SUM({c_}{R_MV0}:{c_}{R_MV0 + 3})"
        put(ws, r, column_index_from_string(c_), v, PCT if kind == "util" else NUM, bold=True, bg=LIGHT)
    red_if(f"{DIF}{R_MV0}:{DIF}{R_MV_TOT}", f"{DIF}{R_MV0}<-0.5")
    ws.cell(R_MV_TOT + 1, 1, "Net add on road = EIP + Own Now + L+DTO net adds. Driver acquisition = net add + churn "
                             "(Own Now and L+DTO). Red = below Lakshya's month-end.").font = F_NOTE

    # ---- 2. Lakshya plan vs our plan (picked)
    ncity = len(CITIES)
    lk_pl_mon = {mon: sum(LK_LDTO_WK[w] + LK_OWN_WK[w] for w in range(N_WEEKS) if WEEK_MONTH[w] == mon) for mon in MONTHS}
    groups = [  # (group title, Lakshya source per month m and city i, plan column in section 1, Lakshya start per city)
        ("OWN NOW (month end)", lambda m, i: f"Inputs!${L(6 + m)}${R_MS0 + i}", [col["Own Now (month end)"]], LK_OWN_OPEN),
        ("LEASING + DTO (month end)", lambda m, i: f"Inputs!${L(10 + m)}${R_MS0 + i}", [col["L+DTO (month end)"]], LK_LDTO_OPEN),
        ("EIP (month end)", lambda m, i: f"Inputs!${L(2 + m)}${R_MS0 + i}", [col["EIP (month end)"]], None),
        ("ON ROAD (month end)", lambda m, i: f"Inputs!${L(14 + m)}${R_MS0 + i}", [col["On road (month end)"]], None),
        ("DRIVER ACQUISITION in the month (Own Now + L+DTO)", None, [col["Own Now driver acquisition"], col["L+DTO driver acquisition"]], None),
    ]
    put(ws, R_LV_T, 1, f'="2.  LAKSHYA PLAN vs OUR PLAN  -  "&UPPER({PICK})', font=F_SECTION).border = Border()
    hdr(ws, R_LV_G, 1, "")
    hdr(ws, R_LV_H, 1, "Month")
    lv = []  # (Lakshya col, Plan col, Diff col) per group
    for g, (gt, _, _, _) in enumerate(groups):
        c0 = 2 + 3 * g
        hdr(ws, R_LV_G, c0, gt, GREY_HDR)
        ws.merge_cells(start_row=R_LV_G, start_column=c0, end_row=R_LV_G, end_column=c0 + 2)
        for k, t in enumerate(("Lakshya", "Plan", "Plan - Lakshya")):
            hdr(ws, R_LV_H, c0 + k, t)
        lv.append((L(c0), L(c0 + 1), L(c0 + 2)))
    # attrition group: Lakshya's flat monthly rates vs the plan's (same rates shaped by last year's weekly attrition)
    ATT0 = 2 + 3 * len(groups)
    AL_, AP_, AD_, AX_ = (L(ATT0 + k) for k in range(4))
    hdr(ws, R_LV_G, ATT0, "ATTRITION % A MONTH (Own Now + L+DTO book)", GREY_HDR)
    ws.merge_cells(start_row=R_LV_G, start_column=ATT0, end_row=R_LV_G, end_column=ATT0 + 3)
    for k, t in enumerate(("Lakshya", "Plan (last year's shape)", "Plan - Lakshya", "Extra drivers to replace churn")):
        hdr(ws, R_LV_H, ATT0 + k, t)
    for j in range(23, 27):
        ws.column_dimensions[L(j)].width = 11
    WHY = L(ATT0 + 4)
    hdr(ws, R_LV_G, column_index_from_string(WHY), "")
    hdr(ws, R_LV_H, column_index_from_string(WHY), "Why they differ")
    ws.merge_cells(f"{WHY}{R_LV_G}:{L(column_index_from_string(WHY) + 5)}{R_LV_G}")
    ws.merge_cells(f"{WHY}{R_LV_H}:{L(column_index_from_string(WHY) + 5)}{R_LV_H}")
    ws.row_dimensions[R_LV_G].height = 30
    ws.row_dimensions[R_LV_H].height = 42
    DIFF = "+#,##0;-#,##0;0"
    OWN_ME, LD_ME = col["Own Now (month end)"], col["L+DTO (month end)"]
    CH_OWN, CH_LD = col["Own Now churn + rollover"], col["L+DTO churn"]

    def flat_churn(i, mon):
        """City i's Own Now + L+DTO churn in a month at Lakshya's flat monthly rates (no last-year shape)."""
        s_ = cities[i]
        days = f"{s_}!$AC${FIRST}:$AC${LAST}"
        own = f"SUMPRODUCT(({_bu(s_)}={mon})*{s_}!$AH${FIRST}:$AH${LAST}*{days})/7"
        ldto = f"SUMPRODUCT(({_bu(s_)}={mon})*{s_}!$AP${FIRST}:$AP${LAST}*{days})/7"
        return (f"({ci('r_own', i)}+{ci('r_roll', i)})/{G_WPM}*{own}+{ci('r_ldto', i)}/{G_WPM}*{ldto}")
    rows = [("start", R_LV_S)] + [(m, R_LV0 + m) for m in range(4)] + [("total", R_LV_TOT)]
    for key, r in rows:
        bg = ACTUAL if key == "start" else (LIGHT if key == "total" else None)
        if key == "start":
            put(ws, r, 1, "Start", bold=True, bg=bg)
        elif key == "total":
            put(ws, r, 1, "Total / 27 Dec", bold=True, bg=bg)
        else:
            put(ws, r, 1, MONTHS[key], bold=True)
        mv_row = {"start": R_MV_S, "total": R_MV_TOT}.get(key, R_MV0 + key if isinstance(key, int) else None)
        for g, (gt, lk_src, plan_cols, lk_open) in enumerate(groups):
            cl, cp, cd = lv[g]
            if lk_src is None:  # driver acquisition: Lakshya monthly exists for India only; city = 14-week total
                if key == "start":
                    lk, pl = None, None
                elif key == "total":
                    lk = pick([str(LK_LDTO_PL[c] + LK_OWN_PL[c]) for c in CITIES], str(sum(lk_pl_mon.values())))
                    pl = f"=SUM({cp}{R_LV0}:{cp}{R_LV0 + 3})"
                else:
                    lk = f'=IF({PICK}="India",{lk_pl_mon[MONTHS[key]]},"")'
                    pl = "=" + "+".join(f"{c_}{mv_row}" for c_ in plan_cols)
            elif key == "start":
                lk = pick([str(lk_open[c]) for c in CITIES]) if lk_open else None
                pl = f"={plan_cols[0]}{R_MV_S}"
            else:
                m = 3 if key == "total" else key
                lk = pick([lk_src(m, i) for i in range(ncity)], lk_src(m, ncity))
                pl = f"={plan_cols[0]}{mv_row}"
            put(ws, r, column_index_from_string(cl), lk, NUM, bg=bg)
            put(ws, r, column_index_from_string(cp), pl, NUM, bg=bg)
            dv_ = None if lk is None else f'=IF(OR({cl}{r}="",{cp}{r}=""),"",ROUND({cp}{r}-{cl}{r},0))'
            put(ws, r, column_index_from_string(cd), dv_, DIFF, bold=True, bg=bg)
        onr_d = f"{lv[3][2]}{r}"
        acq_d = f"{lv[4][2]}{r}"
        # attrition % a month = churn / weeks x 52/12 / average Own Now + L+DTO book
        if key == "start":
            for k in range(4):
                put(ws, r, ATT0 + k, None, bg=bg)
        else:
            if key == "total":
                weeks, prev = str(N_WEEKS), R_MV_S
                extra = f"=SUM({AX_}{R_LV0}:{AX_}{R_LV0 + 3})"
            else:
                weeks, prev = f'COUNTIF({_bu(cities[0])},"{MONTHS[key]}")', mv_row - 1
                extra = (f"={CH_OWN}{mv_row}+{CH_LD}{mv_row}-("
                         + pick([flat_churn(i, f'"{MONTHS[key]}"') for i in range(ncity)])[1:] + ")")
            book = f"AVERAGE({OWN_ME}{prev}+{LD_ME}{prev},{OWN_ME}{mv_row}+{LD_ME}{mv_row})"
            churn = f"({CH_OWN}{mv_row}+{CH_LD}{mv_row})"
            pbr = R_PB_TOT if key == "total" else R_PB0 + key   # same month in 2b (India)
            put(ws, r, ATT0, f'=IF({PICK}="India",J{pbr},({churn}-{AX_}{r})/{weeks}*{G_WPM}/{book})', PCT, bg=bg)
            put(ws, r, ATT0 + 1, f"={churn}/{weeks}*{G_WPM}/{book}", PCT, bg=bg)
            put(ws, r, ATT0 + 2, f"={AP_}{r}-{AL_}{r}", "+0.0%;-0.0%;0.0%", bold=True, bg=bg)
            put(ws, r, ATT0 + 3, f'=IF({PICK}="India",I{pbr}-H{pbr},{extra[1:]})', DIFF, bold=True, bg=bg)
        att = (f'"last year\'s attrition "&TEXT({AP_}{r},"0%")&" a month vs Lakshya\'s "&TEXT({AL_}{r},"0%")&" = "'
               f'&TEXT(ABS({AX_}{r}),"#,##0")&IF({AX_}{r}>=0," more"," fewer")&" drivers to replace churn"')
        acq = (f'IF(ISNUMBER({acq_d}),TEXT({acq_d},"+#,##0;-#,##0;0")&" drivers vs Lakshya: ",'
               f'"No Lakshya monthly driver figure by city; ")')
        if key not in ("start",):
            pbr = R_PB_TOT if key == "total" else R_PB0 + key
            # India: driver gap = catch-up (net add) + churn + Diwali re-acquisition, exactly as in 2b
            india_why = (f'TEXT(O{pbr},"+#,##0;-#,##0;0")&" drivers vs Lakshya = "'
                         f'&IF(ABS(G{pbr}-F{pbr})>=0.5,TEXT(G{pbr}-F{pbr},"#,##0;-#,##0")&" catch-up from the 20 Sep actual"&IF(I{pbr}-H{pbr}<0," - "," + "),IF(I{pbr}-H{pbr}<0,"-",""))'
                         f'&TEXT(ABS(I{pbr}-H{pbr}),"#,##0")&" for churn (last year\'s attrition "&TEXT(K{pbr},"0%")&" a month vs Lakshya\'s "&TEXT(J{pbr},"0%")&")"'
                         f'&IF(ABS(L{pbr})>=0.5," + "&TEXT(L{pbr},"#,##0")&" re-acquired after the Diwali dip","")&"."')
        if key == "start":
            why = ('="Lakshya starts from Own Now ~6 Sep and L+DTO 31 Aug; the plan from the "&TEXT('
                   + G_OPEN_DATE + ',"d mmm")&" actual."')
        elif key == "total":
            why = (f'=IF(ABS({onr_d})<0.5,"Same 27 Dec landing. ","Lands "&TEXT({onr_d},"#,##0")&" short (growth held to last year\'s pace). ")'
                   f'&"Over {N_WEEKS} weeks: "&IF({PICK}="India",{india_why},{acq}&{att}&".")')
        else:
            reason = {0: "one week from the 20 Sep actual to catch up",
                      1: "growth held to last year's pace", 2: "Diwali dip + growth held to last year's pace",
                      3: "growth held to last year's pace"}[key]
            tail = {0: '&" + catching up from the 20 Sep actual."', 2: '&" + drivers re-acquired after the Diwali dip."'}.get(key, '&"."')
            why = (f'=IF(ABS({onr_d})<0.5,"",TEXT({onr_d},"#,##0")&" on road ({reason}). ")'
                   f'&IF({PICK}="India",{india_why},{acq}&{att}{tail})')
        c = put(ws, r, column_index_from_string(WHY), why, bg=bg)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(f"{WHY}{r}:{L(column_index_from_string(WHY) + 5)}{r}")
        ws.row_dimensions[r].height = 30
    for _, _, cd in lv:
        red_if(f"{cd}{R_LV0}:{cd}{R_LV_TOT}", f"AND(ISNUMBER({cd}{R_LV0}),{cd}{R_LV0}<-0.5)")
    ws.cell(R_LV_TOT + 1, 1, "Lakshya = Lakshya v4 month-end books (Inputs A3; December = the targets). Lakshya has no monthly EIP, "
                             "so EIP is a straight line to its December target. Lakshya driver acquisition by month exists for India only; "
                             "for a city the total is Lakshya's 14-week figure. Attrition % a month = churn / weeks x 52/12 / average Own Now + L+DTO book: "
                             "Plan = Lakshya's monthly rates shaped by last year's weekly attrition. Lakshya: for India, the churn implied by its own driver numbers (as in 2b); "
                             "for a city, its flat monthly rates (Inputs A2), as Lakshya has no monthly driver numbers by city. Extra drivers = plan churn - Lakshya churn.").font = F_NOTE

    # ---- 2b. driver acquisition bridge, India: driver acquisition = net add of the Own Now + L+DTO book + churn
    # A month | B:C book at start | D:E book at month end | F:G net add | H:I churn | J:K churn % a month |
    # L Diwali re-acquisition | M:N driver acquisition | O plan - Lakshya | P % | Q:V why
    put(ws, R_PB_T, 1, "2b.  WHY DRIVER ACQUISITION DIFFERS  -  INDIA  (driver acquisition = book at month end - book at start + churn)",
        font=F_SECTION).border = Border()
    pb_groups = [("BOOK AT START (Own Now + L+DTO)", 2), ("BOOK AT MONTH END", 4), ("NET ADD", 6),
                 ("CHURN (drivers who leave)", 8), ("CHURN % A MONTH (of the book)", 10), ("DRIVER ACQUISITION", 13)]
    hdr(ws, R_PB_T + 1, 1, "")
    hdr(ws, R_PB_H, 1, "Month")
    for gt, c0 in pb_groups:
        hdr(ws, R_PB_T + 1, c0, gt, GREY_HDR)
        ws.merge_cells(start_row=R_PB_T + 1, start_column=c0, end_row=R_PB_T + 1, end_column=c0 + 1)
        hdr(ws, R_PB_H, c0, "Lakshya")
        hdr(ws, R_PB_H, c0 + 1, "Plan")
    hdr(ws, R_PB_T + 1, 12, "DIWALI", GREY_HDR)
    hdr(ws, R_PB_H, 12, "Plan: re-acquired after the dip")
    hdr(ws, R_PB_T + 1, 15, "PLAN - LAKSHYA", GREY_HDR)
    ws.merge_cells(start_row=R_PB_T + 1, start_column=15, end_row=R_PB_T + 1, end_column=16)
    hdr(ws, R_PB_H, 15, "Driver Acquisition")
    hdr(ws, R_PB_H, 16, "%")
    hdr(ws, R_PB_T + 1, 17, "", GREY_HDR)
    hdr(ws, R_PB_H, 17, "Why")
    ws.merge_cells(start_row=R_PB_T + 1, start_column=17, end_row=R_PB_T + 1, end_column=22)
    ws.merge_cells(start_row=R_PB_H, start_column=17, end_row=R_PB_H, end_column=22)
    ws.row_dimensions[R_PB_T + 1].height = 30
    ws.row_dimensions[R_PB_H].height = 30
    ni = len(CITIES)  # INDIA row of Inputs A3
    SIGNED = "+#,##0;-#,##0;0"
    fmts = {6: DIFF, 7: DIFF, 10: PCT, 11: PCT, 12: DIFF, 15: DIFF, 16: "+0%;-0%;0%"}

    def churn_pct(churn, start, end, weeks):
        """Churn a month as % of the average book: (churn / weeks) x 52/12 / average book."""
        return f"={churn}/{weeks}*{G_WPM}/AVERAGE({start},{end})"

    for m, mon in enumerate(MONTHS):
        r = R_PB0 + m
        put(ws, r, 1, mon, bold=True)
        weeks = f"COUNTIF({_bu(cities[0])},$A{r})"
        lk_end = f"Inputs!${L(6 + m)}${R_MS0 + ni}+Inputs!${L(10 + m)}${R_MS0 + ni}"
        if m == 0:
            # Lakshya's book on the plan's opening date: its path from ~6 Sep (Own Now, 3 weeks) and 31 Aug (L+DTO, 4 weeks)
            own0, ldto0 = sum(LK_OWN_OPEN.values()), sum(LK_LDTO_OPEN.values())
            lk_start = f"={own0}+(Inputs!$F${R_MS0 + ni}-{own0})*2/3+{ldto0}+(Inputs!$J${R_MS0 + ni}-{ldto0})*3/4"
            pl_start = "=" + "+".join(f"{s}!$X${OPEN_ROW}+{s}!$W${OPEN_ROW}" for s in cities)
        else:
            lk_start, pl_start = f"=D{r - 1}", f"=E{r - 1}"
        mref = f"$A{r}"
        vals = [
            (2, lk_start), (3, pl_start), (4, f"={lk_end}"),
            (5, "=" + "+".join(f"{_stock(s, 'X', mref)}+{_stock(s, 'W', mref)}" for s in cities)),
            (6, f"=D{r}-B{r}"), (7, f"=E{r}-C{r}"),
            (8, f"=M{r}-F{r}"),
            (9, "=" + "+".join("+".join(_flow(s, x, mref) for x in ("AK", "AL", "AS")) for s in cities)),
            (10, churn_pct(f"H{r}", f"B{r}", f"D{r}", weeks)), (11, churn_pct(f"I{r}", f"C{r}", f"E{r}", weeks)),
            (12, f"=N{r}-G{r}-I{r}"), (13, lk_pl_mon[mon]),
            (14, "=" + "+".join(_flow(s, "AU", mref) for s in cities)),
            (15, f"=N{r}-M{r}"), (16, f"=N{r}/M{r}-1"),
        ]
        for j, v in vals:
            put(ws, r, j, v, fmts.get(j, NUM), bold=(j in (15, 16)))
        why = (f'=TEXT(O{r},"{SIGNED}")&" = net add "&TEXT(G{r}-F{r},"{SIGNED}")'
               f'&" (plan book "&TEXT(C{r},"#,##0")&" to "&TEXT(E{r},"#,##0")&", Lakshya "&TEXT(B{r},"#,##0")&" to "&TEXT(D{r},"#,##0")&")"'
               f'&" + churn "&TEXT(I{r}-H{r},"{SIGNED}")&" ("&TEXT(K{r},"0%")&" a month vs Lakshya "&TEXT(J{r},"0%")'
               f'&IF(I{r}<H{r},": last year\'s attrition is low this month)",": last year\'s attrition is high this month)")'
               f'&IF(ABS(L{r})>=0.5," + Diwali re-acquisition "&TEXT(L{r},"+#,##0"),"")')
        c = put(ws, r, 17, why)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=17, end_row=r, end_column=22)
        ws.row_dimensions[r].height = 30
    r = R_PB_TOT
    put(ws, r, 1, "Total", bold=True, bg=LIGHT)
    for j in range(2, 17):
        c_ = L(j)
        if j in (2, 3):
            v = f"={c_}{R_PB0}"
        elif j in (4, 5):
            v = f"={c_}{R_PB0 + 3}"
        elif j in (10, 11):  # over the 14 weeks
            ch, st, en = (("H", "B", "D") if j == 10 else ("I", "C", "E"))
            v = churn_pct(f"{ch}{r}", f"{st}{r}", f"{en}{r}", N_WEEKS)
        elif j == 16:
            v = f"=N{r}/M{r}-1"
        else:
            v = f"=SUM({c_}{R_PB0}:{c_}{R_PB0 + 3})"
        put(ws, r, j, v, fmts.get(j, NUM), bold=True, bg=LIGHT)
    c = put(ws, r, 17, (f'=TEXT(O{r},"{SIGNED}")&" = September catch-up from the 20 Sep actual "&TEXT(G{r}-F{r},"{SIGNED}")'
                        f'&" + churn shaped by last year "&TEXT(I{r}-H{r},"{SIGNED}")&" + Diwali re-acquisition "&TEXT(L{r},"{SIGNED}")'),
            bold=True, bg=LIGHT)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=r, start_column=17, end_row=r, end_column=22)
    ws.row_dimensions[r].height = 30
    red_if(f"O{R_PB0}:O{R_PB_TOT}", f"O{R_PB0}<-0.5")
    ws.cell(R_PB_TOT + 1, 1, "Churn % a month = churn / weeks x 52/12 / average book (Own Now + L+DTO). Lakshya churn = its driver acquisition - its net add "
                             "(a flat rate every week); plan churn = the same monthly rates shaped by last year's weekly attrition (city tabs AK, AL, AS). "
                             "Lakshya's Sep start = its path on the opening date. Diwali: the two dip weeks plan no driver acquisition; drivers for the cars lost are acquired again after.").font = F_NOTE


    # ---- 3. insights (live, all India): read from section 2b, the Inputs C1 summary and the city tabs
    put(ws, R_IN_T, 1, "3.  INSIGHTS  -  India and cities (live; update with the plan)", font=F_SECTION).border = Border()
    ri = R_SUM0 + len(CITIES)                      # INDIA row of Inputs C1
    c1 = lambda col, r=ri: f"Inputs!${col}${r}"    # Inputs C1: B start, C 27 Dec, D target, I fleet, J Lakshya fleet,
    c1r = lambda col: f"Inputs!${col}${R_SUM0}:${col}${ri - 1}"  # M util, N max, O headroom, S driver acquisition
    SIGNED = "+#,##0;-#,##0;0"
    wk = [f'COUNTIF({_bu(cities[0])},"{mon}")' for mon in MONTHS]
    pb = lambda col, m: f"{col}{R_PB0 + m}"      # section 2b, month m
    pbt = lambda col: f"{col}{R_PB_TOT}"         # section 2b, total
    newc = "(" + "+".join(f"SUM({s}!$BJ${FIRST}:$BJ${LAST})" for s in cities) + ")"
    dip = "+".join(f"SUM({s}!$BS${FIRST}:$BS${LAST})" for s in cities)
    capped = "+".join(stretch_count(f"{s}!$BP${FIRST}:$BP${LAST}") for s in cities)
    top_org = "MAX(" + ",".join(f"{s}!$BO${FIRST}:$BO${LAST}" for s in cities) + ")"
    growth = f"({c1r('C')}-{c1r('B')})"
    above = "&".join(f'IF({c1("O", R_SUM0 + i)}<0,"{CITIES[i]} "&TEXT({c1("M", R_SUM0 + i)},"0.0%")&" vs max "&TEXT({c1("N", R_SUM0 + i)},"0.0%")&", ","")'
                     for i in range(len(CITIES)))
    per_week = lambda col, fmt: ", ".join(f'{MONTHS[m]} "&TEXT({pb(col, m)}/{wk[m]},"{fmt}")&"' for m in range(4))
    me_gap = ", ".join(f'{MONTHS[m]} "&TEXT({pb("E", m)}-{pb("D", m)},"{SIGNED}")&"' for m in range(4))
    me_short = "+".join(f"(ABS({pb('E', m)}-{pb('D', m)})>=0.5)" for m in range(4))
    ins = [
        f'="India: "&TEXT({c1("B")},"#,##0")&" cars on road at the start, "&TEXT({c1("C")},"#,##0")&" on 27 Dec ("&TEXT({c1("C")}-{c1("B")},"+#,##0")&", "&TEXT({c1("C")}/{c1("B")}-1,"+0%")&"). '
        f'Lakshya: "&TEXT({c1("D")},"#,##0")&IF(ABS({c1("C")}-{c1("D")})<0.5," - the plan lands on it."," - gap "&TEXT({c1("C")}-{c1("D")},"#,##0")&".")',
        f'="Where the growth comes from: "&TEXT({newc},"#,##0")&" new cars put on road ("&TEXT({newc}/({c1("C")}-{c1("B")}),"0%")&") and "&TEXT({c1("C")}-{c1("B")}-{newc},"#,##0")'
        f'&" organic growth from recruitment net of churn ("&TEXT(1-{newc}/({c1("C")}-{c1("B")}),"0%")&")."',
        f'="Own Now + L+DTO book growth per week: {per_week("G", SIGNED)}. The two Diwali weeks (w/c 2 and 9 Nov) take "&TEXT(ABS({dip}),"#,##0")&" cars off the road; new cars that arrive then go on road from w/c 16 Nov."',
        f'="Driver acquisition: "&TEXT({pbt("N")},"#,##0")&" in {N_WEEKS} weeks ("&TEXT({pbt("N")}/{N_WEEKS},"#,##0")&" a week). Per week by month: {per_week("N", "#,##0")}."',
        f'="Churn: "&TEXT({pbt("I")},"#,##0")&" drivers leave ("&TEXT({pbt("K")},"0%")&" of the book a month), so "&TEXT({pbt("I")}/{pbt("N")},"0%")&" of driver acquisition only replaces churn and "&TEXT(1-{pbt("I")}/{pbt("N")},"0%")&" adds to the road."',
        ("ARRAY", f'="Most growth: "&INDEX({c1r("A")},MATCH(MAX({growth}),{growth},0))&" ("&TEXT(MAX({growth}),"+#,##0")&"). Least: "&INDEX({c1r("A")},MATCH(MIN({growth}),{growth},0))&" ("&TEXT(MIN({growth}),"{SIGNED}")&"). '
                  f'Most recruitment: "&INDEX({c1r("A")},MATCH(MAX({c1r("S")}),{c1r("S")},0))&" ("&TEXT(MAX({c1r("S")}),"#,##0")&" driver acquisitions, "&TEXT(MAX({c1r("S")})/{N_WEEKS},"#,##0")&" a week)."'),
        f'="Own Now + L+DTO book vs Lakshya at each month-end: {me_gap}"&IF(({me_short})=0," - on Lakshya every month."," - section 2 shows why.")',
        f'=IF(({above})="","No city ends above its max utilisation.","Above max utilisation on 27 Dec: "&LEFT({above},LEN({above})-2)&" - these need more fleet or fewer cars sold.")',
        f'="Lakshya vs our plan: "&IF(ABS({c1("C")}-{c1("D")})<0.5,"both land on "&TEXT({c1("D")},"#,##0"),"the plan lands on "&TEXT({c1("C")},"#,##0")&" vs Lakshya\'s "&TEXT({c1("D")},"#,##0"))&" on 27 Dec. '
        f'It needs "&TEXT({pbt("N")},"#,##0")&" driver acquisitions vs Lakshya\'s "&TEXT({pbt("M")},"#,##0")&" ("&TEXT({pbt("O")},"{SIGNED}")&"); fleet on 27 Dec "&TEXT({c1("I")}-{c1("J")},"{SIGNED}")&" vs Lakshya."',
        f'=IF({G_CAP}="No","Stretch vs last year: "&({capped})&" of {len(CITIES) * N_WEEKS} city-weeks need more organic growth than the city\'s best 4-week pace of 2024/25 (red in city tab column BP) - the price of matching Lakshya at every month-end. Biggest single city-week: "&TEXT({top_org},"0.0%")&" organic growth.",'
        f'"Realism: "&({capped})&" of {len(CITIES) * N_WEEKS} city-weeks are held to last year\'s pace, so no week plans more organic growth than 2024/25 showed (Diwali_Dip Analysis tab).")',
    ]
    for k, f in enumerate(ins):
        r = R_IN_T + 1 + k
        if isinstance(f, tuple):  # needs array evaluation (MAX over a difference of two ranges)
            c = put(ws, r, 1, None)
            c.value = ArrayFormula(f"A{r}", f[1])
        else:
            c = put(ws, r, 1, f)
        c.border = Border()
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=22)
        ws.row_dimensions[r].height = 18
    ws.freeze_panes = "B4"
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
    build_dip(wb)
    for i, city in enumerate(CITIES):
        build_city(wb, i, city)
    build_compare(wb)
    build_summary(wb)
    build_dashboard(wb)
    build_combined(wb)
    build_readme(wb)
    build_raw(wb, raw)
    wb.save(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
