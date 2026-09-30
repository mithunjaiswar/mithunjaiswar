# Work Inventory: August–September 2026 (Mithun)

*Audit date: 30 Sep 2026. Sources: Claude Code sessions, Claude artifacts and docs, and files pushed to `mithunjaiswar/mithunjaiswar`. Nothing here is estimated. Where a number appears, it comes from the conversation record or its output files. Where none exists, it says "Result/impact not explicitly available."*

---

## 0. What was inspected (and what was not)

### Inspected
| Location | What it contains | Count |
|---|---|---|
| Claude Code sessions (cloud, desktop app) | Session title, created/updated dates, and each session's final status line (last result / pending question) | 45 sessions (7 Jul – 30 Sep); 33 fall in the Aug–Sep window |
| Claude artifacts (published pages, docs, decks) | Full content of dashboards, reports and forms | 24 artifacts; 17 updated in Aug–Sep, all read |
| Claude Docs | "BLR Weekly City Review — Deck Summary" | 1 doc, read in full |
| GitHub repo `mithunjaiswar/mithunjaiswar`, all branches | Code, summaries, audit files pushed from sessions | 12 branches; 8 with Aug–Sep work, all read |

### Unable to inspect
| Location | Why | What is needed |
|---|---|---|
| **Regular claude.ai chats and claude.ai Projects** (outside Claude Code) | No tool in this environment can list or read claude.ai chat history or Project folders. | Export from claude.ai → Settings → Privacy → Export data, then put the `conversations.json` (or specific chats) in this repo or paste them here. |
| **Full transcripts of the 45 Claude Code sessions** | Only the session title, dates and last-turn status line are readable; the turn-by-turn transcript is not. Detail below is limited to that status line plus any files or artifacts the session produced. | Open each session in the app, or export the chats as above. |
| **Cowork sessions** | Excluded from the default session listing, and the tag filter that would include them is not available here. | Same export. |
| **Sessions behind 2 branches** | Branch `monthly-incentive-audit-4ygyoq` (4–8 Aug) and branch `zealous-knuth-y2w3wb` (14 Sep) have commits but no matching session in the list (archived, deleted or created elsewhere). Their **files** were read. | – |

Gmail, Drive and Calendar are connected but were **not** used, because you asked for information from Claude conversations only. They could fill gaps (sent emails, sheets edited) if you want.

---

## 1. Workstream map (conversations merged into projects)

| # | Workstream | Conversations / outputs merged | Date span |
|---|---|---|---|
| A | Incentive audit, reconciliation and automation | Incentive audit branch · Monthly Payout Tracking · Incentive Maker · Incentive Automation Status · Incentive Automation Final Implementation · Incentive Reconciliation Dashboard · August incentive payout analysis | 4 Aug → 30 Sep |
| B | Supply planning and forecasting (CNG / EV) | Plan vs Target dashboard · Dec-end CNG supply plan · EV supply RTA availability | 7 Aug → 29 Sep |
| C | WBR / city review / DEC decks and MOM | WBR deck house style + builder (Chennai/BLR) · WBR & Manthan decks · WBR action items (MOM) · BLR WBR deck · Bangalore City DEC · Driver Ops & Acquisition DEC · Copy slides / Slides API | 11 Aug → 25 Sep |
| D | SQL / data queries (Everest Reporting DB) | Fleet leasing weekly query · New joins by product & channel · Call history (city/disposition, DSAT) · Employee EF ID lookup · Revenue type (EIP/Single) logic | 25 Aug → 29 Sep |
| E | Business / unit-economics analysis | PBT calculation · City-wise competitor comparison (2 artifacts) | 13 Aug |
| F | Data quality / HR data | Employee (joiner) data completeness audit · Fleet Metrics Review & SSOT mapping | 7 Sep → 9 Sep |
| G | Google Sheets / Apps Script fixes | Chip-link extraction script · Spreadsheet formula correction (shift duration) | 7 Sep, 22 Sep |
| H | Process / KRA / internal tools | Q1 QPEDS KRA creation · IT service survey form · IT Helpdesk request app · Email Manager · Office activation (OSPP) troubleshooting | 3 Sep → 22 Sep |
| I | Claude tooling / automation setup | Google OAuth + Sheets MCP + Gmail MCP · Sheets MCP checks · MCP list · Slides API script | 31 Jul → 23 Sep |
| J | Personal / non-work (listed so you can exclude) | English Fluency Coach · PriceVichar / BestDaam price-comparison side project · India stock agent · Logic & reading comprehension · Greeting | 17 Aug → 30 Sep |

