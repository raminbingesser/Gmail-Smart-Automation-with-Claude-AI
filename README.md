# Gmail Smart Automation with Claude AI

AI-powered Gmail automation with Claude. Automatically classifies emails into 5 intelligent categories, detects priority messages, syncs health appointments to Apple Calendar, and intelligently manages inactive newsletters. Runs daily via macOS LaunchAgent.

## ✨ Features

### Daily Automation (8:00 AM)
- 📧 **Smart Classification** — Classifies emails into 5 categories using Claude AI
- 🏷️ **Auto-Labeling** — Labels: Newsletter, Invoice, General, Tax, Health
- ⭐ **Priority Detection** — Emails needing replies get starred automatically
- 📅 **Health → Calendar** — Medical appointments auto-sync to Apple Calendar "Privat"
- 🗑️ **Spam Cleanup** — Automatically empties Gmail's Spam folder

### Weekly Automation (Mondays 8:00 AM)
- 🧼 **Smart Unsubscribe** — Finds inactive newsletters (30+ days unread)
- 📋 **Interactive Report** — Shows unsubscribe links for confirmation
- 🔗 **Auto-Open** — Opens links after your approval

## Tech Stack

- **Claude API** (Haiku 4.5 — fast & cost-efficient)
- **Gmail API** (OAuth 2.0)
- **Apple Calendar** (via osascript)
- **Python 3.9+**
- **macOS LaunchAgent** (scheduling)

## Quick Start

### 1. Setup Project

```bash
cd ~/Projects/EmailAutomationPrivat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Google Cloud Setup

See [GOOGLE_CLOUD_SETUP.md](./GOOGLE_CLOUD_SETUP.md) for step-by-step instructions.

After setup, you'll have:
- `credentials/credentials.json` (OAuth client secret)
- `GOOGLE_CREDENTIALS_PATH` env var configured

### 3. Add Claude API Key

Get your key from https://console.anthropic.com/keys and add to `.env`:

```bash
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=sk-ant-...
```

### 4. First Run

```bash
python src/main.py
```

Output:
```
📧 Deine Bestellung von wog.ch ist unterwegs
   → Label: 'Invoice' (88%)
   ✅ Gelabelt + als gelesen markiert
   📅 Termin → Apple Calendar
```

## Labels

| Label | Purpose | Examples |
|-------|---------|----------|
| **Newsletter** | Marketing, subscriptions, digests | Unsubscribe, weekly digest |
| **Invoice** | Receipts, payments, transactions | Receipt #123, payment confirmed |
| **General** | Support tickets, requests, offers | Inquiry, ticket #456, proposal |
| **Tax** | Tax docs, AHV, IV, BVG, insurance | Lohnausweis, AXA policy, Steuererklärung |
| **Health** | Medical appointments, prescriptions | Dr. appointment, prescription ready |

Configure in `config/labels.yaml`.

## Automation Schedule

```
Every Day @ 8:00 AM:
  ├─ Classify emails (Newsletter, Invoice, General, Tax, Health)
  ├─ Star emails that need replies
  ├─ Add health appointments to Calendar
  └─ Empty Gmail SPAM folder

Every Monday @ 8:00 AM:
  └─ Find & report inactive newsletters
```

## Project Structure

```
src/
  ├── main.py              # Daily orchestration
  ├── classifier.py        # Claude integration (classification, priority, appointment extraction)
  ├── gmail_client.py      # Gmail API wrapper
  ├── calendar_client.py   # Apple Calendar sync
  ├── smart_unsubscribe.py # Weekly inactive newsletter report
  └── purge_spam.py        # SPAM folder cleanup

config/
  └── labels.yaml          # Label definitions + keywords

run_daily.sh               # Daily automation script
run_weekly.sh              # Weekly automation script

~/Library/LaunchAgents/
  ├── com.emailautomationprivat.daily.plist
  └── com.emailautomationprivat.weekly.plist
```

## Configuration

### Labels: `config/labels.yaml`

```yaml
labels:
  - name: Newsletter
    description: "Marketing, Subscriptions, Digests"
    keywords: ["newsletter", "subscription", "unsubscribe", "digest"]

  - name: Invoice
    description: "Rechnungen, Payments, Transaktionen"
    keywords: ["invoice", "payment", "receipt", "transaction"]

  # ... more labels
```

### Environment: `.env`

```env
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_CREDENTIALS_PATH=credentials/credentials.json
GOOGLE_TOKEN_PATH=credentials/token.json
CLASSIFIER_MODEL=claude-haiku-4-5-20251001
EMAILS_PER_RUN=100
```

## Costs

- **Claude Haiku**: ~0.0001 CHF per email (1000 emails = 0.10 CHF)
- **Gmail API**: Free tier
- **Apple Calendar**: Included with macOS

## Security

⚠️ **Critical:** `.env` and `credentials/*.json` are in `.gitignore` — never commit API keys!

For OAuth token refresh issues:
```bash
rm credentials/token.json
python src/main.py  # Will re-authenticate
```

## Testing

```bash
# Test classification
pytest tests/test_classifier.py -v

# Manual test
python src/main.py

# Test weekly unsubscribe
python src/smart_unsubscribe.py
```

## Troubleshooting

**"ModuleNotFoundError: No module named 'anthropic'"**
→ Activate venv: `source .venv/bin/activate`

**"OAuth token expired"**
→ `rm credentials/token.json` and run again (triggers re-authentication)

**"Calendar Event Creation Error"**
→ Check osascript: `osascript -e 'tell app "Calendar" to name'`
→ Calendar "Privat" must exist on your Mac

## License

Private project. See CLAUDE.md for contribution guidelines.

---

Built with [Claude Code](https://claude.com/claude-code) + ❤️
