"""Simple weekly supply plan, in the format of the team's own supply plan sheet (Supply_Plan_sep_end).

python3 build_simple_plan.py out.xlsx raw.json plan_values.json

One tab per city, one row per week:
  - actual weeks (w/c 3 Aug - 21 Sep 2026): read from raw_performance with SUMIFS
  - plan weeks (w/c 28 Sep - 21 Dec 2026): typed inputs (yellow) taken from the Lakshya-based plan; everything else is a
    short formula on the same row or the row above, so any input can be changed and the plan rolls forward:
        I  Net Allocations   = K + P + U
        U  Net Attrition     = -(H + K) x V
        H  active partners   = previous H + previous K + previous U
        G  cars on road (WB) = previous Y
        Y  cars on road (WE) = G + I
        Z  util              = Y / E
plus Lakshya and last-year columns, Combined All, Summary View (weekly), Summary View (Monthly) and a Lakshya tab.
plan_values.json = the Lakshya-based plan per city (logical city-tab columns), read from the live main sheet.
"""
import datetime as dt
import json
import sys

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

import build_weekly_supply_plan as base
from build_weekly_supply_plan import (CITIES, LK_CMP, EVENTS_ALL, EVENTS_CITY, WEEK_FESTIVAL, fill, hdr, put, note,
                                      F_TITLE, F_NOTE, F_BOLD, F_HDR, NAVY, GREY_HDR, INPUT, ACTUAL, LIGHT, HIST, TEAL, BOX,
                                      CENTER, NUM, PCT, RED_FONT, rc)

YELLOW_IN = "FFFFF2CC"           # typed plan inputs
ACT_W = [dt.date(2026, 8, 3) + dt.timedelta(days=7 * k) for k in range(8)]       # w/c 3 Aug - 21 Sep (actual)
PLAN_W = [dt.date(2026, 9, 28) + dt.timedelta(days=7 * k) for k in range(13)]    # w/c 28 Sep - 21 Dec (plan)
WEEKS = ACT_W + PLAN_W
R0 = 2                            # first week row on a city tab
RP = R0 + len(ACT_W)              # first plan row
RL = R0 + len(WEEKS) - 1          # last plan row
LAST_DAY = "MAX(raw_performance!$C:$C)"
CHANNELS = [("Field Sales Executive", "ni_fse_cnt", "resurrection_fse_cnt"),
            ("Vendor", "ni_vendor_cnt", "resurrection_vendor_cnt"),
            ("Referrals", "ni_driver_referral_cnt", "resurrection_driver_referral_cnt"),
            ("Performance marketing", "ni_perf_mktg_cnt", "resurrection_perf_mktg_cnt")]

# city-tab columns (the first 26 follow the team's sheet, A-Z)
HEAD = ["City", "Fuel Type", "Month", "Week", "Total Cars [week ending]", "nULP (change in cars)", "cars on Road - WB",
        "active partners - WB", "Net Allocations", "Total Allocations", "Total Channel", "Field Sales Executive", "Vendor",
        "Referrals", "Performance marketing", "EIP Net add-on", "Events / seasonality", "EIP cars", "Rejoin %",
        "Attrition + Temp Attrition", "Net Attrition (Abs)", "Net Attrition %", "Leasing + DTO cars on Road - WE",
        "Own Now cars on Road - WE", "Week-ending cars on Road", "Week ending Util",
        "Lakshya: cars on road", "Lakshya: util", "Lakshya: recruitment", "Lakshya: net attrition %", "Lakshya: EIP net add",
        "Plan - Lakshya: cars on road", "Plan - Lakshya: util", "Plan - Lakshya: recruitment",
        "LY: cars on road", "LY: total cars", "LY: util", "LY: recruitment", "LY: net attrition (abs)", "LY: active partners - WB",
        "Row type"]
COL = {h: L(i + 1) for i, h in enumerate(HEAD)}
NC = len(HEAD)


def raw_on(field, day, city="$A{r}"):
    c = rc(field)
    return f"SUMIFS(raw_performance!${c}:${c},raw_performance!$D:$D,{city},raw_performance!$E:$E,$B{{r}},raw_performance!$C:$C,{day})"


