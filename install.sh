#!/bin/bash
# Email Automation — Installer für Hotmail/Outlook
# Einmalig ausführen: bash install.sh

set -e

REPO_URL="https://github.com/raminbingesser/Gmail-Smart-Automation-with-Claude-AI.git"
PROJECT_DIR="$HOME/Projects/EmailAutomationPrivat"
PLIST_LABEL="com.emailautomationprivat.hotmail"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║      Email Automation — Setup (Hotmail)          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Voraussetzungen prüfen ──────────────────────────────
echo "▶ Überprüfe Voraussetzungen..."

if ! command -v python3 &>/dev/null; then
    echo "❌ python3 nicht gefunden. Bitte Python 3 installieren: https://www.python.org"
    exit 1
fi

if ! command -v git &>/dev/null; then
    echo "❌ git nicht gefunden. Bitte Git installieren: https://git-scm.com"
    exit 1
fi

echo "   ✅ python3: $(python3 --version)"
echo "   ✅ git: $(git --version | head -1)"
echo ""

# ── Microsoft App-Passwort Hinweis ─────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 WICHTIG: Microsoft App-Passwort"
echo ""
echo "   Für Hotmail/Outlook brauchst du ein App-Passwort"
echo "   (nicht dein normales Passwort)."
echo ""
echo "   So erstellst du eines:"
echo "   1. Geh auf: https://account.microsoft.com/security"
echo "   2. Klick auf 'Erweiterte Sicherheitsoptionen'"
echo "   3. Aktiviere 2-Schritt-Verifizierung (falls noch nicht)"
echo "   4. Scrolle zu 'App-Kennwörter' → 'Neues App-Kennwort'"
echo "   5. Name: 'Email Automation' → Erstellen"
echo "   6. Kopiere das 16-stellige Passwort"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Drücke Enter wenn du das App-Passwort bereit hast..." _

# ── Zugangsdaten abfragen ───────────────────────────────
echo ""
echo "▶ Zugangsdaten eingeben:"
echo ""

read -p "   Deine Hotmail-Adresse: " HOTMAIL_EMAIL
echo ""

read -s -p "   App-Passwort (16 Zeichen, wird nicht angezeigt): " HOTMAIL_PASSWORD
echo ""
echo ""

read -s -p "   Anthropic API-Key (sk-ant-...): " ANTHROPIC_API_KEY
echo ""
echo ""

# Einfache Validierung
if [[ ! "$HOTMAIL_EMAIL" == *"@"* ]]; then
    echo "❌ Ungültige Email-Adresse."
    exit 1
fi

if [[ ${#HOTMAIL_PASSWORD} -lt 8 ]]; then
    echo "❌ App-Passwort zu kurz. Bitte erneut prüfen."
    exit 1
fi

if [[ ! "$ANTHROPIC_API_KEY" == sk-ant-* ]]; then
    echo "❌ API-Key muss mit 'sk-ant-' beginnen."
    exit 1
fi

# ── Projekt klonen / aktualisieren ─────────────────────
echo "▶ Projekt einrichten..."

if [ -d "$PROJECT_DIR/.git" ]; then
    echo "   Projekt bereits vorhanden — aktualisiere..."
    git -C "$PROJECT_DIR" pull --quiet origin main
else
    mkdir -p "$HOME/Projects"
    git clone --quiet "$REPO_URL" "$PROJECT_DIR"
    echo "   ✅ Projekt geklont nach $PROJECT_DIR"
fi

# ── Python venv + Abhängigkeiten ───────────────────────
echo "▶ Python-Umgebung einrichten..."
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "   ✅ Abhängigkeiten installiert"

# ── .env Datei schreiben ───────────────────────────────
echo "▶ Konfiguration speichern..."

cat > "$PROJECT_DIR/.env" <<EOF
# Anthropic API
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY

# Hotmail IMAP
HOTMAIL_EMAIL=$HOTMAIL_EMAIL
HOTMAIL_PASSWORD=$HOTMAIL_PASSWORD
HOTMAIL_IMAP_SERVER=outlook.office365.com
HOTMAIL_IMAP_PORT=993

# Classifier
CLASSIFIER_MODEL=claude-haiku-4-5-20251001
EMAILS_PER_RUN=100
EOF

chmod 600 "$PROJECT_DIR/.env"
echo "   ✅ .env gespeichert (nur für dich lesbar)"

# ── run_hotmail.sh ausführbar machen ──────────────────
chmod +x "$PROJECT_DIR/run_hotmail.sh"

# ── LaunchAgent erstellen ──────────────────────────────
echo "▶ LaunchAgent registrieren (täglich 08:00)..."

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$PROJECT_DIR/logs"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/run_hotmail.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/stdout_hotmail.log</string>

    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/stderr_hotmail.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# LaunchAgent registrieren (bestehenden erst entladen falls vorhanden)
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
echo "   ✅ LaunchAgent registriert"

# ── Verbindungstest ────────────────────────────────────
echo ""
echo "▶ Teste IMAP-Verbindung..."
python3 - <<PYEOF
import imaplib, ssl, os
from dotenv import load_dotenv
load_dotenv("$PROJECT_DIR/.env")
email = os.getenv("HOTMAIL_EMAIL")
password = os.getenv("HOTMAIL_PASSWORD")
try:
    ctx = ssl.create_default_context()
    imap = imaplib.IMAP4_SSL("outlook.office365.com", 993, ssl_context=ctx)
    imap.login(email, password)
    imap.logout()
    print("   ✅ IMAP-Verbindung erfolgreich!")
except Exception as e:
    print(f"   ❌ Verbindungsfehler: {e}")
    print("   → Prüfe Email-Adresse und App-Passwort")
    exit(1)
PYEOF

# ── Fertig ────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║                ✅ Setup abgeschlossen!            ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "   Die Automation läuft ab morgen täglich um 08:00."
echo "   Du erhältst täglich einen Report an: $HOTMAIL_EMAIL"
echo ""
echo "   Logs: $PROJECT_DIR/logs/hotmail.log"
echo ""
echo "   Bei Problemen: tail -f ~/Projects/EmailAutomationPrivat/logs/hotmail.log"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Tipp: Bestehende Emails einmalig sortieren?"
echo ""
echo "   Falls du auch alle bisherigen Emails in deiner"
echo "   INBOX sortieren möchtest, führe einmalig aus:"
echo ""
echo "   bash ~/Projects/EmailAutomationPrivat/backfill_hotmail.sh"
echo ""
echo "   Das Script zeigt Kosten + fragt vor dem Start."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