---

## 2. AUGUST 2026

### A1. Monthly incentive audit, all 7 cities (4–8 Aug) · **ONGOING at last record**
- **Source:** branch `claude/monthly-incentive-audit-4ygyoq` (20 commits, 4 and 8 Aug). No matching session is visible.
- **Problem:** verify each employee's monthly incentive against source calculators and flag unsupported amounts.
- **What was done:**
  - Built a 23-column audit schema and deep-audit Excel files for Delhi, Kolkata, Chennai and Mumbai.
  - Audited the Delhi R&M group of 81 employees against the technician calculation, then corrected it.
  - Traced 46 "Not Formulated" employees to their source files.
  - Reclassified 8 employees with reproducible formulas.
  - Rewrote the Logic column as a structured calculation path, and split Category into Fixed / Fixed + OT.
  - Traced the Kolkata OT/WFH exception email for 2 employees.
  - Checked 10 named Delhi employees individually, and traced 70 Delhi employees to the R&M roster and technician points scheme.
  - Also: Delhi SubFunction fixed on 110 rows; Hyderabad 15-Jun week merged in from the older workbook; 22 Bangalore employees reclassified to Formula Based.
- **Outputs:**
  - `AUDIT_SUMMARY_ALL_CITIES.md`, `AUDIT_PROGRESS.md`, `KOLKATA_INVESTIGATION_GUIDE.md`
  - City deep-audit xlsx files, `Delhi_R&M_81_Employees_Audit(_Corrected).xlsx`, `Not_Formulated_Incentive_Traced.xlsx`
  - `Incentive_Management_Deck.xlsx` (dashboard, Function/Sub-Function view, Category view, risk exposure)
  - `Incentive_Views.xlsx`
- **Numbers in the record:** 809 employees audited; 411 Verified, 342 Insufficient Evidence, 56 Underpaid. "Overpaid" is marked *not yet classified*.
- **Status:** Kolkata, Chennai and Mumbai are marked "in progress" in the progress log, with open investigation cases.
- **Tools:** Google Sheets, Excel, Python.

### A2. Monthly Payout Tracking dashboard (21 Aug) · **COMPLETED**
- Artifact "Monthly Payout Tracking": month-by-month incentive payout from Apr 2025 to Jul 2026, with employee count, average per employee and MoM change. Source: `Incentive_Views.xlsx`.
- **Findings:** ₹27–33L band through 2025, a lift from Jan 2026, and a peak of ₹50.9L in Jun 2026 (Jul 2026: ₹41.8L).
- **Result/impact:** not explicitly available.

### A3. Incentive Maker: comparison analysis (26 Aug → 30 Sep) · **COMPLETED**
- Session "Incentive Maker" (branch `incentive-analysis-comparisons`).
- Last record: a query was placed in B1 and **395 corrected values** were written in column Q; background tasks were stopped.
- The full detail of the comparison is not in the readable record.

### B1. Plan vs Target: weekly bridge / CNG dashboard (7 Aug → 24 Sep) · **ONGOING (waiting on your decisions)**
- **Artifact (7 Aug):** "Plan vs Target — Weekly Bridge", a rebuild of Sheet3 for the week of 3–9 Aug. Changes:
  - Weekly target spread by day-of-week weights instead of ÷7.
  - Flow, level and ratio metrics treated differently.
  - Future days no longer scored as misses.
  - Projected close and required-per-day added.
  - Sheets formulas supplied for each step (AVERAGEIFS weights, SUMPRODUCT to-date, projections).
- **Numbers shown (Day 4 of that week):**
  - Recruitment: 648 vs 832 paced plan, projected 1,013 vs 1,300 target.
  - Net EIP add: 9 vs 11.
  - Cars on road: 12,690 vs a ramp of 13,761 (week-end target 14,557).
  - Util: 66% vs a 75% target.
