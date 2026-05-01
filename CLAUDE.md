# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projektübersicht

**EmailAutomationPrivat** automatisiert Gmail-Klassifikation mit Claude AI:
1. Liest ungelesene Emails (Gmail API + OAuth)
2. Klassifiziert sie intelligent (Claude Haiku)
3. Setzt automatisch Labels

**Tech:** Python 3.10+, Claude API, Gmail API v1, OAuth 2.0

---

## Häufige Commands

### Vorbereitung (einmalig)

```bash
# Projekt-Ordner
cd ~/projects/EmailAutomationPrivat

# venv aktivieren
source .venv/bin/activate

# Credentials erstellen (siehe GOOGLE_CLOUD_SETUP.md)
# - Google Cloud Project erstellen
# - Gmail API aktivieren
# - OAuth 2.0 Credentials runterladen → credentials/credentials.json

# .env ausfüllen (von .env.example kopieren, ANTHROPIC_API_KEY hinzufügen)
cp .env.example .env
# Editor öffnen → ANTHROPIC_API_KEY=sk-ant-... eintragen
```

### Development

```bash
# Classifier testen (erste Lauf = OAuth Browser-Popup)
python src/main.py

# Unit Tests (mocked, keine echten API-Calls)
pytest tests/ -v

# Einzelnen Test laufen
pytest tests/test_classifier.py::test_classify_email_newsletter -v

# Test-Coverage
pytest tests/ --cov=src --cov-report=html
```

### Debugging

```bash
# Logs schreiben (für später)
python src/main.py > run.log 2>&1

# OAuth Token zurücksetzen (neue Authentifizierung beim nächsten Lauf)
rm credentials/token.json
```

---

## Architektur

### 3-Schicht-Modell

```
┌─────────────┐
│   main.py   │ Orchestrierung: Emails holen → klassifizieren → labeln
├─────────────┤
│ classifier  │ Claude API (Haiku): Email (Subject+Body) → Label+Confidence
│ gmail_client│ Gmail API: OAuth Flow, Email fetch, Label apply
└─────────────┘
```

### Gmail Client (`src/gmail_client.py`)

**OAuth Flow:**
- `get_service()` authentifiziert OAuth (öffnet Browser bei Erstlauf)
- Token wird in `credentials/token.json` gecacht (auto-refresh)
- Scopes: `gmail.modify` (read + label, kein delete/send)

**API Operations:**
- `fetch_unread_emails(limit)` → Liste mit `{id, subject, from, body}`
- `apply_label(email_id, label_name)` → erstellt Label falls nicht existent
- `mark_as_read(email_id)` → entfernt UNREAD label

### Classifier (`src/classifier.py`)

**Claude Haiku Integration:**
- `classify_email(subject, body, labels)` → JSON: `{label, confidence, reason}`
- System Prompt erzwingt JSON-Output (error-handling für Parse-Fehler)
- `batch_classify()` für Multiple Emails (sequenziell)

### Main (`src/main.py`)

**Flow:**
1. Load `.env` (ANTHROPIC_API_KEY, GOOGLE_CREDENTIALS_PATH, etc.)
2. Labels aus `config/labels.yaml` laden
3. OAuth initialisieren (Browser-Popup falls nötig)
4. Emails holen (unread, limit via ENV)
5. Klassifizieren (Claude)
6. Labels setzen + als gelesen markieren
7. Feedback ausgeben (emoji + Begründung)

**Config:**
- `config/labels.yaml` — Label-Namen + Beschreibung
- `.env` — Keys, Paths, Batch-Size

---

## Sicherheit (Prio 5)

⚠️ **Kritische Files (NIEMALS committen!):**
- `.env` — API Keys (ANTHROPIC_API_KEY)
- `credentials/credentials.json` — OAuth Client Secrets
- `credentials/token.json` — OAuth Access Token (auto-generated)

**Beide sind in `.gitignore`** — aber doppel-check!

**Token-Rotation:**
Falls Token kompromittiert:
```bash
rm credentials/token.json
python src/main.py  # Neue Authentifizierung beim nächsten Lauf
```

---

## OAuth Besonderheiten

1. **Erstlauf:** `python src/main.py` → Browser öffnet sich automatisch
   - User muss Gmail-Zugriff erlauben
   - Token wird gecacht in `credentials/token.json`

2. **Token-Refresh:** Auto (wenn abgelaufen) via `GoogleRequest()`

3. **Scopes:** 
   - `gmail.modify` = read + label + archive
   - Kein delete, kein send (sicher by design)

---

## Testing

**Unit Tests** (`tests/test_classifier.py`):
- Mock Claude API (kein echter API-Call)
- Test Happy Path (Newsletter, Invoice, Spam)
- Test Error-Handling (malformed JSON)
- Test Batch-Klassifikation

**Keine Integration Tests** (würden echte Gmail erfordern)

---

## Kosten

- **Claude Haiku:** ~0.0001 CHF pro Email → 1000 Emails = 0.10 CHF
- **Gmail API:** Kostenlos (Free Tier)

---

## Workflow-Regeln (Ramin-spezifisch)

- **git add**: Spezifische Files, nicht `git add -A` (verhindert Secrets)
- **Commit-Messages**: Deutsche Beschreibung, dann Co-Authored-By
- **Plan Mode**: Für mehrteilige Features (neue Module, API-Changes)
- **Sicherheit first**: Secrets checken, .gitignore double-check vor jedem commit

---

## Etappenplan (Referenz)

| Phase | Was | Status |
|-------|-----|--------|
| 1 | Struktur + Setup | ✅ |
| 2 | Google Cloud Config | 📋 |
| 3 | Gmail API Test | ⏳ |
| 4 | Claude Klassifikation | ⏳ |
| 5 | Integration + Tests | ⏳ |

Siehe auch: `GOOGLE_CLOUD_SETUP.md` für Step-by-Step Google Cloud.
