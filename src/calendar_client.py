"""Apple Calendar Integration — erstellt Events via osascript."""

import subprocess
from typing import Optional


def create_event(
    title: str,
    date_str: str,
    time_str: str,
    duration_min: int = 60,
    location: str = "",
    calendar: str = "Privat"
) -> bool:
    """Erstellt Apple Calendar Event via osascript.

    Args:
        title: Event-Titel
        date_str: Datum im Format "DD.MM.YYYY"
        time_str: Uhrzeit im Format "HH:MM"
        duration_min: Dauer in Minuten (default 60)
        location: Ort (optional)
        calendar: Kalender-Name (default "Privat")

    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        # Berechne End-Time basierend auf Duration
        start_hour, start_min = map(int, time_str.split(":"))
        total_min = start_hour * 60 + start_min + duration_min
        end_hour = total_min // 60
        end_min = total_min % 60
        end_time_str = f"{end_hour:02d}:{end_min:02d}"

        # AppleScript — Swiss German Locale (DD.MM.YYYY HH:MM:SS)
        start_datetime = f"{date_str} {time_str}:00"
        end_datetime = f"{date_str} {end_time_str}:00"

        script = f"""
        tell application "Calendar"
            tell calendar "{calendar}"
                make new event with properties {{
                    summary:"{title}",
                    start date:(date "{start_datetime}"),
                    end date:(date "{end_datetime}"),
                    location:"{location}"
                }}
            end tell
        end tell
        """

        subprocess.run(["osascript", "-e", script], check=True)
        return True

    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Calendar Event Creation Error: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️  Unexpected error: {e}")
        return False
