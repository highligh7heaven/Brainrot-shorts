"""Decides whether a scheduled run should make a video.

GitHub only runs schedules in UTC and can start them late, so the workflow
checks every hour and this file decides: make a video if one of your daily
times (POST_TIMES, in TIMEZONE) passed in the last 3 hours and hasn't had
its video yet. That also retries a failed run on the next hourly check.

    python -m brainrot.schedule    # prints run=true/false and slot=... for GitHub
"""

import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import memory

DEFAULT_TIMES = "8am, 1pm, 7pm"
DEFAULT_ZONE = "America/Vancouver"
CATCH_UP = timedelta(hours=3)


def parse_times(text):
    """'8am, 1:30pm, 19:00' -> [(8, 0), (13, 30), (19, 0)]"""
    out = []
    for part in re.split(r"[,;]+", text or ""):
        m = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*", part.lower())
        if not m:
            continue
        hour, minute, half = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if half == "pm" and hour != 12:
            hour += 12
        if half == "am" and hour == 12:
            hour = 0
        if 0 <= hour < 24 and 0 <= minute < 60:
            out.append((hour, minute))
    return sorted(set(out))


def due_slot(times, done, now, zone):
    """The slot name (like '2026-10-24 13:00') that needs a video now, or None."""
    local = now.astimezone(zone)
    for day in (local.date(), local.date() - timedelta(days=1)):
        for hour, minute in reversed(times):
            at = datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone)
            name = f"{day.isoformat()} {hour:02d}:{minute:02d}"
            if at <= local and local - at <= CATCH_UP and name not in done:
                return name
    return None


def main():
    times = parse_times(os.environ.get("POST_TIMES") or DEFAULT_TIMES) or parse_times(DEFAULT_TIMES)
    zone = ZoneInfo(os.environ.get("TIMEZONE") or DEFAULT_ZONE)
    slot = due_slot(times, set(memory.load().get("done_slots", [])), datetime.now(timezone.utc), zone)
    lines = [f"run={'true' if slot else 'false'}", f"slot={slot or ''}"]
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"Daily times: {', '.join(f'{h:02d}:{m:02d}' for h, m in times)} ({zone.key})")


if __name__ == "__main__":
    main()
