# Call Details App - host on Mithun's own Vercel account

Goal: run the Call Details backend + an APK download page on the Vercel account
**mithun-jaiswar's projects** (Hobby), using the SAME Neon database as today (option A:
keep all 85 users and all call data). The old project lives under the Vercel team
`dexter17` (`call-details-backend.vercel.app`) and cannot be transferred without that
team's owner, so a new project is created instead.

## Prerequisite
A Vercel token must be saved as a **Network secret** on this cloud environment:
host `api.vercel.com`, header `Authorization`, value `Bearer <token>`.
Check: `curl -s https://api.vercel.com/v2/user` returns the user (not `missingToken`).
Never ask for the token in chat.

## Source files (Google Drive folder `1Yb_w8x9vWfGcJI9_p52Uf5gXcO2lQXtg`)
Download with the Google Drive connector by file ID. Rebuild this layout:

```
deploy/
  api/_lib.js  api/calls.js  api/health.js  api/users.js
  api/auth/login.js  api/auth/password.js
  package.json  vercel.json  schema.sql  setup.mjs  README.md
  .gitignore            (node_modules/, .vercel, .env*)
  public/index.html     (this folder: call_details_hosting/public/index.html)
  public/call-details-logs.apk
  public/Call_Details_App_How_to_Use_v3.0.pdf
```

| Drive path | file ID |
| --- | --- |
| `backend/api/_lib.js` | `1BfLJzl4t8prTUPpUdZKqAJElCzOCIg5P` |
| `backend/api/auth/login.js` | `1bP4ZjkH2v3S2mTnBuUBjzVGbpsH-GcQR` |
| `backend/api/auth/password.js` | `1Bp-DFwgTQUckvxIw5zy2uJYg-M0G0FEP` |
| `backend/api/calls.js` | `1YF_ZS6-iI_miwl9cLSJi5YCUKEJ7hdvN` |
| `backend/api/health.js` | `1pT1lq0so1sb0F_3avDXMym9w1CdaWA5I` |
| `backend/api/users.js` | `1yAFq-kmitAm2IQjDvrhYvwAafZqTz-Kc` |
| `backend/package.json` | `1hnQ50GOu2USFFfCqWstHRlF_rf6weiNc` |
| `backend/vercel.json` | `1FUZCw4fa7mJXuwiA9quVEmqKq8ooXfIF` |
| `backend/schema.sql` | `1MQfsDV2rvnVckniCWHsW3VWYpBR3n-rl` |
| `backend/setup.mjs` | `1JqJTTSW63Z7UDxXhcvv1pxiW83puAItE` |
| `backend/README.md` | `1D55hb6MrT3cOMOA2Q4cnmVYsZGbK4Be-` |
| `out/call-details-logs.apk` (v3.0, auto-upload OFF, sha256 `db289b3f...9b6e`) | `1lFX2PQky1eAT5BqWQ6-gxxuu-VKY_Y4j` |
| `downloads/rollout/Call_Details_App_How_to_Use_v3.0.pdf` | `1p4yqXZ8BEFX6du0q7v4PJCZ97-Up1hdr` |
| `backend/.env.local` (**secret** - DATABASE_URL) | `1eCDHt9gr7vO3PhK6VWK5-J8JNmg14eS5` |

Do NOT use `out/call-details-logs - Copy.apk`: older build with the 8 pm auto-upload ON.

## Secret handling (strict)
`.env.local` holds the live database password. Save it to a chmod 600 file in the
scratchpad, read only `DATABASE_URL` in a script, and never print, echo, log, commit
or paste any value from it. Only send it to the new Vercel project's env API.

## Steps
1. `GET https://api.vercel.com/v2/user` - confirm the account.
2. Create project `call-details-app` (framework null / Other). If the name is taken,
   pick another and use its `*.vercel.app` domain below.
3. Add env `DATABASE_URL` (type `encrypted`, targets production + preview) via
   `POST /v10/projects/{id}/env`, value read from `.env.local` inside a script.
4. Deploy with the CLI: `cd deploy && npx vercel@latest deploy --prod --yes --token "$X"`
   is NOT possible without the raw token; instead use the REST API:
   `POST /v13/deployments` with `name`, `project`, `target: production` and the files
   (upload each file with `POST /v2/files` + `x-vercel-digest` sha1 first). The proxy
   injects the Authorization header.
5. Verify: `/api/health` -> `{"ok":true,"users":85}`, `/` shows the page,
   `/call-details-logs.apk` downloads with the same sha256.
6. Give the user the link. Agents enter that URL as "Server address" in the app; the
   old URL keeps working as long as the dexter17 project stays up (same database).

## Analysis findings (told to the user on 20-Nov)
- Plain-text passwords in Drive: `downloads/app_logins.csv`, `call_details_app_logins.csv`,
  `downloads/city_logins/*.csv`. DB password in `backend/.env.local` on Drive.
- `POST /api/calls` inserts row by row (500 DB calls per batch) - can hit the 30 s limit.
- No login rate limiting. APK signed with the debug keystore that sits on Drive.
- Vercel Hobby is non-commercial; company use needs Pro.
