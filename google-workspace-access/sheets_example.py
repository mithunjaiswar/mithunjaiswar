"""Example: edit an existing Google Sheet using the token from setup_oauth.py.

Demonstrates the two things the Drive connector can't do:
  1. Add a new tab to a sheet that already exists.
  2. Write rows of data (e.g. a database pull) into that tab.

Usage:
    python sheets_example.py <spreadsheet_id> <new_tab_title>

The spreadsheet_id is the long ID in the sheet's URL:
    https://docs.google.com/spreadsheets/d/<spreadsheet_id>/edit
"""

import sys
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(SCRIPT_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def add_tab_and_write_rows(spreadsheet_id, tab_title, rows):
    service = get_service()

    add_sheet_response = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": tab_title}}}]},
    ).execute()

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_title}'!A1",
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()

    return add_sheet_response


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(f"Usage: python {sys.argv[0]} <spreadsheet_id> <new_tab_title>")

    spreadsheet_id, tab_title = sys.argv[1], sys.argv[2]

    # Placeholder rows — replace with your actual DB pull.
    sample_rows = [
        ["city", "driver_count", "date"],
        ["Delhi", "1240", "2026-07-31"],
        ["Pune", "860", "2026-07-31"],
    ]

    add_tab_and_write_rows(spreadsheet_id, tab_title, sample_rows)
    print(f"Added tab '{tab_title}' and wrote {len(sample_rows)} rows.")