- **Later in the session:** a supply plan audit found **6 structural issues and 1 data mismatch**. It needs 4 decisions before the build: starting point (DB vs model), end date (27 vs 31 Dec), weekly timing for EIP/cars/sales, and linked vs current layout.
- **Tools:** Google Sheets formulas, Everest DB.

### C1. WBR deck house style and city deck builder (11 Aug → 24 Sep) · **COMPLETED**
- Session "Googel sheet gmail accsess" (branch `adjustment-report-etm85798-7ip9mm`).
- **Chennai WBR deck:** restructured to match the approved reference deck (11 slides: Chennai · Fleet → Workshop → Summary).
- **Style guide:** permanent `docs/wbr-deck-style.md` with layout, typography, business polarity (which metrics are "bad when high") and your standing rules (no unnecessary or chunked slides, no renames without asking, check every source).
- **Code:** `wbr-deck/build_city_deck.py`, `blr_helpers.py`, `pull_chennai_data.py` (about 2,500 lines), plus a `CLAUDE.md` note.
- **Tools:** Python, Google Slides API, Google Sheets.

### D1. Fleet leasing weekly data query (25 Aug) · **ONGOING (query ready, not run)**
- An optimised SQL query for weekly fleet leasing data. The last message asks whether to run it on the Everest Reporting DB or whether you will run it yourself.

### D2. New joins by product and channel → daily car allocations (27 Aug → 15 Sep) · **COMPLETED**
- SQL queries on the Everest DB. The final version gives day-on-day car allocations by employee for the last 60 days (19 employees).

### E1. PBT / unit-economics explanation (13 Aug) · **COMPLETED (analysis / explanation)**
- Explained CM/Day, CM/Month, EBITDAR/Car/Month and PBT from revenue data.
- Continues a 27 Jul session (outside the window) that explained 12 metrics and a Mumbai CNG example: −₹2,517/car/month at 64.4% util vs 73.26% breakeven.

### E2. City-wise competitor / provider comparison (13 Aug) · **COMPLETED**
- **Artifacts:**
  - "City-wise Fleet Comparison": chart and heatmap of Asset Util by provider × city.
  - "City-wise Parameter Heatmap": Asset Util, SHPV, Utilised SH%, Adj C/D. Data as of 3 Aug.
- **Scope:** Everest vs Carrum, Moove, PMV, Letzryd, GoBolt and others, across 7 cities.
- **Everest Asset Util:** Mumbai 69%, Bangalore 74%, Chennai 71%, Kolkata 67%, Hyderabad 79%, Pune 64%, Delhi 54%.
- **Result/impact:** not explicitly available.

### I1. Claude tooling setup (31 Jul – 1 Aug; 30 Aug) · **COMPLETED / partly blocked**
- **Done (31 Jul – 1 Aug):** Google OAuth setup, google-sheets MCP server, gmail-sender MCP server (Gmail API backend) and a session-start hook.
- **30 Aug:** "Check Google Sheets MCP availability" ended on a question about export → edit a copy → re-upload.

---

## 3. SEPTEMBER 2026

### A4. Incentive automation rebuild (status page 31 Aug/1 Sep; implementation 4 → 15 Sep) · **ONGOING**
- **Artifact "Incentive Automation Status" (updated 31 Aug)** covers two workbooks (Driver Operations, Driver Acquisition) and 9 functions.
- **Live (5):**
  - **Car Recovery:** 5,228 cases pulled via SQL; Raw → Step1 → Step2 → Employee → Final chain; self-expanding.
  - **Cash Collections & Performance:** 7,118 partner-weeks, rate slabs for all 7 cities.
  - **Vendor Acquisition + Engagement (KAM):** Farmer/Hunter rules.
  - **Referral.**
  - **Field Sales (FSE).**
- **Researched, not built:**
  - Onboarding/Scheduler telecalling.
  - Offline Growth + Perf Marketing telecalling (the largest remaining piece).
  - Rejoining / Winback.
- **Not started:** Support, D2O, EV, Own Now.
- **8 bugs found in the old sheets (6 fixed, 2 queued):**
  - Referral: a flat rate was paid instead of rate × conversions.
  - FSE: the city was hardcoded to Delhi.
  - FSE: the same-day exclusion filter was dead.
  - FSE: case-sensitive duplicate IDs.
  - Cash Collections: the Week-1 ND% column was wrong.
  - Cash Collections: the Advance Collection input was wrong.
  - Queued: Onboarding TL "Khiladi" incentive hardcoded to ₹0.
  - Queued: Rejoining eligibility policy vs implementation mismatch.
