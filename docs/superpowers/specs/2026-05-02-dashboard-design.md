# Design: Gmail Automation Dashboard

**Datum:** 2026-05-02  
**Status:** Approved  
**Ziel:** Tägliches HTML-Dashboard mit Dark Mode — persönlicher Nutzen + Demo/Training

---

## Zusammenfassung

Nach jedem Daily-Run generiert das System automatisch ein visuell ansprechendes HTML-Dashboard. Es speichert täglich einen JSON-Snapshot aller Kennzahlen und baut daraus eine statische HTML-Seite mit Charts und Tabellen. Das Dashboard öffnet sich automatisch im Browser.

---

## Architektur

### Neue Dateien

```
reports/
  data/
    YYYY-MM-DD.json          # täglich nach jedem Run
    unsubscribe_latest.json  # wöchentlich von smart_unsubscribe.py
  YYYY-MM-DD.html            # generiertes Dashboard
  latest.html                # immer das neueste (wird überschrieben)

src/
  reporter.py                # neues Modul: JSON → HTML
```

### Ablauf (Daily Run)

`main.py` und `purge_spam.py` laufen getrennt (über `run_daily.sh`). Deshalb wird `reporter.py` am Ende von `run_daily.sh` aufgerufen, nachdem beide fertig sind.

```
run_daily.sh startet
  ↓
main.py läuft durch
  → Stats gesammelt (Labels, Priority, Calendar, API-Kosten, Laufzeit)
  → reports/data/YYYY-MM-DD.json gespeichert
  ↓
purge_spam.py läuft durch
  → reports/data/YYYY-MM-DD-spam.json gespeichert ({"deleted": 12})
  ↓
reporter.py aufgerufen (neu in run_daily.sh)
  → liest YYYY-MM-DD.json + YYYY-MM-DD-spam.json
  → liest letzte 30 Haupt-JSON-Dateien (für Trend-Chart)
  → reports/YYYY-MM-DD.html generiert
  → reports/latest.html überschrieben
  → open reports/latest.html  (macOS: Browser)
```

---

## JSON-Schema (pro Tag)

```json
{
  "date": "2026-05-02",
  "timestamp": "2026-05-02T08:03:45",
  "total_processed": 23,
  "label_counts": {
    "Newsletter": 8,
    "Invoice": 3,
    "General": 7,
    "Tax": 2,
    "Health": 3
  },
  "priority_emails": [
    { "from": "arzt@praxis.ch", "subject": "Ihr Termin am 15.05", "time": "08:01:23" }
  ],
  "calendar_events": [
    { "title": "Zahnarzt Termin", "date": "15.05.2026", "time": "10:00" }
  ],
  "spam_deleted": 12,
  "api_cost_chf": 0.0008,
  "runtime_seconds": 45.2,
  "errors": []
}
```

Unsubscribe-Daten (separates File, wöchentlich):

```json
{
  "date": "2026-04-28",
  "candidates": [
    { "sender": "newsletter@digitec.ch", "days_unread": 45, "unsubscribe_url": "..." }
  ]
}
```

---

## Dashboard-Layout (Dark Mode)

```
┌─────────────────────────────────────────────────────────────┐
│  Gmail Smart Automation — Report 02.05.2026  [Dark Mode]    │
│  23 Emails  •  45s Laufzeit  •  0.0008 CHF  •  ✅ OK       │
├──────────────┬──────────────────────────────────────────────┤
│  Pie Chart   │  Line Chart                                   │
│  Labels      │  Trend: Emails/Tag (30 Tage)                  │
│  (5 Farben)  │                                               │
├──────────────┴──────────────────────────────────────────────┤
│  ⭐ Priority-Emails heute (N)                               │
│  Absender               Betreff                             │
│  arzt@praxis.ch         Ihr Termin am 15.05                 │
├─────────────────────────────────────────────────────────────┤
│  📅 Kalender-Events (N)   │   🗑️ SPAM gelöscht: 12         │
├─────────────────────────────────────────────────────────────┤
│  📋 Unsubscribe-Kandidaten (nur montags aktuell)            │
│  Digitec Newsletter — 45 Tage ungelesen                     │
├─────────────────────────────────────────────────────────────┤
│  ⚙️ System-Gesundheit: API-Kosten CHF / Laufzeit / Fehler  │
└─────────────────────────────────────────────────────────────┘
```

### Farb-Schema (Dark Mode)

| Element | Farbe |
|---------|-------|
| Background | `#0f172a` (Navy) |
| Karten | `#1e293b` |
| Primär-Akzent | `#22c55e` (Grün) |
| Priority-Akzent | `#f59e0b` (Amber) |
| Text | `#e2e8f0` |
| Charts | Tailwind-Palette |

### Tech-Stack (keine neuen pip-Abhängigkeiten)

- **Tailwind CSS** via CDN — Styling
- **Chart.js** via CDN — Pie + Line Charts
- **Python `string.Template`** oder f-strings — HTML generieren (kein Jinja2)

---

## Änderungen an bestehenden Dateien

### `src/main.py`
- Stats-Dict aufbauen während des Runs
- Am Ende: `reporter.save_snapshot(stats)` aufrufen (nur JSON speichern, kein HTML-Aufruf hier)

### `src/purge_spam.py`
- Spam-Count in `reports/data/YYYY-MM-DD-spam.json` speichern: `{"deleted": N}`

### `run_daily.sh`
- Nach `purge_spam.py`: `python src/reporter.py` aufrufen
- Reporter generiert HTML aus beiden JSON-Files + öffnet Browser

### `src/classifier.py`
- API-Kosten berechnen und zurückgeben (Input + Output Tokens × Haiku-Tarif)

### `src/smart_unsubscribe.py`
- Am Ende: Kandidaten in `reports/data/unsubscribe_latest.json` schreiben

---

## Was NICHT geändert wird

- `gmail_client.py` — keine Änderungen
- `calendar_client.py` — keine Änderungen
- `purge_spam.py` — gibt nur Zahl zurück, wird von main.py gesammelt
- LaunchAgent `.plist`-Dateien — keine Änderungen
- `config/labels.yaml` — keine Änderungen

---

## Fehlerbehandlung

- Falls `reports/data/` nicht existiert: automatisch erstellen
- Falls weniger als 2 JSON-Dateien vorhanden: Trend-Chart zeigt Hinweis "Noch zu wenig Daten"
- Falls `unsubscribe_latest.json` fehlt: Abschnitt zeigt "Noch kein Wochenbericht vorhanden"
- Dashboard-Generierung darf den Daily-Run nicht blockieren: bei Fehler in `reporter.py` nur loggen, nicht crashen

---

## Aufwand-Schätzung

| Schritt | Aufwand |
|---------|---------|
| `reporter.py` schreiben | ~60 min |
| HTML-Template mit Dark Mode + Charts | ~45 min |
| `main.py` anpassen (Stats sammeln) | ~20 min |
| `smart_unsubscribe.py` anpassen | ~10 min |
| Tests schreiben | ~20 min |
| **Total** | **~2.5h** |

---

## Kosten

| Was | Betrag |
|-----|--------|
| Neue API-Calls | 0 (kein extra Claude-Aufruf) |
| Tailwind + Chart.js CDN | 0 |
| Speicher (JSON-Files) | ~1 KB/Tag = ~365 KB/Jahr |
