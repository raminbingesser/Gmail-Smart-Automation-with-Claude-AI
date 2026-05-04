#!/bin/bash
# Tägliche Email-Klassifikation
# Läuft stündlich via launchd — Lock-File verhindert Doppelausführung pro Tag

PROJECT_DIR="/Users/raminbingesser/Projects/EmailAutomationPrivat"
LOG_FILE="$PROJECT_DIR/logs/automation.log"
LOCK_FILE="$PROJECT_DIR/logs/.daily_lock_$(date +%Y-%m-%d)"

# Logs-Ordner erstellen falls nicht vorhanden
mkdir -p "$PROJECT_DIR/logs"

# Heute schon gelaufen? Dann still beenden.
if [ -f "$LOCK_FILE" ]; then
    exit 0
fi

# Lock-File sofort setzen (verhindert parallele Starts)
touch "$LOCK_FILE"

# Timestamp für Logging
echo "================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') — Starting email classification" >> "$LOG_FILE"

# Aktiviere venv und starte Skript
cd "$PROJECT_DIR" || exit 1

# Auto-Update: neueste Änderungen von GitHub holen
git pull --quiet origin main >> "$LOG_FILE" 2>&1

source .venv/bin/activate

python src/main.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ✅ Classification success" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ❌ Classification error" >> "$LOG_FILE"
fi

# SPAM-Bereinigung
echo "$(date '+%Y-%m-%d %H:%M:%S') — Starting spam cleanup (ONLY Gmail SPAM folder)" >> "$LOG_FILE"
python src/purge_spam.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ✅ Spam cleanup success" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ❌ Spam cleanup error" >> "$LOG_FILE"
fi

# Dashboard generieren
echo "$(date '+%Y-%m-%d %H:%M:%S') — Generating daily dashboard..." >> "$LOG_FILE"
python src/reporter.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ✅ Dashboard generated" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ⚠️  Dashboard generation failed (non-blocking)" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
