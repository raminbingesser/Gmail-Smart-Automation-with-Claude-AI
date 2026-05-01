"""Email Classifier: Claude AI für intelligente Klassifikation."""

import json
import os
from typing import Optional
from anthropic import Anthropic


class EmailClassifier:
    """Klassifiziere Emails mit Claude API."""

    def __init__(self, model: str = "claude-3-5-haiku-20241022"):
        self.model = model
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def classify_email(
        self, subject: str, body: str, labels: list[str]
    ) -> dict:
        """
        Klassifiziere Email mit Claude.

        Returns:
            {
                "label": "Newsletter",
                "confidence": 0.92,
                "reason": "Enthält 'unsubscribe' und typische Newsletter-Struktur"
            }
        """
        labels_str = "\n".join([f"{i+1}. {l}" for i, l in enumerate(labels)])

        prompt = f"""Klassifiziere diese Email. ANTWORTE NUR mit JSON, keine anderen Worte.

Labels ({len(labels)}):
{labels_str}

Email Subject: {subject}
Email Body: {body[:500]}

Antworte exakt mit:
{{"label": "LABEL_NAME", "confidence": NUMBER, "reason": "TEXT"}}

Regeln:
- label: exakt ein Label von oben
- confidence: 0.0 bis 1.0
- reason: 1-2 Sätze
- NUR JSON, keine weiteren Worte!"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text.strip()
        try:
            result = json.loads(response_text)
            return {
                "label": result.get("label", labels[0]),
                "confidence": float(result.get("confidence", 0.5)),
                "reason": result.get("reason", ""),
            }
        except (json.JSONDecodeError, ValueError, KeyError):
            return {
                "label": labels[0],
                "confidence": 0.5,
                "reason": "Automatisch klassifiziert",
            }

    def batch_classify(
        self, emails: list[dict], labels: list[str]
    ) -> list[dict]:
        """Klassifiziere mehrere Emails."""
        results = []
        for email in emails:
            classification = self.classify_email(
                email["subject"], email["body"], labels
            )
            results.append(
                {
                    "email_id": email["id"],
                    "subject": email["subject"],
                    "classification": classification,
                }
            )
        return results