def raw_week(field, wk, city="$A{r}"):
    c = rc(field)
    return f"SUMIFS(raw_performance!${c}:${c},raw_performance!$D:$D,{city},raw_performance!$E:$E,$B{{r}},raw_performance!$B:$B,{wk})"


def raw_index(raw):
    """Week sums and day values from raw.json (to set the plan's net attrition % so on-road matches the plan)."""
    h = raw["hdr"]
    I = {k: i for i, k in enumerate(h)}
    f = lambda x: float(x) if x not in (None, "", "NULL", "None") else 0.0
    day, wk = {}, {}
    for row in raw["data"]:
        if row[I["fuel_type"]] != "CNG":
            continue
        c, d, w = row[I["city"]], row[I["date"]][:10], row[I["Week"]][:10]
        day[(c, d)] = row
        acc = wk.setdefault((c, w), {})
        for k in ("attrition_cnt", "temp_attrition_cnt", "rejoin_cnt", "temp_rejoin_cnt") + tuple(x for _, a, b_ in CHANNELS for x in (a, b_)):
            acc[k] = acc.get(k, 0.0) + f(row[I[k]])
    return I, f, day, wk


def build_city(wb, city, pv, rawix):
    ws = wb.create_sheet(city)
    ws.sheet_properties.tabColor = TEAL
    I, f, day, wk = rawix
    for j, h in enumerate(HEAD, start=1):
        c = hdr(ws, 1, j, h, GREY_HDR if j > 26 else NAVY)
        ws.column_dimensions[L(j)].width = 11
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["Q"].width = 26
    ws.row_dimensions[1].height = 54
    v = pv[city]
    lk = LK_CMP[city]

    # net attrition %: set so the plan's drivers leaving (Lakshya-based plan) come out exactly, given this sheet's H
    w21 = "2026-09-21"
    acc = wk.get((city, w21), {})
    H = f(day.get((city, w21), [0] * len(I))[I["uniq_partners_dt_beginning"]]) if (city, w21) in day else 0.0
    K = sum(acc.get(a, 0) + acc.get(b_, 0) for _, a, b_ in CHANNELS)
    U = -(acc.get("attrition_cnt", 0) + acc.get("temp_attrition_cnt", 0) - acc.get("rejoin_cnt", 0) - acc.get("temp_rejoin_cnt", 0))
    H = H + K + U
    V = []
    for t in range(13):
        k_ = sum(v[x][t + 1] for x in ("L", "M", "N", "O"))
        V.append(v["AQ"][t + 1] / (H + k_))
        H = H + k_ - v["AQ"][t + 1]

    for i, d in enumerate(WEEKS):
        r = R0 + i
        plan = r >= RP
        t = r - RP                                     # plan week index
        g = lambda s: s.replace("{r}", str(r))
        row = {
            "City": city, "Fuel Type": "CNG",
            "Month": (dt.date(2026, 10, 1) if d == PLAN_W[0] else f"=EOMONTH(D{r},-1)+1"),
            "Week": d if i == 0 else f"=D{r - 1}+7",
        }
        if not plan:   # actual week, from raw_performance
            end = f"MIN($D{r}+6,{LAST_DAY})"
            row.update({
                "Total Cars [week ending]": "=" + g(raw_on("fleet_total_cars_cnt", end)),
                "nULP (change in cars)": "=0" if i == 0 else f"=E{r}-E{r - 1}",
                "cars on Road - WB": "=" + g(raw_on("allotted_cars_eod", f"$D{r}-1")),
                "active partners - WB": "=" + g(raw_on("uniq_partners_dt_beginning", f"$D{r}")),
                "EIP Net add-on": "=" + g(raw_week("Net EIP Add-ons", f"$D{r}")),
                "EIP cars": "=" + g(raw_on("eip_vehicles_cnt", end)),
                "Attrition + Temp Attrition": "=" + g(raw_week("attrition_cnt", f"$D{r}")) + "+" + g(raw_week("temp_attrition_cnt", f"$D{r}")),
                "Rejoin %": (f'=IFERROR(({g(raw_week("rejoin_cnt", f"$D{r}"))}+{g(raw_week("temp_rejoin_cnt", f"$D{r}"))})/T{r},"")'),
                "Net Attrition (Abs)": (f'=-(T{r}-{g(raw_week("rejoin_cnt", f"$D{r}"))}-{g(raw_week("temp_rejoin_cnt", f"$D{r}"))})'),
                "Net Attrition %": f"=IFERROR(-U{r}/(H{r}+K{r}),\"\")",
                "Own Now cars on Road - WE": "=" + g(raw_on("own_now_cars_eod", end)),
                "Week-ending cars on Road": "=" + g(raw_on("allotted_cars_eod", end)),
            })
            for name, a, b_ in CHANNELS:
                row[name] = "=" + g(raw_week(a, f"$D{r}")) + "+" + g(raw_week(b_, f"$D{r}"))
        else:          # plan week: typed inputs + short formulas
            row.update({
                "Total Cars [week ending]": round(v["E"][t + 1], 1),
                "nULP (change in cars)": f"=E{r}-E{r - 1}",
                "cars on Road - WB": f"=Y{r - 1}",
                "active partners - WB": f"=H{r - 1}+K{r - 1}+U{r - 1}",
                "EIP Net add-on": round(v["AG"][t + 1], 1),
                "EIP cars": f"=R{r - 1}+P{r}",
                "Net Attrition (Abs)": f"=-(H{r}+K{r})*V{r}",
                "Net Attrition %": round(V[t], 5),
                "Own Now cars on Road - WE": round(v["X"][t + 1], 1),
                "Week-ending cars on Road": f"=G{r}+I{r}",
            })
            for name, key in zip([c[0] for c in CHANNELS], ("L", "M", "N", "O")):
                row[name] = round(v[key][t + 1], 1)
            # Lakshya v4 for the same week
            row.update({
                "Lakshya: cars on road": round(lk["onroad"][t + 1], 1),
                "Lakshya: util": f"=IFERROR(AA{r}/{round(lk['fleet'][t + 1], 1)},\"\")",
                "Lakshya: recruitment": round(lk["rec"][t + 1], 1),
                "Lakshya: net attrition %": round(lk["leave"][t + 1] / (lk["book"][t + 1] + lk["rec"][t + 1]), 5),
                "Lakshya: EIP net add": round(v["AG"][t + 1], 1),
                "Plan - Lakshya: cars on road": f"=Y{r}-AA{r}",
                "Plan - Lakshya: util": f"=IFERROR(Z{r}-AB{r},\"\")",
                "Plan - Lakshya: recruitment": f"=K{r}-AC{r}",
            })
        ev = []
        if plan:
            fest = WEEK_FESTIVAL[t]
            if fest == "Diwali" or (fest == "Durga Puja" and city == "Kolkata"):
                ev.append(fest)
            ev += [x for x in (EVENTS_ALL.get(t + 1), EVENTS_CITY.get((city, t + 1))) if x]
        row.update({
            "Net Allocations": f"=K{r}+P{r}+U{r}",
            "Total Allocations": f"=K{r}+P{r}",
            "Total Channel": f"=SUM(L{r}:O{r})",
            "Events / seasonality": "; ".join(ev),
            "Leasing + DTO cars on Road - WE": f"=Y{r}-R{r}-X{r}",
            "Week ending Util": f"=IFERROR(Y{r}/E{r},\"\")",
            "LY: cars on road": "=" + g(raw_on("allotted_cars_eod", f"$D{r}-364+6")),
            "LY: total cars": "=" + g(raw_on("fleet_total_cars_cnt", f"$D{r}-364+6")),
            "LY: util": f"=IFERROR(AI{r}/AJ{r},\"\")",
            "LY: recruitment": "=" + "+".join(g(raw_week(x, f"$D{r}-364")) for _, a, b_ in CHANNELS for x in (a, b_)),
            "LY: net attrition (abs)": ("=-(" + g(raw_week("attrition_cnt", f"$D{r}-364")) + "+" + g(raw_week("temp_attrition_cnt", f"$D{r}-364"))
                                        + "-" + g(raw_week("rejoin_cnt", f"$D{r}-364")) + "-" + g(raw_week("temp_rejoin_cnt", f"$D{r}-364")) + ")"),
            "LY: active partners - WB": "=" + g(raw_on("uniq_partners_dt_beginning", f"$D{r}-364")),
            "Row type": "Plan" if plan else "Actual",
        })
        for j, h in enumerate(HEAD, start=1):
            val = row.get(h)
            fmt = NUM
            if h in ("Month",):
                fmt = "mmm-yy"
            elif h == "Week":
                fmt = "dd-mmm-yy"
            elif h in ("Rejoin %", "Net Attrition %", "Week ending Util", "Lakshya: util", "Lakshya: net attrition %",
                       "Plan - Lakshya: util", "LY: util"):
                fmt = "0.0%"
            elif h in ("City", "Fuel Type", "Events / seasonality", "Row type"):
                fmt = None
            typed = plan and h in ("Total Cars [week ending]", "Field Sales Executive", "Vendor", "Referrals",
                                   "Performance marketing", "EIP Net add-on", "Net Attrition %", "Own Now cars on Road - WE")
            bg = YELLOW_IN if typed else (ACTUAL if not plan and j <= 26 else (HIST if h.startswith("LY") else
                                                                              (LIGHT if h.startswith(("Lakshya", "Plan -")) else None)))
            c = put(ws, r, j, val, fmt, bg=bg, bold=h in ("Week-ending cars on Road", "Week ending Util"))
            c.border = BOX
            if h == "Events / seasonality":
                c.alignment = Alignment(wrap_text=True, vertical="center")
            elif j > 2:
                c.alignment = Alignment(horizontal="center", vertical="center")
    # totals for the plan weeks
    r = RL + 2
    put(ws, r, 1, "Plan total, w/c 28 Sep - 21 Dec", bold=True, bg=LIGHT)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    for h in ("Net Allocations", "Total Allocations", "Total Channel", "Field Sales Executive", "Vendor", "Referrals",
              "Performance marketing", "EIP Net add-on", "Net Attrition (Abs)", "Lakshya: recruitment", "Lakshya: EIP net add",
              "Plan - Lakshya: recruitment", "LY: recruitment"):
        c_ = COL[h]
        put(ws, r, HEAD.index(h) + 1, f"=SUM({c_}{RP}:{c_}{RL})", NUM, bold=True, bg=LIGHT).alignment = CENTER
    for h, src in (("Week-ending cars on Road", "Y"), ("Week ending Util", "Z"), ("Lakshya: cars on road", "AA"),
                   ("Lakshya: util", "AB"), ("Plan - Lakshya: cars on road", "AF"), ("Plan - Lakshya: util", "AG")):
        put(ws, r, HEAD.index(h) + 1, f"={src}{RL}", "0.0%" if "util" in h.lower() else NUM, bold=True, bg=LIGHT).alignment = CENTER
    note(ws, r + 1, "Yellow = plan inputs you can change (cars, recruitment by channel, EIP add, net attrition %, Own Now cars). "
                    "Grey-blue = actual (raw_performance). Everything else is a formula: I = K + P + U, U = -(H + K) x V, H = previous H + "
                    "previous K + previous U, G = previous Y, Y = G + I, Z = Y / E, W = Y - R - X. Lakshya = Lakshya v4, same week (net "
                    "attrition on the same basis as V). LY = the same week 364 days earlier. Last actual week (w/c 21 Sep) has 6 days loaded.")
    red = Font(name="Calibri", size=10, bold=True, color="FFC00000")
    ws.conditional_formatting.add(f"AF{RP}:AH{RL}", FormulaRule(formula=[f"AF{RP}<0"], font=red))
    ws.freeze_panes = "E2"
    return ws


