# Gmail Automation Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tägliches Dark Mode HTML-Dashboard mit Charts — wird automatisch nach jedem Daily-Run generiert und im Browser geöffnet.

**Architecture:** `main.py` und `purge_spam.py` speichern nach ihrem Run je eine JSON-Datei in `reports/data/`. Danach ruft `run_daily.sh` das neue `reporter.py` auf, das beide JSONs liest, die letzten 30 Tage lädt und daraus eine HTML-Seite generiert. `smart_unsubscribe.py` speichert wöchentlich seinen Kandidaten-Report als JSON.

**Tech Stack:** Python 3.9+ (json, pathlib, subprocess, string), Chart.js via CDN, Tailwind CSS via CDN, pytest

---

## File Map

| Datei | Aktion | Zweck |
|-------|--------|-------|
| `src/reporter.py` | **Neu** | JSON speichern, History laden, HTML generieren |
| `tests/test_reporter.py` | **Neu** | Tests für reporter.py |
| `src/classifier.py` | **Ändern** | Token-Tracking + `total_cost_chf()` |
| `src/main.py` | **Ändern** | Stats sammeln + `reporter.save_snapshot()` aufrufen |
| `src/purge_spam.py` | **Ändern** | Spam-Count als JSON speichern |
| `src/smart_unsubscribe.py` | **Ändern** | Kandidaten als JSON speichern |
| `run_daily.sh` | **Ändern** | `python src/reporter.py` am Ende aufrufen |

---

## Task 1: reporter.py — Datenfunktionen + Tests

**Files:**
- Create: `src/reporter.py`
- Create: `tests/test_reporter.py`

### Projektwurzel-Konstanten (kommen ganz oben in reporter.py)

```python
"""Reporter: Speichert tägliche Stats als JSON und generiert HTML-Dashboard."""

import json
import subprocess
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = REPORTS_DIR / "data"
```

---

- [ ] **Schritt 1: Failing Tests schreiben**

Datei `tests/test_reporter.py` erstellen:

```python
"""Tests für reporter.py — Datenfunktionen."""

import json
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.reporter import save_snapshot, save_spam_snapshot, load_history


SAMPLE_STATS = {
    "date": "2026-05-02",
    "timestamp": "2026-05-02T08:03:45",
    "total_processed": 23,
    "label_counts": {"Newsletter": 8, "Invoice": 3, "General": 7, "Tax": 2, "Health": 3},
    "priority_emails": [{"from": "arzt@praxis.ch", "subject": "Ihr Termin", "time": "08:01"}],
    "calendar_events": [{"title": "Zahnarzt", "date": "15.05.2026", "time": "10:00"}],
    "api_cost_chf": 0.0008,
    "runtime_seconds": 45.2,
    "errors": [],
}


def test_save_snapshot_creates_json_file(tmp_path):
    save_snapshot(SAMPLE_STATS, data_dir=tmp_path)
    expected = tmp_path / "2026-05-02.json"
    assert expected.exists()


def test_save_snapshot_content_is_correct(tmp_path):
    save_snapshot(SAMPLE_STATS, data_dir=tmp_path)
    data = json.loads((tmp_path / "2026-05-02.json").read_text())
    assert data["total_processed"] == 23
    assert data["label_counts"]["Newsletter"] == 8
    assert len(data["priority_emails"]) == 1


def test_save_snapshot_creates_missing_directory(tmp_path):
    target = tmp_path / "deep" / "nested"
    save_snapshot(SAMPLE_STATS, data_dir=target)
    assert (target / "2026-05-02.json").exists()


def test_save_spam_snapshot_creates_file(tmp_path):
    save_spam_snapshot(12, data_dir=tmp_path, today="2026-05-02")
    expected = tmp_path / "2026-05-02-spam.json"
    assert expected.exists()
    data = json.loads(expected.read_text())
    assert data["deleted"] == 12


def test_load_history_returns_sorted_list(tmp_path):
    for day, count in [("2026-05-01", 10), ("2026-05-02", 23), ("2026-04-30", 5)]:
        stats = {**SAMPLE_STATS, "date": day, "total_processed": count}
        save_snapshot(stats, data_dir=tmp_path)

    history = load_history(days=30, data_dir=tmp_path)
    assert len(history) == 3
    assert history[0]["date"] == "2026-04-30"
    assert history[-1]["date"] == "2026-05-02"


def test_load_history_ignores_spam_files(tmp_path):
    save_snapshot(SAMPLE_STATS, data_dir=tmp_path)
    save_spam_snapshot(5, data_dir=tmp_path, today="2026-05-02")

    history = load_history(days=30, data_dir=tmp_path)
    assert len(history) == 1


def test_load_history_empty_when_no_files(tmp_path):
    history = load_history(days=30, data_dir=tmp_path)
    assert history == []
```

