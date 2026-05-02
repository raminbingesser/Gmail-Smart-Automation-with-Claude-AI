"""Reporter: Speichert tägliche Stats als JSON und generiert HTML-Dashboard."""

import json
import subprocess
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = REPORTS_DIR / "data"


def save_snapshot(stats: dict, data_dir: Path = None) -> None:
    """Speichere tägliche Stats in reports/data/YYYY-MM-DD.json."""
    target = data_dir or DATA_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{stats['date']}.json"
    path.write_text(json.dumps(stats, ensure_ascii=False, indent=2))


def save_spam_snapshot(count: int, data_dir: Path = None, today: str = None) -> None:
    """Speichere Spam-Count in reports/data/YYYY-MM-DD-spam.json."""
    target = data_dir or DATA_DIR
    target.mkdir(parents=True, exist_ok=True)
    day = today or date.today().isoformat()
    path = target / f"{day}-spam.json"
    path.write_text(json.dumps({"date": day, "deleted": count}))


def load_history(days: int = 30, data_dir: Path = None) -> list:
    """Lade letzte N Tages-Snapshots, sortiert nach Datum aufsteigend."""
    target = data_dir or DATA_DIR
    if not target.exists():
        return []
    files = sorted(
        [f for f in target.glob("????-??-??.json")],
        key=lambda f: f.stem
    )
    snapshots = []
    for f in files[-days:]:
        try:
            snapshots.append(json.loads(f.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return snapshots


def load_unsubscribe(data_dir: Path = None) -> dict:
    """Lade letzten Unsubscribe-Report, falls vorhanden."""
    target = data_dir or DATA_DIR
    path = target / "unsubscribe_latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def calculate_total_cost(data_dir: Path = None) -> float:
    """Summiere api_cost_chf aus allen gespeicherten Snapshots."""
    target = data_dir or DATA_DIR
    if not target.exists():
        return 0.0
    total = 0.0
    for f in target.glob("????-??-??.json"):
        try:
            data = json.loads(f.read_text())
            total += data.get("api_cost_chf", 0.0)
        except (json.JSONDecodeError, OSError):
            continue
    return total


def _build_html(today: dict, history: list, unsubscribe: dict, total_cost_chf: float = 0.0) -> str:
    """Baue HTML-String für das Dashboard."""
    import json as _json
    import html as _html_lib

    def _esc(s) -> str:
        return _html_lib.escape(str(s))

    label_names = list(today.get("label_counts", {}).keys())
    label_values = list(today.get("label_counts", {}).values())
    chart_colors = ["#22c55e", "#3b82f6", "#f59e0b", "#ec4899", "#8b5cf6"]

    trend_labels = [d["date"] for d in history]
    trend_values = [d.get("total_processed", 0) for d in history]

    priority_emails = today.get("priority_emails", [])
    calendar_events = today.get("calendar_events", [])
    errors = today.get("errors", [])
    spam_deleted = today.get("spam_deleted", 0)
    cost = today.get("api_cost_chf", 0.0)
    total_cost = total_cost_chf
    runtime = today.get("runtime_seconds", 0.0)
    total = today.get("total_processed", 0)
    report_date = today.get("date", date.today().isoformat())
    health_icon = "✅ Keine Fehler" if not errors else f"⚠️ {len(errors)} Fehler"

    # Priority emails HTML rows
    priority_rows = "".join(
        f'<tr class="border-b border-slate-700">'
        f'<td class="py-2 pr-4 text-amber-400">{_esc(e.get("from",""))}</td>'
        f'<td class="py-2 text-slate-300">{_esc(e.get("subject",""))}</td>'
        f'</tr>'
        for e in priority_emails
    ) or '<tr><td colspan="2" class="py-3 text-slate-500 italic">Keine Priority-Emails heute</td></tr>'

    # Calendar events HTML
    calendar_items = "".join(
        f'<div class="flex items-center gap-3 py-2 border-b border-slate-700">'
        f'<span class="text-green-400">📅</span>'
        f'<span>{_esc(e.get("title",""))}</span>'
        f'<span class="text-slate-400 ml-auto">{_esc(e.get("date",""))} {_esc(e.get("time",""))}</span>'
        f'</div>'
        for e in calendar_events
    ) or '<p class="text-slate-500 italic py-2">Keine Kalender-Events heute</p>'

    # Unsubscribe candidates HTML
    if unsubscribe and unsubscribe.get("candidates"):
        unsub_date = unsubscribe.get("date", "")
        candidates_html = "".join(
            f'<div class="flex items-center gap-3 py-2 border-b border-slate-700">'
            f'<span class="text-slate-300">{_esc(c.get("sender",""))}</span>'
            f'<span class="text-amber-400 ml-auto">{c.get("days_unread", 0)} Tage ungelesen</span>'
            f'</div>'
            for c in unsubscribe["candidates"]
        )
        unsub_section = f'<p class="text-slate-400 text-sm mb-3">Stand: {unsub_date}</p>' + candidates_html
    else:
        unsub_section = '<p class="text-slate-500 italic py-2">Noch kein Wochenbericht vorhanden (läuft montags)</p>'

    trend_section = ""
    if len(history) < 2:
        trend_section = '<p class="text-slate-500 italic text-center py-16">Noch zu wenig Daten — nach 2+ Tagen erscheint der Trend-Chart</p>'
    else:
        trend_section = '<canvas id="lineChart" class="max-h-64"></canvas>'

    # Pre-build the line chart JS block to avoid nested f-strings (Python 3.9 limitation)
    if len(history) >= 2:
        line_chart_js = (
            "// Line chart (30-day trend)\n"
            "new Chart(document.getElementById('lineChart'), {\n"
            "  type: 'line',\n"
            "  data: {\n"
            f"    labels: {_json.dumps(trend_labels)},\n"
            "    datasets: [{\n"
            "      label: 'Emails pro Tag',\n"
            f"      data: {_json.dumps(trend_values)},\n"
            "      borderColor: '#22c55e',\n"
            "      backgroundColor: 'rgba(34,197,94,0.1)',\n"
            "      tension: 0.3,\n"
            "      fill: true,\n"
            "      pointBackgroundColor: '#22c55e'\n"
            "    }]\n"
            "  },\n"
            "  options: { ...chartDefaults, plugins: { legend: { labels: { color: '#e2e8f0' } } } }\n"
            "});"
        )
    else:
        line_chart_js = "// Not enough data for trend chart"

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gmail Automation — {report_date}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body class="bg-[#0f172a] text-[#e2e8f0] min-h-screen p-6 font-sans">

  <!-- Header -->
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-white">Gmail Smart Automation</h1>
    <p class="text-slate-400 mt-1">Report vom {report_date}</p>
    <div class="flex flex-wrap gap-6 mt-4 text-sm">
      <span class="flex items-center gap-2">📧 <strong class="text-white">{total}</strong> Emails verarbeitet</span>
      <span class="flex items-center gap-2">⏱ <strong class="text-white">{runtime:.0f}s</strong> Laufzeit</span>
      <span class="flex items-center gap-2">💰 <strong class="text-white">{cost:.4f} CHF</strong> API-Kosten</span>
      <span class="flex items-center gap-2">📊 Gesamt: <strong class="text-white">{total_cost:.4f} CHF</strong></span>
      <span class="flex items-center gap-2 {'text-green-400' if not errors else 'text-amber-400'}">{health_icon}</span>
    </div>
  </div>

  <!-- Charts Row -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
    <div class="bg-[#1e293b] rounded-2xl p-6 shadow-lg">
      <h2 class="text-lg font-semibold mb-4 text-white">Label-Verteilung</h2>
      <canvas id="pieChart" class="max-h-64"></canvas>
    </div>
    <div class="bg-[#1e293b] rounded-2xl p-6 shadow-lg">
      <h2 class="text-lg font-semibold mb-4 text-white">Trend (30 Tage)</h2>
      {trend_section}
    </div>
  </div>

  <!-- Priority Emails -->
  <div class="bg-[#1e293b] rounded-2xl p-6 shadow-lg mb-6">
    <h2 class="text-lg font-semibold mb-4 text-white">⭐ Priority-Emails heute ({len(priority_emails)})</h2>
    <table class="w-full text-sm">
      <thead>
        <tr class="text-slate-400 border-b border-slate-600">
          <th class="text-left pb-2 pr-4">Absender</th>
          <th class="text-left pb-2">Betreff</th>
        </tr>
      </thead>
      <tbody>
        {priority_rows}
      </tbody>
    </table>
  </div>

  <!-- Calendar + SPAM Row -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
    <div class="bg-[#1e293b] rounded-2xl p-6 shadow-lg">
      <h2 class="text-lg font-semibold mb-4 text-white">📅 Kalender-Events ({len(calendar_events)})</h2>
      {calendar_items}
    </div>
    <div class="bg-[#1e293b] rounded-2xl p-6 shadow-lg">
      <h2 class="text-lg font-semibold mb-4 text-white">🗑️ SPAM-Bereinigung</h2>
      <p class="text-4xl font-bold text-green-400">{spam_deleted}</p>
      <p class="text-slate-400 text-sm mt-1">Spam-Emails heute gelöscht</p>
    </div>
  </div>

  <!-- Unsubscribe Candidates -->
  <div class="bg-[#1e293b] rounded-2xl p-6 shadow-lg mb-6">
    <h2 class="text-lg font-semibold mb-2 text-white">📋 Unsubscribe-Kandidaten</h2>
    {unsub_section}
  </div>

  <!-- System Health -->
  <div class="bg-[#1e293b] rounded-2xl p-6 shadow-lg">
    <h2 class="text-lg font-semibold mb-4 text-white">⚙️ System-Gesundheit</h2>
    <div class="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
      <div><p class="text-slate-400">Heute</p><p class="text-white font-mono">{cost:.6f} CHF</p></div>
      <div><p class="text-slate-400">Gesamt seit Start</p><p class="text-white font-mono">{total_cost:.4f} CHF</p></div>
      <div><p class="text-slate-400">Laufzeit</p><p class="text-white font-mono">{runtime:.1f}s</p></div>
      <div><p class="text-slate-400">SPAM gelöscht</p><p class="text-white font-mono">{spam_deleted}</p></div>
      <div><p class="text-slate-400">Fehler</p><p class="{'text-green-400' if not errors else 'text-amber-400'} font-mono">{len(errors)}</p></div>
    </div>
    {''.join(f'<p class="text-red-400 text-sm mt-2 font-mono">{_esc(e)}</p>' for e in errors)}
  </div>

  <p class="text-center text-slate-600 text-xs mt-8">Generiert: {datetime.now().strftime('%d.%m.%Y %H:%M')} · Gmail Smart Automation</p>

<script>
const chartDefaults = {{
  plugins: {{ legend: {{ labels: {{ color: '#e2e8f0' }} }} }},
  scales: {{ x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }},
             y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }} }}
}};