def build_lakshya(wb):
    ws = wb.create_sheet("Lakshya")
    ws.sheet_properties.tabColor = TEAL
    heads = ["City", "Week", "Month", "Cars on road", "Total cars", "Util", "Recruitment", "Drivers leaving", "Drivers at week start",
             "Net attrition %", "Cars added", "Cars sold"]
    for j, h in enumerate(heads, start=1):
        hdr(ws, 1, j, h)
        ws.column_dimensions[L(j)].width = 13
    ws.row_dimensions[1].height = 34
    r = 2
    for city in CITIES:
        lk = LK_CMP[city]
        for t, d in enumerate(PLAN_W):
            vals = [city, d, dt.date(2026, 10, 1) if t == 0 else dt.date(d.year, d.month, 1), round(lk["onroad"][t + 1], 1),
                    round(lk["fleet"][t + 1], 1), f"=D{r}/E{r}", round(lk["rec"][t + 1], 1), round(lk["leave"][t + 1], 1),
                    round(lk["book"][t + 1], 1), f"=H{r}/(I{r}+G{r})", round(lk["added"][t + 1], 1), round(lk["sold"][t + 1], 1)]
            fm = [None, "dd-mmm-yy", "mmm-yy", NUM, NUM, "0.0%", NUM, NUM, NUM, "0.0%", NUM, NUM]
            for j, (x, f_) in enumerate(zip(vals, fm), start=1):
                put(ws, r, j, x, f_).border = BOX
            r += 1
    note(ws, r + 1, "Lakshya_15000_Model_v4, week by week (w/e 4 Oct - 27 Dec), as the Lakshya model's weekly placements, churn and "
                    "month-end books give it. Net attrition % = drivers leaving / (drivers at week start + recruitment), the same basis as "
                    "the city tabs' column V.")
    ws.freeze_panes = "C2"