- [ ] **Schritt 2: Tests laufen lassen — müssen FAIL**

```bash
cd ~/Projects/EmailAutomationPrivat
source .venv/bin/activate
pytest tests/test_reporter.py -v
```

Erwartet: `ImportError: cannot import name 'save_snapshot' from 'src.reporter'`

- [ ] **Schritt 3: reporter.py mit Datenfunktionen implementieren**

Datei `src/reporter.py` erstellen:

```python
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


def load_history(days: int = 30, data_dir: Path = None) -> list[dict]:
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


def load_unsubscribe(data_dir: Path = None) -> dict | None:
    """Lade letzten Unsubscribe-Report, falls vorhanden."""
    target = data_dir or DATA_DIR
    path = target / "unsubscribe_latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
```

- [ ] **Schritt 4: Tests laufen lassen — müssen PASS**

```bash
pytest tests/test_reporter.py -v
```

Erwartet: alle 7 Tests grün.

- [ ] **Schritt 5: Commit**

```bash
git add src/reporter.py tests/test_reporter.py
git commit -m "Feat: reporter.py — Datenfunktionen save/load mit Tests"
```

---

## Task 2: reporter.py — HTML-Generierung

**Files:**
- Modify: `src/reporter.py` (Funktionen ergänzen)
- Modify: `tests/test_reporter.py` (1 Smoke-Test ergänzen)

- [ ] **Schritt 1: Smoke-Test für HTML-Generierung schreiben**

Am Ende von `tests/test_reporter.py` hinzufügen:

```python
def test_generate_report_creates_html_file(tmp_path):
    from src.reporter import generate_report
    reports_dir = tmp_path / "reports"
    save_snapshot(SAMPLE_STATS, data_dir=tmp_path)
    save_spam_snapshot(12, data_dir=tmp_path, today="2026-05-02")

    report_path = generate_report(
        today_date="2026-05-02",
        data_dir=tmp_path,
        reports_dir=reports_dir,
        open_browser=False,
    )

    assert report_path.exists()
    content = report_path.read_text()
    assert "Gmail Smart Automation" in content
    assert "Chart.js" in content
    assert "23" in content  # total_processed
    assert "Zahnarzt" in content  # calendar event
```

- [ ] **Schritt 2: Test laufen lassen — muss FAIL**

```bash
pytest tests/test_reporter.py::test_generate_report_creates_html_file -v
```

Erwartet: `ImportError: cannot import name 'generate_report'`

- [ ] **Schritt 3: _build_html() Hilfsfunktion implementieren**

In `src/reporter.py` hinzufügen (nach `load_unsubscribe`):