- **Pending actions:**
  - 5 IMPORTRANGE "Allow access" clicks.
  - The ops team to fill 3 manual Car Recovery columns.
  - The FSE Delhi NCR rate table expired on 31 Aug.
- **Session "Incentive Automation Final Implementation" (4–15 Sep):**
  - Fixed #REF!/#VALUE! errors: Col15 → Col14 in Helper_RawAll, and restored the Final_incetive_file A2 formula.
  - **Open:** rebuild the Dashboard week columns to the 5-week window (10 Aug – 7 Sep).
- **Tools:** Google Sheets (QUERY, IMPORTRANGE), SQL, Apps Script.

### A5. Incentive Reconciliation Dashboard (8 Sep) · **COMPLETED**
- Artifact covering Jul–Aug 2026: city-submitted vs centrally formulated incentive, by city, department and function, plus a Final File reconciliation and the top 40 discrepancies. Searchable at employee level.
- **Numbers:**
  - 1,056 employees.
  - City-submitted ₹33,17,509 vs central ₹14,91,251.
  - 825 formulated / 231 non-formulated.
  - Non-formulated (risk) amount ₹5,91,393.
  - Final File: 1,046 employees, ₹24,45,977.
- **Result/impact:** not explicitly available.

### A6. August incentive payout: approval and follow-up (21–22 Sep) · **COMPLETED (drafts)**
- Drafted the WhatsApp approval message to Sunny Sir for the August incentive, and an email to Ronit/Narasimha asking for the final VMT calculator sheet and timeline.
- Whether they were actually sent is not in the record.

### B2. Dec-end CNG supply plan: weekly plan 28 Sep – 27 Dec (24 → 29 Sep) · **COMPLETED (v1 built, summary for review; open points remain)**
- **Outputs:** 3 Google Sheets.
  - **Lakshya-based plan:** matches Lakshya v4 month by month.
  - **Actuals view:** run-rate plus festival seasonality.
  - **v2:** reference.
- Supporting files: `supply-plan/build_weekly_supply_plan.py` (~3,300 lines) plus helpers, `CNG_Supply_Plan_Summary.md` and a documented source list.
- **Sources:** Lakshya_15000_Model_v4, the SSOT raw_performance query, and Everest DB car books.
- **Built:**
  - Weekly plan per city (7 cities).
  - Comparison tab: Lakshya vs Plan vs LY, 8-week box, month box.
  - Summary View with a city picker.
  - Attrition working traced to Lakshya's Churn tab.
  - Diwali and Durga Puja seasonality.
  - EIP on the last 4 weeks' trend.
  - Hiring capped at each city's best week.
- **Headline (13 weeks, India):**
  - Lakshya-based plan: recruitment 14,815, cars added 2,300, sold 721, EIP +612. 21 Dec util: Plan 72.2% vs Lakshya 72.1%.
  - Actuals view: 21 Dec util 69.4% vs 72.1%. December hiring is 334 short of Lakshya.
- **15 review changes are logged.** The 5 open points include the December hiring gap, the Mumbai December smoothing, EIP 598 vs 612, the large first-week step and the v2 layout.
- **Tools:** Python, Google Sheets, SQL.

### B3. EV supply plan: RTA availability view (29 Sep) · **ONGOING**
- In the "EV Oct – Dec Plan" sheet, built 3 tabs:
  - **RTA Flow Data:** 8-week history per city from `car_status_log`, `car_deallocation` and `car_allocation`.
  - **RTA Inputs:** goodness % grid, normal RTA levels, evening %, carry-over.
  - **RTA Availability:** summary, 8-week averages with explanation and source columns.
- **Analysis:**
  - Explained RTA to garage/other, the balancing line, and Kolkata's high RTA (negative October net allocation).
  - Found that RTA exceeded total cars because a typed "2" had overwritten formulas; the formulas were restored.
  - Found Delhi NCR and Hyderabad plan on-road exceeding total cars from mid-November.
  - Reality check: Mumbai DB RTA averaged 18–23 in Aug–Sep vs a hub reality of 5–10, so the DB overstates by about 10–15.
  - Diagnosed why the old forecast rose to 59.
