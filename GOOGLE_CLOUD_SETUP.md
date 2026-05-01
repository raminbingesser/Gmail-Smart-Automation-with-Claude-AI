# Google Cloud Setup für Gmail API

Diese Anleitung führt dich Schritt für Schritt durch die Einrichtung der Gmail API auf Google Cloud.

## Schritt 1: Google Cloud Project erstellen

1. Öffne https://console.cloud.google.com/ in deinem Browser
2. Oben links: **"Select a Project"** → **"New Project"**
3. Name: `EmailAutomationPrivat`
4. Organisation: `(No Organization)` ist okay
5. Klick **"Create"** und warte ~30 Sekunden

## Schritt 2: Gmail API aktivieren

1. **Search Bar** oben → Type `Gmail API`
2. Klick auf "Gmail API"
3. Button **"Enable"** (blau)
4. Warte bis die API aktiviert ist (grüner Haken)

## Schritt 3: OAuth 2.0 Credentials erstellen

1. Linkes Menü → **"Credentials"**
2. Button **"+ Create Credentials"** → **"OAuth client ID"**
3. Falls gefragt: **"Configure OAuth consent screen"** klicken

### OAuth Consent Screen ausfüllen:
- **User Type**: `External`
- **App name**: `EmailAutomationPrivat`
- **User support email**: deine Email (r.bingesser@gmail.com)
- **Developer contact**: deine Email
- Speichern, nächster Screen: **"Add or Remove Scopes"**

### Scopes hinzufügen:
- Search: `https://www.googleapis.com/auth/gmail.modify`
- Klick auf gefundenen Scope hinzufügen
- **"Update"** speichern
- Zurück → **"Create"**

### OAuth Client ID erstellen:
1. **Application type**: `Desktop application`
2. **Name**: `Gmail Automation`
3. **"Create"**

→ **Download JSON** (rot Button "Download" oder JSON-Icon)

## Schritt 4: Credentials.json ins Projekt kopieren

1. Download des JSON sollte automatisch starten → `OAuth 2.0 Client IDs.json`
2. **Umbenennen** zu `credentials.json`
3. Speichern im Ordner: `~/projects/EmailAutomationPrivat/credentials/`

**Verify:**
```bash
ls -la ~/projects/EmailAutomationPrivat/credentials/
# Sollte anzeigen:
# credentials.json
# .gitkeep
```

## Schritt 5: .env Setup

1. Öffne Terminal
2. ```bash
   cd ~/projects/EmailAutomationPrivat
   cp .env.example .env
   ```
3. Öffne `.env` in deinem Editor
4. Füll `ANTHROPIC_API_KEY` aus (von https://console.anthropic.com/keys)
5. `GOOGLE_CREDENTIALS_PATH` und `GOOGLE_TOKEN_PATH` sind schon korrekt

## Schritt 6: Test

1. Terminal → `cd ~/projects/EmailAutomationPrivat`
2. ```bash
   source .venv/bin/activate
   python src/main.py
   ```
3. Falls gefragt: **Öffnet Browser** → Erlaubnis erteilen ("r.bingesser@gmail.com darf auf deine Gmail zugreifen")
4. Browser schließt automatisch, Script läuft weiter

### Erwartete Ausgabe:

```
🔐 OAuth Authentifizierung...
✅ Verbunden mit Gmail

📧 Lese 5 ungelesene Emails...
🤖 Klassifiziere mit Claude (claude-3-5-haiku-20241022)...

📧 Weekly Newsletter #42
   → Label: 'Newsletter' (95%)
   → Grund: Enthält Unsubscribe-Link und typische Newsletter-Struktur
   ✅ Gelabelt + als gelesen markiert
```

---

## Troubleshooting

### "FileNotFoundError: credentials.json"
- Prüf: `ls ~/projects/EmailAutomationPrivat/credentials/credentials.json`
- Falls nicht: Siehe Schritt 4 oben nochmal

### "ModuleNotFoundError: No module named 'google'"
- venv nicht aktiviert?
- `source .venv/bin/activate` und erneut versuchen

### "OAuth Token wird verlangt, aber Browser öffnet sich nicht"
- Manchmal geht localhost nicht direkt
- Kopier Link aus Terminal in Browser manuell

### "Gmail API not enabled"
- Zurück zu Google Cloud Console
- Verify dass Gmail API "Enabled" ist (grüner Haken)

---

## Sicherheit

⚠️ **`credentials.json` NUR lokal** — niemals committen!
- `.gitignore` schützt dich (aber double-check!)
- Wenn du mal `.gitignore` änderst: sei vorsichtig!

💡 **Token rotieren:**
Wenn du Angst hast, dass credentials kompromittiert sind:
1. `rm ~/projects/EmailAutomationPrivat/credentials/token.json`
2. Skript neu starten (neue OAuth)
3. Oder Google Cloud Console: Credentials → Client ID löschen + neue erstellen

---

Du bist fertig! Zurück zu `main` oder `README.md` für nächste Schritte.
