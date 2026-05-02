"""Reporter: Speichert tägliche Stats als JSON und generiert HTML-Dashboard."""

import json
import subprocess
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = REPORTS_DIR / "data"


def save_snapshot(stats: dict, data_dir: Path = None) -> None:
    """Speichere tägliche Stats in reports/data/YYYY-MM-DD.json."""
    target = data_dir or DATA_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{stats['date']}.json"
    path.write_text(json.dumps(stats, ensure_ascii=False, indent=2))


def save_spam_snapshot(count: int, data_dir: Path = None, today: str = None) -> None:
    """Speichere Spam-Count in reports/data/YYYY-MM-DD-spam.json."""
    target = data_dir or DATA_DIR
    target.mkdir(parents=True, exist_ok=True)
    day = today or date.today().isoformat()
    path = target / f"{day}-spam.json"
    path.write_text(json.dumps({"date": day, "deleted": count}))


def load_history(days: int = 30, data_dir: Path = None) -> list:
    """Lade letzte N Tages-Snapshots, sortiert nach Datum aufsteigend."""
    target = data_dir or DATA_DIR
    if not target.exists():
        return []
    files = sorted(
        [f for f in target.glob("????-??-??.json")],
        key=lambda f: f.stem
    )
    snapshots = []
    for f in files[-days:]:
        try:
            snapshots.append(json.loads(f.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return snapshots


def load_unsubscribe(data_dir: Path = None) -> dict:
    """Lade letzten Unsubscribe-Report, falls vorhanden."""
    target = data_dir or DATA_DIR
    path = target / "unsubscribe_latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