def build_combined(wb):
    ws = wb.create_sheet("Combined All")
    for j, h in enumerate(HEAD, start=1):
        hdr(ws, 1, j, h)
        ws.column_dimensions[L(j)].width = 11
    ws.row_dimensions[1].height = 54
    stack = ";".join(f"'{c}'!A{R0}:{L(NC)}{RL}" for c in CITIES)
    ws["A2"] = f'=QUERY({{{stack}}},"select * where Col1 is not null",0)'
    ws.freeze_panes = "E2"


CA = "'Combined All'"


def ca(col, crit):   # SUMIFS on Combined All for the pick (B1 city or *, B2 fuel)
    return f"SUMIFS({CA}!${col}:${col},{CA}!$A:$A,$E$2,{CA}!$B:$B,$B$2,{crit})"


METRICS = [   # (title, kind, plan/actual(crit), Lakshya(crit) or None, LY(crit) or None, format)
    ("Util", "ratio", lambda k: (ca("Y", k), ca("E", k)), lambda k: (ca("AA", k), f"({ca('AA', k)}/1)"), lambda k: (ca("AI", k), ca("AJ", k)), "0.0%"),
    ("On Road Cars (week end)", "end", lambda k: ca("Y", k), lambda k: ca("AA", k), lambda k: ca("AI", k), NUM),
    ("Total Cars (week end)", "end", lambda k: ca("E", k), None, lambda k: ca("AJ", k), NUM),
    ("Recruitment (all channels)", "sum", lambda k: ca("K", k), lambda k: ca("AC", k), lambda k: ca("AL", k), NUM),
    ("Field Sales Executive", "sum", lambda k: ca("L", k), None, None, NUM),
    ("Vendor", "sum", lambda k: ca("M", k), None, None, NUM),
    ("Referrals", "sum", lambda k: ca("N", k), None, None, NUM),
    ("Performance marketing", "sum", lambda k: ca("O", k), None, None, NUM),
    ("Net Attrition (Abs)", "sum", lambda k: ca("U", k), None, lambda k: ca("AM", k), NUM),
    ("Net Attrition %", "att", lambda k: (ca("U", k), ca("H", k), ca("K", k)), None, lambda k: (ca("AM", k), ca("AN", k), ca("AL", k)), "0.0%"),
    ("EIP Net add-on", "sum", lambda k: ca("P", k), lambda k: ca("AE", k), None, NUM),
    ("EIP cars (week end)", "end", lambda k: ca("R", k), None, None, NUM),
    ("Own Now cars on road (week end)", "end", lambda k: ca("X", k), None, None, NUM),
    ("Leasing + DTO cars on road (week end)", "end", lambda k: ca("W", k), None, None, NUM),
]