- **New level-based RTA model:** designed and inputs written, but the city blocks were **not yet applied** (the write was stopped).
- **Pending:**
  - Apply the model.
  - Oct–Dec 2025 seasonality check.
  - Confirm normal RTA for 4 cities.
  - Confirm Kolkata's negative October net allocation.
  - Fix the Delhi and Hyderabad over-capacity.
- **Tools:** SQL, Google Sheets.

### C2. WBR decks + Manthan Driver Ops & Acquisition deck (9 Sep) · **COMPLETED (with data caveat)**
- Produced `WBR_2026-09-07.pptx` and `Manthan_DriverOps_Acquisition_2026-09-07.pptx` from live data.
- Plan/target data was flagged as stale (last snapshot 25 May 2026).

### C3. WBR action items / MOM (3 → 25 Sep) · **COMPLETED**
- `WBR_MOM_2026-09-24.docx` with **13 action items**, owners, assignees and city recovery plans.

### C4. Driver Ops & Acquisition DEC dashboards (9 → 23 Sep) · **ONGOING (needs input)**
- The last record was a request to clarify what you wanted (sample slide, full deck or a specific table).

### C5. Copy slides to the top of a presentation (15 Sep) · **ONGOING / blocked**
- Diagnosing a Slides API access error; retry logic was drafted.

### C6. BLR Weekly City Review deck, Google Slides (23 Sep) · **COMPLETED**
- A 77-slide deck built from the BLR WBR doc, covering all 19 agenda sections. It has a cover, an action-items tracker (owner and due date), and section slides with data tables.
- **Fixes:**
  - Garbled tables from merged or duplicated headers.
  - Formatting matched to the reference deck.
  - Red "concerns" / green "doing well" call-outs.
  - Business-polarity colour coding.
  - Cover and action-item table formats.
- **Known limits:**
  - Bangalore only.
  - EFG Review and Budget Tracking use best-effort parsing.
  - Polarity is keyword-based.
- Recorded in the Claude Doc "BLR Weekly City Review — Deck Summary" (two copies exist).

### C7. Bangalore City DEC deck (23 Sep) · **COMPLETED (built; review status unknown)**
- Claude Slides deck with 160 slides in 21 sections. The sections are:
  - Check-in plan, City Overview, Perf Marketing, Referral, Rejoin, Resurrection, Vendor
  - Onboarding, Workshop (EFG, service due, budget), VMT (RTA, revisit, stickers, fitness, vehicle movement, key master)
  - EIP, DTO, Own Now, Support, Helpdesk, Collections, Car Recovery
  - CNG Utilisation, EV Utilisation
- Also "New slide with hi text" (23 Sep): a test script, `slides_example.py`, adding Google Slides API support.

### D3. Call history query with city / disposition logic (10–11 Sep) · **COMPLETED**
- SQL with city and disposition logic. DSAT was corrected to `AVG(NULLIF(rating,'0'))` on a 1–5 scale, excluding zeros; it is not a dissatisfaction rate.

### D4. Employee EF ID → username lookup (25 Sep) · **COMPLETED**
- SQL joining `public.everest_employee` to `public.auth_user` on `auth_user_id`.

### D5. Revenue type logic: EIP / Single split for DTO and Own Now (28–29 Sep) · **PLANNED / PROPOSAL (awaiting approval)**
- **Proposal:** a DTO or Own Now driver holding 2 or more cars at end of day counts as EIP; 1 car counts as Single. Leasing is unchanged.
- **Implementation:** add an `eip_single` column in the `ssot_alloc_dealloc_full` Airflow DAG.
- **Validation:** live data matches the scorecard exactly. On 27 Sep: DTO 3,799 cars (EIP 521), Own Now 3,088 cars (EIP 180).
- **Files:** `EIP_Single_Logic_DTO_OwnNow.md` with the SQL.
- **Open question:** keep or remove the SQL in the manager version of the doc.

### F1. Employee / joiner data completeness audit (9 Sep) · **COMPLETED**
- Audited the "After – 1st April" joiner sheet: **634 joiners**, 509 with at least one issue, 125 clean, 712 issue instances in total.
- **Main gaps:** UAN blank or placeholder (375); residence/permanent address missing (277).
- **Outputs:** an Excel file with a Summary Dashboard (KPIs, QUERY formulas, charts), plus the "Joiner Data Health" artifact (by department and city, field-level breakdown, search to find and fix).

