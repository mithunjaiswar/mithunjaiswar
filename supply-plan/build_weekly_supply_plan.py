"""Build the Lakshya 15,000 weekly supply plan workbook (1 Inputs tab + 7 city tabs).

Source of targets: Lakshya_15000_Model_v4.xlsx (the AOP does not match it, so it is not used).
Opening position: reporting DB, analytics.ssot_scorecard_agg, CNG, Sun 20 Sep 2026.
City tab layout follows the existing Weekly Supply Plan sheet (columns A-Z), with the
Lakshya build-up (the logic behind each weekly number) to the right of it.

Every number on a city tab is a formula that reads from the Inputs tab.

Usage: python3 build_weekly_supply_plan.py <output.xlsx>
"""
import datetime as dt
import sys

from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------- data
CITIES = ["Mumbai", "Delhi NCR", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune"]

# Opening, Sun 20 Sep 2026 (reporting DB): fleet_total_cars_cnt, allotted_cars_eod,
# eip_vehicles_cnt, own_now_cars_eod
OPENING = {
    "Mumbai":    (4170, 2606, 973, 496),
    "Delhi NCR": (4182, 2207, 63, 680),
    "Bangalore": (2857, 1952, 339, 668),
    "Hyderabad": (2583, 1686, 424, 299),
    "Chennai":   (2555, 1727, 465, 418),
    "Kolkata":   (1085, 524, 48, 192),
    "Pune":      (1735, 971, 60, 277),
}
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

N_WEEKS = 15  # w/c 21 Sep ... w/c 28 Dec (28-31 Dec only)
W_EIP = [5, 5, 8, 8, 8, 8, 4, 4, 7, 7, 7, 8, 8, 7, 6]
W_OWN = [3, 4, 7, 8, 8, 7, 3, 3, 8, 9, 9, 9, 9, 8, 5]
W_LDTO = [5, 7, 8, 8, 6, 5, 0, 0, 6, 9, 10, 11, 11, 10, 4]
EVENTS_ALL = {
    2: "Gandhi Jayanti (Fri 2 Oct)",
    5: "Dussehra (Tue 20 Oct)",
    7: "Diwali (Sun 8 Nov) - low week",
    8: "Bali Pratipada, Bhai Dooj - low week",
    10: "Guru Nanak Jayanti (Tue 24 Nov)",
    11: "Last week new cars can land (30 Nov)",
    14: "Christmas (Fri 25 Dec)",
    15: "Part week: 28-31 Dec, plan ends 31 Dec",
}
EVENTS_CITY = {
    ("Bangalore", 6): "Kannada Rajyotsava (Sun 1 Nov)",
    ("Hyderabad", 8): "GHMC election (Sun 15 Nov)",
    ("Kolkata", 13): "KMC election (Tue 15 Dec)",
}

# ---------------------------------------------------------------- styles
NAVY = "FF1F3864"
GREY_HDR = "FF404040"
YELLOW = "FFFFFF00"
INPUT = "FFFFF2CC"
GREEN = "FFA2D9BE"
LIGHT = "FFF2F2F2"
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


def q(sheet):
    return f"'{sheet}'"


# ---------------------------------------------------------------- Inputs tab layout
R_GLOBAL = 5          # header row of global settings; values start next row
R_SUM_H = 15          # summary header row
R_SUM0 = R_SUM_H + 1  # first city row in summary
R_CITY_H = 28         # city inputs header row
R_CITY0 = R_CITY_H + 1
R_ADD_H = 40          # new cars header
R_ADD0 = R_ADD_H + 1
R_SALE_H = 52         # sales header
R_SALE0 = R_SALE_H + 1
R_CAL_H = 64          # calendar header
R_CAL0 = R_CAL_H + 1

G_OPEN_DATE = f"Inputs!$B${R_GLOBAL + 1}"
G_PLAN_END = f"Inputs!$B${R_GLOBAL + 3}"
G_WPM = f"Inputs!$B${R_GLOBAL + 4}"

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
    ("AC", "Days in plan", 6), ("AD", "New cars added", 8), ("AE", "Cars sold", 7),
    ("AF", "EIP weight", 7), ("AG", "EIP net add", 8),
    ("AH", "Own Now book - WB", 8), ("AI", "Own Now weight", 7), ("AJ", "Own Now net add", 8),
    ("AK", "Own Now churn", 8), ("AL", "Own Now purchase rollover", 9),
    ("AM", "Own Now placements", 9), ("AN", "of which new cars", 8),
    ("AO", "of which existing cars", 8),
    ("AP", "L+DTO book - WB", 8), ("AQ", "L+DTO weight", 7), ("AR", "L+DTO net add", 8),
    ("AS", "L+DTO churn", 8), ("AT", "L+DTO placements", 9),
    ("AU", "Total placements (Own Now + L+DTO)", 10), ("AV", "Check: on road = EIP + L+DTO + Own Now", 9),
    ("AW", "Util headroom", 8),
]
FIRST = 3                      # first week row (row 2 = opening actual)
LAST = FIRST + N_WEEKS - 1     # 17
R_TOT = LAST + 2               # 19
R_MON_T = R_TOT + 3            # 22 monthly block title
R_MON_H = R_MON_T + 1          # 23
R_MON0 = R_MON_H + 1           # 24..27
R_MON_TOT = R_MON0 + 4         # 28
R_NOTES = R_MON_TOT + 3        # 31