def lk_util(k):     # Lakshya util for the pick: Lakshya on road / Lakshya fleet (Lakshya tab)
    sel = 'IF($B$1="India","*",$B$1)'
    return (f"SUMIFS(Lakshya!$D:$D,Lakshya!$A:$A,{sel},{k.replace(CA + '!$D:$D', 'Lakshya!$B:$B').replace(CA + '!$C:$C', 'Lakshya!$C:$C')})",
            f"SUMIFS(Lakshya!$E:$E,Lakshya!$A:$A,{sel},{k.replace(CA + '!$D:$D', 'Lakshya!$B:$B').replace(CA + '!$C:$C', 'Lakshya!$C:$C')})")


def picker(ws, title):
    ws["A1"] = "City"
    ws["A1"].font = F_BOLD
    ws["A2"] = "Fuel Type"
    ws["A2"].font = F_BOLD
    for cell, val, opts in (("B1", "India", ["India"] + CITIES), ("B2", "CNG", ["CNG"])):
        c = ws[cell]
        c.value = val
        c.font = Font(name="Calibri", size=11, bold=True, color="FF1F4E79")
        c.fill = fill(INPUT)
        c.border = BOX
        dv = DataValidation(type="list", formula1='"' + ",".join(opts) + '"', allow_blank=False)
        ws.add_data_validation(dv)
        dv.add(cell)
    ws["D1"] = title
    ws["D1"].font = F_TITLE
    ws["D2"] = "City filter:"
    ws["D2"].font = F_NOTE
    ws["E2"] = '=IF($B$1="India","*",$B$1)'
    ws["E2"].font = F_NOTE