### F2. Fleet Metrics Review & SSOT mapping (7–8 Sep) · **COMPLETED (117 of 118 rows)**
- Batch update mapping fleet metrics to SSOT. It stopped after resolving 117 of the 118 remaining rows.

### G1. Apps Script: extract links from smart chips (7 Sep) · **COMPLETED**
- `extractAllLinksCentral()` now reads smart chips, whole-cell hyperlinks and textFormatRuns in column J, and writes to `Central_Extracted`.

### G2. Spreadsheet formula correction (22 Sep) · **COMPLETED**
- Fixed the shift duration formulas in D:E (9-hour shift assumed) and 6 metrics (Spent / Remaining / Progress), and cleaned stale data.
- Offered, not confirmed: cleanup of B544:B694 and orphaned helpers.

### H1. Q1 QPEDS KRA creation (16–17 Sep) · **ONGOING**
- KRA document with an action-item list. Open question: add the new items as a new KRA section, or merge them into the existing list.

### H2. IT service survey + IT Helpdesk request app (22 Sep) · **COMPLETED (built)**
- **13-question IT support survey:** location, department, contact frequency, problem areas, response time and so on.
- **"Everest Fleet IT Helpdesk" artifact:** a 6-question request form that issues ticket numbers, sets P1–P3 priority with reply SLAs, keeps a shared request log with Mark done / Reopen, and exports CSV.
- **Adoption:** not explicitly available.

### H3. Email Manager (3–5 Sep) · **PLANNED (draft awaiting approval)**
- A follow-up email was drafted; the session ended waiting for your approval to send.

### H4. Office activation troubleshooting, OSPP.VBS (17 Sep) · **ONGOING**
- Elevated command prompt, but OSPP was blocked. Waiting on 4 diagnostic command outputs.

### I2. Claude tooling (3 Sep, 23 Sep) · **mixed**
- **"Google Sheets tools test" (3 Sep):** Sheets auth failed with invalid_scope; needs a reconnect (pending creation of the "lala" tab and 3 other tabs).
- **"Claude MCP list" (3 Sep):** servers listed; 3 needed auth.
- **Slides API support added (23 Sep):** see C7.

---

## 4. MASTER TABLE

