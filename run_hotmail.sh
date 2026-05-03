#!/bin/bash
# Tägliche Hotmail-Klassifikation (Ehefrau)
# Wird täglich um 8 Uhr via launchd ausgeführt

PROJECT_DIR="$HOME/Projects/EmailAutomationPrivat"
LOG_FILE="$PROJECT_DIR/logs/hotmail.log"

mkdir -p "$PROJECT_DIR/logs"

echo "================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') — Starting Hotmail classification" >> "$LOG_FILE"

cd "$PROJECT_DIR" || exit 1

# Auto-Update: neueste Änderungen von GitHub holen
git pull --quiet origin main >> "$LOG_FILE" 2>&1

source .venv/bin/activate

python src/main_hotmail.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ✅ Classification success" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ❌ Classification error" >> "$LOG_FILE"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') — Generating daily dashboard..." >> "$LOG_FILE"
python src/reporter_hotmail.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ✅ Dashboard generated" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') — ⚠️  Dashboard generation failed (non-blocking)" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
