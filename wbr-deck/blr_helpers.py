import json
import re
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_PATH = "/home/user/mithunjaiswar/google-workspace-access/token.json"
PRES_ID = "1vQXpZ9eXzU8F4TxVx2Z0_HR9luNx8XJ7RiZcoledAJk"
DOC_URL = "https://docs.google.com/document/d/1-OWLml_4rKVz0ZtrK_dYkkKTDWMXbRlQiE1Mj6osD34/edit"

with open(TOKEN_PATH) as f:
    info = json.load(f)
creds = Credentials.from_authorized_user_info(info)
slides = build("slides", "v1", credentials=creds)

with open("/tmp/claude-0/-home-user-mithunjaiswar/a3071d57-7e4f-504e-99c9-482796a8dddc/scratchpad/all_tables.json") as f:
    ALL_TABLES = {int(k): v for k, v in json.load(f).items()}

EMU = 914400
SCALE = 10.0 / 13.333

def in_(v):
    return {"magnitude": v * SCALE * EMU, "unit": "EMU"}

def pos(x):
    return x * SCALE * EMU

def pt(v):
    return v * SCALE

DARK = {"red": 0.2, "green": 0.2, "blue": 0.2}
BLACK = {"red": 0, "green": 0, "blue": 0}
LABEL_BG = {"red": 0.94, "green": 0.94, "blue": 0.94}
WHITE = {"red": 1, "green": 1, "blue": 1}
GRAY_TEXT = {"red": 0.46666667, "green": 0.46666667, "blue": 0.46666667}
BORDER = {"red": 0.8, "green": 0.8, "blue": 0.8}
LINK_BLUE = {"red": 0.26, "green": 0.45, "blue": 0.86}
ACCENT = {"red": 0.85, "green": 0.86, "blue": 0.88}

RED = (0.93, 0.45, 0.42)
YEL = (0.98, 0.80, 0.52)
GRN = (0.53, 0.76, 0.48)


def lerp(a, b, t):
    return a + (b - a) * t


def heat_color(t):
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        u = t / 0.5
        return tuple(lerp(RED[i], YEL[i], u) for i in range(3))
    else:
        u = (t - 0.5) / 0.5
        return tuple(lerp(YEL[i], GRN[i], u) for i in range(3))


def parse_num(s):
    s = (s or "").strip()
    if not s or s in ("-", "y", "Y"):
        return None
    s2 = s.replace("%", "").replace(",", "").replace("₹", "")
    m = re.match(r"^(\d+):(\d{2}):(\d{2})$", s2)
    if m:
        h, mi, se = map(int, m.groups())
        return h * 3600 + mi * 60 + se
    try:
        return float(s2)
    except ValueError:
        return None


def row_heat_colors(values, invert=False):
    nums = [parse_num(v) for v in values]
    valid = [n for n in nums if n is not None]
    if len(valid) < 2 or max(valid) == min(valid):
        return [None] * len(values)
    lo, hi = min(valid), max(valid)
    out = []
    for n in nums:
        if n is None:
            out.append(None)
            continue
        t = (n - lo) / (hi - lo)
        out.append(heat_color(1 - t if invert else t))
    return out


# Metrics where a HIGHER number is worse for the business — colour them
# red-when-high / green-when-low instead of the default green-when-high.
BAD_WHEN_HIGH_WORDS = (
    "parking", "pending", "downtime", "audit fail", "missing", "revisit",
    "urgent", "cost", "wash", "inactive", "handover pending",
    "battery issue", "issue", "dropoff", "drop off", "drop-off", "bad debt",
    "carry forward", "carryforward", "cancel",
    "rejected", "tat to", "abd", "wrap", "fatal", "failure", "garage", "repair",
    "rta", "insurance", "misc", "net attrition %", "breaktime", "break duration",
)


# Some whole tables are a "pending/urgent work" or "money spent" breakdown
# by category — every row in them (not just ones literally named 'pending'
# or 'cost') is bad-when-high, since they're all just a split of the same
# backlog / spend total.
INVERT_TABLE_TITLE_WORDS = ("service due", "urgent service", "budget tracking")

# ...except a few rows that move the opposite way even inside an inverted
# table (e.g. remaining budget going up is good, not bad).
NOT_INVERTED_OVERRIDE_WORDS = ("budget available", "fleet", "reconnect", "alloted %", "allocated")


def table_is_inverted(table_title):
    t = table_title.lower()
    return any(w in t for w in INVERT_TABLE_TITLE_WORDS)


def row_is_inverted(label):
    l = label.lower()
    return any(w in l for w in BAD_WHEN_HIGH_WORDS)


def compute_row_invert(label, table_title):
    l = label.lower()
    if any(w in l for w in NOT_INVERTED_OVERRIDE_WORDS):
        return False
    if row_is_inverted(label):
        return True
    return table_is_inverted(table_title)


