# EmailAutomationPrivat

Automatisiere deinen Gmail-Account: Claude liest Emails, klassifiziert sie intelligent und setzt automatisch Labels.

## Features (Phase 1)

- 📧 Liest ungelesene Emails aus Gmail
- 🤖 Klassifiziert Emails mit Claude AI (intelligent, nicht Regex)
- 🏷️ Setzt automatisch Labels (Wichtig, Newsletter, Rechnung, etc.)

## Tech Stack

- **Claude API** (Haiku für schnell + günstig)
- **Gmail API** (über OAuth)
- **Python 3.10+**

## Quick Start

### 1. Projekt aufsetzen

```bash
cd ~/projects/EmailAutomationPrivat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Google Cloud Setup (manuell)

Siehe [GOOGLE_CLOUD_SETUP.md](./GOOGLE_CLOUD_SETUP.md) für Step-by-Step Anleitung.

Danach:
- `credentials/credentials.json` vorhanden
- Env-Var gesetzt: `GOOGLE_CREDENTIALS_PATH`

### 3. Claude API Key

Von https://console.anthropic.com/keys kopieren und in `.env` eintragen.

### 4. Erste Testlauf

```bash
python src/main.py
```

Ausgabe:
```
📧 Email: "Neue Rechnung von XYZ"
  → Label: "Rechnung" (confidence: 0.95)
  ✅ Gelabelt in Gmail
```

## Config

**Labels definieren:** `config/labels.yaml`

```yaml
labels:
  - name: Wichtig
    keywords: ["urgent", "asap", "action required"]
  - name: Newsletter
    keywords: ["unsubscribe", "volume"]
  - name: Rechnung
    keywords: ["invoice", "payment", "rechnung"]
```

## Projektstruktur

```
src/
  ├── gmail_client.py   # Gmail API Wrapper
  ├── classifier.py     # Claude Integration
  └── main.py          # Entry Point

config/
  └── labels.yaml      # Label-Konfiguration

credentials/           # OAuth Tokens (gitignored!)
```

## Kosten

- **Claude Haiku**: ~0.0001 CHF pro Email (1000 Emails = 0.10 CHF)
- **Gmail API**: kostenfrei

## Etappenplan

| Phase | Was | Status |
|-------|-----|--------|
| 1 | Struktur + Setup | ✅ Done |
| 2 | Google Cloud Konfiguration | 📋 Next |
| 3 | Gmail API testen | ⏳ Pending |
| 4 | Claude Klassifikation | ⏳ Pending |
| 5 | Integration + Tests | ⏳ Pending |

## Troubleshooting

**"ModuleNotFoundError: No module named 'anthropic'"**
→ venv nicht aktiviert? `source .venv/bin/activate`

**"OAuth token expired"**
→ `rm credentials/token.json` und neu starten (neue OAuth Authentifizierung)

---

Fragen? Siehe CLAUDE.md oder starte ein neues Gespräch.
