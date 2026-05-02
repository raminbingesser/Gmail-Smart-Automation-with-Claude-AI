"""Cleanup: Löscht alte Label-Definitionen (EmailAuto_* → neue Namen)."""

import os
from dotenv import load_dotenv
from gmail_client import GmailClient


def main():
    """Lösche alte Label-Definitionen."""
    load_dotenv()

    gmail = GmailClient(
        credentials_path=os.getenv(
            "GOOGLE_CREDENTIALS_PATH", "credentials/credentials.json"
        ),
        token_path=os.getenv("GOOGLE_TOKEN_PATH", "credentials/token.json"),
    )

    print("🧹 Cleanup: Lösche alte Label-Definitionen...\n")
    gmail.get_service()

    old_labels = ["EmailAuto_Invoice", "EmailAuto_Newsletter", "EmailAuto_Work"]

    for label_name in old_labels:
        gmail.delete_label_definition(label_name)

    print("\n✅ Cleanup fertig!")


if __name__ == "__main__":
    main()
