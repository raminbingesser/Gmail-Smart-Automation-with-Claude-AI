"""Tägliche SPAM-Bereinigung: Verschiebt alle Emails im Gmail SPAM-Ordner in den Papierkorb.

SICHERHEITSREGEL: Dieses Script löscht AUSSCHLIESSLICH Emails aus dem Gmail-Systemordner
'Spam'. Es werden KEINE Emails aus dem Posteingang oder anderen Ordnern gelöscht.
"""

import os
from dotenv import load_dotenv
from gmail_client import GmailClient


def main():
    """Starte tägliche SPAM-Bereinigung."""
    load_dotenv()

    gmail = GmailClient(
        credentials_path=os.getenv(
            "GOOGLE_CREDENTIALS_PATH", "credentials/credentials.json"
        ),
        token_path=os.getenv("GOOGLE_TOKEN_PATH", "credentials/token.json"),
    )

    print("🗑️  Starte SPAM-Bereinigung (nur Gmail SPAM-Ordner)...")
    gmail.get_service()

    count = gmail.delete_spam_folder()
    print(f"✅ {count} Spam-Email(s) in den Papierkorb verschoben.")


if __name__ == "__main__":
    main()