DATE_RE = re.compile(
    r"^(\d{1,2}[\-\s][A-Za-z]{3}(\-\d{2,4})?|[A-Za-z]{3}[\-\s]\d{1,2}(,?\s?\d{2,4})?|\d{1,2}/\d{1,2}/\d{2,4})$",
    re.IGNORECASE,
)
SUMMARY_WORDS = ("change", "wow", "delta", "vs lw", "vs. lw", "% change")


def is_summary_col(h):
    hl = h.strip().lower()
    return any(w in hl for w in SUMMARY_WORDS) and not DATE_RE.match(h.strip())


def date_score(row):
    return sum(1 for c in row if DATE_RE.match(c.strip()))


def humanize_header(h):
    """Some source headers are multi-level headers concatenated without
    spaces during doc extraction (e.g. 'AllotedBranding DoneCars'). Insert
    spaces at lower->upper and letter->hyphen boundaries so they wrap
    legibly instead of running together."""
    h = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", h)
    h = re.sub(r"(?<=[A-Za-z])(?=-[A-Za-z])", " ", h)
    h = re.sub(r"\s+", " ", h).strip()
    return h


def normalize_table(raw, max_rows=10, max_cols=6):
    if not raw or len(raw) < 2:
        return None

    # Strip a leading date-range preamble + blank rows some source tables
    # carry before the real header (e.g. 'Start Date | End Date' / 'Start
    # From Date >>...'), so header detection isn't confused by them.
    skip = 0
    while skip < len(raw) and skip < 4:
        r = raw[skip]
        joined = " ".join(c for c in r).lower()
        non_empty = [c for c in r if c.strip()]
        if (
            not any(c.strip() for c in r)
            or "start date" in joined or "start from date" in joined
            or ("end date" in joined and len(r) <= 3)
            or len(non_empty) <= 1
        ):
            skip += 1
        else:
            break
    if skip:
        raw = raw[skip:]
        if len(raw) < 2:
            return None

    # Pick the best header row among the first few rows (the one with the
    # most date-like cells) — some source tables have a non-header first row.
    candidates = raw[:3]
    best_idx = max(range(len(candidates)), key=lambda i: date_score(candidates[i]))
    no_heat = False
    header = None
    body = None
    if date_score(candidates[best_idx]) == 0:
        # No weekly-date columns — this is a snapshot/count table, not a
        # trend table. If it's at least a clean, consistent grid, render it
        # as a plain (non-heat-mapped) table instead of dropping to raw text.
        header0 = raw[0]
        body_check = raw[1:6]
        consistent = body_check and all(len(r) == len(header0) for r in body_check if any(c.strip() for c in r))
        if consistent and len(header0) >= 2:
            best_idx = 0
            no_heat = True
            header = header0
            body = raw[1:]
        else:
            # Two-row header: row0 is a colspan group row (e.g. 'Expired'
            # spanning several sub-columns, with '' for the spanned cells),
            # row1 the real sub-header (e.g. 'EV'/'ETS'/'CNG') — merge them
            # instead of dropping the table to a raw-text fallback.
            header1 = raw[1] if len(raw) > 1 else None
            body_check2 = raw[2:7]
            consistent2 = (
                header1 and body_check2
                and all(len(r) == len(header0) for r in body_check2 if any(c.strip() for c in r))
            )
            if not consistent2 or len(header0) < 2:
                return None
            group_filled = []
            last = ""
            for c in header0:
                if c.strip():
                    last = c.strip()
                group_filled.append(last)
            merged_header = []
            for i in range(len(header0)):
                g = group_filled[i] if group_filled[i] not in ("*", "-") else ""
                s = header1[i].strip() if i < len(header1) and header1[i].strip() not in ("*", "-") else ""
                merged = (g + " " + s).strip() if (g and s and g != s) else (s or g)
                merged_header.append(merged or header0[i])
            header = merged_header
            no_heat = True
            body = raw[2:]

    if header is None:
        header = raw[best_idx]
        body = raw[best_idx + 1:]

    data_start = len(header)
    for i, h in enumerate(header):
        if DATE_RE.match(h.strip()):
            data_start = i
            break
    if data_start == 0:
        data_start = 1
    if data_start >= len(header):
        data_start = 1 if no_heat else max(1, len(header) - 5)

    label_header = " · ".join(h for h in header[:data_start] if h) or "Metric"
    raw_data_headers = header[data_start:]

    # Some source tables (e.g. "Agent Level OB") are genuinely wide-format:
    # multiple metric blocks side by side, each its own [metric-name col,
    # date-run, WoW col] — not a single trailing/duplicated summary column.
    # Split into blocks so each metric gets its own row with only its own
    # dates, instead of mixing two metrics' values into one row.
    if no_heat:
        blocks = [(None, list(range(len(raw_data_headers))))]
    else:
        blocks = []
        i, n = 0, len(raw_data_headers)
        while i < n and not raw_data_headers[i].strip():
            i += 1  # skip a leading blank separator column
        while i < n:
            metric_col = None
            if raw_data_headers[i].strip() and not DATE_RE.match(raw_data_headers[i].strip()) and not is_summary_col(raw_data_headers[i]):
                metric_col = i
                i += 1
            while i < n and not raw_data_headers[i].strip():
                i += 1  # skip a blank separator column between blocks
            date_idxs = []
            while i < n and DATE_RE.match(raw_data_headers[i].strip()):
                date_idxs.append(i)
                i += 1
            while i < n and is_summary_col(raw_data_headers[i]):
                i += 1
            if date_idxs:
                blocks.append((metric_col, date_idxs))
            elif metric_col is not None:
                break
            else:
                i += 1
        if not blocks:
            return None

    # Some multi-block tables carry the block's group name (e.g. "New Join",
    # "Rejoin") in the row ABOVE the date header, one cell per block (via
    # colspan in the source), rather than inline as its own column. Recover
    # it so blocks don't end up with indistinguishable labels.
    group_labels = [None] * len(blocks)
    if len(blocks) > 1 and best_idx > 0:
        group_row = raw[best_idx - 1]
        if len(group_row) == 1 + len(blocks):
            for b_i in range(len(blocks)):
                g = (group_row[1 + b_i] or "").strip()
                if g and g not in ("*", "-"):
                    group_labels[b_i] = g

    data_headers_full = [raw_data_headers[j] for j in blocks[0][1]]
    if not data_headers_full:
        return None

    data_headers = data_headers_full
    trim = len(data_headers_full) - min(len(data_headers_full), max_cols)
    if trim:
        data_headers = data_headers_full[trim:]
        blocks = [(mc, idxs[trim:]) for mc, idxs in blocks]

    any_named_block = any(group_labels) or any(mc is not None for mc, _ in blocks)

    out_rows = []
    section_prefix = None
    found_section_marker = False
    for r in body:
        if not r or not any(c.strip() for c in r):
            continue
        # Some tables stack multiple mini-tables vertically, each with its
        # own repeated header row (e.g. 'New Join' / 'Resurrection' / 'Total
        # Supply', each followed by the same date columns again). A real
        # data row never contains date-formatted cells, so treat any body
        # row that does as a new section marker rather than data.
        if not no_heat and date_score(r) >= max(2, len(raw_data_headers) // 2):
            section_prefix = (r[0] or "").strip()
            found_section_marker = True
            continue
        # Per-row label boundary: some source rows carry one label cell,
        # others two (e.g. a metric name + a sub-label) before the numbers
        # start — detect it per row instead of trusting the header's fixed
        # position, which only holds for rows shaped like the header.
        row_split = None
        scan_width = 1 if no_heat else 4
        for i in range(min(data_start + scan_width, len(r))):
            if parse_num(r[i]) is not None:
                row_split = i
                break
        if row_split is None or row_split == 0:
            row_split = data_start if data_start <= len(r) else 1
        # 3+ prefix cells before the first number is usually stray extracted
        # noise (not real sub-labels) — keep just the row's own name rather
        # than joining it with cells that don't add clear meaning.
        if row_split > 2:
            base_label = r[0].strip() or "-"
        else:
            base_label = " · ".join(c for c in r[:row_split] if c.strip()) or "-"
        agent_id = r[0].strip() if r and r[0].strip() else base_label
        r_data = r[row_split: row_split + len(raw_data_headers)]
        r_data = r_data + [""] * (len(raw_data_headers) - len(r_data))

        for b_i, (metric_col, date_idxs) in enumerate(blocks):
            metric_val = r_data[metric_col].strip() if metric_col is not None and metric_col < len(r_data) else ""
            group_val = group_labels[b_i]
            if b_i == 0 and not group_val:
                label = base_label
            elif group_val:
                label = f"{agent_id} · {group_val}" + (f" · {metric_val}" if metric_val else "")
            elif metric_val:
                label = f"{agent_id} · {metric_val}"
            else:
                label = agent_id
            vals = [r_data[j] if j < len(r_data) else "" for j in date_idxs]
            vals = vals + [""] * (len(data_headers) - len(vals))
            # Disambiguate identically-labelled blocks (e.g. a raw-count
            # block and a %-of-total block side by side with no metric-name
            # column of their own) by what their own values look like.
            if len(blocks) > 1 and not any_named_block:
                if any("%" in v for v in vals if v):
                    label += " (%)"
                elif b_i == 0:
                    label += " (count)"
            if section_prefix:
                label = f"{section_prefix} · {label}"
            out_rows.append([label] + vals)
            if len(out_rows) >= max_rows:
                break
        if len(out_rows) >= max_rows:
            break

    if not out_rows:
        return None
    disp_headers = [humanize_header(h) for h in [label_header] + data_headers]
    return {"headers": disp_headers, "rows": out_rows, "no_heat": no_heat}


def compute_insight(section_title, table_title, norm):
    """Factual, computed observations only — no invented commentary."""
    headers = norm["headers"]
    rows = norm["rows"]
    no_heat = norm.get("no_heat", False)
    last_col_header = headers[-1] if len(headers) > 1 else ""

    best_row, best_val, worst_row, worst_val = None, None, None, None
    movers = []
    for r in rows:
        label = r[0]
        vals = r[1:]
        nums = [(headers[1 + i], parse_num(v)) for i, v in enumerate(vals)]
        nums = [(h, v) for h, v in nums if v is not None]
        if not nums:
            continue
        last_h, last_v = nums[-1]
        if best_val is None or last_v > best_val:
            best_val, best_row = last_v, label
        if worst_val is None or last_v < worst_val:
            worst_val, worst_row = last_v, label
        if not no_heat and len(nums) >= 2:
            prev_v = nums[-2][1]
            if prev_v:
                pct = (last_v - prev_v) / abs(prev_v) * 100
                movers.append((label, prev_v, last_v, pct))

    if no_heat:
        headline = f"{table_title} — {len(rows)} metric row(s), current snapshot."
        if best_row is not None:
            headline = f"{table_title}: {best_row} highest at {best_val:g} ({last_col_header})."
        callouts = [(r[0], f"{last_col_header}: {r[-1]}") for r in rows[:3] if len(r) > 1]
        read = ""
        if best_row is not None and worst_row is not None and best_row != worst_row:
            read = f"Read: {best_row} highest at {best_val:g}, {worst_row} lowest at {worst_val:g} ({last_col_header})."
        return headline, callouts, read

    headline = f"{table_title} — {len(rows)} metric row(s) shown for the week of {last_col_header}."
    if best_row is not None:
        headline = f"{best_row} led at {best_val:g} in the week of {last_col_header}."

    movers.sort(key=lambda m: abs(m[3]), reverse=True)
    callouts = []
    for label, prev_v, last_v, pct in movers[:3]:
        direction = "up" if pct >= 0 else "down"
        callouts.append((label, f"{prev_v:g} → {last_v:g} ({direction} {abs(pct):.0f}% vs previous week)."))

    read = ""
    if best_row is not None and worst_row is not None and best_row != worst_row:
        read = f"Read: {best_row} was highest at {best_val:g} and {worst_row} lowest at {worst_val:g} in the week of {last_col_header}."
    elif best_row is not None:
        read = f"Read: {best_row} stood at {best_val:g} in the week of {last_col_header}."

    return headline, callouts, read


def add_text(reqs, obj_id, page_id, x, y, w, h, text, font_size, bold, color, align="START", font="Helvetica Neue", link=None, underline=False, valign="MIDDLE"):
    reqs.append({
        "createShape": {
            "objectId": obj_id,
            "shapeType": "TEXT_BOX",
            "elementProperties": {
                "pageObjectId": page_id,
                "size": {"width": in_(w), "height": in_(h)},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": pos(x), "translateY": pos(y), "unit": "EMU"},
            },
        }
    })
    reqs.append({
        "updateShapeProperties": {
            "objectId": obj_id,
            "shapeProperties": {"contentAlignment": valign},
            "fields": "contentAlignment",
        }
    })
    if not text:
        return
    reqs.append({"insertText": {"objectId": obj_id, "text": text}})
    style = {
        "fontFamily": font,
        "fontSize": {"magnitude": pt(font_size), "unit": "PT"},
        "bold": bold,
        "underline": underline,
        "foregroundColor": {"opaqueColor": {"rgbColor": color}},
    }
    fields = "fontFamily,fontSize,bold,underline,foregroundColor"
    if link:
        style["link"] = {"url": link}
        fields += ",link"
    reqs.append({"updateTextStyle": {"objectId": obj_id, "style": style, "fields": fields}})


def add_rich_text(reqs, obj_id, page_id, x, y, w, h, part1, part2, font_size, font="Helvetica Neue", valign="MIDDLE"):
    """One text box, two runs: part1 = (text, color, bold) in normal flow,
    part2 = (text, color, link) appended right after it, underlined — used
    for 'description text. Source: link' on a single line like the reference."""
    reqs.append({
        "createShape": {
            "objectId": obj_id,
            "shapeType": "TEXT_BOX",
            "elementProperties": {
                "pageObjectId": page_id,
                "size": {"width": in_(w), "height": in_(h)},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": pos(x), "translateY": pos(y), "unit": "EMU"},
            },
        }
    })
    reqs.append({
        "updateShapeProperties": {
            "objectId": obj_id,
            "shapeProperties": {"contentAlignment": valign},
            "fields": "contentAlignment",
        }
    })
    t1, c1, b1 = part1
    t2, c2, link2 = part2
    full_text = t1 + t2
    reqs.append({"insertText": {"objectId": obj_id, "text": full_text}})
    reqs.append({
        "updateTextStyle": {
            "objectId": obj_id,
            "textRange": {"type": "FIXED_RANGE", "startIndex": 0, "endIndex": len(t1)},
            "style": {
                "fontFamily": font,
                "fontSize": {"magnitude": pt(font_size), "unit": "PT"},
                "bold": b1,
                "foregroundColor": {"opaqueColor": {"rgbColor": c1}},
            },
            "fields": "fontFamily,fontSize,bold,foregroundColor",
        }
    })
    if t2:
        style2 = {
            "fontFamily": font,
            "fontSize": {"magnitude": pt(font_size), "unit": "PT"},
            "bold": False,
            "underline": bool(link2),
            "foregroundColor": {"opaqueColor": {"rgbColor": c2}},
        }
        fields2 = "fontFamily,fontSize,bold,underline,foregroundColor"
        if link2:
            style2["link"] = {"url": link2}
            fields2 += ",link"
        reqs.append({
            "updateTextStyle": {
                "objectId": obj_id,
                "textRange": {"type": "FIXED_RANGE", "startIndex": len(t1), "endIndex": len(full_text)},
                "style": style2,
                "fields": fields2,
            }
        })


def add_rect(reqs, obj_id, page_id, x, y, w, h, fill_color, border=True, border_color=None):
    reqs.append({
        "createShape": {
            "objectId": obj_id,
            "shapeType": "RECTANGLE",
            "elementProperties": {
                "pageObjectId": page_id,
                "size": {"width": in_(w), "height": in_(h)},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": pos(x), "translateY": pos(y), "unit": "EMU"},
            },
        }
    })
    bc = border_color or BORDER
    reqs.append({
        "updateShapeProperties": {
            "objectId": obj_id,
            "shapeProperties": {
                "shapeBackgroundFill": {"solidFill": {"color": {"rgbColor": fill_color}}},
                "outline": {
                    "outlineFill": {"solidFill": {"color": {"rgbColor": bc}}},
                    "weight": {"magnitude": pt(1.0), "unit": "PT"},
                } if border else {"propertyState": "NOT_RENDERED"},
            },
            "fields": "shapeBackgroundFill.solidFill.color,outline",
        }
    })


_ctr = [0]
def next_id(page_id, prefix):
    _ctr[0] += 1
    return f"{page_id}_{prefix}{_ctr[0]}"


def build_fallback_slide(page_id, section_title, table_title, raw, source_url):
    """For tables with irregular/multi-level headers that can't be safely
    auto-tabulated — show raw rows as plain text rather than dropping them."""
    reqs = [{"createSlide": {"objectId": page_id, "slideLayoutReference": {"predefinedLayout": "BLANK"}}}]
    add_text(reqs, next_id(page_id, "cat"), page_id, 0.4, 0.22, 12.5, 0.3, f"{section_title} - {table_title}", 11, False, GRAY_TEXT)
    add_text(reqs, next_id(page_id, "hl"), page_id, 0.4, 0.5, 12.5, 0.85,
              f"{table_title} — irregular table structure, shown as raw rows.", 20, True, DARK)
    add_rect(reqs, next_id(page_id, "div"), page_id, 0.4, 1.42, 12.53, 0.025, DARK, border=False)
    add_text(reqs, next_id(page_id, "subicn"), page_id, 0.4, 1.53, 0.2, 0.28, "🔗", 11, False, GRAY_TEXT)
    add_text(reqs, next_id(page_id, "sub"), page_id, 0.62, 1.53, 6.0, 0.28, "Source: BLR WBR doc", 11, False, LINK_BLUE, link=source_url, underline=True)

    y = 2.0
    max_lines = 18
    for i, r in enumerate((raw or [])[:max_lines]):
        line = " | ".join(c for c in r if c.strip())[:150]
        bold = i == 0
        add_text(reqs, next_id(page_id, f"ln{i}"), page_id, 0.4, y, 12.5, 0.25, line, 10, bold, DARK)
        y += 0.26

    add_text(reqs, next_id(page_id, "ft"), page_id, 0.4, 7.15, 10.0, 0.28,
              "Everest Fleet  ·  BLR Weekly City Review  ·  Strategy & Analytics", 9, False, GRAY_TEXT)
    return reqs


def build_section_title_slide(page_id, section_title, poc):
    """White section-divider slide matching the reference's own divider
    format: short black rule, big bold title, a bordered subtitle box,
    a thin rule, credit + prep lines, a bold operating note, and footer."""
    reqs = [{"createSlide": {"objectId": page_id, "slideLayoutReference": {"predefinedLayout": "BLANK"}}}]

    add_rect(reqs, next_id(page_id, "rule"), page_id, 0.6, 2.35, 1.1, 0.06, BLACK, border=False)
    add_text(reqs, next_id(page_id, "st"), page_id, 0.55, 2.55, 12.2, 1.0, section_title, 34, True, BLACK)

    sub = f"{section_title}  —  POC: {poc}" if poc else section_title
    add_rect(reqs, next_id(page_id, "subbox"), page_id, 0.6, 3.65, 12.13, 0.5, WHITE, border_color=BORDER)
    add_text(reqs, next_id(page_id, "subtxt"), page_id, 0.75, 3.65, 11.83, 0.5, sub, 15, False, DARK)

    add_rect(reqs, next_id(page_id, "rule2"), page_id, 0.6, 4.3, 12.13, 0.012, BORDER, border=False)
    add_text(reqs, next_id(page_id, "cred"), page_id, 0.6, 4.45, 12.13, 0.3,
              "Everest Fleet  ·  BLR Weekly City Review  ·  Bangalore data only", 11, False, GRAY_TEXT)
    add_rich_text(
        reqs, next_id(page_id, "prep"), page_id, 0.6, 4.75, 12.13, 0.3,
        part1=(f"Prepared by Strategy & Analytics", GRAY_TEXT, False),
        part2=(f"  ·  POC: {poc}" if poc else "", GRAY_TEXT, None),
        font_size=11,
    )

    add_rich_text(
        reqs, next_id(page_id, "note1"), page_id, 0.6, 5.85, 12.13, 0.5,
        part1=("Bangalore data only. ", BLACK, True),
        part2=("Blank, ‘-’ and ‘y’ cells are treated as zero throughout this deck.", BLACK, None),
        font_size=13,
    )
    add_text(reqs, next_id(page_id, "note2"), page_id, 0.6, 6.2, 12.13, 0.4,
              "Colour coding: green = higher in range, red = lower in range, relative per row.", 10.5, False, GRAY_TEXT, valign="TOP")

    add_text(reqs, next_id(page_id, "ft"), page_id, 0.4, 7.15, 10.0, 0.28,
              "Everest Fleet  ·  BLR Weekly City Review  ·  Strategy & Analytics", 9, False, GRAY_TEXT)
    return reqs


GREEN_TXT = {"red": 0.20, "green": 0.55, "blue": 0.30}
RED_TXT = {"red": 0.80, "green": 0.25, "blue": 0.20}
FOOTER_BG = {"red": 0.12, "green": 0.12, "blue": 0.12}


def build_metrics_slide(page_id, section_title, table_title, table, source_url, week_no):
    headers = table["headers"]
    rows = table["rows"]
    headline, callout_items, read_line = compute_insight(section_title, table_title, table)

    reqs = [{"createSlide": {"objectId": page_id, "slideLayoutReference": {"predefinedLayout": "BLANK"}}}]

    # 1. small breadcrumb label
    add_text(reqs, next_id(page_id, "cat"), page_id, 0.4, 0.22, 12.5, 0.3, f"{section_title} - {table_title}", 9, True, GRAY_TEXT)
    # 2. big bold headline (the insight)
    add_text(reqs, next_id(page_id, "hl"), page_id, 0.4, 0.5, 12.5, 0.85, headline, 17, True, DARK)
    # 3. divider
    add_rect(reqs, next_id(page_id, "div"), page_id, 0.4, 1.42, 12.53, 0.025, DARK, border=False)
    # 4. subtitle sentence + inline clickable source, one line (matches reference)
    add_rich_text(
        reqs, next_id(page_id, "sub"), page_id, 0.4, 1.53, 9.5, 0.28,
        part1=(f"Weekly {table_title}, by row, complete weeks only.  ", DARK, False),
        part2=("Source: BLR WBR doc", LINK_BLUE, source_url),
        font_size=10.5,
    )
    # 5. table section label
    add_text(reqs, next_id(page_id, "tt"), page_id, 0.4, 1.9, 8.0, 0.32, table_title, 11, True, DARK)

    label_w = 2.6
    n_cols = len(headers) - 1
    data_w = 6.0
    col_w = data_w / max(n_cols, 1)
    x0 = 0.4
    y = 2.35
    row_h = 0.38 if len(rows) <= 8 else max(0.26, 3.0 / max(len(rows), 1))
    lbl_font = 9 if row_h >= 0.32 else 7.5
    val_font = 9.5 if row_h >= 0.32 else 7.5

    # Header cells can hold long, multi-word text (source tables with
    # concatenated multi-level headers) — size the header row tall enough
    # to fit the wrapped text instead of clipping it.
    hdr_font = 9
    chars_per_line = max(6, int(col_w * 11))
    max_hdr_len = max([len(h) for h in headers[1:]], default=0)
    hdr_lines = max(1, -(-max_hdr_len // chars_per_line))
    hdr_row_h = max(row_h, 0.2 * hdr_lines + 0.16)

    add_rect(reqs, next_id(page_id, "hc0"), page_id, x0, y, label_w, hdr_row_h, BLACK, border_color=WHITE)
    add_text(reqs, next_id(page_id, "ht0"), page_id, x0 + 0.05, y, label_w - 0.1, hdr_row_h, headers[0], hdr_font, True, WHITE)
    for c in range(n_cols):
        cx = x0 + label_w + c * col_w
        add_rect(reqs, next_id(page_id, f"hc{c+1}"), page_id, cx, y, col_w, hdr_row_h, BLACK, border_color=WHITE)
        add_text(reqs, next_id(page_id, f"ht{c+1}"), page_id, cx + 0.03, y, col_w - 0.06, hdr_row_h, headers[c + 1], hdr_font, True, WHITE, align="CENTER")

    ry = y + hdr_row_h
    for row in rows:
        label = row[0]
        values = row[1:]
        colors = row_heat_colors(values, invert=compute_row_invert(label, table_title))
        add_rect(reqs, next_id(page_id, "lc"), page_id, x0, ry, label_w, row_h, LABEL_BG, border_color=WHITE)
        add_text(reqs, next_id(page_id, "lt"), page_id, x0 + 0.05, ry, label_w - 0.1, row_h, label, lbl_font, False, DARK)
        for c, val in enumerate(values):
            cx = x0 + label_w + c * col_w
            fill = colors[c]
            fill_rgb = {"red": fill[0], "green": fill[1], "blue": fill[2]} if fill else WHITE
            add_rect(reqs, next_id(page_id, "dc"), page_id, cx, ry, col_w, row_h, fill_rgb, border_color=WHITE)
            add_text(reqs, next_id(page_id, "dt"), page_id, cx + 0.02, ry, col_w - 0.04, row_h, val, val_font, False, DARK, align="CENTER")
        ry += row_h

    table_bottom = ry

    # 6. Read: summary line below the table (bold "Read:" prefix, like reference)
    if read_line:
        assert read_line.startswith("Read: ")
        add_rich_text(
            reqs, next_id(page_id, "read"), page_id, x0, table_bottom + 0.14, 8.6, 0.55,
            part1=("Read:  ", DARK, True),
            part2=(read_line[len("Read: "):], DARK, None),
            font_size=10.5,
        )

    # 7. legend
    add_text(reqs, next_id(page_id, "leg"), page_id, x0, 6.75, 8.6, 0.3,
              "Green = better · Red = worse (relative, per row)", 9, False, GRAY_TEXT)

    # 8. footer — plain small gray text, no bar (matches reference: no dark
    # footer band, just quiet credit line + page number on white)
    add_text(reqs, next_id(page_id, "ft"), page_id, 0.4, 7.15, 10.0, 0.28,
              "Everest Fleet  ·  BLR Weekly City Review  ·  Strategy & Analytics", 9, False, GRAY_TEXT)
    add_text(reqs, next_id(page_id, "ftpg"), page_id, 12.6, 7.15, 0.6, 0.28, str(week_no), 9, False, GRAY_TEXT, align="END")

    # call-out box (right side) — concerns (red) on top, a divider, then a
    # single combined "DOING WELL" (green) block below, per the reference.
    def is_bad_move(item):
        lbl, body = item
        up = "(up" in body
        down = "(down" in body
        if not (up or down):
            return None
        return up if compute_row_invert(lbl, table_title) else down

    concerns = [c for c in callout_items if is_bad_move(c) is True]
    wins = [c for c in callout_items if is_bad_move(c) is False]
    neutral = [c for c in callout_items if is_bad_move(c) is None]

    cx0, cy0, cw = 9.2, 2.35, 3.0
    content_h = 0.6 + 0.15
    if not callout_items:
        content_h += 0.4
    content_h += len(concerns + neutral) * 0.85
    if wins:
        content_h += (0.18 if (concerns or neutral) else 0) + 0.3 + 0.85
    ch = min(max(content_h, table_bottom + 0.3 - cy0), 6.6 - cy0)
    add_rect(reqs, next_id(page_id, "cob"), page_id, cx0, cy0, cw, ch, WHITE, border_color=BLACK)
    add_rect(reqs, next_id(page_id, "cobh"), page_id, cx0, cy0, cw, 0.4, BLACK, border=False)
    add_text(reqs, next_id(page_id, "coh"), page_id, cx0 + 0.15, cy0 + 0.08, cw - 0.3, 0.3, "FLAGS — CALL-OUTS", 9.5, True, WHITE)
    cy = cy0 + 0.6
    if not callout_items:
        add_text(reqs, next_id(page_id, "cone"), page_id, cx0 + 0.15, cy, cw - 0.3, 0.4, "No significant week-over-week movers.", 9, False, GRAY_TEXT)

    for label, body in concerns + neutral:
        head_color = RED_TXT if (label, body) in concerns else DARK
        add_text(reqs, next_id(page_id, "ch"), page_id, cx0 + 0.15, cy, cw - 0.3, 0.25, label, 9, True, head_color)
        cy += 0.3
        add_text(reqs, next_id(page_id, "cb"), page_id, cx0 + 0.15, cy, cw - 0.3, 0.5, body, 9, False, GRAY_TEXT)
        cy += 0.55

    if wins:
        if concerns or neutral:
            add_rect(reqs, next_id(page_id, "codiv"), page_id, cx0 + 0.15, cy, cw - 0.3, 0.012, BORDER, border=False)
            cy += 0.18
        names = " AND ".join(label.split(" · ")[0].upper() for label, _ in wins[:2])
        add_text(reqs, next_id(page_id, "cwh"), page_id, cx0 + 0.15, cy, cw - 0.3, 0.25, f"DOING WELL — {names}", 9, True, GREEN_TXT)
        cy += 0.3
        combined_body = "  ".join(f"{label}: {body}" for label, body in wins[:2])
        add_text(reqs, next_id(page_id, "cwb"), page_id, cx0 + 0.15, cy, cw - 0.3, 0.8, combined_body, 9, False, GRAY_TEXT)
        cy += 0.85

    return reqs


# ---- Section -> (poc, list of (doc table index, table_title override)) ----
SECTIONS = [
    ("City Overview", "Shivraju", [(2, "Bangalore — Weekly Summary")]),
    ("Workshop Overview", "Gouav", [(24, "EFG Review"), (25, "Service Due Vehicle Plan Wise"), (26, "Urgent Service"),
                             (27, "City Wise Weekly Budget Tracking"), (28, "City Wise Weekly Budget Tracking (2)"),
                             (29, "Revisit"), (30, "Driver Wanted Sticker Installation"), (31, "Installation Count"),
                             (32, "Driver Wanted (Metal Plate / Stickers)"), (33, "Washing Report"),
                             (34, "Washing Report — Weekly"), (35, "Fitness Cars Status Report"),
                             (37, "Vehicles Movement — Top Issues"), (38, "Saturday Reco Report"),
                             (39, "Team-wise Petrol Consumption"), (40, "Funnel View"), (41, "BLR_KEY_Master — CNG")]),
    ("VMT Overview", "Sathish", [(36, "Vehicles Movement Weekly-Wise Report")]),
    ("EIP -Sharath", "Sharath", [(43, "EIP — Bangalore")]),
    ("DTO - Srinivas", "Srinivas", [(44, "Drive To Own — Product Overview")]),
    ("Own Now", "Srinivas", [(45, "OWN NOW — Product Overview"), (46, "Input Metrics")]),
    ("Helpdesk", "Nuthan", [(50, "Help Desk Dash")]),
    ("Support", "Nuthan", [(47, "Weekly Trend"), (48, "Issue Health Summary [Top 15 Dispositions]"), (49, "Input Metrics — Support")]),
    ("Collection", "Vikas", [(51, "Collections — Bangalore"), (52, "Input Metrics — Collection")]),
    ("Car Recovery", "Vikas", [(53, "Car Recovery"), (54, "Agent / Vendor-wise"), (55, "Agent / Vendor-wise (2)"), (56, "Agent-wise Cash Collection")]),
    ("CNG Operations", "Vikas", [(57, "Car Utilization — CNG")]),
    ("EV Operations", "Ashwin", [(58, "Car Utilization — EV")]),
    ("EV SSOT Overview", "Ashwin", [(42, "BLR_KEY_Master — EV")]),
    ("On Boarding", "Nikitha", [(21, "Onboarding — Bangalore"), (22, "Agent Level OB"), (23, "Not Allotted Reasons")]),
    ("Vendor Channel", "Lokesh/Ikram", [(19, "Vendor — New Leads"), (20, "Vendor Level")]),
    ("Rejoin and Resurrection", "Ram", [(14, "Rejoin"), (15, "TC Metrics Rejoining"), (16, "Split Days"),
                                   (17, "Resurrection"), (18, "TC Metrics Resurrection")]),
    ("Referral Channel", "Ram", [(11, "Referral Funnel"), (12, "New Referral Dash (Non Funnel)"), (13, "City Referral Project")]),
    ("Perf Marketing", "Ram", [(4, "Funnel Perf_Marketing"), (5, "Speed of Funnel"), (6, "Funnel Leads"),
                          (7, "Funnel Conversions"), (8, "Allocation Split: Performance Marketing"),
                          (9, "Inbound Report — Perf Marketing"), (10, "Outbound Efficiency — Perf Marketing")]),
    ("Discussion", None, []),
]

pres = slides.presentations().get(presentationId=PRES_ID).execute()
existing_slide_ids = [s["objectId"] for s in pres["slides"]]
print("existing slides:", existing_slide_ids)

reqs_all = []
seq = 0
for section_title, poc, tables in SECTIONS:
    seq += 1
    tsid = f"v17sc{seq:02d}"
    reqs_all += build_section_title_slide(tsid, section_title, poc)
    if not tables:
        continue
    for j, (tidx, ttitle) in enumerate(tables):
        raw = ALL_TABLES.get(tidx)
        norm = normalize_table(raw, max_rows=8)
        pid = f"v17tb{seq:02d}_{j:02d}"
        if norm:
            reqs_all += build_metrics_slide(
                pid,
                section_title=section_title,
                table_title=ttitle,
                table=norm,
                source_url=DOC_URL,
                week_no=seq,
            )
        else:
            reqs_all += build_fallback_slide(pid, section_title, ttitle, raw, DOC_URL)

print("total requests:", len(reqs_all))

# batch in chunks of ~500 requests to stay well under API limits
CHUNK = 400
for i in range(0, len(reqs_all), CHUNK):
    chunk = reqs_all[i:i + CHUNK]
    slides.presentations().batchUpdate(presentationId=PRES_ID, body={"requests": chunk}).execute()
    print("submitted", i + len(chunk), "/", len(reqs_all))
    time.sleep(1)

# now that new slides exist, delete the old ones (safe — presentation never
# drops to 0 slides at any point)
if existing_slide_ids:
    del_reqs = [{"deleteObject": {"objectId": sid}} for sid in existing_slide_ids]
    slides.presentations().batchUpdate(presentationId=PRES_ID, body={"requests": del_reqs}).execute()
    print("deleted", len(existing_slide_ids), "old slides")

print("done. view_url:", f"https://docs.google.com/presentation/d/{PRES_ID}/edit")
