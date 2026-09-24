# City WBR deck: house style (follow this every time)

Reference deck (the approved look): https://docs.google.com/presentation/d/1mLrbvRWoHdRMO0D5AcPuVqYNIqnwa2KDgUN1Dd_MscU/edit
Before building or changing any city WBR deck (BLR, Chennai or another city), open this reference and match it.
The user's feedback: "look how clean and good the view is, and you are making unnecessary slides."

## Rules the user has set
- Match the reference exactly: layout, fonts, colours, slide order. Clean, with no clutter.
- **No unnecessary slides.** One slide per sub-function. Never split a table into "(1/3)", "(2/3)" chunks: pick the rows that matter (max ~11).
- **No slide without data.** If a source has no data for the city, drop the slide. List the missing metrics once in the Annexure.
- **Never rename slides, metrics or the deck without asking.** Keep the source/doc names.
- **Check every source link and every doc tab** before saying data is unavailable. The WBR doc has many tabs; the city SSOT sheet has a city dropdown. Never modify shared source sheets.
- Call-outs must be professional, specific and numeric: "Metric: a → b (±x pp)".
- Business polarity: higher is WORSE (red) for parking, pending, pendency, downtime, revisit, cost/spend, wash, GPS inactive, handover pending, battery issue, drop-off, bad debt, carry forward, cancelled, rejected, abandon, TAT, service due, urgent service, budget spend, attrition, missing cars, overdue.
- Hinglish instructions are normal. Reply briefly and share links fast.

## Canvas and typography
- 10 × 5.625 in, font **Helvetica Neue** everywhere, white background, no dark header bars.
- Breadcrumb (y 0.17): 9 pt bold, grey #666. Format: `City  ·  Department  ›  Function  ›  Sub-function   ·   Owner: Name`.
- Headline (y 0.35): 14 pt bold black (16 pt on non-table slides). Format:
  `Metric: 1,727 in the week of 14 Sep, +22 WoW, -6% vs AOP, +19% vs LY`. Drop the AOP/LY parts when there is no target or no LY data.
- Black rule under the headline: y 0.86, full width 0.5 → 9.5, 1.5 pt.
- Subtitle (y 0.88): 7 pt grey. "Week of 14 Sep and 6 weeks before; AOP for week of 14 Sep, LY in headline. Cells: green better, red worse, per row. WoW Δ, vs AOP: green favourable, red unfavourable." followed by a blue "Backing sheet ↗" link to the source.
- Footer (y 5.39): 7 pt grey, `Everest Fleet  ·  <City> Weekly City Review  ·  Week starting 14 Sep ending on 20 Sep 2026  ·  Strategy & Planning`, with the page number right-aligned.

## Metric slide (one per sub-function)
- Table at x 0.5, y 1.08. Columns: Metric (2.47 in) | 7 weekly columns "Aug 3 … Sep 14" (0.5 in each) | WoW Δ (0.58) | AOP (0.53) | vs AOP (0.53).
- Header row: black fill, white bold 6–7 pt, 0.22 in high. Body rows: 0.24 in; the Metric cell has #F2F2F2 fill with 7 pt bold text. Values are 7 pt, centred.
- Weekly cells: a red → amber → green heat map per row, respecting polarity.
- WoW Δ: bold, with a light green (#D9ECD6) or light red tint. The "vs AOP" cell is tinted too. "–" means no target or no data.
- Numbers use Indian/English thousands commas (1,727), % metrics use pp for deltas, and time metrics use h:mm.
- Use ‡ after a metric name when it has not been cross-checked against a published figure.
- **FLAGS panel** (right, x 8.19, w 1.31):
  - A black "FLAGS" header, 8 pt bold white.
  - Below it a box with a 1 pt black outline, h 3.56.
  - Inside: "CONCERNS" (red #C62828, 7.5 pt bold) with up to 3 items, then "DOING WELL" (green #2E7D32) with up to 2 items.
  - Items are 7 pt black: `Metric: a → b (±x)`.
  - If nothing moved, write "No week-on-week move to flag."
- "How to read" strip: y 4.94, #F2F2F2 fill, 5.5 pt dark grey. It explains WoW Δ, ‡, the AOP source and the metric definitions.
- Bottom line (y 5.18): 7.5 pt bold. `Concern: <top item>.  Next: <next sub-function>` (or `Doing well: …`).

## Deck order
1. Cover: white. "<City> — Weekly City Review" in large bold black, a black rule, then "Everest Fleet · Week starting … · Weekly review vs last week, AOP and last year" and a grey "Prepared by Strategy & Planning".
2. City KRA: two side-by-side black-header tables with the columns KRA | Owner | Sep tgt | Dec tgt | Last wk | This wk | Gap. The headline is e.g. "1,727 cars on road in the week of 14 Sep vs a Sep target of 1,828: 101 short".
3. Action items: # | Action item | Owner | Due | Status. Owners update the status before Thursday.
4. Contents: three columns. Each department has a grey (#D9D9D9) header bar, and each row reads "page#  Function › Sub-function".
5. Business overview: the City › Fleet, utilisation and realisation metric slide.
6. For each department (Driver Operations, Driver Acquisition, Vehicle Management, Workshop):
   - an **Owner's view** slide with three columns: WHAT WORKED (green #2E7D32), WHAT DIDN'T (red #C62828) and WHERE I NEED HELP (black). They have grey-outlined boxes and the placeholder "Owner fills this before the review…".
   - then one metric slide per sub-function.
7. Summary: "What is working, what is not: biggest moves, week of X vs Y". Two boxes, WORKING (green header) and NOT WORKING (red header), with 8 items each: `Function › Metric` / `7 Sep a → 14 Sep b (±x)`.
8. Annexure: the metrics that were asked for but have no weekly city source yet.

Owners seen in the Chennai reference:
- City: Vigneshwar Munuswamy
- Driver Ops / Acquisition: Yamini A
- Own Now: R Sarathy
- Onboarding: Satheesh Kumar J
- Support: Kaarthik Manikandan
- Performance Marketing / Referral: Sri Kavitha
- Vehicle Management: Nagappan S
- Workshop: Hamish Joel

## Build notes
- Build through the Slides API batchUpdate, chunked at 400 requests per batch. Give each rebuild a new object-ID prefix, delete the old slides, and pin the slide order.
- After building, verify with `presentations.pages.getThumbnail` and look at the slides before telling the user it's done.
- OAuth token: `google-workspace-access/token.json`. It is gitignored; never commit or print it.

## Code
- `wbr-deck/pull_chennai_data.py`: pulls the Chennai tables from every source link into `chennai_tables.json`. It reuses the BLR helpers in `wbr-deck/blr_helpers.py`.
- `wbr-deck/build_city_deck.py`: builds the deck in this house style from `chennai_tables.json`. Run it as `python3 build_city_deck.py <new-id-prefix>`. The `DEPTS` spec maps department › function › sub-function, the owner and the rows, with polarity (pol=-1 means higher is worse).
- The scripts use a scratchpad path (`SP`) for intermediate JSON; point it at a local folder before running.
- Chennai deck: https://docs.google.com/presentation/d/1QoPHyJ67aYjbLtQXNPs2y9owwbAJUIcEDXKCUXS8i1w/edit
