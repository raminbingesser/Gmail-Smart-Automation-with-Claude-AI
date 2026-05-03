"""Einmaliger Backfill: Alle INBOX-Emails klassifizieren + sortieren (kein Email wird gelöscht)."""

import os
import sys
import email as emaillib
import yaml
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from hotmail_client import HotmailClient
from classifier import EmailClassifier


def load_labels() -> list[str]:
    config_path = Path(__file__).parent.parent / "config" / "labels.yaml"
    if not config_path.exists():
        return ["Newsletter", "Invoice", "General", "Tax", "Health"]
    with open(config_path) as f:
        config = yaml.safe_load(f)
        return [label["name"] for label in config.get("labels", [])]


def find_ai_folders(hotmail: HotmailClient) -> list[str]:
    """Gibt alle IMAP-Ordner zurück, die mit 'AI/' beginnen."""
    status, folder_list = hotmail.service.list('"AI"', '"*"')
    if status != "OK" or not folder_list or folder_list == [None]:
        return []
    folders = []
    for entry in folder_list:
        if not entry:
            continue
        decoded = entry.decode(errors="replace")
        # Format: (\HasNoChildren) "/" "AI/Newsletter"
        if '"AI/' in decoded:
            # Letztes quoted Segment = Ordnername
            parts = decoded.split('"')
            for part in reversed(parts):
                if part.startswith("AI/"):
                    folders.append(part)
                    break
    return folders


def reset_ai_folders(hotmail: HotmailClient):
    """Alle AI/*-Ordner leeren (Emails zurück in INBOX) und Ordner löschen."""
    print("🔄 Setze bestehende AI-Ordner zurück...")

    ai_folders = find_ai_folders(hotmail)
    if not ai_folders:
        print("   Keine AI-Ordner vorhanden.\n")
        return

    for folder in ai_folders:
        try:
            hotmail.service.select(f'"{folder}"')
            status, data = hotmail.service.uid("SEARCH", None, "ALL")
            if status == "OK" and data[0]:
                uids = data[0].split()
                for uid in uids:
                    hotmail.service.uid("COPY", uid, "INBOX")
                    hotmail.service.uid("STORE", uid, "+FLAGS", "\\Deleted")
                hotmail.service.expunge()
                print(f"   ✅ {folder}: {len(uids)} Emails zurück in INBOX")
            hotmail.service.delete(f'"{folder}"')
        except Exception as e:
            print(f"   ⚠️  {folder}: {e}")

    try:
        hotmail.service.delete('"AI"')
    except Exception:
        pass

    print()


def main():
    load_dotenv()

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║     Email Automation — Einmaliger Backfill       ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    hotmail = HotmailClient(
        email_address=os.getenv("HOTMAIL_EMAIL", ""),
        password=os.getenv("HOTMAIL_PASSWORD", ""),
    )

    print("🔐 Verbinde mit Hotmail...")
    hotmail.get_service()
    print("✅ Verbunden\n")

    # Bestehende AI-Ordner zurücksetzen?
    reset = input("Bestehende AI-Ordner zurücksetzen und Emails zurück in INBOX? [j/N]: ").strip().lower()
    if reset == "j":
        reset_ai_folders(hotmail)

    # Alle Emails in INBOX zählen
    print("📊 Zähle Emails in INBOX...")
    hotmail.service.select("INBOX")
    status, data = hotmail.service.uid("SEARCH", None, "ALL")

    if status != "OK" or not data[0]:
        print("   Keine Emails in INBOX gefunden.")
        hotmail.logout()
        return

    all_uids = list(reversed(data[0].split()))  # neueste zuerst
    total = len(all_uids)
    estimated_cost = total * 0.00015  # ~0.15 CHF pro 1000 Emails (Haiku)

    print(f"\n📧 {total} Emails in INBOX")
    print(f"💰 Geschätzte Kosten: ~{estimated_cost:.3f} CHF")
    print(f"⏱  Geschätzte Zeit:   ~{max(1, total // 10)} Minuten")
    print()

    confirm = input(f"Alle {total} Emails klassifizieren und sortieren? Kein Email wird gelöscht. [j/N]: ").strip().lower()
    if confirm != "j":
        print("Abgebrochen.")
        hotmail.logout()
        return

    labels = load_labels()
    classifier = EmailClassifier(model=os.getenv("CLASSIFIER_MODEL", "claude-haiku-4-5-20251001"))

    BATCH_SIZE = 20
    processed = 0
    skipped = 0

    print(f"\n🤖 Klassifiziere {total} Emails in Batches à {BATCH_SIZE}...\n")

    for i in range(0, total, BATCH_SIZE):
        batch_uids = all_uids[i:i + BATCH_SIZE]
        batch_emails = []

        hotmail.service.select("INBOX")
        for uid in batch_uids:
            try:
                status, msg_data = hotmail.service.uid("FETCH", uid, "(RFC822)")
                if status != "OK" or not msg_data[0]:
                    continue
                msg = emaillib.message_from_bytes(msg_data[0][1])
                batch_emails.append({
                    "id": uid.decode(),
                    "subject": hotmail._decode_str(msg.get("Subject", "(No Subject)")),
                    "from": hotmail._decode_str(msg.get("From", "(Unknown)")),
                    "body": hotmail._extract_body(msg),
                })
            except Exception:
                skipped += 1
                continue

        if not batch_emails:
            continue

        results = classifier.batch_classify(batch_emails, labels)

        for result in results:
            email_id = result["email_id"]
            label = result["classification"]["label"]
            subject = result["subject"]

            try:
                hotmail.service.select("INBOX")
                hotmail.mark_as_read(email_id)
                hotmail.apply_label(email_id, label)
                processed += 1
                print(f"   [{processed:>4}/{total}] {subject[:45]:<45} → {label}")
            except Exception as e:
                skipped += 1
                print(f"   ❌ {subject[:45]}: {e}")

    hotmail.logout()

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║              ✅ Backfill abgeschlossen!           ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"\n   Sortiert: {processed} Emails")
    print(f"   Kosten:   {classifier.total_cost_chf():.4f} CHF")
    if skipped:
        print(f"   Skipped:  {skipped} Emails (Fehler beim Lesen)")
    print()


if __name__ == "__main__":
    main()
