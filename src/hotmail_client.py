"""Hotmail IMAP Client: Gleiche Schnittstelle wie gmail_client.py."""

import imaplib
import email
import ssl
from datetime import datetime, timedelta
from email.header import decode_header as _decode_header


class HotmailClient:
    """IMAP Client für Hotmail/Outlook (outlook.office365.com)."""

    IMAP_SERVER = "outlook.office365.com"
    IMAP_PORT = 993
    FOLDER_PREFIX = "AI"  # Unterordner in Outlook: AI/Newsletter, AI/Invoice, ...

    def __init__(self, email_address: str, password: str):
        self.email_address = email_address
        self.password = password
        self.service = None

    def get_service(self) -> imaplib.IMAP4_SSL:
        """Verbinde und authentifiziere via IMAP SSL."""
        ctx = ssl.create_default_context()
        self.service = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT, ssl_context=ctx)
        self.service.login(self.email_address, self.password)
        return self.service

    def _ensure_connected(self):
        if self.service is None:
            self.get_service()

    def _decode_str(self, value: str) -> str:
        """Dekodiere RFC-2047 Email-Header (z.B. =?UTF-8?B?...?)."""
        if not value:
            return ""
        parts = _decode_header(value)
        result = []
        for part, charset in parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(str(part))
        return "".join(result)

    def _extract_body(self, msg) -> str:
        """Extrahiere Text-Body (max 500 Zeichen), identisch zu gmail_client.py."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        break
                    except Exception:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
            except Exception:
                pass
        return body[:500]

    def _ensure_folder(self, folder: str):
        """Erstelle IMAP-Ordner-Hierarchie falls nicht vorhanden (Fehler = bereits vorhanden → ok)."""
        parts = folder.split("/")
        for i in range(1, len(parts) + 1):
            partial = "/".join(parts[:i])
            self.service.create(f'"{partial}"')
            # imaplib gibt NO zurück wenn Ordner bereits existiert — das ist ok

    def fetch_recent_emails(self, limit: int = 100, query: str = "") -> list[dict]:
        """Hole Emails der letzten 24h aus INBOX (max limit Stück, neueste zuerst)."""
        self._ensure_connected()
        self.service.select("INBOX")

        since = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        status, data = self.service.uid("SEARCH", None, f"SINCE {since}")

        if status != "OK" or not data[0]:
            return []

        uid_list = data[0].split()
        uid_list = uid_list[-limit:][::-1]  # neueste zuerst, auf limit begrenzen

        emails = []
        for uid in uid_list:
            try:
                status, msg_data = self.service.uid("FETCH", uid, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                emails.append({
                    "id": uid.decode(),
                    "subject": self._decode_str(msg.get("Subject", "(No Subject)")),
                    "from": self._decode_str(msg.get("From", "(Unknown)")),
                    "body": self._extract_body(msg),
                })
            except Exception:
                continue

        return emails

    def mark_as_read(self, email_id: str) -> bool:
        """Markiere Email als gelesen (IMAP \\Seen Flag). Muss VOR apply_label aufgerufen werden."""
        self._ensure_connected()
        self.service.select("INBOX")
        try:
            self.service.uid("STORE", email_id.encode(), "+FLAGS", "\\Seen")
            return True
        except Exception:
            return False

    def star_email(self, email_id: str) -> bool:
        """Markiere Email als wichtig (IMAP \\Flagged = Outlook Fähnchen). Muss VOR apply_label aufgerufen werden."""
        self._ensure_connected()
        self.service.select("INBOX")
        try:
            self.service.uid("STORE", email_id.encode(), "+FLAGS", "\\Flagged")
            return True
        except Exception:
            return False

    def apply_label(self, email_id: str, label_name: str) -> bool:
        """Verschiebe Email nach AI/<label> (COPY + DELETE aus INBOX). Immer zuletzt aufrufen."""
        self._ensure_connected()
        self.service.select("INBOX")

        folder = f"{self.FOLDER_PREFIX}/{label_name}"
        self._ensure_folder(folder)

        try:
            uid = email_id.encode()
            status, _ = self.service.uid("COPY", uid, f'"{folder}"')
            if status == "OK":
                self.service.uid("STORE", uid, "+FLAGS", "\\Deleted")
                self.service.expunge()
            return status == "OK"
        except Exception as e:
            print(f"   ⚠️  Fehler beim Verschieben: {e}")
            return False

    def logout(self):
        """IMAP-Verbindung sauber schliessen."""
        if self.service:
            try:
                self.service.logout()
            except Exception:
                pass
            self.service = None
