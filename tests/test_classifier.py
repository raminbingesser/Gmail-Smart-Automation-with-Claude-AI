"""Tests für Classifier."""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Damit imports funktionieren
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.classifier import EmailClassifier


@pytest.fixture
def classifier():
    """Teste Classifier ohne echte API-Aufrufe."""
    with patch("src.classifier.Anthropic"):
        return EmailClassifier()


def test_classify_email_newsletter(classifier):
    """Test: Newsletter werden erkannt."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text='{"label": "Newsletter", "confidence": 0.95, "reason": "Enthält Unsubscribe-Link"}'
        )
    ]
    mock_response.usage.input_tokens = 50
    mock_response.usage.output_tokens = 20
    classifier.client.messages.create.return_value = mock_response

    result = classifier.classify_email(
        subject="Weekly Newsletter #42",
        body="Hi there, here's our weekly digest...",
        labels=["Wichtig", "Newsletter", "Rechnung"],
    )

    assert result["label"] == "Newsletter"
    assert result["confidence"] == 0.95
    assert "Unsubscribe" in result["reason"]


def test_classify_email_invoice(classifier):
    """Test: Rechnungen werden erkannt."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text='{"label": "Rechnung", "confidence": 0.99, "reason": "Enthält Rechnungsnummer und Betrag"}'
        )
    ]
    mock_response.usage.input_tokens = 50
    mock_response.usage.output_tokens = 20
    classifier.client.messages.create.return_value = mock_response

    result = classifier.classify_email(
        subject="Invoice #2024-001",
        body="Amount Due: CHF 150.00",
        labels=["Wichtig", "Newsletter", "Rechnung"],
    )

    assert result["label"] == "Rechnung"
    assert result["confidence"] == 0.99


def test_classify_email_malformed_json(classifier):
    """Test: Fehlerbehandlung bei JSON-Parse Error."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Das ist kein JSON")]
    mock_response.usage.input_tokens = 50
    mock_response.usage.output_tokens = 20
    classifier.client.messages.create.return_value = mock_response

    result = classifier.classify_email(
        subject="Broken Response",
        body="Test",
        labels=["Label1", "Label2", "Label3"],
    )

    # Fallback: erstes Label
    assert result["label"] == "Label1"
    assert result["confidence"] == 0.5
    assert result["reason"] == "Claude returned invalid JSON"


def test_batch_classify():
    """Test: Mehrere Emails gleichzeitig."""
    emails = [
        {"id": "1", "subject": "Test 1", "body": "Body 1"},
        {"id": "2", "subject": "Test 2", "body": "Body 2"},
    ]

    with patch("src.classifier.Anthropic"):
        classifier = EmailClassifier()
        # Mock classify_email
        with patch.object(
            classifier,
            "classify_email",
            return_value={"label": "Test", "confidence": 0.8, "reason": "Mock"},
        ):
            results = classifier.batch_classify(emails, ["Test"])

    assert len(results) == 2
    assert results[0]["email_id"] == "1"
    assert results[1]["email_id"] == "2"


def test_total_cost_chf_accumulates(classifier):
    """Token-Tracking akkumuliert korrekt über mehrere Calls."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"label":"Newsletter","confidence":0.9,"reason":"Test"}')]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 40
    classifier.client.messages.create.return_value = mock_response

    classifier.classify_email("Test", "Body", ["Newsletter"])
    classifier.classify_email("Test2", "Body2", ["Newsletter"])

    assert classifier._total_input_tokens == 200
    assert classifier._total_output_tokens == 80
    cost = classifier.total_cost_chf()
    assert cost > 0
    expected = round(200 * 0.80 * 0.90 / 1_000_000 + 80 * 4.00 * 0.90 / 1_000_000, 10)
    assert round(cost, 10) == expected