| Date | Project / Folder | Workstream | Task | What I Did | Output | Tool | Business Purpose | Result / Impact | Status |
|---|---|---|---|---|---|---|---|---|---|
| 4–8 Aug | Repo branch monthly-incentive-audit | A Incentives | 7-city incentive audit | Traced employee incentives to source; reclassified; Delhi R&M 81 audit; 46 Not-Formulated traced | Audit xlsx per city, management deck, summary md | Sheets, Excel, Python | Verify payouts are formula-backed | 809 audited: 411 verified, 342 insufficient evidence, 56 underpaid | ONGOING |
| 7 Aug → 24 Sep | Session "Plan vs target dashboard" | B Planning | CNG plan vs target weekly bridge | Redesigned Sheet3 logic (day weights, flow/level/ratio, projections); later audited supply plan | Artifact + formulas; audit findings | Sheets, DB | Track weekly delivery vs target | 6 structural issues + 1 data mismatch found; result/impact not explicitly available | ONGOING (4 decisions pending) |
| 11 Aug → 24 Sep | Session "Googel sheet gmail accsess" | C Reporting | Chennai WBR deck + house style | Restructured deck to reference; wrote style guide + builder code | 11-slide deck, style guide, 3 Python scripts | Python, Slides API | Standard city WBR format | Result/impact not explicitly available | COMPLETED |
| 13 Aug | Session "PBT calculation" | E Analysis | PBT / CM / EBITDAR explanation | Explained metrics from revenue data | Explanation | – | Unit economics understanding | Result/impact not explicitly available | COMPLETED |
| 13 Aug | Artifacts | E Analysis | Competitor city comparison | Built provider × city charts/heatmaps (4 parameters) | 2 dashboards | HTML/JS | Benchmark Everest vs other fleet providers | Result/impact not explicitly available | COMPLETED |
| 17–18 Aug | Artifacts | J Personal | PriceVichar / BestDaam brand + price check | Logo/identity, price check page | 7 artifacts | – | Personal side project | – | (personal) |
| 21 Aug | Artifact | A Incentives | Monthly payout trend | Monthly tracking Apr'25–Jul'26 | Dashboard | HTML/JS | Payout trend visibility | Peak ₹50.9L Jun'26 (a data point, not impact) | COMPLETED |
| 25 Aug | Session | D SQL | Fleet leasing weekly query | Optimised query | SQL | SQL | Weekly leasing data | Not run | ONGOING |
| 26 Aug → 30 Sep | Session "Incentive Maker" | A Incentives | Incentive comparisons | Query + corrections in sheet | Query in B1, 395 corrected values | Sheets, SQL | Correct incentive data | Result/impact not explicitly available | COMPLETED |
| 27 Aug → 15 Sep | Session | D SQL | New joins / allocations query | Day-on-day allocations by employee, 60 days | SQL | SQL | Acquisition performance | Result/impact not explicitly available | COMPLETED |
| 31 Aug–15 Sep | Artifact + session "Incentive Automation Final Implementation" | A Incentives | Incentive automation rebuild | 5 functions live, 3 researched; 8 bugs found (6 fixed); REF/VALUE fixes | Workbooks, status page | Sheets, SQL, Apps Script | Automate incentive calculation | 5,228 recovery cases, 7,118 partner-weeks automated; impact not explicitly available | ONGOING |
| 3–5 Sep | Session "Email Manager" | H Process | Follow-up email | Drafted email | Draft | Gmail | Follow-up | Not sent (awaiting approval) | PLANNED |
| 3 → 25 Sep | Session "WBR action items" | C Reporting | WBR MOM | Generated MOM | WBR_MOM_2026-09-24.docx, 13 action items | Word | Track WBR actions | Result/impact not explicitly available | COMPLETED |
| 7 Sep | Session | G Apps Script | Chip-link extraction | Updated script for 3 link types | extractAllLinksCentral() | Apps Script | Extract links from sheet | Result/impact not explicitly available | COMPLETED |
| 7–8 Sep | Session | F Data | Fleet metrics → SSOT mapping | Batch mapping update | Updated mapping | Sheets | SSOT alignment | 117/118 rows resolved | COMPLETED |
| 8 Sep | Artifact | A Incentives | Incentive reconciliation (Jul–Aug) | City vs central comparison, risk by department | Dashboard | HTML/JS | Identify unverified incentive claims | ₹5.91L non-formulated flagged (a data point) | COMPLETED |
| 9 Sep | Session | C Reporting | WBR + Manthan decks | Built 2 decks from live data | 2 pptx | Python, pptx | Weekly review | Plan data stale (25 May) | COMPLETED |
| 9 Sep | Session + artifact | F Data | Joiner data completeness | Audited 634 joiners | Excel dashboard + Joiner Data Health page | Sheets/Excel | HR data quality | 509 records with issues found | COMPLETED |
| 9 → 23 Sep | Session | C Reporting | Driver Ops & Acquisition DEC | – | – | Slides | DEC review | – | ONGOING (needs input) |
| 10–11 Sep | Session | D SQL | Call history query | City/disposition logic; DSAT fix | SQL | SQL | Support / call quality | Result/impact not explicitly available | COMPLETED |
| 15 Sep | Session | C Reporting | Copy slides to top | Diagnosed API error | Retry logic | Slides API | Deck assembly | Blocked | ONGOING |
| 16–17 Sep | Session | H Process | Q1 QPEDS KRA | KRA doc + action items | Doc | Docs | KRA setting | – | ONGOING |
| 17 Sep | Session | H IT | Office activation | Troubleshooting | Commands | Windows | Fix Office licence | – | ONGOING |
| 21–22 Sep | Session | A Incentives | August payout approval | Drafted approval message + email | WhatsApp text, email | – | Payout approval | Send not confirmed | COMPLETED (draft) |
| 22 Sep | Session | G Sheets | Formula correction | Shift duration + 6 metrics fixed | Corrected sheet | Sheets | Accurate tracking | Result/impact not explicitly available | COMPLETED |
| 22 Sep | Session + artifact | H Process | IT survey + helpdesk | 13-Q survey; ticketing form app | Form list, helpdesk page | HTML/JS | IT support process | Adoption not available | COMPLETED |
| 23 Sep | Doc + Slides | C Reporting | BLR WBR deck (77 slides) + Bangalore City DEC (160 slides) | Built decks, fixed tables/format/polarity | Google Slides deck, Claude deck, summary doc | Slides API, Python | Bangalore weekly city review | Result/impact not explicitly available | COMPLETED |
| 24–29 Sep | Session "Dec-end CNG supply plan" | B Planning | CNG weekly supply plan to 27 Dec | Built 3 plan sheets, comparison tabs, seasonality, attrition working | 3 Sheets, builder code, summary | Python, Sheets, SQL | Dec-end supply target planning | 21 Dec util Plan 72.2% vs Lakshya 72.1% (plan, not outcome) | COMPLETED (v1; 5 open points) |
| 25 Sep | Session | D SQL | EF ID lookup | Join query | SQL | SQL | Employee lookup | – | COMPLETED |
| 28–29 Sep | Session "Analytics revenue type logic" | D SQL | EIP/Single logic for DTO & Own Now | Proposal + validated SQL | Proposal doc | SQL, Airflow | Correct EIP classification | Matches scorecard exactly on 21 and 27 Sep | PLANNED (awaiting approval) |
| 29 Sep | Session "EV supply RTA availability" | B Planning | EV RTA availability view | 3 tabs, analysis, new model design | Sheet tabs, summary md | SQL, Sheets | Forecast visible RTA cars | Model not yet applied | ONGOING |