```python
def _build_html(today: dict, history: list[dict], unsubscribe: dict | None) -> str:
    """Baue HTML-String für das Dashboard."""
    import json as _json

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
    runtime = today.get("runtime_seconds", 0.0)
    total = today.get("total_processed", 0)
    report_date = today.get("date", date.today().isoformat())
    health_icon = "✅ Keine Fehler" if not errors else f"⚠️ {len(errors)} Fehler"

    # Priority emails HTML rows
    priority_rows = "".join(
        f'<tr class="border-b border-slate-700">'
        f'<td class="py-2 pr-4 text-amber-400">{e.get("from","")}</td>'
        f'<td class="py-2 text-slate-300">{e.get("subject","")}</td>'
        f'</tr>'
        for e in priority_emails
    ) or '<tr><td colspan="2" class="py-3 text-slate-500 italic">Keine Priority-Emails heute</td></tr>'

    # Calendar events HTML
    calendar_items = "".join(
        f'<div class="flex items-center gap-3 py-2 border-b border-slate-700">'
        f'<span class="text-green-400">📅</span>'
        f'<span>{e.get("title","")}</span>'
        f'<span class="text-slate-400 ml-auto">{e.get("date","")} {e.get("time","")}</span>'
        f'</div>'
        for e in calendar_events
    ) or '<p class="text-slate-500 italic py-2">Keine Kalender-Events heute</p>'

    # Unsubscribe candidates HTML
    if unsubscribe and unsubscribe.get("candidates"):
        unsub_date = unsubscribe.get("date", "")
        candidates_html = "".join(
            f'<div class="flex items-center gap-3 py-2 border-b border-slate-700">'
            f'<span class="text-slate-300">{c.get("sender","")}</span>'
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

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gmail Automation — {report_date}</title>
  <script src="https://cdn.tailwindcss.com"></script>
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
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
      <div><p class="text-slate-400">API-Kosten</p><p class="text-white font-mono">{cost:.6f} CHF</p></div>
      <div><p class="text-slate-400">Laufzeit</p><p class="text-white font-mono">{runtime:.1f}s</p></div>
      <div><p class="text-slate-400">SPAM gelöscht</p><p class="text-white font-mono">{spam_deleted}</p></div>
      <div><p class="text-slate-400">Fehler</p><p class="{'text-green-400' if not errors else 'text-amber-400'} font-mono">{len(errors)}</p></div>
    </div>
    {''.join(f'<p class="text-red-400 text-sm mt-2 font-mono">{e}</p>' for e in errors)}
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

{'// Line chart (30-day trend)' if len(history) >= 2 else '// Not enough data for trend chart'}
{f"""new Chart(document.getElementById('lineChart'), {{
  type: 'line',
  data: {{
    labels: {_json.dumps(trend_labels)},
    datasets: [{{
      label: 'Emails pro Tag',
      data: {_json.dumps(trend_values)},
      borderColor: '#22c55e',
      backgroundColor: 'rgba(34,197,94,0.1)',
      tension: 0.3,
      fill: true,
      pointBackgroundColor: '#22c55e'
    }}]
  }},
  options: {{ ...chartDefaults, plugins: {{ legend: {{ labels: {{ color: '#e2e8f0' }} }} }} }}
}});""" if len(history) >= 2 else ""}
</script>
</body>
</html>"""
```

- [ ] **Schritt 4: generate_report() Funktion implementieren**

In `src/reporter.py` hinzufügen (nach `_build_html`):

```python
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

    html = _build_html(today, history, unsubscribe)

    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{day}.html"
    report_path.write_text(html, encoding="utf-8")

    latest_path = out_dir / "latest.html"
    latest_path.write_text(html, encoding="utf-8")

    if open_browser:
        subprocess.run(["open", str(report_path)], check=False)

    return report_path
```

- [ ] **Schritt 5: main() Einstiegspunkt hinzufügen**

Am Ende von `src/reporter.py` hinzufügen:

```python
def main():
    """CLI-Einstiegspunkt: Dashboard generieren und Browser öffnen."""
    try:
        report_path = generate_report()
        print(f"✅ Dashboard generiert: {report_path}")
    except FileNotFoundError as e:
        print(f"⚠️  Dashboard konnte nicht generiert werden: {e}")
    except Exception as e:
        print(f"❌ Reporter-Fehler: {e}")


if __name__ == "__main__":
    main()
```

- [ ] **Schritt 6: Alle Tests laufen lassen**

```bash
pytest tests/test_reporter.py -v
```

Erwartet: alle 8 Tests grün.

- [ ] **Schritt 7: Commit**

```bash
git add src/reporter.py tests/test_reporter.py
git commit -m "Feat: reporter.py — HTML-Dashboard Generierung mit Dark Mode + Chart.js"
```

---

## Task 3: classifier.py — Token-Kosten-Tracking

**Files:**
- Modify: `src/classifier.py`

Ziel: Alle Claude-Aufrufe akkumulieren Token-Counts. `total_cost_chf()` gibt Gesamtkosten zurück.

Haiku-Tarif: $0.80/1M Input, $4.00/1M Output. Kurs: 1 USD = 0.90 CHF.

- [ ] **Schritt 1: `__init__` in EmailClassifier erweitern**

In `src/classifier.py`, `__init__` anpassen (Zeile 13-14):

```python
def __init__(self, model: str = "claude-3-5-haiku-20241022"):
    self.model = model
    self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    self._total_input_tokens = 0
    self._total_output_tokens = 0
```