// Pie chart (label distribution)
new Chart(document.getElementById('pieChart'), {{
  type: 'doughnut',
  data: {{
    labels: {_json.dumps(label_names)},
    datasets: [{{
      data: {_json.dumps(label_values)},
      backgroundColor: {_json.dumps(chart_colors[:len(label_names)])},
      borderColor: '#0f172a',
      borderWidth: 2
    }}]
  }},
  options: {{ plugins: {{ legend: {{ position: 'right', labels: {{ color: '#e2e8f0', padding: 16 }} }} }} }}
}});

{line_chart_js}
</script>
</body>
</html>"""


def _build_email_html(today: dict, total_cost_chf: float = 0.0) -> str:
    """Baue HTML-Email (ohne JS/Charts, inline CSS für Email-Clients)."""
    import html as _html_lib

    def _esc(s) -> str:
        return _html_lib.escape(str(s))

    cost = today.get("api_cost_chf", 0.0)
    total = today.get("total_processed", 0)
    runtime = today.get("runtime_seconds", 0.0)
    spam_deleted = today.get("spam_deleted", 0)
    report_date = today.get("date", date.today().isoformat())
    errors = today.get("errors", [])
    priority_emails = today.get("priority_emails", [])
    calendar_events = today.get("calendar_events", [])
    label_counts = today.get("label_counts", {})
    health = "✅ Keine Fehler" if not errors else f"⚠️ {len(errors)} Fehler"

    # Label rows
    label_rows = "".join(
        f'<tr><td style="padding:6px 12px;color:#374151;">{_esc(k)}</td>'
        f'<td style="padding:6px 12px;text-align:right;font-weight:bold;color:#111827;">{v}</td></tr>'
        for k, v in label_counts.items()
    )

    # Priority email rows
    if priority_emails:
        prio_rows = "".join(
            f'<tr><td style="padding:6px 12px;color:#d97706;">{_esc(e.get("from",""))}</td>'
            f'<td style="padding:6px 12px;color:#374151;">{_esc(e.get("subject",""))}</td></tr>'
            for e in priority_emails
        )
    else:
        prio_rows = '<tr><td colspan="2" style="padding:8px 12px;color:#9ca3af;font-style:italic;">Keine Priority-Emails heute</td></tr>'

    # Calendar rows
    if calendar_events:
        cal_rows = "".join(
            f'<tr><td style="padding:6px 12px;color:#374151;">{_esc(e.get("title",""))}</td>'
            f'<td style="padding:6px 12px;color:#6b7280;">{_esc(e.get("date",""))} {_esc(e.get("time",""))}</td></tr>'
            for e in calendar_events
        )
    else:
        cal_rows = '<tr><td colspan="2" style="padding:8px 12px;color:#9ca3af;font-style:italic;">Keine Kalender-Events heute</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Gmail Automation Report {report_date}</title></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
<div style="max-width:600px;margin:24px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">

  <!-- Header -->
  <div style="background:#0f172a;padding:24px 28px;">
    <h1 style="margin:0;color:#ffffff;font-size:20px;">Gmail Smart Automation</h1>
    <p style="margin:4px 0 0;color:#94a3b8;font-size:14px;">Report vom {report_date}</p>
  </div>

  <!-- Stats Bar -->
  <div style="display:flex;flex-wrap:wrap;gap:0;background:#1e293b;">
    <div style="flex:1;min-width:120px;padding:14px 20px;text-align:center;">
      <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">Emails</p>
      <p style="margin:4px 0 0;color:#ffffff;font-size:22px;font-weight:bold;">{total}</p>
    </div>
    <div style="flex:1;min-width:120px;padding:14px 20px;text-align:center;">
      <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">Laufzeit</p>
      <p style="margin:4px 0 0;color:#ffffff;font-size:22px;font-weight:bold;">{runtime:.0f}s</p>
    </div>
    <div style="flex:1;min-width:120px;padding:14px 20px;text-align:center;">
      <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">Heute CHF</p>
      <p style="margin:4px 0 0;color:#22c55e;font-size:22px;font-weight:bold;">{cost:.4f}</p>
    </div>
    <div style="flex:1;min-width:120px;padding:14px 20px;text-align:center;">
      <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">Gesamt CHF</p>
      <p style="margin:4px 0 0;color:#22c55e;font-size:22px;font-weight:bold;">{total_cost_chf:.4f}</p>
    </div>
  </div>

  <div style="padding:20px 28px;">

    <!-- Label Distribution -->
    <h2 style="margin:0 0 12px;font-size:15px;color:#111827;">🏷️ Label-Verteilung</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;background:#f9fafb;border-radius:8px;overflow:hidden;">
      {label_rows}
    </table>

    <!-- Priority Emails -->
    <h2 style="margin:0 0 12px;font-size:15px;color:#111827;">⭐ Priority-Emails ({len(priority_emails)})</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;background:#fffbeb;border-radius:8px;overflow:hidden;">
      {prio_rows}
    </table>

    <!-- Calendar Events -->
    <h2 style="margin:0 0 12px;font-size:15px;color:#111827;">📅 Kalender-Events ({len(calendar_events)})</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;background:#f0fdf4;border-radius:8px;overflow:hidden;">
      {cal_rows}
    </table>

    <!-- SPAM + Health -->
    <div style="display:flex;gap:16px;margin-bottom:16px;">
      <div style="flex:1;background:#fef2f2;border-radius:8px;padding:16px;text-align:center;">
        <p style="margin:0;color:#6b7280;font-size:12px;">🗑️ SPAM gelöscht</p>
        <p style="margin:4px 0 0;font-size:28px;font-weight:bold;color:#ef4444;">{spam_deleted}</p>
      </div>
      <div style="flex:1;background:#f0fdf4;border-radius:8px;padding:16px;text-align:center;">
        <p style="margin:0;color:#6b7280;font-size:12px;">System</p>
        <p style="margin:4px 0 0;font-size:16px;font-weight:bold;color:{'#16a34a' if not errors else '#d97706'};">{health}</p>
      </div>
    </div>

  </div>

  <div style="padding:12px 28px;background:#f9fafb;text-align:center;">
    <p style="margin:0;color:#9ca3af;font-size:11px;">Gmail Smart Automation · {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
  </div>
</div>
</body>
</html>"""


