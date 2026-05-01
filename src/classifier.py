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
        labels_str = "\n".join([f"- {l}" for l in labels])

        prompt = f"""Du bist ein Email-Klassifikations-Expert. Analysiere diese Email und ordne sie einem Label zu.

LABELS ZUR AUSWAHL:
{labels_str}

EMAIL:
Subject: {subject}
Body: {body[:1000]}

ANTWORT (JSON):
{{
  "label": "...",
  "confidence": 0.0-1.0,
  "reason": "kurze Begründung"
}}

Wichtig:
- Wähle GENAU eines der Labels
- confidence: 0.0 = keine Sicherheit, 1.0 = absolut sicher
- Sei präzise und praktisch (kein Over-Engineering)"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        # Response parsen
        response_text = message.content[0].text
        try:
            result = json.loads(response_text)
            return {
                "label": result.get("label"),
                "confidence": result.get("confidence", 0.0),
                "reason": result.get("reason", ""),
            }
        except json.JSONDecodeError:
            # Fallback wenn JSON parsing fehlschlägt
            return {
                "label": labels[0],
                "confidence": 0.5,
                "reason": "Klassifikation unsicher (JSON Parse Error)",
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
