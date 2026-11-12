# Email Delivery

The newsletter ships as a **Gmail draft with the content inline as HTML**. No attachment — the
tables render in the mail body. A DOCX copy goes to the archive folder separately.

## Subject line

```
Everest India | Weekly Collections Newsletter – <Mon DD>
```

e.g. `Everest India | Weekly Collections Newsletter – Aug 10`. En-dash, and the date is the
**reporting week**, not the send date.

## Recipients

Take **To** and **Cc** from the most recent sent newsletter in Gmail (as of Aug-24 it was 13 To / 7 Cc). The address list is not stored here on purpose.

Confirm the list is still current if several weeks have passed since the last send.

## Create a DRAFT — never send

Use `mcp__Gmail__create_draft`. Never `send_message`. The user reviews and sends.

## HTML rules for Gmail

Gmail strips `<style>` blocks and external CSS. Everything must be inline or an HTML attribute.

**Keep the payload small** — verbose per-cell inline styles balloon the body to ~100KB. Push
repeated properties up:

- Table level: `<table border="1" bordercolor="#e6e6e6" cellpadding="7" cellspacing="0" style="border-collapse:collapse;width:100%;font-family:Calibri,Arial,sans-serif;font-size:13px">`
- Row level: `<tr align="center" bgcolor="#fafafa">` — alignment and shading inherit to every cell
- Cell level: only what actually varies — `align="left"`, `style="font-weight:700;color:#008000"`
- List level: put font/size/colour/line-height on the `<ul>`; leave `<li>` bare

This cuts the body roughly in half with identical rendering. Verify by rendering the HTML in a
headless browser and screenshotting before drafting.

**Do not use** `localStorage`, external images, or web fonts. Colours as hex.

## Plain-text alternative

Supply a short `body` alongside `htmlBody` — title, week, and the four KPI headline figures.
Do not attempt a full plain-text transcription of the tables.

## Sign-off

The house sign-off is `Best,` / `Collections Team` plus the Data Source footer. **Confirm with the
user each time** — some weeks they want no sign-off at all (drafting on someone else's behalf).
Always include the footer line:

```
Data Source: Everest | India Collections Dashboard V2.0 | Central Car Recovery Dashboard | Reporting Week: <Mon-DD>, YYYY
```

## Archive copy

Write the DOCX to the user's `collections_newsletter` folder as
`Collections_Weekly_Newsletter <Mon DD>.docx` via `device_commit_files`.
