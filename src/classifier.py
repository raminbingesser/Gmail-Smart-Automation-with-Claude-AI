"""Email Classifier: Claude AI für intelligente Klassifikation."""

import json
import os
from typing import Optional, Union
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

    def extract_appointment(self, subject: str, body: str) -> Optional[dict]:
        """Extrahiert Termin-Daten aus Email.

        Returns:
            {titel, datum, uhrzeit, dauer_min, ort} oder None
        """
        prompt = f"""Extrahiere den Termin aus dieser Email. Antworte mit JSON oder "NULL" falls kein Termin.

Subject: {subject}
Body: {body[:500]}

Format (Swiss German Locale - DD.MM.YYYY):
{{"titel":"Zahnarzttermin","datum":"15.05.2026","uhrzeit":"14:30","dauer_min":30,"ort":"Zahnarzt Dr. Schmidt"}}

Nur pures JSON, kein Markdown, kein ```json```.
Falls KEIN Termin erkennbar: antworte mit: NULL"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text.strip()

        if response_text == "NULL" or "null" in response_text.lower():
            return None

        try:
            result = json.loads(response_text)
            return {
                "titel": result.get("titel", ""),
                "datum": result.get("datum", ""),
                "uhrzeit": result.get("uhrzeit", ""),
                "dauer_min": int(result.get("dauer_min", 60)),
                "ort": result.get("ort", ""),
            }
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def needs_reply(self, subject: str, body: str) -> bool:
        """Entscheidet, ob Email eine Antwort braucht."""
        prompt = f"""Braucht diese Email eine Antwort oder Handlung? Antworte nur mit "JA" oder "NEIN".

Subject: {subject}
Body: {body[:300]}

Beispiele für JA:
- "Kannst du mir bitte helfen?"
- "Wann hast du Zeit?"
- "Action required: ..."
- "Bitte antworte bis Freitag"

Beispiele für NEIN:
- Newsletter / Marketing
- Rechnungen / Bestätigungen
- Automatische Benachrichtigungen
- Informative Mails ohne Frage"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )

        response = message.content[0].text.strip().upper()
        return "JA" in response

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
                    "body": email["body"],
                    "classification": classification,
                }
            )
        return results
