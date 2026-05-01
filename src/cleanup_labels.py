"""Cleanup: Entfernt alte Labels (IMPORTANT, SPAM, CATEGORY_PERSONAL) von Mails."""

import os
from dotenv import load_dotenv
from gmail_client import GmailClient


def main():
    """Entferne alte Labels."""
    load_dotenv()

    gmail = GmailClient(
        credentials_path=os.getenv(
            "GOOGLE_CREDENTIALS_PATH", "credentials/credentials.json"
        ),
        token_path=os.getenv("GOOGLE_TOKEN_PATH", "credentials/token.json"),
    )

    print("🧹 Cleanup: Entferne alte Labels...\n")
    gmail.get_service()

    old_labels = ["EmailAuto_Newsletter", "EmailAuto_Invoice", "EmailAuto_Work", "EmailAuto_Steuern"]

    for label_name in old_labels:
        count = gmail.remove_label_by_name(label_name)
        if count > 0:
            print(f"   ✅ '{label_name}': {count} Mail(s) delabelt")
        else:
            print(f"   ℹ️  '{label_name}': keine Mails gefunden")

    print("\n✅ Cleanup fertig!")


if __name__ == "__main__":
    main()
