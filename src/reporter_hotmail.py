"""Reporter für Hotmail: Dashboard generieren + via Outlook SMTP versenden."""

import os
import sys
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
import reporter


def main():
    load_dotenv()

    try:
        report_path = reporter.generate_report(open_browser=False)
        print(f"✅ Dashboard generiert: {report_path}")
    except FileNotFoundError as e:
        print(f"⚠️  Dashboard konnte nicht generiert werden: {e}")
        return
    except Exception as e:
        print(f"❌ Reporter-Fehler: {e}")
        return

    sender = os.getenv("HOTMAIL_EMAIL", "")
    password = os.getenv("HOTMAIL_PASSWORD", "")
    recipient = os.getenv("HOTMAIL_EMAIL", sender)
    today_str = date.today().isoformat()

    email_path = reporter.REPORTS_DIR / f"{today_str}-email.html"
    if not email_path.exists():
        print("⚠️  Email-HTML nicht gefunden, kein Versand.")
        return

    try:
        email_html = email_path.read_text(encoding="utf-8")
        reporter.send_report_email_smtp(email_html, sender, password, recipient, today_str)
        print(f"📧 Report-Email gesendet an {recipient}")
    except Exception as e:
        print(f"⚠️  Email konnte nicht gesendet werden: {e}")


if __name__ == "__main__":
    main()
