---
name: news
description: "Build the weekly Collections Newsletter (Week of Hissab / WBR newsletter / collections weekly) as a Gmail draft with inline HTML. Use when the user types /news or asks to generate, update or edit the weekly collections newsletter."
---

# Collections Newsletter — Production Skill

Weekly newsletter titled **"Week of Hissab"**, covering Everest Fleet's pan-India collections
performance across 7 cities: Mumbai, Kolkata, Bangalore, Delhi NCR, Hyderabad, Chennai, Pune.

**The deliverable is a Gmail draft with the newsletter inline as HTML** — not an attachment.
A DOCX copy is produced alongside it for the archive folder.

---

## ⚠ Two reference files carry WRONG colours — do not follow them

The grey-header defect shipped for several weeks because two files in `references/` specify a light
header and they corroborate each other:

- **`mail-html.md`** (old file, deliberately NOT included in this skill) — **OBSOLETE, do not follow.** It describes a retired
  `newsletter_body.html` / `mkdocx.py` / `mkmail.py` pipeline that no longer exists, and its
  "Table geometry" section specifies header `bgcolor="#f5f5f5"` with `color:#777`, alt rows
  `#fafafa` and `bordercolor="#e6e6e6"` — all wrong. Its type scale (21px title, 17px heading,
  12px body, 11px cells) is also wrong. Ignore this file entirely.
- **`references/docx-specs.md`** — its **Palette** section (`Header fill 333333`, white text) is
  CORRECT; its **"CRITICAL: the DOCX must mirror the HTML mail"** block near the end is WRONG
  (`f5f5f5` / `777777` / `fafafa`). Use this file for **geometry only** — column widths, margins,
  page-break discipline, the tblGrid trap.

The House Style table below overrides both. When in doubt, the fetched sent mail wins over every
file in this skill.

---

## Golden Rules

1. **The most recent SENT MAIL is the format spec — fetch its HTML, not its text.**
   `Gmail.search_threads` for `subject:"Weekly Collections Newsletter"`, then `get_message` with
   `messageFormat: FULL_CONTENT` and pull `htmlBody`. `PLAIN_TEXT` gives content and section order
   but **no formatting** — building from it reproduces last week's words with this skill's colours,
   which is exactly how the defect shipped. The result is usually too large for context: it is
   auto-saved to a file — `jq -r '.htmlBody'` it out and diff the style tokens with a script.
2. **Never fabricate a metric to fill a row.** If the source data has no such block, drop the row
   and say so. Precedent: "Recovery with Advances" was removed from the KPI table for this reason.
3. **Verify every cell AND every style token programmatically before delivery.** Not optional.
4. **Draft, never send.** The user reviews and sends.

---

## House Style — authoritative

Lifted verbatim from the sent mail. Re-confirm against this week's fetched HTML anyway.

| Element | Exact markup |
|---|---|
| Wrapper (font set once, inherited) | `<div style="max-width:900px;font-family:Calibri,Arial,sans-serif;font-size:13px;color:#2f2f2f;line-height:1.4">` |
| Title | `<div style="font-size:22px;font-weight:700;color:#2f2f2f;text-align:center;margin:0 0 2px">` |
| Week line | `<div style="font-size:14px;color:#666666;text-align:center;margin:0 0 14px">` |
| Section heading | `<div style="font-size:15px;font-weight:700;border-bottom:1px solid #d9d9d9;padding-bottom:3px;margin:18px 0 8px">` |
| Sub-heading ("Key Insights") | `<div style="font-weight:700;margin:8px 0 4px">` |
| Italic note line | `<div style="font-size:11px;font-style:italic;color:#808080;margin:0 0 6px">` |
| Table | `<table border="1" cellpadding="7" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:13px;margin:6px 0 10px">` |
| **Header row** | `<tr align="center" bgcolor="#333333" style="color:#ffffff;font-weight:700">` — **dark charcoal, white text** |
| Overall row | `<tr align="center" bgcolor="#f2f2f2" style="color:#2f2f2f;font-weight:700">` |
| Banded row | `<tr align="center" bgcolor="#f7f7f7" style="color:#2f2f2f">` |
| Plain row | `<tr align="center" bgcolor="#ffffff" style="color:#2f2f2f">` |
| Bullet list | `<ul style="line-height:1.5;margin:4px 0 10px;padding-left:20px">` |
| Paragraph | `<p style="margin:6px 0">` |
| Footer | `<div style="font-size:11px;color:#808080;border-top:1px solid #d9d9d9;padding-top:6px;margin-top:14px">` |

