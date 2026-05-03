"""Hotmail-Orchestrator: Klassifikation + Labeling + Kalender für Hotmail/Outlook."""

import os
import time
import sys
import yaml
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from hotmail_client import HotmailClient
from classifier import EmailClassifier
from calendar_client import create_event
import reporter


def load_labels() -> list[str]:
    """Lade Labels aus config/labels.yaml."""
    config_path = Path(__file__).parent.parent / "config" / "labels.yaml"
    if not config_path.exists():
        return ["Newsletter", "Invoice", "General", "Tax", "Health"]
    with open(config_path) as f:
        config = yaml.safe_load(f)
        return [label["name"] for label in config.get("labels", [])]


def main():
    """Lese Hotmail-Emails, klassifiziere, verschiebe in Ordner."""
    load_dotenv()

    start_time = time.time()
    label_counts = {}
    priority_emails = []
    calendar_events = []
    errors = []

    hotmail = HotmailClient(
        email_address=os.getenv("HOTMAIL_EMAIL", ""),
        password=os.getenv("HOTMAIL_PASSWORD", ""),
    )

    classifier = EmailClassifier(
        model=os.getenv("CLASSIFIER_MODEL", "claude-haiku-4-5-20251001")
    )

    labels = load_labels()
    emails_per_run = int(os.getenv("EMAILS_PER_RUN", "100"))

    print("🔐 Verbinde mit Hotmail (IMAP)...")
    hotmail.get_service()
    print("✅ Verbunden mit Hotmail\n")

    print("📧 Lese Emails der letzten 24h...")
    emails = hotmail.fetch_recent_emails(limit=emails_per_run)

    if not emails:
        print("   Keine Emails gefunden.")
        hotmail.logout()
        return

    print(f"🤖 Klassifiziere mit Claude ({classifier.model})...\n")
    results = classifier.batch_classify(emails, labels)

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

        try:
            # WICHTIG: Flags setzen VOR dem Verschieben (IMAP: INBOX muss selektiert sein)
            hotmail.mark_as_read(email_id)

            needs_reply = False
            if label not in ["Newsletter", "Invoice"]:
                needs_reply = classifier.needs_reply(subject, body)
                if needs_reply:
                    hotmail.star_email(email_id)
                    print("   ⭐ Braucht Antwort — markiert")
                    priority_emails.append({
                        "from": email_from,
                        "subject": subject[:80],
                        "time": datetime.now().strftime("%H:%M"),
                    })

            # Kalender: Termin extrahieren vor dem Verschieben
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
                        print("   📅 Termin → Apple Calendar")
                        calendar_events.append({
                            "title": appointment.get("titel", subject[:30]),
                            "date": appointment["datum"],
                            "time": appointment.get("uhrzeit", ""),
                        })
                    else:
                        print("   ⚠️  Termin konnte nicht hinzugefügt werden")

            # Email in IMAP-Ordner verschieben (zuletzt — danach ist Email nicht mehr in INBOX)
            hotmail.apply_label(email_id, label)
            print("   ✅ Verschoben + als gelesen markiert\n")

        except Exception as e:
            print(f"   ❌ Fehler: {e}\n")
            errors.append(f"{subject[:40]}: {str(e)}")

    hotmail.logout()

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
