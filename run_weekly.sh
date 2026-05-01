#!/bin/bash
# Wöchentliche Smart Unsubscribe — jeden Montag um 8:00 MEZ

PROJECT_DIR="/Users/raminbingesser/Projects/EmailAutomationPrivat"
LOG_FILE="$PROJECT_DIR/logs/automation.log"

# Logs-Ordner erstellen falls nicht vorhanden
mkdir -p "$PROJECT_DIR/logs"

# Timestamp für Logging
echo "================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') — Starting weekly smart unsubscribe" >> "$LOG_FILE"

# Aktiviere venv und starte Script
cd "$PROJECT_DIR" || exit 1
source .venv/bin/activate

python src/smart_unsubscribe.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ✅ Smart unsubscribe success" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ❌ Smart unsubscribe error" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
