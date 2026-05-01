# CLAUDE.md — Gmail Smart Automation with Claude AI

Guidance für Claude Code beim Arbeiten an diesem Projekt.

## Projektübersicht

**Gmail Smart Automation** — vollautomatisierte Email-Verwaltung mit Claude AI + macOS LaunchAgent:

### Was läuft täglich (8:00 AM)
- 📧 **Klassifikation** — Liest bis zu 100 Emails (gelesen + ungelesen)
- 🏷️ **Auto-Labeling** — 5 Labels: Newsletter, Invoice, General, Tax, Health
- ⭐ **Priority Detection** — Claude erkennt Emails die Antwort brauchen → Gmail-Stern
- 📅 **Health → Calendar** — Arzttermine landen automatisch in Apple Calendar "Privat"
- 🗑️ **Spam Cleanup** — Leert Gmail SPAM-Ordner

### Was läuft wöchentlich (Montags 8:00 AM)
- 🧼 **Smart Unsubscribe** — Findet Newsletter, die 30+ Tage ungelesen sind
- 📋 **Interaktiver Report** — User bestätigt → Script öffnet Unsubscribe-Links

**Tech:** Python 3.9+, Claude Haiku 4.5, Gmail API v1 (OAuth 2.0), Apple Calendar (osascript), macOS LaunchAgent

---

## Häufige Commands

### Setup (einmalig)

```bash
cd ~/Projects/EmailAutomationPrivat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Google Cloud Setup (siehe GOOGLE_CLOUD_SETUP.md)
cp .env.example .env
# Dann: ANTHROPIC_API_KEY=sk-ant-... eintragen
```

### Manuelles Testen

```bash
# Täglich-Job manuell (100 Emails, mit Priority + Calendar)
python src/main.py

# Wöchentlich-Job manuell (findet inaktive Newsletter)
python src/smart_unsubscribe.py

# Nur SPAM-Ordner leeren
python src/purge_spam.py

# Tests
pytest tests/ -v
```

### Logs checken

```bash
tail -f logs/automation.log  # Daily + Weekly + SPAM
tail -f logs/weekly.log      # Weekly nur
```

### Debugging

```bash
# OAuth neu authentifizieren
rm credentials/token.json && python src/main.py

# Calendar Test (prüf ob osascript funktioniert)
osascript -e 'tell app "Calendar" to name'

# Claude API debuggen (check model + token usage)
ANTHROPIC_API_KEY=... python -c "from anthropic import Anthropic; c = Anthropic(); print(c.models.list())"
```

---

## Architektur

### Files Overview

```
src/
  ├── main.py              # Daily orchestration (täglich 8:00)
  ├── classifier.py        # Claude: classification + needs_reply + extract_appointment
  ├── gmail_client.py      # Gmail API wrapper (OAuth, fetch, label, star, delete_spam)
  ├── calendar_client.py   # Apple Calendar (osascript)
  ├── smart_unsubscribe.py # Weekly: inactive newsletters (montags 8:00)
  └── purge_spam.py        # Tägliche SPAM-Bereinigung

config/
  └── labels.yaml          # 5 Labels + Keywords

run_daily.sh               # → main.py + purge_spam.py
run_weekly.sh              # → smart_unsubscribe.py

~/Library/LaunchAgents/
  ├── com.emailautomationprivat.daily.plist    (täglich 8:00)
  └── com.emailautomationprivat.weekly.plist   (montags 8:00)
```

### Labels (aktuell)

| Label | Zweck |
|-------|-------|
| **Newsletter** | Marketing, Subscriptions, Digests |
| **Invoice** | Rechnungen, Payments, Transaktionen |
| **General** | Anfragen, Support, Tickets |
| **Tax** | Steuern, AHV, IV, BVG, Versicherungen |
| **Health** | Arzttermine, Medizin, Zahnärzte |

Konfiguriert in `config/labels.yaml`.

### Classifier (`src/classifier.py`)

```python
# Klassifikation
classify_email(subject, body, labels) → {label, confidence, reason}

# Priority Detection
needs_reply(subject, body) → bool  # Claude: "Braucht Antwort?"

# Health Appointment Extraction
extract_appointment(subject, body) → {titel, datum, uhrzeit, dauer_min, ort} | None
```

### Gmail Client (`src/gmail_client.py`)

```python
fetch_recent_emails(limit=100) → [{id, subject, from, body}]  # gelesen + ungelesen
apply_label(email_id, label_name) → bool
star_email(email_id) → bool  # Priority Detection
mark_as_read(email_id) → bool
delete_spam_folder() → int  # Anzahl gelöschter Mails
remove_label_by_name(label_name) → int  # Cleanup bei Label-Änderungen
```

### Calendar Client (`src/calendar_client.py`)

```python
create_event(title, date_str, time_str, duration_min, location, calendar="Privat") → bool
# Nutzt osascript (macOS AppleScript)
# Datum-Format: "DD.MM.YYYY" (Swiss German Locale)
```

---

## Sicherheit

⚠️ **NIEMALS committen:**
- `.env` — ANTHROPIC_API_KEY
- `credentials/credentials.json` — OAuth Client Secret
- `credentials/token.json` — OAuth Access Token

**Beide sind in `.gitignore`**. Double-check vor jedem commit!

**Falls Token kompromittiert:**
```bash
rm credentials/token.json
python src/main.py  # Neue Authentifizierung
```

---

## Workflow-Regeln

- **git add**: Spezifische Files (`git add src/`, nicht `git add -A`)
- **Commit-Messages**: Deutsch, Format: "Feat: X", "Fix: Y", dann Co-Authored-By
- **Plan Mode**: Für Features mit >3 Schritten oder unsicheren Entscheidungen
- **Tests**: Vor jedem Push — `pytest tests/ -v`
- **GitHub**: Push nur auf main, ReadMe aktuell halten

---

## Kosten (monatlich)

| Service | Preis | Anmerkung |
|---------|-------|----------|
| Claude Haiku | ~0.01 CHF | ~1000 Emails = 0.10 CHF |
| Gmail API | 0 CHF | Free tier |
| Apple Calendar | 0 CHF | macOS included |

---

## Monitoring

**Logs prüfen:**
```bash
tail -f logs/automation.log
# Output:
# 2026-05-01 08:00:23 — Starting email classification
# 📧 Deine Bestellung...
# ✅ Classification success
# ...
# ✅ Spam cleanup success
```

**LaunchAgent Status:**
```bash
launchctl list | grep emailautomationprivat
# -	0	com.emailautomationprivat.daily
# -	0	com.emailautomationprivat.weekly
```

---

## Nächste Ideen (Backlog)

- Auto-Archivierung nach X Tagen
- Newsletter-Sampling (nur 1 von N behalten)
- Delegation an Team-Mitglieder (Tickets zuweisen)
- Email-Summarization für lange Threads
