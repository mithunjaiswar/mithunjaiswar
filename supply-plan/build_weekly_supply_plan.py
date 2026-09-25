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
R_PACE_H = R_SEAS1 + 6  # proven pace table header
R_PACE0 = R_PACE_H + 1
R_DIP_H = R_PACE0 + 13  # Diwali dip table header
R_DIP0 = R_DIP_H + 1
R_DIPC_H = R_DIP0 + 14  # cars on road around Diwali, header
R_DIPC0 = R_DIPC_H + 1
R_MS_H = R_DIPC0 + 13   # Lakshya month-end targets header
R_MS0 = R_MS_H + 1
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
    ("AM", "Own Now placements", 9), ("AN", "of which new cars", 8),
    ("AO", "of which existing cars", 8),
    ("AP", "L+DTO book - WB", 8), ("AQ", "L+DTO need this week (to Lakshya month-end)", 9), ("AR", "L+DTO net add", 8),
    ("AS", "L+DTO churn (LY-shaped)", 8), ("AT", "L+DTO placements", 9),
    ("AU", "Total placements (Own Now + L+DTO)", 10), ("AV", "Check: on road = EIP + L+DTO + Own Now", 9),
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
    ("BR", "Diwali dip % (2024/25 avg, Inputs s.9)", 9), ("BS", "Diwali dip (cars)", 8),
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
            "BH": f"=INDEX(Inputs!$B${R_PACE0 + idx}:$D${R_PACE0 + idx},MATCH(AF{r},Inputs!$B${R_PACE_H}:$D${R_PACE_H},0))",
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
            "BR": f'=IF(AF{r}="Diwali",IFERROR(INDEX(Inputs!$B${R_DIP0 + idx}:$C${R_DIP0 + idx},MATCH(Inputs!$O${cal},Inputs!$B${R_DIP_H}:$C${R_DIP_H},0)),0),0)',
            "BS": f"=G{r}*BR{r}",
            "BT": (f"=SUM($AD${FIRST}:$AD${LAST - 1})" if w == 0 else f"=SUM($AD${FIRST}:$AD${LAST - 1})-SUM($BJ${FIRST}:BJ{p})"),
            # Lakshya month-end targets (Inputs, section 10)
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
    cput(ws, r, "BP", f'=COUNTIF(BP{FIRST}:BP{LAST},"Capped at LY pace")&" weeks capped at LY pace"', bold=True, bg=LIGHT)
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
        "LAST YEAR (AY:BD): same week last year (week start - 364 days) from raw_performance. LY net attrition % = (attrition + temp attrition - rejoins - temp rejoins) / (active partners at week start + new joins + resurrections), as in the Weekly Supply Plan. LY attrition index = that week's LY % / the average over the 14 plan weeks.",
        "SEASONALITY (BE:BF): festival impact on recruitment for the event in that week (Inputs, sections 6-7); seasonality factor = 1 + impact, floored. Weeks with no festival have a factor of 1.",
        "REALISM (BH:BQ): new cars bought last week go straight on road (BJ). The rest of the gap to the next Lakshya month-end (BU:BY - Lakshya's Own Now and L+DTO books on 27 Sep, 25 Oct, 29 Nov, 27 Dec), after the new cars due before it, is spread over the weeks left in that month by seasonality factor (BL) - but a week never gets more organic growth than cars on road x the city's best 4-week weekly pace in the same season of 2024/25 (BH, BI). Planned add BM = BJ + MIN(BL, BI). BP says 'Capped at LY pace' when the week needed more than that.",
        "LAYERS: each layer is planned to its own Lakshya month-end (AI Own Now need, AQ L+DTO need, CA EIP need). If the pace cap or new cars move the total away from the sum of the needs, the difference (CB) is shared over the layers with a positive need; L+DTO takes the Diwali dip and wins it back afterwards. Churn (AK, AS) = last week's book x Lakshya monthly rate / 4.33 x LY attrition index (BD). Placements (AM, AT) = net add + churn (+ rollover for Own Now).",
        "Recruitment by channel (N:Q) = total placements (AU) x the city's channel mix on the Inputs tab. Net Attrition (W) = net adds - placements: Own Now churn + rollover + L+DTO churn, plus any extra exits in the Diwali weeks when the dip is bigger than normal churn.",
        "Fleet (E) = previous week + Total buy (G) - Total sold (H); each month's cars are split evenly across that month's weeks (Inputs, sections 4 and 5). Buy and sold are blank in actual weeks: raw_performance has fleet only. Util (AB) = week-ending cars on road / fleet; red when above the Lakshya ceiling (AC).",
        "DIWALI (BR:BT): in the two Diwali weeks cars on road follow the city's average dip of 2024 and 2025 (Inputs, section 9) instead of growing; the dip is taken from the Leasing + DTO book. New cars that arrive in those weeks wait and go on road in the recovery week (BJ). The weeks before and after are asked to make up the dip, within last year's pace.",
        "If the proven pace cannot carry the city to its Lakshya number, the plan lands short and BQ shows the gap still open on 27 Dec. Nothing forces a spike in the last weeks. Check column AV must be 0.",
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
    ws.conditional_formatting.add(f"BP{FIRST}:BP{LAST}", FormulaRule(formula=[f'BP{FIRST}="Capped at LY pace"'], font=red,
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
        ("Hold weekly growth to last year's pace?", "Yes", None, True,
         "Yes = realistic plan (section 8 caps each week). No = every week takes what Lakshya's month-end needs, even above last year's pace (the Diwali dip still applies)."),
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
        r = R_GLOBAL + 8 + k
        put(ws, r, 1, label, bold=True)
        put(ws, r, 2, link(url, text), font=F_LINK)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)

    # ---- 2. summary
    ws.cell(R_SUM_H - 1, 1, "2.  PLAN SUMMARY - OUTPUT, DO NOT EDIT  (pulled from the city tabs)").font = F_SECTION
    sum_cols = ["City", "On road 20 Sep", "On road 27 Dec", "Lakshya target", "Gap to target",
                "EIP 27 Dec", "Own Now 27 Dec", "L+DTO 27 Dec", "Fleet 27 Dec", "Lakshya fleet Dec",
                "Util 27 Dec", "Ceiling", "Headroom", "EIP net add", "Own Now placements",
                "L+DTO placements", "Total placements", "Peak week placements", "Check (0 = OK)",
                "Weeks capped at LY pace", "Top weekly growth %"]
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
            (f'=COUNTIF({s}!BP{FIRST}:BP{LAST},"Capped at LY pace")', "0"),
            (f"=MAX({s}!BN{FIRST}:BN{LAST})", "0.0%"),
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
        elif L == "U":
            v, fmt = f"=MAX(U{R_SUM0}:U{r - 1})", "0.0%"
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
    def month_table(r_h, title, data, lakshya, note, cap_col=False):
        ws.cell(r_h - 1, 1, title).font = F_SECTION
        hdr(ws, r_h, 1, "City")
        for m in range(4):
            c = hdr(ws, r_h, 2 + m, dt.date(2026, 9 + m, 1))
            c.number_format = "mmm-yy"
        for j, t in enumerate(["Total", "Lakshya Sep-Dec", "Difference"], start=6):
            hdr(ws, r_h, j, t)
        if cap_col:
            hdr(ws, r_h, 9, "Most new cars on road in one week")
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
        put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
        for j in range(2, 9):
            L = get_column_letter(j)
            put(ws, r, j, f"=SUM({L}{r_h + 1}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)
        ws.cell(r + 1, 1, note).font = F_NOTE
        ws.conditional_formatting.add(f"H{r_h + 1}:H{r}", FormulaRule(formula=[f"H{r_h + 1}<>0"], font=red))

    month_table(R_ADD_H, "4.  NEW CARS ADDED TO FLEET, BY MONTH  (Sep = 21-30 Sep only)", ADDS, LAKSHYA_ADDS,
                "Lakshya: 2,300 cars (WagonR 1,200, Dzire 600, Rumion 500), all landed by 30 Nov. Default phasing 50% Oct / 50% Nov - change to the delivery schedule. Each month's cars are split evenly across that month's weeks. "
                "New cars go on road the week after they land, at most column I a week (1.5 x normal arrivals), so cars held back over Diwali are placed over the following weeks.", cap_col=True)
    month_table(R_SALE_H, "5.  CARS SOLD, BY MONTH  (Sep = 21-30 Sep only)", SALES, LAKSHYA_SALES,
                "Lakshya: 721 cars (AOP 1,776). Sales come out of idle cars, so they change utilisation, not cars on road. Default phasing: even Oct-Dec. Any sold between 1 and 20 Sep are already in the opening fleet - reduce these rows by them.")

    # ---- 6. calendar
    ws.cell(R_CAL_H - 1, 1, "6.  WEEKLY CALENDAR AND PHASING  -  weeks run Mon-Sun; a week counts in the month its Monday falls in").font = F_SECTION
    cal_heads = ["Week #", "Week start (Mon)", "Week end", "Month", "Days in plan", "Season (section 8)"] + [
        f"Events - {c}" for c in CITIES] + ["Event used for impact (section 7)", "Diwali week (section 9)",
                                             "New cars go on road this week?", "Lakshya month-end it counts to (section 10)"]
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
        inp(ws, r, 6, WEEK_SEASON[w])
        for k, city in enumerate(CITIES):
            parts = [x for x in (EVENTS_ALL.get(w + 1), EVENTS_CITY.get((city, w + 1))) if x]
            inp(ws, r, 7 + k, "; ".join(parts) if parts else "")
        inp(ws, r, 14, WEEK_EVENT.get(w + 1, ""))
        inp(ws, r, 15, DIWALI_WEEK.get(w + 1, ""))
        inp(ws, r, 16, "No" if WEEK_SEASON[w] == "Diwali" else "Yes")
        inp(ws, r, 17, WEEK_MONTH[w])
    r = R_CAL0 + N_WEEKS
    put(ws, r, 1, "Total", bold=True, bg=LIGHT)
    for j in (2, 3, 4):
        put(ws, r, j, None, bg=LIGHT)
    put(ws, r, 5, f"=SUM(E{R_CAL0}:E{r - 1})", "0", bold=True, bg=LIGHT)
    put(ws, r, 6, None, bg=LIGHT)
    notes = [
        "Season decides which proven weekly pace (section 8) caps the week: Pre-Diwali = w/c 21 Sep - 26 Oct, Diwali = w/c 2 and 9 Nov (Diwali Sun 8 Nov), Post-Diwali = w/c 16 Nov - 21 Dec.",
        "Event used for impact: the festival whose recruitment impact (section 7) shapes that week. Weeks with no event get a seasonality factor of 1.",
        "Diwali week: which historical Diwali dip (section 9) applies. New cars go on road this week? 'No' holds the week's new cars back; they go on road in the next 'Yes' week.",
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
        "then seasonality factor = 1 + impact, floored at the global setting. The factor shapes how much of the remaining gap a week is asked to close.",
        "Kannada Rajyotsava is a Bangalore-only holiday (0 elsewhere). The Hyderabad and Kolkata civic elections have no measured impact.",
    ]):
        ws.cell(r + k, 1, t).font = F_NOTE

    # ---- 8. proven weekly pace
    ws.cell(R_PACE_H - 1, 1, "8.  PROVEN WEEKLY PACE - the most a city's cars on road has grown per week, sustained over 4 weeks, in the same season of 2024 or 2025").font = F_SECTION
    for j, t in enumerate(["City"] + SEASONS + ["2024 Pre", "2024 Diwali", "2024 Post", "2025 Pre", "2025 Diwali", "2025 Post"], start=1):
        hdr(ws, R_PACE_H, j, t, NAVY if j <= 4 else GREY_HDR)
    for i, city in enumerate(CITIES + ["INDIA (reference)"]):
        r = R_PACE0 + i
        key = city if city in PACE else "INDIA"
        put(ws, r, 1, city, bold=True)
        vals = PACE.get(city, PACE_INDIA)
        for k in range(3):
            (inp if city in PACE else put)(ws, r, 2 + k, vals[k], "0.0%")
        for y in range(2):
            for k in range(3):
                put(ws, r, 5 + 3 * y + k, PACE_HIST[key][y][k], "0.0%", font=F_NOTE)
    r = R_PACE0 + len(CITIES) + 1
    for k, t in enumerate([
        "Cap used on the city tabs (columns B:D, editable) = the higher of 2024 and 2025 for that season, floored at 0% (where even the best stretch shrank, the week is planned flat, not down).",
        "Measured on allotted_cars_eod each Sunday, CNG, with one-off data glitches removed. Pre-Diwali = mid-Sep to Diwali, Diwali = Diwali week + next 2, Post-Diwali = late Nov to early Jan.",
        "New cars bought are added on top of this organic pace in the week after they arrive (city tab column BJ): they are extra supply last year did not have.",
        "The Diwali column is kept for reference only: the two Diwali weeks follow the historical dip in section 9, not a pace cap.",
    ]):
        ws.cell(r + k, 1, t).font = F_NOTE

    # ---- 9. Diwali dip
    ws.cell(R_DIP_H - 1, 1, "9.  DIWALI DIP - change in cars on road in the Diwali weeks of 2024 and 2025 (used for w/c 2 and 9 Nov 2026)").font = F_SECTION
    heads = ["City", "Run-up week", "Diwali week", "Two weeks together", "Recovery week (info)",
             "2024 run-up", "2024 Diwali", "2024 recovery", "2025 run-up", "2025 Diwali", "2025 recovery"]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_DIP_H, j, t, NAVY if j <= 5 else GREY_HDR)
    cc = R_DIPC0  # cars table rows, same city order
    for i, city in enumerate(CITIES + ["INDIA (reference)"]):
        r = R_DIP0 + i
        put(ws, r, 1, city, bold=True)
        cr = cc + i
        # history from the cars table below: (run-up, Diwali, recovery) = weeks 2/1, 3/2, 4/3 of each year
        hist = [f"=C{cr}/B{cr}-1", f"=D{cr}/C{cr}-1", f"=E{cr}/D{cr}-1",
                f"=G{cr}/F{cr}-1", f"=H{cr}/G{cr}-1", f"=I{cr}/H{cr}-1"]
        for k, f in enumerate(hist):
            put(ws, r, 6 + k, f, "0.0%", font=F_NOTE)
        avg_ru, avg_dw = f"=AVERAGE(F{r},I{r})", f"=AVERAGE(G{r},J{r})"
        if city in CITIES:
            # typed as the formula so it stays live; overwrite with a number to override
            put(ws, r, 2, avg_ru, "0.0%", font=F_INPUT, bg=INPUT)
            put(ws, r, 3, avg_dw, "0.0%", font=F_INPUT, bg=INPUT)
        else:
            put(ws, r, 2, avg_ru, "0.0%")
            put(ws, r, 3, avg_dw, "0.0%")
        put(ws, r, 4, f"=(1+B{r})*(1+C{r})-1", "0.0%", bold=True)
        put(ws, r, 5, f"=AVERAGE(H{r},K{r})", "0.0%")
    r = R_DIP0 + len(CITIES) + 1
    for k, t in enumerate([
        "Run-up week = the week before the week with Bhai Dooj; Diwali week = the week with Bhai Dooj; recovery = the week after. "
        "2024 (Diwali Fri 1 Nov): w/e 27 Oct, 3 Nov, 10 Nov. 2025 (Diwali Mon 20 Oct): w/e 19 Oct, 26 Oct, 2 Nov. 2026 (Diwali Sun 8 Nov): w/c 2 Nov, 9 Nov, 16 Nov.",
        "Columns B:C (the average of the two years) are what the city tabs use for the two Diwali weeks; type a number over them to override. The recovery week is not forced: it follows the post-Diwali pace.",
    ]):
        ws.cell(r + k, 1, t).font = F_NOTE
    ws.cell(R_DIPC_H - 1, 1, "Cars on road on the Sundays around Diwali (allotted_cars_eod, CNG)").font = F_SECTION
    heads = ["City"] + [f"{d}" for d in DIWALI_SUNDAYS[0]] + [f"{d}" for d in DIWALI_SUNDAYS[1]]
    for j, t in enumerate(heads, start=1):
        hdr(ws, R_DIPC_H, j, t, GREY_HDR)
    for i, city in enumerate(CITIES):
        r = R_DIPC0 + i
        put(ws, r, 1, city, bold=True)
        for y in range(2):
            for k in range(4):
                put(ws, r, 2 + 4 * y + k, DIWALI_CARS[city][y][k], NUM)
    r = R_DIPC0 + len(CITIES)
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in range(2, 10):
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{R_DIPC0}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)

    # ---- 10. Lakshya month-end targets
    ws.cell(R_MS_H - 2, 1, "10.  LAKSHYA MONTH-END TARGETS - the books each plan week works towards (Lakshya months end on Sundays: 27 Sep, 25 Oct, 29 Nov, 27 Dec)").font = F_SECTION
    groups = [(2, 5, "EIP (not monthly in Lakshya - straight line)"), (6, 9, "OWN NOW - Lakshya v4"),
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
            # EIP: straight line from the 20 Sep opening to the December target
            put(ws, r, 2 + m, f"={ci('eip', i)}+({ci('t_eip', i)}-{ci('eip', i)})*{MS_WEEKS[m]}/{N_WEEKS}", NUM)
            if m < 3:
                inp(ws, r, 6 + m, LK_OWN_ME[city][m], NUM)
                inp(ws, r, 10 + m, LK_LDTO_ME[city][m], NUM)
            else:  # December = the Lakshya December target in section 3
                put(ws, r, 6 + m, f"={ci('t_own', i)}", NUM)
                put(ws, r, 10 + m, f"={ci('t_ldto', i)}", NUM)
            L = [get_column_letter(2 + m), get_column_letter(6 + m), get_column_letter(10 + m)]
            put(ws, r, 14 + m, f"={L[0]}{r}+{L[1]}{r}+{L[2]}{r}", NUM, bold=True)
    r = R_MS0 + len(CITIES)
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in range(2, 18):
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{R_MS0}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)
    for k, t in enumerate([
        "Own Now and L+DTO for Sep-Nov are Lakshya v4's month-end books (Weekly Own Now and Weekly L+DTO tabs, monthly reconciliation); December is the target in section 3. "
        "Each plan week is asked for its share of the gap to the month-end it counts to (section 6, last column), within last year's pace and the Diwali dip.",
        "Where a month-end cannot be reached within the pace (e.g. September: one week from 20 Sep), the shortfall rolls into the next month. The Lakshya vs Plan tab, section 5, shows each month-end side by side.",
    ]):
        ws.cell(r + 1 + k, 1, t).font = F_NOTE
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
         "The weekly plan never grows a city faster than its best 4-week pace of 2024/25 (plus new cars). Where that pace cannot reach the Lakshya number, it lands short - see Read Me."),
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
    ws.cell(r + 1, 1, "Each plan week works towards Lakshya's next month-end book (Inputs, section 10). September has only one plan week (from the 20 Sep actual), "
                      "so it cannot close; later months miss only where last year's pace or the Diwali dip does not allow it. City detail below.").font = F_NOTE

    # ---- 5b. month-end by city
    r += 4
    section(r, "5b.  MONTH-END BY CITY - Lakshya's Own Now and Leasing + DTO books vs the plan")
    r += 1
    heads = [("City", NAVY), ("Month-end", NAVY), ("Own Now - Lakshya", GREY_HDR), ("Own Now - plan", NAVY), ("Difference", NAVY),
             ("L+DTO - Lakshya", GREY_HDR), ("L+DTO - plan", NAVY), ("Difference", NAVY), ("Status", NAVY),
             ("Why", NAVY)]
    for j, (t, col) in enumerate(heads, start=1):
        hdr(ws, r, j, t, col)
    ws.row_dimensions[r].height = 32
    first = r + 1
    b_rows = {}
    dates = [dt.date(2026, 9, 27), dt.date(2026, 10, 25), dt.date(2026, 11, 29), dt.date(2026, 12, 27)]
    for i, city in enumerate(CITIES):
        s_ = q(city)
        for m, (d, wrow) in enumerate(zip(dates, ME_WEEK_ROWS)):
            r += 1
            put(ws, r, 1, city if m == 0 else "", bold=True)
            put(ws, r, 2, d, "dd-mmm")
            put(ws, r, 3, f"=Inputs!{get_column_letter(6 + m)}{R_MS0 + i}", NUM)
            put(ws, r, 4, f"={s_}!X{wrow}", NUM)
            put(ws, r, 5, f"=D{r}-C{r}", NUM)
            put(ws, r, 6, f"=Inputs!{get_column_letter(10 + m)}{R_MS0 + i}", NUM)
            put(ws, r, 7, f"={s_}!W{wrow}", NUM)
            put(ws, r, 8, f"=G{r}-F{r}", NUM)
            put(ws, r, 9, f'=IF(AND(ABS(E{r})<0.5,ABS(H{r})<0.5),"Match","Differs")')
            b_rows[(i, m)] = r
            mon = MONTHS[m]
            bu, bp, af = (f"{s_}!$BU${FIRST}:$BU${LAST}", f"{s_}!$BP${FIRST}:$BP${LAST}", f"{s_}!$AF${FIRST}:$AF${LAST}")
            pace = f"Inputs!$B${R_PACE0 + i}" if m < 2 else f"Inputs!$D${R_PACE0 + i}"
            weeks = f'COUNTIFS({bu},"{mon}",{af},"<>Diwali")'
            capped = f'COUNTIFS({bu},"{mon}",{bp},"Capped at LY pace")'
            if m == 0:
                reason = '"only 1 week after the 20 Sep actual"'
            else:
                reason = f'"growth held to last year\'s pace ("&TEXT({pace},"0.0%")&"/wk)"'
                if m == 2:
                    reason += f'&" + Diwali dip "&TEXT(Inputs!$D${R_DIP0 + i},"0%")'
            why = (f'=IF(I{r}="Match","",IF(E{r}+H{r}>0,"Above Lakshya by "&TEXT(E{r}+H{r},"#,##0"),'
                   f'TEXT(-(E{r}+H{r}),"#,##0")&" short - "&{reason}))')
            put(ws, r, 10, why)
    status_rules(f"I{first}:I{r}", f"I{first}")
    # India reasons in section 5: which cities are short at each month-end
    for m, r5 in enumerate(s5_rows):
        terms = "&".join(f'IF(ABS(E{b_rows[(i, m)]}+H{b_rows[(i, m)]})>=0.5,"{c} "&TEXT(E{b_rows[(i, m)]}+H{b_rows[(i, m)]},"+#,##0;-#,##0")&"  ","")'
                         for i, c in enumerate(CITIES))
        lead = ['"Only 1 week after the 20 Sep actual. "', '"Growth held to last year\'s pace. "',
                '"Diwali dip + last year\'s pace. "', '""'][m]
        put(ws, r5, 9, f'=IF(H{r5}="Match","",{lead}&"Short: "&{terms})', font=F_NOTE)
    ws.cell(r + 1, 1, "Differs in September: one week from the 20 Sep actual. Differs later: the city's proven pace (Inputs, section 8) or the Diwali dip (section 9) "
                      "stops it closing the gap that month - the city tab column BP shows 'Capped at LY pace' in those weeks. Every city matches in December. "
                      "To see the plan fill every month-end regardless, set Inputs 'Hold weekly growth to last year's pace?' to No.").font = F_NOTE

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

    r = para(5, "1.  THE RULE THAT KEEPS THE PLAN REALISTIC", [
        "New cars go on road the week after they arrive (2,300 cars, Oct-Nov, Inputs section 4) - supply we did not have last year. Everything else is organic growth from recruitment net of churn.",
        "Organic growth: each week is asked for its share of the gap to Lakshya's next month-end (Own Now and L+DTO books on 27 Sep, 25 Oct, 29 Nov, 27 Dec - Inputs, section 10), after the new cars due in that month, less in festival weeks. "
        "It is never allowed above the city's proven pace - its best 4-week average weekly growth in the same season of 2024 or 2025 (Inputs, section 8). If a week needs more, it is capped and the rest rolls into the next month; "
        "if the gap cannot close by 27 Dec, the city lands short. Nothing forces a jump in the last weeks. Month-end by city vs Lakshya: Lakshya vs Plan tab, section 5b.",
        "So the plan never assumes organic growth that last year did not show. The two Diwali weeks follow the dip seen in 2024 and 2025 instead of growing (section 4). "
        "City tab column BP marks each week 'Yes', 'Capped at LY pace' or 'Diwali dip', and the Summary View shows week-on-week growth next to the same week last year.",
    ])

    # ---- 2. the bridge
    ws.cell(r, 1, "2.  THE BRIDGE - from 20 Sep to 27 Dec, by season").font = F_SECTION
    r += 1
    heads = ["City", "On road 20 Sep", "Pre-Diwali organic (w/c 21 Sep-26 Oct)", "Diwali organic (w/c 2-9 Nov)",
             "Post-Diwali organic (w/c 16 Nov-21 Dec)", "New cars put on road", "On road 27 Dec (plan)",
             "Lakshya target", "Short of Lakshya", "Weeks capped at LY pace"]
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
        put(ws, r, 10, f'=COUNTIF({rng(s, "BP")},"Capped at LY pace")', "0")
    r += 1
    put(ws, r, 1, "INDIA", bold=True, bg=LIGHT)
    for j in range(2, 11):
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{first}:{L}{r - 1})", NUM, bold=True, bg=LIGHT)
    red = Font(name="Calibri", size=10, bold=True, color="FFC00000")
    ws.conditional_formatting.add(f"I{first}:I{r}", FormulaRule(formula=[f"I{first}>0.5"], font=red, fill=fill("FFFFC7CE")))
    r += 1
    ws.cell(r, 1, "Organic = growth from recruitment net of churn, within the proven pace. On road 27 Dec = on road 20 Sep + the three organic columns + new cars. "
                  "Short of Lakshya > 0 means last year's pace cannot carry the city all the way: that gap needs something last year did not have (more cars earlier, more EIP, lower churn). "
                  "New cars: 2,300 over nine weeks is 250-290 a week going on road - confirm deliveries and onboarding; if a delivery slips, change Inputs section 4 and the plan re-spreads.").font = F_NOTE
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
        put(ws, r, 6, f"=INDEX(Inputs!$B${R_PACE0 + len(CITIES)}:$D${R_PACE0 + len(CITIES)},MATCH(B{r},Inputs!$B${R_PACE_H}:$D${R_PACE_H},0))", "0.0%")
        put(ws, r, 7, (f'=IFERROR(SUMIFS(raw_performance!${rc("allotted_cars_eod")}:${rc("allotted_cars_eod")},raw_performance!$E:$E,"CNG",raw_performance!$C:$C,A{r}-364+6)'
                       f'/SUMIFS(raw_performance!${rc("allotted_cars_eod")}:${rc("allotted_cars_eod")},raw_performance!$E:$E,"CNG",raw_performance!$C:$C,A{r}-364-1)-1,"")'), "0.0%")
        put(ws, r, 8, f"={allc('Y')}", NUM)
        put(ws, r, 9, f"={allc('BJ')}", NUM)
    ws.conditional_formatting.add(f"E{wfirst}:E{r}", FormulaRule(formula=[f"E{wfirst}>F{wfirst}+0.0005"], font=red, fill=fill("FFFFC7CE")))
    r += 1
    ws.cell(r, 1, "Organic growth above the India proven pace (red) can happen when cities peak in the same week; each city on its own stays within its own pace. "
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
        put(ws, r, 2, f"=(1+Inputs!F{d})*(1+Inputs!G{d})-1", "0.0%")
        put(ws, r, 3, f"=(1+Inputs!I{d})*(1+Inputs!J{d})-1", "0.0%")
        put(ws, r, 4, f"=Inputs!D{d}", "0.0%", bold=True)
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
        put(ws, r, 8, f"=Inputs!E{d}", "0.0%", bg=LIGHT if city == "INDIA" else None)
    r += 1
    ws.cell(r, 1, "The plan's two Diwali weeks now fall by each city's two-year average dip (Inputs, section 9) - India about -9%, as in 2024 (-9.8%) and 2025 (-8.5%). "
                  "New cars that arrive in those weeks wait, then go on road from the recovery week at up to 1.5x the normal weekly rate (Inputs, section 4), so the recovery week is also lifted by new cars. "
                  "The Summary View shows the same weeks against last year's week of the same date (Diwali 2025 fell three weeks earlier).").font = F_NOTE
    r += 3

    r = para(r, "5.  WHERE THE PLAN DROPS, WHERE IT GAINS, AND THE WEEKS IN BETWEEN", [
        "PRE-DIWALI (w/c 21 Sep - 26 Oct): last year cars on road fell in these weeks (India -0.1% at best, weeks of -2.6% to -5.4%); in 2024 the best was +1.5% a week. The plan allows each city its better of the two years "
        "and adds the October new cars the week after they land. Last year's attrition peaks here (LY attrition index up to 1.2-1.4), so more placements are needed just to hold the book.",
        "DIWALI (w/c 2 and 9 Nov): cars on road fell in these weeks in both years - India -9.8% in 2024 and -8.5% in 2025 over the two weeks (drivers go home; recruitment stops). "
        "The plan now falls by each city's two-year average (section 4 above; Inputs section 9), all of it from the Leasing + DTO book, and holds new cars back until the recovery week. This is where the plan dips.",
        "POST-DIWALI (w/c 16 Nov - 21 Dec): the season where we have shown real recovery - India +2.7% to +2.9% a week at best, Mumbai and Pune above 5%. Most of the remaining gap is closed here, "
        "but no city goes above its own best 4-week pace.",
        "WEEKS WITH NO FESTIVAL (the middle of each season): no seasonality is applied - the factor is 1, so the week is simply asked for an equal share of the gap still open, capped by the season's pace. "
        "Only last year's attrition shape (city tab column BD) changes how many placements such a week needs.",
    ])
    r = para(r, "6.  HOW TO READ A CITY TAB", [
        "Rows 2-5 are actual weeks from raw_performance. Plan weeks start at row 6. Columns A-AC follow the Weekly Supply Plan layout; the Lakshya build-up is AF-AW.",
        "Brown block BH-BQ is the realism check: BH proven pace, BI organic capacity, BJ new cars going on road, BK most we can add, BL organic add needed, BM what we plan (new cars + the smaller of BL and BI), "
        "BN/BO planned and organic growth %, BP 'Yes' / 'Capped at LY pace' / 'Diwali dip', BQ gap to the Lakshya number still open, BR:BS the Diwali dip, BT new cars still to go on road.",
        "BM is split into EIP / Own Now / Leasing+DTO by each layer's share of the gap it still has to its Lakshya number (the Diwali dip is taken from Leasing+DTO, which then wins it back). Placements = that layer's net add + churn. Recruitment by channel = placements x the city's channel mix.",
    ])
    r = para(r, "7.  UPDATING EACH WEEK", [
        "Paste a fresh SSOT query result (link on the Inputs tab) into raw_performance. The Summary View 'actual' rows fill in for finished weeks. "
        "To re-plan from a later week, move the opening date on Inputs to the latest Sunday and extend the calendar.",
        "Change what the plan may assume on the Inputs tab: proven pace (section 8), festival impacts (7), new cars and sales by month (4, 5), churn rates and targets (3).",
    ])
    ws.freeze_panes = "A4"
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
    ("Own Now placements", "AM"), ("L+DTO placements", "AT"), ("Total placements (Own Now + L+DTO)", "AU"),
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
        ("Placements (Own Now + L+DTO)", lambda w: ca(cb("Total placements (Own Now + L+DTO)"), w), None, "#,##0"),
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
    for i, city in enumerate(CITIES):
        build_city(wb, i, city)
    build_compare(wb)
    build_summary(wb)
    build_combined(wb)
    build_readme(wb)
    build_raw(wb, raw)
    wb.save(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