No `table-layout:fixed`, no per-cell width attributes, no `bordercolor` — Gmail strips it.

**Row banding** — one rule: the Overall row occupies index 0 and gets `f2f2f2`; thereafter odd
indexes are `f7f7f7` and even are white. A table with no Overall row (the KPI table) starts white.

**Prose colour** — the value AND the WoW each get their own span, and the two colours can differ (a
leader that slipped is a green value with a red WoW):
`rose to <span style="font-weight:700;color:#008000">83%</span> (<span style="font-weight:700;color:#008000">+2% WoW</span>)`.

**Other house details:** deposit/aging bullet labels are plain `<b>`, never coloured. Glossary terms
are **not** bolded. Initiative status is `<span style="color:#808080">[On Track]</span>`.

The DOCX mirrors all of this: `333333` fill + white header text, `f2f2f2` bold Overall, `f7f7f7`
banding.

---

## Inputs

| File | Feeds |
|---|---|
| `Everest _ India Collections Dashboard V2.0 - WBR View.csv` | KPI, Recovery, Bad Debts, CF OS, CtoR, Advance Collections |
| `Everest _ India Collections Dashboard V2.0 - SD_Profiles.csv` | Deposit Health slab distribution |
| `Central Car Recovery Dash - Weekly_Summary.csv` | Vehicle Recovery Aging + P50 TAT |
| Prior week's **sent mail HTML** | Format spec — see Golden Rule 1 |

Parsing details, column offsets and known traps: `references/data-mapping.md`. **Read it before parsing.**

The dashboard **restates prior weeks** between exports. Always take all four weeks from the current
export, never carry values forward from the last issue, and flag any restatement in the handoff.

---

## Section Order (must not be changed)

1. Title + "Week of Hissab : <Month DD, YYYY>"
2. TL;DR — 4 bullets: **Snapshot**, **Highlights**, **Watch**, **Deposit Health**
3. "Hello Everyone," + intro paragraph
4. Key Performance Indicators | 4-Week Trend → Key Insights
5. Total Recovery % | City-wise Performance → Key Insights
6. Total Recovery % | Product-wise Performance → Key Insights
7. Bad Debts % | City-wise Performance (+ "lower is better" note) → Key Insights
8. Bad Debts % | Product-wise Performance → Key Insights
9. Vehicle Recovery Aging | City-wise (+ source note) → bullets
10. Deposit Health | PAN India Deposit Slab Distribution → Key Insights | City-wise Risk Analysis
11. Collection Without Deposit Conversion | City-wise → Key Insights
12. Partners with Advance Collections | City-wise (one table, two stacked blocks) → Key Insights
13. Next Week Focus Areas
14. New Initiatives
15. Definitions & Glossary (Appendix)
16. Data Source footer line

---

## KPI Table — exactly 4 rows

| Row | Metric | Source block | Direction |
|---|---|---|---|
| 1 | Total Recovery % | `Total Collections %` | ↑ good |
| 2 | Total Recovery (W/O deposit to OS) % | `Total Collections % (w/o DP to OS)` | ↑ good |
| 3 | Bad Debts % | `Bad Debt %` | ↓ good |
| 4 | Carry Forward OS (%) | `CarryForward % (OS Bifurcation)` | ↓ good |

There is **no "Recovery with Advances" row** — the WBR export has no such block. Glossary only.

---

## WoW Trend Rules

| Metric family | ↑ | ↓ | flat |
|---|---|---|---|
| Recovery, Recovery W/O CtoR, Advance %, Advance count | Improving `008000` | Declining `cc0000` | Stable `cc7a00` |
| Bad Debts, Carry Forward OS | Worsening `cc0000` | Improving `008000` | Stable `cc7a00` |

Use the WoW value **from the source CSV verbatim** — do not recompute it from the displayed
(rounded) week values, or the sign will disagree with the numbers on rounding boundaries.
Format signed: `+1%`, `-0.7%`, `0%`. Colour the WoW cell and the Trend cell the same.

---

## New Initiatives

Source: the **Initiative** tab of the "New Projects Collection" sheet. Two filters:

- **Drop the red-highlighted row.** Cell colour is lost in every text/CSV export and the in-app
  browser is not signed into the user's Google account — **ask the user which Sl No is red**.
- **Keep rows whose Deadline falls on or before the reporting week's date**, unless told otherwise.

One line per initiative, status verbatim from the tracker in a grey span. Never invent status,
owner, go-live date, or who an initiative targets.

---

## Verification Pass — mandatory before delivery

A script that **independently re-reads the source CSVs** and asserts every rendered cell. It must check:

1. Every week value and WoW in every table, against the source cell.
2. Every trend label against the sign + metric polarity.
3. Row/column totals — aging city counts must sum to Overall. Deposit slab percentages are rounded
   independently and legitimately sum to 99–101; assert that band, don't force 100.
4. Every derived claim in prose bullets (ratios, "≤₹5K" roll-ups, "N-week high", multiples,
   "lowest city by N points", streak counts).
5. **Format parity.** Assert each House Style token appears in this week's HTML *and* in last week's
   fetched mail; that no `<tr>` variant outside the four house rows is emitted; that the banding
   sequence is right; and that the regression markers `#f5f5f5`, `#777777`, `#fafafa` and
   `bordercolor` appear **nowhere**. This check is what catches a session that followed
   `mail-html.md` or the bad `docx-specs.md` block.

A "best/lowest in N weeks" claim requires the current value to be **strictly** beyond all N prior
values shown. If only 4 weeks are present, never claim more than 4.

After creating the Gmail draft, **fetch it back and diff its `htmlBody` against the local build** —
the body passes through the conversation, so this is the only proof it arrived intact. Normalise
Gmail's `www.google.com/url?q=` link wrapper and HTML entities before comparing.

Re-run to zero failures. Report the check count in the handoff.

---

## Delivery

- Recipients: copy **To and Cc from the most recent sent mail**, not from a reference file — the Cc
  list has grown over time (13 To / 7 Cc as of Aug-24).
- Google Doc: `Google_Drive.create_file` with `contentMimeType: text/html`. Docs' importer is
  unreliable with row-level `bgcolor`, so emit shading **per cell** for the Doc variant. There is no
  update-content API — revising means creating a new Doc and trashing the old, which changes the
  URL, so settle content before creating it. The Doc lands in My Drive **unshared**: tell the user
  to set access before sending.
- Top line of the mail, italic: `Collections Weekly Newsletter - WB - <Month DD> <a>click here</a> for a Google doc version`.
- DOCX archive copy: `device_commit_files` is not available in cloud sessions. Build the DOCX with python-docx in the scratchpad, send it to the user with SendUserFile, and ask where to archive it (Drive folder `collections_newsletter` or the repo).

---

## Reference Files

| File | When to read |
|---|---|
| `references/data-mapping.md` | Before parsing any CSV. Column offsets, product mapping, P50 TAT conversion, known traps. |
| `references/email-delivery.md` | Subject line and draft flow only. Its recipient list is stale — the sent mail wins. |
| `references/docx-specs.md` | **Geometry only** — column widths, margins, tblGrid trap, page-break discipline. Its "CRITICAL" colour block is wrong; House Style above wins. |
| `references/writing-guide.md` | When writing TL;DR, Key Insights, Focus Areas. |

---

## Quick start for /news (this workspace)

- Dashboard sheet: **Everest | India Collections Dashboard V2.0** = `1wkebsPPLwXnRYAuvRV_fhMGQLRxv6JwH-cYlaIEBjRw`. Read the `WBR View` and `SD_Profiles` tabs directly with the Google Sheets tools (no CSV export needed; the block layout is the same as the CSV described in `references/data-mapping.md`). Raw_Data there is refreshed every 2 hours by the SQL automation, and rent-stop pilots are excluded via Raw_Data!BX.
- Central Car Recovery Dash: find it with Google Drive search ("Central Car Recovery Dash"), tab `Weekly_Summary`.
- Initiatives: Google Drive search "New Projects Collection", tab `Initiative`.
- Last sent mail: Gmail search `subject:"Weekly Collections Newsletter"`, open the latest SENT one with full content and use its HTML as the format spec, and its To/Cc as recipients.
- Before building, ask the user once: reporting week (if WBR is >2 weeks old), which Initiative Sl No is red, sign-off yes/no.
- Never send. Create the Gmail draft, fetch it back, diff, report the verification check count.