- [ ] **Schritt 2: `total_cost_chf()` Methode hinzufügen**

Nach `__init__` einfügen:

```python
def total_cost_chf(self) -> float:
    """Berechne Gesamtkosten aller bisherigen API-Aufrufe in CHF."""
    INPUT_COST_CHF = 0.80 * 0.90 / 1_000_000
    OUTPUT_COST_CHF = 4.00 * 0.90 / 1_000_000
    return (self._total_input_tokens * INPUT_COST_CHF +
            self._total_output_tokens * OUTPUT_COST_CHF)
```

- [ ] **Schritt 3: Token-Tracking in `classify_email()` hinzufügen**

Nach `message = self.client.messages.create(...)` in `classify_email()` (Zeile 40-44), direkt nach dem API-Aufruf einfügen:

```python
        message = self.client.messages.create(
            model=self.model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        self._total_input_tokens += message.usage.input_tokens
        self._total_output_tokens += message.usage.output_tokens
```

- [ ] **Schritt 4: Token-Tracking in `extract_appointment()` hinzufügen**

Nach dem `messages.create()`-Aufruf in `extract_appointment()` (Zeile 93-97):

```python
        message = self.client.messages.create(
            model=self.model,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        self._total_input_tokens += message.usage.input_tokens
        self._total_output_tokens += message.usage.output_tokens
```

- [ ] **Schritt 5: Token-Tracking in `needs_reply()` hinzufügen**

Nach dem `messages.create()`-Aufruf in `needs_reply()` (Zeile 135-139):

```python
        message = self.client.messages.create(
            model=self.model,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        self._total_input_tokens += message.usage.input_tokens
        self._total_output_tokens += message.usage.output_tokens
```

- [ ] **Schritt 6: Bestehende Tests noch grün?**

```bash
pytest tests/test_classifier.py -v
```

Erwartet: alle bestehenden Tests PASS. (Mocks liefern MagicMock für `.usage.input_tokens` — gibt `MagicMock` zurück, was bei Addition mit int zu TypeError führt. Falls Tests fehlschlagen: Mock-Response um `usage`-Attribut ergänzen — das ist ein Hinweis, bestehende Tests anzupassen, nicht den Code.)

Falls Tests fehlschlagen, in `tests/test_classifier.py` bei jedem `mock_response` ergänzen:

```python
mock_response.usage.input_tokens = 50
mock_response.usage.output_tokens = 20
```

- [ ] **Schritt 7: Commit**

```bash
git add src/classifier.py tests/test_classifier.py
git commit -m "Feat: classifier.py — Token-Tracking + total_cost_chf()"
```

---

## Task 4: main.py — Stats sammeln + Snapshot speichern

**Files:**
- Modify: `src/main.py`

- [ ] **Schritt 1: Imports und Start-Zeit ergänzen**

In `src/main.py`, neue Imports am Anfang (nach bestehenden Imports):

```python
import time
from datetime import datetime
import reporter
```

- [ ] **Schritt 2: Stats-Variablen am Anfang von `main()` initialisieren**

In der `main()` Funktion, nach `load_dotenv()` (Zeile 29), einfügen:

```python
    start_time = time.time()
    label_counts = {}
    priority_emails = []
    calendar_events = []
    errors = []
```

- [ ] **Schritt 3: Label-Count pro Email aufzeichnen**

Im `for result in results:` Loop, nach `label = classification["label"]` (nach Zeile 69), einfügen:

```python
        label_counts[label] = label_counts.get(label, 0) + 1
```

- [ ] **Schritt 4: Priority-Emails aufzeichnen**

Im Block wo `gmail.star_email(email_id)` aufgerufen wird, danach einfügen:

```python
                    priority_emails.append({
                        "from": result.get("from", ""),
                        "subject": subject[:80],
                        "time": datetime.now().strftime("%H:%M"),
                    })
```

Achtung: `result.get("from", "")` — das `from`-Feld muss aus dem Email-Dict kommen. Das `result`-Dict hat aktuell nur `email_id`, `subject`, `body`, `classification`. Die `from`-Adresse ist im originalen `emails`-Dict. Lösung: im `for result in results:` Loop die originale Email suchen:

```python
        email_from = next(
            (e.get("from", "") for e in emails if e["id"] == email_id), ""
        )
```

Dann `priority_emails.append` mit `"from": email_from`.

