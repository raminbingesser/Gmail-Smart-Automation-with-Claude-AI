#!/bin/bash
# Einmaliger Backfill: Alle bestehenden Emails klassifizieren und sortieren
# Nur einmal ausführen — danach läuft die tägliche Automation automatisch

PROJECT_DIR="$HOME/Projects/EmailAutomationPrivat"
cd "$PROJECT_DIR" || exit 1
source .venv/bin/activate
python src/backfill_hotmail.py
