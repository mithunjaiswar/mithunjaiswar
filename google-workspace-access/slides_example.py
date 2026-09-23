"""Example: create a new Google Slides presentation with text.

Demonstrates creating a new presentation and adding a slide with text content.

Usage:
    python slides_example.py [presentation_title]

If no title is provided, uses 'New Presentation' as the default.
"""

import sys
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(SCRIPT_DIR, "token.json")
SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
]


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("slides", "v1", credentials=creds)


def create_presentation_with_text(title, text_content):
    service = get_service()

    # Create a new presentation
    presentation_body = {"title": title}
    presentation = service.presentations().create(body=presentation_body).execute()
    presentation_id = presentation.get("presentationId")

    # Add a blank slide
    requests = [
        {
            "addSlide": {
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
                "insertIndex": 0,
            }
        }
    ]
    service.presentations().batchUpdate(
        presentationId=presentation_id, body={"requests": requests}
    ).execute()

    # Get the slide ID of the newly added slide
    presentation_data = service.presentations().get(presentationId=presentation_id).execute()
    slide_id = presentation_data["slides"][0]["objectId"]

    # Add text to the slide
    text_requests = [
        {
            "insertText": {
                "objectId": slide_id,
                "insertionIndex": 0,
                "text": text_content,
            }
        }
    ]
    service.presentations().batchUpdate(
        presentationId=presentation_id, body={"requests": text_requests}
    ).execute()

    return presentation_id, presentation_data["slides"][0]["objectId"]


if __name__ == "__main__":
    title = sys.argv[1] if len(sys.argv) > 1 else "New Presentation"
    text_content = "hi"

    presentation_id, slide_id = create_presentation_with_text(title, text_content)
    print(f"Created presentation '{title}' with ID: {presentation_id}")
    print(f"Slide ID: {slide_id}")
    print(f"View at: https://docs.google.com/presentation/d/{presentation_id}/edit")
