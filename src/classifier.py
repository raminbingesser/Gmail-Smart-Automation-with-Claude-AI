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
        """Klassifiziere Email mit Claude."""
        labels_str = ", ".join(labels)

        prompt = f"""Klassifiziere diese Email streng nach Labels. Antworte EXAKT mit diesem JSON Format:
{{"label":"LABELNAME","confidence":0.95,"reason":"Kurze Begründung"}}

Labels: {labels_str}

Subject: {subject}
Body: {body[:300]}

Regeln:
- Wähle GENAU ein Label
- confidence: 0.0-1.0 (als Dezimalzahl)
- reason: 1 Satz max
- Antwort: NUR das JSON Objekt, keine Worte davor oder danach!
- Kein Markdown, kein ```json```, nur pures JSON!

Beispiel Output:
{{"label":"Invoice","confidence":0.92,"reason":"Enthält Rechnung und Betrag"}}"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text.strip()

        # Versuche JSON zu parsen (mit cleanup)
        try:
            # Entferne Markdown-Code-Blöcke falls vorhanden
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            result = json.loads(response_text)
            label = result.get("label", labels[0])

            # Validate dass label in der liste ist
            if label not in labels:
                label = labels[0]

            return {
                "label": label,
                "confidence": float(result.get("confidence", 0.5)),
                "reason": result.get("reason", ""),
            }
        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            print(f"   DEBUG: JSON Parse Error: {e}, Response: {response_text[:100]}")
            return {
                "label": labels[0],
                "confidence": 0.5,
                "reason": "Claude returned invalid JSON",
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
