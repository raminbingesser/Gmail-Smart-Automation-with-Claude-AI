#!/bin/bash
# Tägliche Email-Klassifikation
# Wird täglich um 8 Uhr morgens ausgeführt (via launchd)

PROJECT_DIR="/Users/raminbingesser/projects/EmailAutomationPrivat"
LOG_FILE="$PROJECT_DIR/logs/automation.log"

# Logs-Ordner erstellen falls nicht vorhanden
mkdir -p "$PROJECT_DIR/logs"

# Timestamp für Logging
echo "================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') — Starting email classification" >> "$LOG_FILE"

# Aktiviere venv und starte Skript
cd "$PROJECT_DIR" || exit 1
source .venv/bin/activate

python src/main.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ✅ Success" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ❌ Error occurred" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
