"""One-time OAuth consent script for Claude's Google Sheets/Drive access.

Run this once, locally, in a machine with a browser:

    python setup_oauth.py

It opens a browser window, you approve as yourself, and it saves a
refresh token to token.json next to this script. Rerun it (after deleting
token.json) if you ever change SCOPES.

credentials.json (the OAuth client downloaded from Google Cloud Console)
must be in the same directory as this script.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, "credentials.json")
TOKEN_PATH = os.path.join(SCRIPT_DIR, "token.json")

# Minimum scopes to fix "Claude can't edit an existing Google Sheet".
# Extend this list (and enable the matching APIs in Cloud Console) if you
# also want Docs/Slides/Gmail/Calendar access, e.g.:
#   "https://www.googleapis.com/auth/documents"
#   "https://www.googleapis.com/auth/presentations"
#   "https://www.googleapis.com/auth/gmail.modify"
#   "https://www.googleapis.com/auth/calendar"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def main():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise SystemExit(
                    f"Missing {CREDENTIALS_PATH}. Download the OAuth client "
                    "JSON from Google Cloud Console (Desktop app type) and "
                    "save it as credentials.json in this folder first."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    print(f"Token saved to {TOKEN_PATH}. Granted scopes: {SCOPES}")


if __name__ == "__main__":
    main()