def block_rows(ws, r, title, kind, pf, lf, yf, fmt, cols, crit_of, label_main, actual_keys=()):
    """One metric: rows Plan/Actual, Lakshya, Plan - Lakshya, Last year; columns = weeks or months."""
    hdr(ws, r, 1, title, NAVY).alignment = Alignment(horizontal="left", vertical="center")
    for j, (lab, _) in enumerate(cols, start=2):
        c = hdr(ws, r, j, lab, NAVY)
    rows = [(label_main, "p")]
    if lf is not None or kind == "ratio":
        rows += [("Lakshya v4", "l"), ("Plan - Lakshya", "g")]
    if yf is not None:
        rows.append(("Last year (same weeks)", "y"))
    rr = {k: r + 1 + i for i, (_, k) in enumerate(rows)}
    for i, (lab, k) in enumerate(rows):
        row = r + 1 + i
        put(ws, row, 1, lab, bold=k == "p", bg=HIST if k == "y" else None).border = BOX
        for j, (_, key) in enumerate(cols, start=2):
            crit, end_crit = crit_of(key)
            if k in ("l", "g") and key in actual_keys:     # Lakshya has no figures for the actual weeks
                v = None
            elif k == "g":
                v = f'=IFERROR({L(j)}{rr["p"]}-{L(j)}{rr["l"]},"")'
            else:
                fn = {"p": pf, "l": lf, "y": yf}[k]
                if kind == "ratio":
                    if k == "l":
                        a, b_ = lk_util(crit)
                    else:
                        a, b_ = fn(crit)
                    v = f'=IFERROR({a}/{b_},"")'
                elif kind == "att":
                    u, h_, k_ = fn(crit)
                    v = f'=IFERROR(-{u}/({h_}+{k_}),"")'
                elif kind == "end":
                    v = "=" + fn(end_crit)
                else:
                    v = "=" + fn(crit)
            c = put(ws, row, j, v, fmt, bold=k == "p", bg=HIST if k == "y" else (YELLOW_IN if k == "p" else None))
            c.alignment = CENTER
            c.border = BOX
        if k == "g":
            ws.conditional_formatting.add(f"B{row}:{L(1 + len(cols))}{row}",
                                          FormulaRule(formula=[f'AND(B{row}<>"",B{row}<0)'], font=RED_FONT))
    return r + len(rows) + 2


