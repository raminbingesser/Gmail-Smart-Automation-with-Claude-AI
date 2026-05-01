"""Gmail API Client: OAuth Flow + Email Operations."""

import os
import base64
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build


GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailClient:
    """OAuth2 + Gmail API Wrapper."""

    def __init__(
        self,
        credentials_path: str = "credentials/credentials.json",
        token_path: str = "credentials/token.json",
    ):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

    def get_service(self):
        """OAuth Flow: Token laden oder neu authentifizieren."""
        from google.oauth2.credentials import Credentials as UserCredentials

        creds = None

        # Token aus Datei laden (falls vorhanden)
        if os.path.exists(self.token_path):
            creds = UserCredentials.from_authorized_user_file(self.token_path)

        # Token ist invalid oder nicht vorhanden → OAuth Flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(GoogleRequest())
            else:
                # Neue Authentifizierung (öffnet Browser)
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Token speichern für nächsten Lauf
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())

        self.service = build("gmail", "v1", credentials=creds)
        return self.service

    def fetch_unread_emails(self, limit: int = 5) -> list[dict]:
        """Hole N ungelesene Emails (ID, Subject, Body)."""
        if not self.service:
            self.get_service()

        # Query: unread messages
        results = self.service.users().messages().list(
            userId="me", q="is:unread", maxResults=limit
        ).execute()

        messages = results.get("messages", [])
        emails = []

        for msg in messages:
            msg_data = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )

            headers = msg_data["payload"]["headers"]
            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"),
                "(No Subject)",
            )
            sender = next(
                (h["value"] for h in headers if h["name"] == "From"),
                "(Unknown)",
            )

            # Body extrahieren (einfach: Part[0])
            body = ""
            if "parts" in msg_data["payload"]:
                for part in msg_data["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        data = part["body"].get("data", "")
                        if data:
                            body = base64.urlsafe_b64decode(data).decode("utf-8")
                        break
            else:
                data = msg_data["payload"]["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8")

            emails.append(
                {
                    "id": msg["id"],
                    "subject": subject,
                    "from": sender,
                    "body": body[:500],  # First 500 chars only
                }
            )

        return emails

    def apply_label(self, email_id: str, label_name: str) -> bool:
        """Wende ein Label auf eine Email an."""
        if not self.service:
            self.get_service()

        # Label ID suchen oder erstellen
        labels_result = (
            self.service.users().labels().list(userId="me").execute()
        )
        labels = labels_result.get("labels", [])
        label_id = next(
            (l["id"] for l in labels if l["name"] == label_name), None
        )

        if not label_id:
            # Label erstellen
            label_body = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            created_label = (
                self.service.users()
                .labels()
                .create(userId="me", body=label_body)
                .execute()
            )
            label_id = created_label["id"]

        # Label zur Email hinzufügen
        self.service.users().messages().modify(
            userId="me",
            id=email_id,
            body={"addLabelIds": [label_id]},
        ).execute()

        return True

    def mark_as_read(self, email_id: str) -> bool:
        """Markiere Email als gelesen."""
        if not self.service:
            self.get_service()

        self.service.users().messages().modify(
            userId="me",
            id=email_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()

        return True
