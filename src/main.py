"""Main: Orchestriere Gmail-Klassifikation."""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from gmail_client import GmailClient
from classifier import EmailClassifier


def load_labels() -> list[str]:
    """Lade Labels aus config/labels.yaml."""
    config_path = Path(__file__).parent.parent / "config" / "labels.yaml"

    if not config_path.exists():
        # Default labels
        return ["Wichtig", "Newsletter", "Rechnung", "Arbeit", "Spam-Kandidat"]

    with open(config_path) as f:
        config = yaml.safe_load(f)
        return [label["name"] for label in config.get("labels", [])]


def main():
    """Lese Emails, klassifiziere, labele."""
    # Load .env
    load_dotenv()

    # Setup
    gmail = GmailClient(
        credentials_path=os.getenv(
            "GOOGLE_CREDENTIALS_PATH", "credentials/credentials.json"
        ),
        token_path=os.getenv("GOOGLE_TOKEN_PATH", "credentials/token.json"),
    )

    classifier = EmailClassifier(
        model=os.getenv("CLASSIFIER_MODEL", "claude-3-5-haiku-20241022")
    )

    labels = load_labels()
    emails_per_run = int(os.getenv("EMAILS_PER_RUN", "5"))

    # OAuth Authentifizierung
    print("🔐 OAuth Authentifizierung...")
    gmail.get_service()
    print("✅ Verbunden mit Gmail\n")

    # Emails holen
    print(f"📧 Lese {emails_per_run} ungelesene Emails...")
    emails = gmail.fetch_unread_emails(limit=emails_per_run)

    if not emails:
        print("   Keine ungelesenen Emails gefunden.")
        return

    # Klassifizieren
    print(f"🤖 Klassifiziere mit Claude ({classifier.model})...\n")
    results = classifier.batch_classify(emails, labels)

    # Labeln + Feedback
    for result in results:
        email_id = result["email_id"]
        subject = result["subject"]
        classification = result["classification"]
        label = classification["label"]
        confidence = classification["confidence"]
        reason = classification["reason"]

        print(f"📧 {subject[:50]}")
        print(f"   → Label: '{label}' ({confidence:.0%})")
        print(f"   → Grund: {reason}")

        # In Gmail labeln
        try:
            gmail.apply_label(email_id, label)
            gmail.mark_as_read(email_id)
            print(f"   ✅ Gelabelt + als gelesen markiert\n")
        except Exception as e:
            print(f"   ❌ Fehler beim Labeln: {e}\n")


if __name__ == "__main__":
    main()
