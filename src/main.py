"""Main: Orchestriere Gmail-Klassifikation."""

import os
import time
import sys
import yaml
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).parent))
from gmail_client import GmailClient
from classifier import EmailClassifier
from calendar_client import create_event
import reporter


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

    start_time = time.time()
    label_counts = {}
    priority_emails = []
    calendar_events = []
    errors = []

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

    # Emails holen (nur letzte 24h, gelesen + ungelesen)
    print(f"📧 Lese Emails der letzten 24h (gelesen + ungelesen)...")
    emails = gmail.fetch_recent_emails(limit=emails_per_run, query="newer_than:1d")

    if not emails:
        print("   Keine ungelesenen Emails gefunden.")
        return

    # Klassifizieren
    print(f"🤖 Klassifiziere mit Claude ({classifier.model})...\n")
    results = classifier.batch_classify(emails, labels)

    # Labeln + Feedback
    for result in results:
        email_id = result["email_id"]
        email_from = next(
            (e.get("from", "") for e in emails if e["id"] == email_id), ""
        )
        subject = result["subject"]
        body = result.get("body", "")
        classification = result["classification"]
        label = classification["label"]
        confidence = classification["confidence"]
        reason = classification["reason"]

        label_counts[label] = label_counts.get(label, 0) + 1

        print(f"📧 {subject[:50]}")
        print(f"   → Label: '{label}' ({confidence:.0%})")
        print(f"   → Grund: {reason}")

        # In Gmail labeln
        try:
            gmail.apply_label(email_id, label)
            gmail.mark_as_read(email_id)
            print(f"   ✅ Gelabelt + als gelesen markiert")

            # Priority Detection: Stern setzen wenn Antwort gebraucht (alle außer Newsletter + Invoice)
            if label not in ["Newsletter", "Invoice"]:
                if classifier.needs_reply(subject, body):
                    gmail.star_email(email_id)
                    print(f"   ⭐ Braucht Antwort — gestarrt")
                    priority_emails.append({
                        "from": email_from,
                        "subject": subject[:80],
                        "time": datetime.now().strftime("%H:%M"),
                    })

            # Health → Calendar: Termin extrahieren + in Kalender eintragen
            if label == "Health":
                appointment = classifier.extract_appointment(subject, body)
                if appointment:
                    success = create_event(
                        title=appointment.get("titel", subject[:30]),
                        date_str=appointment["datum"],
                        time_str=appointment["uhrzeit"],
                        duration_min=appointment.get("dauer_min", 60),
                        location=appointment.get("ort", ""),
                        calendar="Privat"
                    )
                    if success:
                        print(f"   📅 Termin → Apple Calendar")
                        calendar_events.append({
                            "title": appointment.get("titel", subject[:30]),
                            "date": appointment["datum"],
                            "time": appointment.get("uhrzeit", ""),
                        })
                    else:
                        print(f"   ⚠️  Termin konnte nicht hinzugefügt werden")

            print()
        except Exception as e:
            print(f"   ❌ Fehler: {e}\n")
            errors.append(f"{subject[:40]}: {str(e)}")

    # Stats-Snapshot speichern
    stats = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "total_processed": len(results),
        "label_counts": label_counts,
        "priority_emails": priority_emails,
        "calendar_events": calendar_events,
        "api_cost_chf": classifier.total_cost_chf(),
        "runtime_seconds": round(time.time() - start_time, 1),
        "errors": errors,
    }
    try:
        reporter.save_snapshot(stats)
        print(f"\n📊 Stats gespeichert ({stats['total_processed']} Emails, {stats['api_cost_chf']:.4f} CHF)")
    except Exception as e:
        print(f"⚠️  Stats konnten nicht gespeichert werden: {e}")


if __name__ == "__main__":
    main()