def build_summary_weekly(wb):
    ws = wb.create_sheet("Summary View", 0)
    ws.sheet_view.showGridLines = False
    picker(ws, "SUMMARY VIEW (weekly)  -  actual to w/c 21 Sep, then the plan")
    ws.column_dimensions["A"].width = 34
    for j in range(2, 2 + len(WEEKS)):
        ws.column_dimensions[L(j)].width = 9
    put(ws, 4, 1, "Week (w/c)", bold=True)
    put(ws, 5, 1, "Actual / Plan", bold=True)
    for j, d in enumerate(WEEKS, start=2):
        put(ws, 4, j, d, 'dd" "mmm', bold=True).alignment = CENTER
        put(ws, 5, j, "Actual" if d < PLAN_W[0] else "Plan", bold=True, bg=ACTUAL if d < PLAN_W[0] else None).alignment = CENTER
        put(ws, 6, j, f'=IF(AND(TODAY()>={L(j)}4,TODAY()<{L(j)}4+7),"We are here","")', bold=True).alignment = CENTER
    ws.conditional_formatting.add(f"B6:{L(1 + len(WEEKS))}6", FormulaRule(formula=['B6="We are here"'], fill=fill("FFFFFF00")))
    cols = [(f"={L(j)}$4", L(j)) for j in range(2, 2 + len(WEEKS))]
    crit_of = lambda col: (f"{CA}!$D:$D,{col}$4", f"{CA}!$D:$D,{col}$4")
    r = 8
    for title, kind, pf, lf, yf, fmt in METRICS:
        r = block_rows(ws, r, title, kind, pf, lf, yf, fmt, cols, crit_of, "2026 (actual, then plan)",
                       actual_keys={L(j) for j in range(2, 2 + len(ACT_W))})
    note(ws, r, "Pick a city (or India) in B1. 2026 = the city tabs (actual weeks from raw_performance, then the plan). Lakshya v4 = the same "
                "week in Lakshya's model. Last year = the same week 364 days earlier. Plan - Lakshya is red when below Lakshya.")
    ws.freeze_panes = "B7"


def build_summary_monthly(wb):
    ws = wb.create_sheet("Summary View (Monthly)", 1)
    ws.sheet_view.showGridLines = False
    picker(ws, "SUMMARY VIEW (Monthly)  -  Aug and Sep actual, Oct to Dec plan")
    ws.column_dimensions["A"].width = 34
    months = [dt.date(2026, 8, 1), dt.date(2026, 9, 1), dt.date(2026, 10, 1), dt.date(2026, 11, 1), dt.date(2026, 12, 1)]
    for j in range(2, 8):
        ws.column_dimensions[L(j)].width = 13
    put(ws, 4, 1, "Month", bold=True)
    for j, m in enumerate(months, start=2):
        put(ws, 4, j, m, "mmm-yy", bold=True).alignment = CENTER
        put(ws, 5, j, "Actual" if m < dt.date(2026, 10, 1) else "Plan", bold=True,
            bg=ACTUAL if m < dt.date(2026, 10, 1) else None).alignment = CENTER
    put(ws, 4, 7, "Oct - Dec plan", bold=True).alignment = CENTER
    # last week of each month (for month-end figures): the latest week whose Month is the month
    cols = [(f"={L(j)}$4", L(j)) for j in range(2, 7)] + [("Oct - Dec", "G")]

    def crit_of(col):
        if col == "G":
            return (f"{CA}!$C:$C,\">=\"&$D$4,{CA}!$C:$C,\"<=\"&$F$4", f"{CA}!$D:$D,MAXIFS({CA}!$D:$D,{CA}!$C:$C,$F$4)")
        return (f"{CA}!$C:$C,{col}$4", f"{CA}!$D:$D,MAXIFS({CA}!$D:$D,{CA}!$C:$C,{col}$4)")
    r = 8
    for title, kind, pf, lf, yf, fmt in METRICS:
        t = title.replace("(week end)", "(month end)")
        if kind in ("sum",):
            t += "  (month total)"
        elif kind == "ratio":
            t += "  (month: total on road / total cars over the weeks)"
        r = block_rows(ws, r, t, kind, pf, lf, yf, fmt, cols, crit_of, "2026 (actual, then plan)", actual_keys={"B", "C"})
    note(ws, r, "Months follow column C of the city tabs (the week's Monday; w/c 28 Sep counts in October as the plan starts there). "
                "Totals for flows; month-end for cars on road, total cars and the on-road split; util = the month's total on road / total "
                "cars over its weeks; net attrition % = -net attrition / (active partners + recruitment) over the month.")
    ws.freeze_panes = "B6"


