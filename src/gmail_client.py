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
                creds = flow.run_local_server(port=8080)

            # Token speichern für nächsten Lauf
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())

        self.service = build("gmail", "v1", credentials=creds)
        return self.service

    def fetch_recent_emails(self, limit: int = 20) -> list[dict]:
        """Hole N neueste Emails (gelesen + ungelesen)."""
        if not self.service:
            self.get_service()

        # Query: alle Emails (neueste zuerst), nicht nur unread
        results = self.service.users().messages().list(
            userId="me", maxResults=limit
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
        """Wende ein Label auf eine Email an (nutzt System + Custom Labels)."""
        if not self.service:
            self.get_service()

        label_name = label_name.strip() if label_name else "Work"

        labels_result = (
            self.service.users().labels().list(userId="me").execute()
        )
        labels = labels_result.get("labels", [])

        label_id = next(
            (l["id"] for l in labels if l["name"] == label_name), None
        )

        if not label_id:
            try:
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
            except Exception as e:
                print(f"   ⚠️  Label erstellen fehlgeschlagen: {e}")
                return False

        try:
            self.service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": [label_id]},
            ).execute()
            return True
        except Exception as e:
            print(f"   ⚠️  Fehler beim Labeln: {e}")
            return False

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

    def remove_label_by_name(self, label_name: str) -> int:
        """Entfernt ein Label von ALLEN Mails, die es haben.

        ACHTUNG: Alle Mails mit diesem Label werden delabelt (nicht gelöscht).
        """
        if not self.service:
            self.get_service()

        removed_count = 0
        page_token = None

        # Finde Label-ID
        labels_result = self.service.users().labels().list(userId="me").execute()
        labels = labels_result.get("labels", [])
        label_id = next((l["id"] for l in labels if l["name"] == label_name), None)

        if not label_id:
            print(f"   ℹ️  Label '{label_name}' nicht gefunden.")
            return 0

        # Finde alle Mails mit diesem Label
        while True:
            result = self.service.users().messages().list(
                userId="me",
                labelIds=[label_id],
                maxResults=500,
                pageToken=page_token
            ).execute()

            messages = result.get("messages", [])
            if not messages:
                break

            # Entferne Label von jeder Mail
            for msg in messages:
                self.service.users().messages().modify(
                    userId="me",
                    id=msg["id"],
                    body={"removeLabelIds": [label_id]}
                ).execute()
                removed_count += 1

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return removed_count

    def delete_spam_folder(self) -> int:
        """Verschiebt ALLE Emails im Gmail SPAM-Ordner in den Papierkorb.

        ACHTUNG: Nur Gmail-Systemordner 'SPAM'. Keine anderen Emails werden berührt.
        Emails landen im Papierkorb (nach 30 Tagen auto-gelöscht).
        """
        if not self.service:
            self.get_service()

        deleted_count = 0
        page_token = None

        while True:
            result = self.service.users().messages().list(
                userId="me",
                q="in:spam",
                maxResults=500,
                pageToken=page_token
            ).execute()

            messages = result.get("messages", [])
            if not messages:
                break

            for msg in messages:
                self.service.users().messages().trash(
                    userId="me", id=msg["id"]
                ).execute()
                deleted_count += 1

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return deleted_count