- [ ] **Schritt 5: Calendar-Events aufzeichnen**

Wo `create_event(...)` erfolgreich war (nach `if success:`, Zeile 101), einfügen:

```python
                        calendar_events.append({
                            "title": appointment.get("titel", subject[:30]),
                            "date": appointment["datum"],
                            "time": appointment.get("uhrzeit", ""),
                        })
```

- [ ] **Schritt 6: Fehler aufzeichnen**

Im `except Exception as e:` Block (Zeile 107), nach `print(f"   ❌ Fehler: {e}\n")` einfügen:

```python
            errors.append(f"{subject[:40]}: {str(e)}")
```

- [ ] **Schritt 7: Snapshot am Ende von main() speichern**

Am Ende von `main()`, nach dem letzten `for`-Loop (vor `if __name__ == "__main__":`):

```python
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
```

- [ ] **Schritt 8: Manuell testen (kein echter API-Run nötig)**

```bash
cd ~/Projects/EmailAutomationPrivat
source .venv/bin/activate
python -c "
from src.reporter import save_snapshot
stats = {
    'date': '2026-05-02', 'timestamp': '2026-05-02T10:00:00',
    'total_processed': 5, 'label_counts': {'Newsletter': 2, 'Invoice': 1, 'General': 2},
    'priority_emails': [], 'calendar_events': [],
    'api_cost_chf': 0.001, 'runtime_seconds': 30.0, 'errors': []
}
save_snapshot(stats)
print('OK:', list(((__import__('pathlib').Path('reports/data')).glob('*.json'))))
"
```

Erwartet: `OK: [PosixPath('reports/data/2026-05-02.json')]`

- [ ] **Schritt 9: Commit**

```bash
git add src/main.py
git commit -m "Feat: main.py — Stats sammeln und täglichen Snapshot speichern"
```

---

## Task 5: purge_spam.py — Spam-Count als JSON speichern

**Files:**
- Modify: `src/purge_spam.py`

- [ ] **Schritt 1: Import ergänzen**

In `src/purge_spam.py`, nach `from gmail_client import GmailClient` einfügen:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import reporter
```

- [ ] **Schritt 2: Spam-Count nach dem Löschen speichern**

In `main()`, nach `print(f"✅ {count} Spam-Email(s)...")` (Zeile 27) einfügen:

```python
    try:
        reporter.save_spam_snapshot(count)
    except Exception as e:
        print(f"⚠️  Spam-Stats konnten nicht gespeichert werden: {e}")
```

- [ ] **Schritt 3: Commit**

```bash
git add src/purge_spam.py
git commit -m "Feat: purge_spam.py — Spam-Count als JSON speichern"
```

---

## Task 6: smart_unsubscribe.py — Kandidaten als JSON speichern

**Files:**
- Modify: `src/smart_unsubscribe.py`

- [ ] **Schritt 1: Import ergänzen**

In `src/smart_unsubscribe.py`, nach `from gmail_client import GmailClient` einfügen:

```python
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "reports" / "data"
```

- [ ] **Schritt 2: Kandidaten-JSON nach der Analyse speichern**

In `main()`, direkt VOR der interaktiven Bestätigung (`response = input(...)`, Zeile 135), einfügen:

```python
    # Kandidaten für Dashboard speichern
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        unsub_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "candidates": [
                {"sender": sender, "days_unread": 30, "unsubscribe_url": link}
                for sender, link in candidates
            ]
        }
        (DATA_DIR / "unsubscribe_latest.json").write_text(
            json.dumps(unsub_data, ensure_ascii=False, indent=2)
        )
    except Exception as e:
        print(f"⚠️  Unsubscribe-Stats konnten nicht gespeichert werden: {e}")
```

- [ ] **Schritt 3: Commit**

```bash
git add src/smart_unsubscribe.py
git commit -m "Feat: smart_unsubscribe.py — Kandidaten als JSON für Dashboard speichern"
```

---

## Task 7: run_daily.sh — Reporter am Ende aufrufen

**Files:**
- Modify: `run_daily.sh`

- [ ] **Schritt 1: Reporter-Aufruf am Ende von run_daily.sh ergänzen**

Direkt vor der letzten `echo ""` Zeile (Zeile 35) in `run_daily.sh` einfügen:

```bash
# Dashboard generieren
echo "$(date '+%Y-%m-%d %H:%M:%S') — Generating daily dashboard..." >> "$LOG_FILE"
python src/reporter.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ✅ Dashboard generated" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ⚠️  Dashboard generation failed (non-blocking)" >> "$LOG_FILE"
fi
```

- [ ] **Schritt 2: End-to-End Test mit Sample-Daten**

```bash
cd ~/Projects/EmailAutomationPrivat
source .venv/bin/activate