---

## 5. Second-pass check (keyword coverage)

| Keyword | Found? | Where |
|---|---|---|
| Fleet | Yes | B1, B2, B3, E2, F2 |
| Supply planning | Yes | B1, B2, B3 |
| Car addition planning | Yes | B2 (cars added/sold 2,300 / 721 vs Lakshya) |
| Driver acquisition | Yes | A4 (Driver Acquisition workbook), C2, C4, D2, B2 recruitment |
| Forecasting | Yes | B1 projections, B2, B3 |
| EV | Yes | B3, C7 EV utilisation |
| CNG | Yes | B1, B2, C7 |
| Utilisation | Yes | B1, B2, E2 |
| Vendor / KAM | Yes | A4 (Vendor Acquisition + Engagement KAM), C6/C7 vendor channel |
| Incentives | Yes | A1–A6 |
| Collections | Yes | A4 Cash Collections, C7 |
| Recovery | Yes | A4 Car Recovery, C7 |
| SQL | Yes | D1–D5, A4, B2, B3 |
| Google Sheets | Yes | A, B, F, G |
| Apps Script | Yes | G1, A4 |
| Dashboards | Yes | A2, A5, B1, E2, F1 |
| Looker Studio | **No evidence found** in accessible records |
| WBR | Yes | C1, C2, C3, C6 |
| MOM | Yes | C3 |
| Management reporting | Yes | C2, C6, C7, A1 management deck |
| SOP / process improvement | Partial | C1 style guide (deck process), H1 KRA, H2 IT helpdesk process, D5 logic proposal |
| Automation | Yes | A4, C1 builder, B2 builder, I1 |
| Data analysis | Yes | A1, A5, B3, E1, E2, F1 |
| Future planning | Yes | B2, B3, D5, A4 "what's next" |

---

## 6. Personal / non-work items (for you to exclude)
- **English Fluency Coach** (17 Aug) and "english ai coach app" (Jul).
- **PriceVichar / BestDaam:** India price comparison project, logo and identity, price check pages (Jul 12 → Aug 18; 7 artifacts).
- **India Stock Market Investment Agent:** Claude subagent and GPT prompt (14 Sep, branch `zealous-knuth-y2w3wb`).
- **Logic and reading comprehension** (22 Jul → 30 Sep).
- **"Greeting"** (24 Sep): no task.

## 7. Just outside the window (July, for context)
- AOP FY27 model audit and net attrition logic, v9 vs v10 comparison, model reference (27–28 Jul).
- AOP spreadsheet changes (29 Jul).
- Weekly net attrition query (20 Jul).
- Double-Dip Ledger Chennai (22 Jul).
- Recruitment Chart Builder (15 Jul).
- Mail setup help (15 Jul).
