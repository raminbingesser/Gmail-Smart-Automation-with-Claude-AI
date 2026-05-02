"""Tests für reporter.py — Datenfunktionen."""

import json
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.reporter import save_snapshot, save_spam_snapshot, load_history


SAMPLE_STATS = {
    "date": "2026-05-02",
    "timestamp": "2026-05-02T08:03:45",
    "total_processed": 23,
    "label_counts": {"Newsletter": 8, "Invoice": 3, "General": 7, "Tax": 2, "Health": 3},
    "priority_emails": [{"from": "arzt@praxis.ch", "subject": "Ihr Termin", "time": "08:01"}],
    "calendar_events": [{"title": "Zahnarzt", "date": "15.05.2026", "time": "10:00"}],
    "api_cost_chf": 0.0008,
    "runtime_seconds": 45.2,
    "errors": [],
}


def test_save_snapshot_creates_json_file(tmp_path):
    save_snapshot(SAMPLE_STATS, data_dir=tmp_path)
    expected = tmp_path / "2026-05-02.json"
    assert expected.exists()


def test_save_snapshot_content_is_correct(tmp_path):
    save_snapshot(SAMPLE_STATS, data_dir=tmp_path)
    data = json.loads((tmp_path / "2026-05-02.json").read_text())
    assert data["total_processed"] == 23
    assert data["label_counts"]["Newsletter"] == 8
    assert len(data["priority_emails"]) == 1


def test_save_snapshot_creates_missing_directory(tmp_path):
    target = tmp_path / "deep" / "nested"
    save_snapshot(SAMPLE_STATS, data_dir=target)
    assert (target / "2026-05-02.json").exists()


def test_save_spam_snapshot_creates_file(tmp_path):
    save_spam_snapshot(12, data_dir=tmp_path, today="2026-05-02")
    expected = tmp_path / "2026-05-02-spam.json"
    assert expected.exists()
    data = json.loads(expected.read_text())
    assert data["deleted"] == 12


def test_load_history_returns_sorted_list(tmp_path):
    for day, count in [("2026-05-01", 10), ("2026-05-02", 23), ("2026-04-30", 5)]:
        stats = {**SAMPLE_STATS, "date": day, "total_processed": count}
        save_snapshot(stats, data_dir=tmp_path)

    history = load_history(days=30, data_dir=tmp_path)
    assert len(history) == 3
    assert history[0]["date"] == "2026-04-30"
    assert history[-1]["date"] == "2026-05-02"


def test_load_history_ignores_spam_files(tmp_path):
    save_snapshot(SAMPLE_STATS, data_dir=tmp_path)
    save_spam_snapshot(5, data_dir=tmp_path, today="2026-05-02")

    history = load_history(days=30, data_dir=tmp_path)
    assert len(history) == 1


def test_load_history_empty_when_no_files(tmp_path):
    history = load_history(days=30, data_dir=tmp_path)
    assert history == []


def test_load_unsubscribe_returns_none_when_missing(tmp_path):
    from src.reporter import load_unsubscribe
    result = load_unsubscribe(data_dir=tmp_path)
    assert result is None


def test_load_unsubscribe_returns_dict_when_present(tmp_path):
    from src.reporter import load_unsubscribe
    data = {"date": "2026-05-02", "candidates": [{"sender": "test@example.com", "days_unread": 45}]}
    (tmp_path / "unsubscribe_latest.json").write_text(__import__("json").dumps(data))
    result = load_unsubscribe(data_dir=tmp_path)
    assert result is not None
    assert result["date"] == "2026-05-02"
    assert len(result["candidates"]) == 1


def test_generate_report_creates_html_file(tmp_path):
    from src.reporter import generate_report, save_snapshot, save_spam_snapshot
    reports_dir = tmp_path / "reports"
    save_snapshot(SAMPLE_STATS, data_dir=tmp_path)
    save_spam_snapshot(12, data_dir=tmp_path, today="2026-05-02")

    report_path = generate_report(
        today_date="2026-05-02",
        data_dir=tmp_path,
        reports_dir=reports_dir,
        open_browser=False,
    )

    assert report_path.exists()
    assert (reports_dir / "latest.html").exists()
    content = report_path.read_text()
    assert "Gmail Smart Automation" in content
    assert "Chart.js" in content
    assert "23" in content  # total_processed
    assert "Zahnarzt" in content  # calendar event
