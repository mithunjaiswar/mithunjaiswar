# DOCX Specs — archive copy

The DOCX is the archive/reference copy. The mail body is the primary deliverable
(see `email-delivery.md`). Both carry identical content.

## Document settings

| Property | Value |
|---|---|
| Font | Calibri (throughout) |
| Body / bullets | 9pt |
| Table cell text | 8pt |
| Section heading | 13pt bold + bottom border `d9d9d9` |
| Sub-heading ("Key Insights") | 10pt bold |
| Title | 16pt bold, centred |
| Table width | 10080 DXA total |
| Margins | 0.6" left/right, 0.5" top/bottom |

## Palette

| Name | Hex | Usage |
|---|---|---|
| Header fill | `333333` | table header row, white text |
| Alt row fill | `f7f7f7` | alternating body rows |
| Overall row fill | `f2f2f2` | the Overall/total row, bold |
| Green | `008000` | Improving, positive WoW |
| Red | `cc0000` | Declining / Worsening, negative WoW |
| Orange | `cc7a00` | Stable |
| Grey | `808080` | notes, N/A |
| Body text | `2f2f2f` | |

## Column widths (DXA, must total 10080)

**KPI (7 col)** — 2800, 1000, 1000, 1000, 1000, 1100, 2180

**City / Product tables (7 col)** — 2100, 1200, 1200, 1200, 1200, 1200, 1980

**Vehicle Aging (8 col)** — 1560, 1080, 1080, 1080, 1080, 1080, 1260, 1860
*(8 columns: City, 5 buckets, Pending total, P50 TAT. The Pending total column is an addition to the
older 7-column layout — it makes the bullets' queue-size claims checkable. Keep unless told otherwise.)*

**Deposit Health (3 col)** — 2800, 3640, 3640

## Build approach

python-docx, built fresh from the verified data — **not** XML surgery on the prior file.

Rationale: the older "clone the prior DOCX and edit run indices" rule was written when the week
count was stable. It breaks the moment the table shape changes (3 week columns → 4), because every
row needs a new cell and every downstream run index shifts. Rebuilding to these specs is both safer
and diffable. Keep the prior DOCX as the **format reference**, not as the edit target.

Set cell shading via `w:shd` on `tcPr`; set widths via `w:tcW` per cell (autofit off); set borders
via a `w:tblBorders` block with `sz=4`, colour `d9d9d9`.

---

## ⚠ WRONG — ignore the colour values in this block (use SKILL.md House Style: header 333333 + white text, f7f7f7 banding, no bordercolor)

## (old) CRITICAL: the DOCX must mirror the HTML mail

The Word attachment and the mail body are the same document in two containers. Any styling value
below that disagrees with the HTML email is a bug, not a variant. Historical trap: the DOCX used a
dark `333333` header with white text while the mail used a light `f5f5f5`/`777777` header — they
drifted apart and the mismatch shipped.

| Element | Value | Must equal HTML |
|---|---|---|
| Header fill | `f5f5f5` | yes |
| Header text | `777777`, bold | yes |
| Alt row fill | `fafafa` | yes |
| Overall row fill | `f2f2f2`, bold | yes |
| Cell borders | `e6e6e6`, sz 4 | yes |

## Page setup

A4 (210×297 mm), side margins 0.6in, top/bottom 0.5in → usable text column **10178 dxa**.

## Table width — the tblGrid trap

`python-docx`'s `add_table()` writes a `w:tblGrid` with **equal** column widths. Word and LibreOffice
lay out from that grid, so setting `w:tcW` per cell alone does nothing — columns stay equal and long
labels wrap to three lines.

Always do all three:
1. `w:tblW` = `5000` type `pct` (fill the text column)
2. `w:tblLayout` type `fixed`
3. **rewrite `w:tblGrid`** with the actual per-column widths

Scale the width profile so it sums to 10178, and push any rounding remainder into the last column.

## Page-break discipline

Tables must never tear. Apply every time:

| Rule | XML | Applied to |
|---|---|---|
| Row never splits across pages | `w:cantSplit` in `w:trPr` | every row |
| Header reprints on overflow | `w:tblHeader` in `w:trPr` | row 0 only |
| Table stays on one page | `w:keepNext` on every paragraph | all rows except the last |
| Heading glued to its table | `w:keepNext` | section headings, `Key Insights` sub-heads, italic captions |
| Short list not split | `w:keepNext` | lists of ≤6 bullets, all but last |

Verify by converting to PDF (`soffice --headless --convert-to pdf`) and rendering each page —
never ship page-break changes unrendered.

## Column widths (pre-scaling profile)

| Table | Widths |
|---|---|
| KPI | 3300, 1000, 1000, 1000, 1000, 1100, 1680 |
| City / Product | 2500, 1200, 1200, 1200, 1200, 1200, 1580 |
| Vehicle Aging (8 col) | 1560, 1080, 1080, 1080, 1080, 1080, 1260, 1860 |
| Deposit Health | 2800, 3640, 3640 |

Column 1 must be wide enough that the longest row label sits on **one line** — check
"Total Recovery (W/O deposit to OS) %" and "Partners w/ Advance Collections".
