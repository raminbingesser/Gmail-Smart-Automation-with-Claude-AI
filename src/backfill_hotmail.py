"""Einmaliger Backfill: Eigene Ordner löschen + alle INBOX-Emails neu klassifizieren."""

import os
import sys
import email as emaillib
import yaml
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from hotmail_client import HotmailClient
from classifier import EmailClassifier


# Outlook-Systemordner: Diese werden NIE angefasst
SYSTEM_FLAGS = {"\\Sent", "\\Trash", "\\Junk", "\\Drafts", "\\Archive", "\\All", "\\Flagged", "\\Noselect"}
SYSTEM_NAMES = {
    "inbox",
    "sent items", "gesendete elemente", "sent",
    "deleted items", "gelöschte elemente", "trash",
    "drafts", "entwürfe",
    "junk email", "junk-e-mail", "spam", "junk",
    "archive", "archiv",
    "outbox", "postausgang",
    "conversation history",
    "clutter", "notes", "calendar", "contacts", "tasks",
}


def load_labels() -> list[str]:
    config_path = Path(__file__).parent.parent / "config" / "labels.yaml"
    if not config_path.exists():
        return ["Newsletter", "Invoice", "General", "Tax", "Health"]
    with open(config_path) as f:
        config = yaml.safe_load(f)
        return [label["name"] for label in config.get("labels", [])]


def parse_folder_list(folder_list: list) -> list[tuple[set, str]]:
    """Parst imaplib LIST-Response in (Attribute, Ordnername)-Tupel."""
    result = []
    for entry in folder_list:
        if not entry:
            continue
        decoded = entry.decode(errors="replace")
        # Format: (\HasNoChildren \Sent) "/" "Sent Items"
        attrs_start = decoded.find("(")
        attrs_end = decoded.find(")")
        if attrs_start == -1 or attrs_end == -1:
            continue
        attrs = set(decoded[attrs_start + 1:attrs_end].split())

        # Ordnername: nach dem Trennzeichen (z.B. "/")
        after_attrs = decoded[attrs_end + 1:].strip()
        tokens = after_attrs.split(None, 1)
        if len(tokens) < 2:
            continue
        folder_name = tokens[1].strip().strip('"')
        if folder_name:
            result.append((attrs, folder_name))
    return result


def is_system_folder(attrs: set, name: str) -> bool:
    """True wenn Outlook-Systemordner (niemals löschen)."""
    if attrs & SYSTEM_FLAGS:
        return True
    return name.lower() in SYSTEM_NAMES


def delete_custom_folders(hotmail: HotmailClient):
    """Alle eigenen Ordner leeren (Emails → INBOX) und löschen. Systemordner bleiben."""
    print("📂 Scanne alle Ordner...")
    status, folder_list = hotmail.service.list('""', '"*"')
    if status != "OK" or not folder_list:
        print("   Keine Ordner gefunden.\n")
        return

    all_folders = parse_folder_list(folder_list)
    custom = [(attrs, name) for attrs, name in all_folders if not is_system_folder(attrs, name)]

    if not custom:
        print("   Keine eigenen Ordner vorhanden — nichts zu tun.\n")
        return

    print(f"\n   Folgende {len(custom)} eigene Ordner werden gelöscht")
    print("   (Emails kommen vorher sicher in die INBOX zurück):\n")
    for _, name in custom:
        print(f"   🗂  {name}")
    print()

    confirm = input("   Alle löschen? [j/N]: ").strip().lower()
    if confirm != "j":
        print("   Übersprungen.\n")
        return

    # Tiefste Ordner zuerst löschen (Unterordner vor Elternordner)
    custom.sort(key=lambda x: x[1].count("/"), reverse=True)

    print()
    for attrs, folder in custom:
        try:
            # Emails zurück in INBOX (ausser bei \Noselect-Ordnern die keine Emails haben)
            if "\\Noselect" not in attrs:
                hotmail.service.select(f'"{folder}"')
                status, data = hotmail.service.uid("SEARCH", None, "ALL")
                if status == "OK" and data[0]:
                    uids = data[0].split()
                    for uid in uids:
                        hotmail.service.uid("COPY", uid, "INBOX")
                        hotmail.service.uid("STORE", uid, "+FLAGS", "\\Deleted")
                    hotmail.service.expunge()
                    print(f"   ↩  {folder}: {len(uids)} Emails zurück in INBOX")
            hotmail.service.delete(f'"{folder}"')
            print(f"   🗑  {folder} gelöscht")
        except Exception as e:
            print(f"   ⚠️  {folder}: {e}")
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

    # Schritt 1: Eigene Ordner löschen
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Schritt 1: Eigene Ordner löschen")
    print("(Systemordner wie Posteingang, Gesendet etc. bleiben)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    delete_custom_folders(hotmail)

    # Schritt 2: Alle Emails in INBOX zählen
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Schritt 2: Alle INBOX-Emails klassifizieren")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    print("📊 Zähle Emails in INBOX...")
    hotmail.service.select("INBOX")
    status, data = hotmail.service.uid("SEARCH", None, "ALL")

    if status != "OK" or not data[0]:
        print("   Keine Emails in INBOX gefunden.")
        hotmail.logout()
        return

    all_uids = list(reversed(data[0].split()))  # neueste zuerst
    total = len(all_uids)
    estimated_cost = total * 0.00015

    print(f"\n   📧 {total} Emails in INBOX")
    print(f"   💰 Geschätzte Kosten: ~{estimated_cost:.3f} CHF")
    print(f"   ⏱  Geschätzte Zeit:   ~{max(1, total // 10)} Minuten")
    print()

    confirm = input(f"Alle {total} Emails klassifizieren und in AI/-Ordner sortieren? [j/N]: ").strip().lower()
    if confirm != "j":
        print("Abgebrochen.")
        hotmail.logout()
        return

    labels = load_labels()
    classifier = EmailClassifier(model=os.getenv("CLASSIFIER_MODEL", "claude-haiku-4-5-20251001"))

    BATCH_SIZE = 20
    processed = 0
    skipped = 0

    print(f"\n🤖 Klassifiziere {total} Emails...\n")

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
        print(f"   Skipped:  {skipped} Emails")
    print()


if __name__ == "__main__":
    main()
