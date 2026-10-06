# Context handoff (read this first in a new session)

The user is Mithun Jaiswar (Everest Fleet, Strategy & Planning). They write in Hinglish; reply in Hinglish, short and direct. They want fast, finished links, not long explanations.

## Standing rules from the user
- WBR decks must look like the approved reference deck. Follow `docs/wbr-deck-style.md` exactly.
- No unnecessary slides. Never split one table across "(1/3)" slides. Never make a slide that has no data.
- **Never rename slides, metrics or decks without asking.** This has upset the user before.
- **Check every source link and every doc tab before saying data is missing.** Earlier I wrongly said Chennai data didn't exist; the user was scolded by their manager because of it.
- Don't change shared source sheets (for example, city dropdowns).
- Don't paste tokens or secrets into commits.

## Work done so far

### BLR deck
- Deck: https://docs.google.com/presentation/d/1vQXpZ9eXzU8F4TxVx2Z0_HR9luNx8XJ7RiZcoledAJk/edit
- It was matched to the BLR reference slide w0914s03 of https://docs.google.com/presentation/d/1JprlLAsT4zcGs7w8SHWR8zf95VKCm48SzUjjG0GwKwc. That covered:
  - black header, white cover and white section slides;
  - call-out box with a black border, split into concerns (top) and doing well (bottom), plus a bold "Read:" line;
  - action items table with 11 BLR items;
  - business-polarity colour coding (parking, pending, cost, wash, GPS inactive, bad debt, etc. are red when higher).
- The BLR deck has NOT been rebuilt in the new house style. Ask before changing it.
- Manager summary doc: https://claude.ai/artifact/MKSjvstdLHLpWGcFvmmbgK

### Chennai deck (latest, house style)
- Deck: https://docs.google.com/presentation/d/1QoPHyJ67aYjbLtQXNPs2y9owwbAJUIcEDXKCUXS8i1w/edit (33 slides, object-ID prefix `d4`).
- Approved style reference: https://docs.google.com/presentation/d/1mLrbvRWoHdRMO0D5AcPuVqYNIqnwa2KDgUN1Dd_MscU/edit
- Built by `wbr-deck/build_city_deck.py` from data pulled by `wbr-deck/pull_chennai_data.py`. The scripts use a scratchpad path `SP`; set it to a local folder first.
- Week shown: week of 14 Sep 2026 (14–20 Sep), with 5 weeks before it.
- Differences from the reference:
  - The column is called "Plan", not AOP, because the Chennai SSOT labels those rows Plan.
  - There is no last-year (LY) data in the sources.
  - Owner's-view and action-item slides are blanks for owners to fill.
- Data sources:
  - Chennai SSOT CORE_WBR (sheet `1bgcN-GJlk1nEOBji_-49nkUGi5xLK5LQ30gSbGvyQ8Q`, tab "CORE_ WBR [make copy for changes]");
  - Central EIP, DTO, Own Now, Existing Calling, India Collections Deck_CityView, Central Rejoining, Central Resurrection, Recruitment Channel Funnel, Agent_Performance_Report_BI, Inbound Synopsis, Parking Reco, Driver Wanted Sticker.
  - These links come from the BLR WBR doc, which has many tabs: https://docs.google.com/document/d/1-OWLml_4rKVz0ZtrK_dYkkKTDWMXbRlQiE1Mj6osD34/edit
  - Pan-India SSOT the user gave: sheet `14hL5rbI66NHylDV2UvWW9mulzsYzLzyPKSpuoSofzg0`. Its city dropdown is set to Mumbai; do not change it.
- Left out on purpose:
  - vendor daily view, outbound efficiency (daily), top-8 collection agents (to keep the deck clean);
  - stale or missing items, which are listed in the deck's Annexure slide.

### Owner names (from the reference deck)
- City: Vigneshwar Munuswamy
- Driver Ops / Acquisition: Yamini A
- Own Now: R Sarathy
- Onboarding: Satheesh Kumar J
- Support: Kaarthik Manikandan
- Perf Marketing / Referral: Sri Kavitha
- Vehicle Management: Nagappan S
- Workshop: Hamish Joel

## Google access (Sheets/Slides/Drive/Gmail)
- Claude uses its own OAuth token. The session-start hook writes it from the environment variables `GOOGLE_SHEETS_TOKEN_JSON` and `GOOGLE_SHEETS_CREDENTIALS_JSON` into `google-workspace-access/token.json` and `credentials.json`.
- GCP project: `claude-sheets-access`. The consent screen is **Internal**, so the 7-day "Testing" expiry is NOT the cause of past failures.
- Client in use: `claude-sheets-web-client` (`300322818824-aj7g…`).
- On 6 Oct 2026 the old token was found "expired or revoked". The user made a new refresh token in OAuth Playground and put it in the environment variables.
- First step in a new session: test access with a token refresh plus one Sheets read.
  - If it fails with invalid_grant, a letter in the refresh token was probably mis-copied. Ask the user to copy it again from Playground.
- If it breaks again later, ask whether the user changed their Google password: password changes revoke tokens that have Gmail scope.
- After access is confirmed, remind the user once to **disable the old client secret `****9m9j`**, because it was shared in chat.
- `setup_oauth.py` now includes the Slides scope.

## Branch
All of this is on branch `claude/adjustment-report-etm85798-7ip9mm`.
