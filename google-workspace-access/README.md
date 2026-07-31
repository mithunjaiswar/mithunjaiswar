# Google Workspace access for Claude (Sheets edit fix)

## The problem

The built-in Google Drive connector in Claude can search Drive, read files,
and create brand-new files — but it cannot edit a Sheet that already exists
(no adding tabs, no changing cells). That's a capability limit of the
connector itself, not a permissions issue on the Google account.

## The fix

Give Claude its own Google OAuth credential, scoped for read/write, that it
holds directly and uses to call the Google APIs — bypassing the connector
entirely. This is the same approach Suraj Lath's setup uses (see the
"Need help - Claude access issue for editing Google Sheets" email thread,
30 Jul 2026).

Once set up, Claude can add tabs, edit cells on an existing multi-tab
workbook, and write a database pull straight into a sheet.

## One-time setup (~20 minutes, run on your own machine)

This has to run locally, in your own browser, signed in as yourself — the
consent step can't be done on your behalf by an agent.

1. **Create a Google Cloud project**
   Go to https://console.cloud.google.com, signed in as your
   `@everestfleet.com` account, and create a new project.

2. **Enable the APIs you need**
   In "APIs & Services" → "Library", enable:
   - Google Sheets API
   - Google Drive API

   (Suraj's setup also enables Docs, Slides, Gmail, Calendar for broader use.
   This repo defaults to the minimum needed to fix the reported issue —
   Sheets + Drive. Add more scopes/APIs below only if you actually need
   Claude to touch Docs/Slides/Gmail/Calendar too.)

3. **Configure the OAuth consent screen**
   "APIs & Services" → "OAuth consent screen" → User type **Internal**.

4. **Create an OAuth client ID**
   "APIs & Services" → "Credentials" → "Create credentials" → "OAuth client
   ID" → Application type **Desktop app**. Download the JSON and save it in
   this folder as `credentials.json`.

   If Cloud Console won't let you create the project or the Internal
   consent screen, that's an org policy block — contact Vinayak Karande
   (IT) to unblock it.

5. **Install dependencies**

   ```bash
   cd google-workspace-access
   pip install -r requirements.txt
   ```

6. **Run the one-time consent script**

   ```bash
   python setup_oauth.py
   ```

   This opens your browser, you approve as yourself, and it saves
   `token.json` next to the script. After that it's silent — Claude
   refreshes the token on its own with no further prompts.

7. **Wire it into your Claude setup**
   Point whatever MCP server or script you use for Sheets access at the
   generated `token.json` + `credentials.json` pair. See
   `sheets_example.py` for a minimal example of what that looks like in
   practice (adding a tab and writing rows into an existing sheet).

## Security notes

- `token.json` and `credentials.json` are full read/write access to
  whatever scopes were granted. Both are gitignored in this repo — **never
  commit them, never paste them into a chat window.**
- Keep them on your own machine only.
- If you ever suspect either file leaked, revoke access at
  https://myaccount.google.com/permissions and redo step 6.

## Expanding scopes later

`setup_oauth.py` has a `SCOPES` list at the top. To match Suraj's full
setup (adds Docs, Slides, Gmail send/modify, Calendar), enable the
corresponding APIs in step 2 and extend `SCOPES`, then delete `token.json`
and rerun the script so it re-consents with the new scopes.