# Sample-Snapshot erstellen (simuliert main.py Run)
python -c "
from src.reporter import save_snapshot, save_spam_snapshot
from datetime import date
today = date.today().isoformat()
save_snapshot({
    'date': today, 'timestamp': today + 'T08:00:00',
    'total_processed': 18,
    'label_counts': {'Newsletter': 6, 'Invoice': 3, 'General': 5, 'Tax': 2, 'Health': 2},
    'priority_emails': [{'from': 'chef@firma.ch', 'subject': 'Meeting morgen?', 'time': '08:01'}],
    'calendar_events': [{'title': 'Zahnarzt', 'date': '20.05.2026', 'time': '14:00'}],
    'api_cost_chf': 0.0012, 'runtime_seconds': 38.5, 'errors': []
})
save_spam_snapshot(7)
print('Sample data created')
"

# Reporter manuell aufrufen
python src/reporter.py
```

Erwartet: Browser öffnet sich mit dunklem Dashboard. `reports/latest.html` und `reports/YYYY-MM-DD.html` existieren.

- [ ] **Schritt 3: Commit**

```bash
git add run_daily.sh
git commit -m "Feat: run_daily.sh — Reporter nach Daily-Run aufrufen"
```

---

## Task 8: Abschluss-Tests + Push

- [ ] **Schritt 1: Komplette Test-Suite laufen lassen**

```bash
pytest tests/ -v
```

Erwartet: alle Tests grün.

- [ ] **Schritt 2: Visuellen Check des Dashboards machen**

```bash
open reports/latest.html
```

Prüfen:
- [ ] Dark Mode Hintergrund sichtbar (Navy `#0f172a`)
- [ ] Pie Chart zeigt Label-Verteilung
- [ ] Priority-Tabelle ist sichtbar
- [ ] System-Gesundheit-Karte ist unten sichtbar
- [ ] Kein JavaScript-Fehler in Browser-Console (Rechtsklick → Inspizieren → Console)

- [ ] **Schritt 3: `.gitignore` prüfen — reports/ nicht committen**

```bash
grep "reports/" .gitignore
```

Falls nicht vorhanden, in `.gitignore` einfügen:
```
reports/
```

```bash
git add .gitignore
git commit -m "Chore: reports/ von git ausschliessen"
```

- [ ] **Schritt 4: Final Push**

```bash
git push
```

---

## Self-Review Checkliste

Spec-Abgleich:

| Spec-Anforderung | Abgedeckt in |
|-----------------|--------------|
| JSON-Snapshot täglich | Task 1 (save_snapshot) + Task 4 (main.py) |
| Spam-JSON getrennt | Task 1 (save_spam_snapshot) + Task 5 (purge_spam.py) |
| HTML mit Dark Mode | Task 2 (_build_html) |
| Pie Chart Labels | Task 2 (Chart.js doughnut) |
| Line Chart Trend 30 Tage | Task 2 (load_history + Chart.js line) |
| Priority-Emails Tabelle | Task 2 (priority_rows HTML) |
| Kalender-Events | Task 2 (calendar_items HTML) |
| SPAM-Stats | Task 2 (spam_deleted) |
| Unsubscribe-Kandidaten | Task 2 (unsub_section) + Task 6 |
| System-Gesundheit | Task 2 (API-Kosten, Laufzeit, Fehler) |
| Browser auto-öffnen | Task 2 (subprocess.run open) |
| API-Kosten tracken | Task 3 (classifier.py Token-Tracking) |
| run_daily.sh ergänzen | Task 7 |
| Fehlerbehandlung (non-blocking) | Task 2 (generate_report try/except) + Task 7 (exit code check) |
| Trend-Fallback "zu wenig Daten" | Task 2 (len(history) < 2 check) |
| Unsubscribe-Fallback | Task 2 (unsub_section else-Branch) |
| reports/ nicht in git | Task 8 (.gitignore) |
