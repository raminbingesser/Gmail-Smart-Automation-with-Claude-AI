"""Smart Unsubscribe: Findet inaktive Newsletter und bietet deabonnieren an."""

import os
import re
import webbrowser
from typing import Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from gmail_client import GmailClient


def find_unsubscribe_link(headers: list[dict], body: str) -> Optional[str]:
    """Findet Unsubscribe-Link aus List-Unsubscribe Header oder Body."""
    # Prüfe List-Unsubscribe Header (zuverlässiger)
    for header in headers:
        if header.get("name") == "List-Unsubscribe":
            value = header.get("value", "")
            # Format: <https://...>, <mailto:...>
            match = re.search(r"<(https?://[^>]+)>", value)
            if match:
                return match.group(1)

    # Fallback: Suche im Body
    urls = re.findall(r"https?://[^\s]+(?:unsubscribe|opt-out|remove)[^\s]*", body, re.IGNORECASE)
    if urls:
        return urls[0]

    return None


def main():
    """Wöchentlicher Check: Inaktive Newsletter finden."""
    load_dotenv()

    gmail = GmailClient(
        credentials_path=os.getenv(
            "GOOGLE_CREDENTIALS_PATH", "credentials/credentials.json"
        ),
        token_path=os.getenv("GOOGLE_TOKEN_PATH", "credentials/token.json"),
    )

    print("🧼 Smart Unsubscribe: Finde inaktive Newsletter...\n")
    gmail.get_service()

    # Newsletter der letzten 30 Tage fetchen
    days_back = 30
    old_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    query = f'label:Newsletter after:{old_date}'

    results = gmail.service.users().messages().list(
        userId="me", q=query, maxResults=500
    ).execute()

    messages = results.get("messages", [])

    if not messages:
        print(f"   ℹ️  Keine Newsletter in den letzten {days_back} Tagen gefunden.")
        return

    print(f"   📧 {len(messages)} Newsletter-Emails gefunden. Analysiere...\n")

    # Gruppiere nach From-Adresse + prüfe ob alle ungelesen
    senders = {}
    for msg in messages:
        msg_data = gmail.service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()

        headers = msg_data["payload"].get("headers", [])
        sender = next(
            (h["value"] for h in headers if h["name"] == "From"),
            "(Unknown)",
        )
        is_unread = "UNREAD" in msg_data.get("labelIds", [])

        if sender not in senders:
            senders[sender] = {"count": 0, "all_unread": True, "msg_id": msg["id"], "headers": headers}

        senders[sender]["count"] += 1
        if not is_unread:
            senders[sender]["all_unread"] = False

    # Filtere: nur senders mit ALLEN ungelesenen Mails (= nie interagiert)
    inactive = {k: v for k, v in senders.items() if v["all_unread"] and v["count"] >= 2}

    if not inactive:
        print(f"   ✅ Alle Newsletter sind aktiv (mindestens eine Mail gelesen).")
        return

    print(f"   ⚠️  {len(inactive)} inaktive Newsletter-Absender gefunden:\n")

    # Zeige Report
    candidates = []
    for sender, data in inactive.items():
        # Extrahiere Email-Adresse aus "Name <email@domain>"
        sender_email = re.search(r"<([^>]+)>", sender)
        sender_display = sender_email.group(1) if sender_email else sender

        # Finde Unsubscribe-Link
        msg_body = gmail.service.users().messages().get(
            userId="me", id=data["msg_id"], format="full"
        ).execute()

        body_text = ""
        if "parts" in msg_body["payload"]:
            for part in msg_body["payload"]["parts"]:
                if part["mimeType"] == "text/plain":
                    import base64
                    data_b64 = part["body"].get("data", "")
                    if data_b64:
                        body_text = base64.urlsafe_b64decode(data_b64).decode("utf-8")
                    break
        else:
            import base64
            data_b64 = msg_body["payload"]["body"].get("data", "")
            if data_b64:
                body_text = base64.urlsafe_b64decode(data_b64).decode("utf-8")

        unsub_link = find_unsubscribe_link(data["headers"], body_text)

        print(f"   • {sender_display}")
        print(f"     Ungelesene Mails: {data['count']}")
        if unsub_link:
            print(f"     Unsubscribe: {unsub_link[:60]}...")
            candidates.append((sender_display, unsub_link))
        else:
            print(f"     ⚠️  Kein Unsubscribe-Link gefunden")
        print()

    if not candidates:
        print("   ℹ️  Keine Unsubscribe-Links gefunden.")
        return

    # Interaktive Bestätigung
    response = input(f"   Sollen alle {len(candidates)} deabonniert werden? [j/n]: ")
    if response.lower() != "j":
        print("   ✅ Abgebrochen.")
        return

    print("\n   Öffne Unsubscribe-Links...\n")
    for sender, link in candidates:
        print(f"   → {sender}")
        webbrowser.open(link)

    print("\n   ✅ Fertig! Bestätige jeden Unsubscribe im Browser.")


if __name__ == "__main__":
    main()