def build_city(wb, idx, city):
    ws = wb.create_sheet(city)
    for letter, text, width in COLS:
        ws.column_dimensions[letter].width = width
        if text:
            color = GREY_HDR if letter >= "AC" and len(letter) == 2 and letter != "AA" else NAVY
            hdr(ws, 1, ws[letter + "1"].column, text, color)
    ws.row_dimensions[1].height = 54
    ws.freeze_panes = "F2"

    ev_col = get_column_letter(9 + idx)  # events columns on Inputs calendar: I..O

    # ---- row 2: opening actual
    r = 2
    put(ws, r, 1, city, bg=LIGHT, bold=True)
    put(ws, r, 2, "CNG", bg=LIGHT)
    put(ws, r, 3, f"=EOMONTH(D{r},-1)+1", DATE, bg=LIGHT)
    put(ws, r, 4, f"={G_OPEN_DATE}", DATE, bg=LIGHT)
    put(ws, r, 5, f"={ci('fleet', idx)}", NUM, bg=LIGHT)
    put(ws, r, 17, "Opening - actual Sun 20 Sep (reporting DB)", bg=LIGHT)
    put(ws, r, 18, f"={ci('eip', idx)}", NUM, bg=LIGHT)
    put(ws, r, 23, f"={ci('ldto', idx)}", NUM, bg=LIGHT)
    put(ws, r, 24, f"={ci('own', idx)}", NUM, bg=LIGHT)
    put(ws, r, 25, f"={ci('onroad', idx)}", NUM, bg=LIGHT)
    put(ws, r, 26, f"=Y{r}/E{r}", PCT, bg=LIGHT)
    put(ws, r, 27, f"={ci('ceiling', idx)}", PCT, bg=LIGHT)
    put(ws, r, 48, f"=Y{r}-(R{r}+W{r}+X{r})", NUM, bg=LIGHT)
    put(ws, r, 49, f"=AA{r}-Z{r}", PCT, bg=LIGHT)
    for c in range(1, 50):
        if c != 28 and ws.cell(r, c).value is None:
            put(ws, r, c, None, bg=LIGHT)

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
            "AH": f"=X{p}", "AI": f"=Inputs!$G${cal}",
            "AJ": f"=({ci('t_own', idx)}-{ci('own', idx)})*AI{r}",
            "AK": f"=AH{r}*{ci('r_own', idx)}/{G_WPM}*AC{r}/7",
            "AL": f"=AH{r}*{ci('r_roll', idx)}/{G_WPM}*AC{r}/7",
            "AM": f"=AJ{r}+AK{r}+AL{r}", "AN": f"=AM{r}*{ci('newshare', idx)}",
            "AO": f"=AM{r}-AN{r}",
            "AP": f"=W{p}", "AQ": f"=Inputs!$H${cal}",
            "AR": f"=({ci('t_ldto', idx)}-{ci('ldto', idx)})*AQ{r}",
            "AS": f"=AP{r}*{ci('r_ldto', idx)}/{G_WPM}*AC{r}/7",
            "AT": f"=AR{r}+AS{r}", "AU": f"=AM{r}+AT{r}",
            "AV": f"=Y{r}-(R{r}+W{r}+X{r})", "AW": f"=AA{r}-Z{r}",
        }
        for letter, _, _ in COLS:
            col = ws[letter + "1"].column
            if letter == "AB":
                continue
            v = f.get(letter)
            fmt = NUM
            if letter in ("C", "D"):
                fmt = DATE
            elif letter in ("V", "Z", "AA", "AF", "AI", "AQ", "AW"):
                fmt = PCT
            elif letter in ("A", "B", "Q"):
                fmt = None
            bg = None
            if letter in ("L", "M", "N", "O", "P"):
                bg = YELLOW
            elif letter == "K":
                bg = GREEN
            elif letter == "AU":
                bg = YELLOW
            put(ws, r, col, v, fmt, bg=bg)

    # ---- totals row
    r = R_TOT
    put(ws, r, 1, "Total 21 Sep - 31 Dec", bold=True)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    for letter in ["F", "I", "J", "K", "L", "M", "N", "O", "P", "U", "AD", "AE", "AG", "AJ", "AK",
                   "AL", "AM", "AN", "AO", "AR", "AS", "AT", "AU"]:
        col = ws[letter + "1"].column
        put(ws, r, col, f"=SUM({letter}{FIRST}:{letter}{LAST})", NUM, bold=True, bg=LIGHT)
    for letter in ["AF", "AI", "AQ"]:
        col = ws[letter + "1"].column
        put(ws, r, col, f"=SUM({letter}{FIRST}:{letter}{LAST})", PCT, bold=True, bg=LIGHT)
    put(ws, r, 17, "Closing stock on 31 Dec is the last week row", font=F_NOTE)

    # ---- monthly view
    ws.cell(R_MON_T, 1, "MONTHLY VIEW  -  each week counts in the month its Monday falls in; "
                        "month-end stock = last week of that month").font = F_SECTION
    mon_cols = [
        ("Month", None, DATE), ("Weeks", "count", "0"), ("New cars added", "AD", NUM),
        ("Cars sold", "AE", NUM), ("Fleet (month end)", "=E", NUM), ("EIP net add", "P", NUM),
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
                s = src[1:]
                v = f"=INDEX({s}${FIRST}:{s}${LAST},MATCH($A{r},{rng},1))"
            else:
                v = f"=SUMIF({rng},$A{r},{src}${FIRST}:{src}${LAST})"
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
        "Row 2 is the actual position on Sun 20 Sep. Each week then starts from the previous week's close.",
        "EIP: the gap to the December target is spread across the weeks by the EIP weights (AG = gap x weight). No EIP churn is modelled, as in Lakshya v4.",
        "Own Now: net add = gap to December target x Own Now weight (AJ). Churn and purchase rollover = opening book x monthly rate / 4.33 x days/7 (AK, AL). Placements needed = net add + churn + rollover (AM).",
        "Leasing + DTO: net add = gap to December target x L+DTO weight (AR). Churn = opening book x Lakshya net churn rate / 4.33 x days/7 (AS). Placements needed = net add + churn (AT).",
        "Recruitment by channel (L:O) = total placements (AU) x the city's channel mix on the Inputs tab. Net Attrition (U) = Own Now churn + rollover + L+DTO churn.",
        "Fleet (E) = previous week + new cars added - cars sold; each month's cars are split evenly across that month's weeks. Util (Z) = week-ending cars on road / fleet; red when above the Lakshya ceiling (AA).",
        "Weights sum to 100%, so the last week (28-31 Dec) lands exactly on the Lakshya December target for each layer. Check column AV must be 0.",
    ]
    for k, text in enumerate(notes):
        ws.cell(R_NOTES + k, 1, text).font = F_SECTION if k == 0 else F_NOTE

    # ---- conditional formats
    ws.conditional_formatting.add(
        f"Z2:Z{LAST}", ColorScaleRule(start_type="min", start_color="FFF8696B", mid_type="percentile",
                                      mid_value=50, mid_color="FFFFEB84", end_type="max", end_color="FF63BE7B"))
    ws.conditional_formatting.add(
        f"K{FIRST}:K{LAST}", ColorScaleRule(start_type="min", start_color="FFFFFFFF", end_type="max",
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
         "Close of w/c 14 Sep. Opening fleet, on road, EIP and Own Now in section 3 are as of this date."),
        ("First plan week starts (Monday)", f"=B{R_GLOBAL + 1}+1", DATE, False, "Current week, Mon 21 - Sun 27 Sep."),
        ("Plan ends (month-end spot)", dt.date(2026, 12, 31), DATE, True,
         "The last week (w/c 28 Dec) counts 4 days, so the plan lands on 31 Dec."),
        ("Weeks per month", "=52/12", "0.00", False, "Turns a monthly churn rate into a weekly one."),
        ("India CNG on-road goal, Dec", 15000, NUM, True, "Lakshya lands at 15,082. ~1,000 EV held flat on top = 16,000."),
    ]
    for k, (label, val, fmt, is_input, note) in enumerate(rows):
        r = R_GLOBAL + 1 + k
        put(ws, r, 1, label)
        (inp if is_input else put)(ws, r, 2, val, fmt)
        c = put(ws, r, 3, note, font=F_NOTE)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=8)

    # ---- 2. summary
    ws.cell(R_SUM_H - 1, 1, "2.  PLAN SUMMARY - OUTPUT, DO NOT EDIT  (pulled from the city tabs)").font = F_SECTION
    sum_cols = ["City", "On road 20 Sep", "On road 31 Dec", "Lakshya target", "Gap to target",
                "EIP 31 Dec", "Own Now 31 Dec", "L+DTO 31 Dec", "Fleet 31 Dec", "Lakshya fleet Dec",
                "Util 31 Dec", "Ceiling", "Headroom", "EIP net add", "Own Now placements",
                "L+DTO placements", "Total placements", "Peak week placements", "Check (0 = OK)"]
    for j, t in enumerate(sum_cols, start=1):
        hdr(ws, R_SUM_H, j, t)
    ws.row_dimensions[R_SUM_H].height = 40
    for i, city in enumerate(CITIES):
        r = R_SUM0 + i
        s = q(city)
        vals = [
            (city, None), (f"={s}!Y2", NUM), (f"={s}!Y{LAST}", NUM), (f"={ci('t_onroad', i)}", NUM),
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
    groups = [(2, 6, "OPENING - actual Sun 20 Sep"), (7, 10, "DECEMBER TARGET - Lakshya v4"),
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
        fl, on, eip, own = OPENING[city]
        te, to, tl = TARGET[city]
        rl, ro, rr, ns, ce = RATES[city]
        fse, ven, ref = CHANNEL[city]
        put(ws, r, 1, city, bold=True)
        inp(ws, r, 2, fl, NUM)
        inp(ws, r, 3, on, NUM)
        inp(ws, r, 4, eip, NUM)
        inp(ws, r, 5, own, NUM)
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
        "Opening: allotted_cars_eod (on road), eip_vehicles_cnt, own_now_cars_eod, fleet_total_cars_cnt. Leasing + DTO = on road - EIP - Own Now (EIP sits inside leasing in the source).",
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
    cal_heads = ["Week #", "Week start (Mon)", "Week end", "Month", "Days in plan", "EIP weight",
                 "Own Now weight", "L+DTO weight"] + [f"Events - {c}" for c in CITIES]
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
        inp(ws, r, 7, W_OWN[w] / 100, "0%")
        inp(ws, r, 8, W_LDTO[w] / 100, "0%")
        for k, city in enumerate(CITIES):
            parts = [x for x in (EVENTS_ALL.get(w + 1), EVENTS_CITY.get((city, w + 1))) if x]
            inp(ws, r, 9 + k, "; ".join(parts) if parts else "")
    r = R_CAL0 + N_WEEKS
    put(ws, r, 1, "Total", bold=True, bg=LIGHT)
    for j in (2, 3, 4):
        put(ws, r, j, None, bg=LIGHT)
    put(ws, r, 5, f"=SUM(E{R_CAL0}:E{r - 1})", "0", bold=True, bg=LIGHT)
    for j in (6, 7, 8):
        L = get_column_letter(j)
        put(ws, r, j, f"=SUM({L}{R_CAL0}:{L}{r - 1})", "0%", bold=True, bg=LIGHT)
        ws.conditional_formatting.add(f"{L}{r}", FormulaRule(formula=[f"ROUND({L}{r},6)<>1"], font=red,
                                                             fill=fill("FFFFC7CE")))
    notes = [
        "Weights spread each layer's gap (December target - 20 Sep opening) across the weeks. Each column must total 100% or the plan will not land on target (the total turns red).",
        "Default shape: L+DTO holds its book flat through the two Diwali weeks (weight 0% = placements only replace churn) and recovers over the last six weeks, as in Lakshya v4.",
        "Own Now follows new-car arrivals (Oct-Nov) and dips around Diwali; EIP is spread fairly evenly. Change the weights to reshape the weekly plan; the December landing does not move.",
    ]
    for k, t in enumerate(notes):
        ws.cell(r + 1 + k, 1, t).font = F_NOTE
    ws.freeze_panes = "B4"
    ws.sheet_view.zoomScale = 90


def main(out):
    wb = Workbook()
    build_inputs(wb)
    for i, city in enumerate(CITIES):
        build_city(wb, i, city)
    wb.save(out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Lakshya_Weekly_Supply_Plan.xlsx")