def send_report_email(html: str, recipient: str, date_str: str) -> None:
    """Sende Dashboard-Email via Gmail API."""
    import base64
    import os
    import sys
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    sys.path.insert(0, str(Path(__file__).parent))
    from gmail_client import GmailClient
    from dotenv import load_dotenv
    load_dotenv()

    gmail = GmailClient(
        credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/credentials.json"),
        token_path=os.getenv("GOOGLE_TOKEN_PATH", "credentials/token.json"),
    )
    gmail.get_service()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Gmail Automation Report — {date_str}"
    msg["From"] = recipient
    msg["To"] = recipient
    msg.attach(MIMEText(html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    gmail.service.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()


def generate_report(
    today_date: str = None,
    data_dir: Path = None,
    reports_dir: Path = None,
    open_browser: bool = True,
) -> Path:
    """Generiere HTML-Dashboard. Gibt Pfad zur HTML-Datei zurück."""
    day = today_date or date.today().isoformat()
    src_dir = data_dir or DATA_DIR
    out_dir = reports_dir or REPORTS_DIR

    # Lade heutigen Snapshot
    main_path = src_dir / f"{day}.json"
    if not main_path.exists():
        raise FileNotFoundError(f"Kein Snapshot für {day} gefunden: {main_path}")
    today = json.loads(main_path.read_text())

    # Spam-Count einmergen
    spam_path = src_dir / f"{day}-spam.json"
    if spam_path.exists():
        spam_data = json.loads(spam_path.read_text())
        today["spam_deleted"] = spam_data.get("deleted", 0)
    else:
        today.setdefault("spam_deleted", 0)

    history = load_history(days=30, data_dir=src_dir)
    unsubscribe = load_unsubscribe(data_dir=src_dir)

    total_cost = calculate_total_cost(data_dir=src_dir)
    html = _build_html(today, history, unsubscribe, total_cost)

    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{day}.html"
    report_path.write_text(html, encoding="utf-8")

    latest_path = out_dir / "latest.html"
    latest_path.write_text(html, encoding="utf-8")

    email_html = _build_email_html(today, total_cost)
    email_html_path = out_dir / f"{day}-email.html"
    email_html_path.write_text(email_html, encoding="utf-8")

    if open_browser:
        subprocess.run(["open", str(report_path)], check=False)

    return report_path


def main():
    """CLI-Einstiegspunkt: Dashboard generieren, Browser öffnen, Email senden."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    try:
        report_path = generate_report()
        print(f"✅ Dashboard generiert: {report_path}")
    except FileNotFoundError as e:
        print(f"⚠️  Dashboard konnte nicht generiert werden: {e}")
        return
    except Exception as e:
        print(f"❌ Reporter-Fehler: {e}")
        return

    # Email senden
    recipient = os.getenv("EMAIL_RECIPIENT", "r.bingesser@gmail.com")
    today_str = date.today().isoformat()
    email_path = REPORTS_DIR / f"{today_str}-email.html"
    if email_path.exists():
        try:
            email_html = email_path.read_text(encoding="utf-8")
            send_report_email(email_html, recipient, today_str)
            print(f"📧 Report-Email gesendet an {recipient}")
        except Exception as e:
            print(f"⚠️  Email konnte nicht gesendet werden: {e}")


if __name__ == "__main__":
    main()