def build_howto(wb):
    ws = wb.create_sheet("How to use", 2)
    ws.column_dimensions["A"].width = 120
    lines = [
        ("HOW THIS SHEET WORKS", F_TITLE),
        ("One tab per city, one row per week. Rows w/c 3 Aug - 21 Sep are ACTUAL (grey-blue, from raw_performance). Rows w/c 28 Sep - 21 Dec are the PLAN.", None),
        ("", None),
        ("Change the plan only in the YELLOW cells of a city tab:", F_BOLD),
        ("  E  Total Cars [week ending]      - fleet at the end of the week (new cars in, cars sold out)", None),
        ("  L-O  Recruitment by channel        - FSE, Vendor, Referrals, Performance marketing (K = their total)", None),
        ("  P  EIP Net add-on                 - EIP cars added minus dropped in the week", None),
        ("  V  Net Attrition %                - drivers lost in the week / (active partners at week start + recruitment)", None),
        ("  X  Own Now cars on Road - WE      - Own Now cars on road at week end (L+DTO in W = the rest)", None),
        ("", None),
        ("Everything else is a short formula and rolls forward by itself:", F_BOLD),
        ("  U  Net Attrition (Abs)  = -(H + K) x V", None),
        ("  I  Net Allocations      = K + P + U          (recruitment + EIP add - drivers lost)", None),
        ("  H  active partners - WB = previous week's H + K + U", None),
        ("  G  cars on Road - WB    = previous week's Y", None),
        ("  Y  cars on Road - WE    = G + I", None),
        ("  Z  Util                 = Y / E", None),
        ("  R  EIP cars             = previous R + P;   W  Leasing + DTO = Y - R - X", None),
        ("", None),
        ("Next to each week: Lakshya v4's numbers for the same week (AA-AE), Plan - Lakshya (AF-AH, red when below), and last year (AI-AN).", None),
        ("Summary View (weekly) and Summary View (Monthly) read the city tabs through Combined All; pick a city or India in B1.", None),
        ("", None),
        ("Where the plan numbers come from (the Lakshya-based plan):", F_BOLD),
        ("  - Starts from the actual on Sun 27 Sep (actuals loaded to Sat 26 Sep).", None),
        ("  - Recruitment: Lakshya's month average a week, x the Diwali / Durga Puja (Kolkata) shape, + catch-up hiring each month so each", None),
        ("    city's average util in Oct, Nov and Dec equals Lakshya's month average. Split into channels by the AOP mix.", None),
        ("  - Net attrition: Lakshya's month average (column V is that rate on this sheet's basis, so on-road matches the plan exactly).", None),
        ("  - Total cars: Lakshya's 2,300 new cars (582 bought, phased by RTO status; the rest in Oct-Nov) and 721 cars sold.", None),
        ("  - EIP: a straight line to Lakshya's December EIP. Own Now: drivers for new cars + the existing-car trend.", None),
        ("", None),
        ("To refresh actuals: paste a new SSOT query output into raw_performance. Actual rows update; when a plan week becomes actual, copy an", None),
        ("actual row's formulas over it (or ask for a rebuild).", None),
    ]
    for i, (t, font) in enumerate(lines, start=1):
        c = ws.cell(i, 1, t)
        c.font = font or Font(name="Calibri", size=11)


def main(out, raw_path, pv_path):
    raw = json.load(open(raw_path))
    base.RAW_HDR[:] = raw["hdr"]
    pv = json.load(open(pv_path))
    rawix = raw_index(raw)
    wb = Workbook()
    wb.remove(wb.active)
    for city in CITIES:
        build_city(wb, city, pv, rawix)
    build_lakshya(wb)
    build_combined(wb)
    build_summary_weekly(wb)
    build_summary_monthly(wb)
    build_howto(wb)
    base.build_raw(wb, raw)
    order = ["Summary View", "Summary View (Monthly)", "How to use"] + CITIES + ["Lakshya", "Combined All", "raw_performance"]
    wb._sheets.sort(key=lambda w: order.index(w.title))
    wb.active = 0
    wb.save(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
