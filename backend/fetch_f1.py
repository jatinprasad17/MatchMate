import json
from datetime import date, datetime, timedelta

import requests

from cache import get_cache, set_cache


def _seconds_until_next_monday() -> int:
    now = datetime.now()
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = (now + timedelta(days=days_until_monday)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return max(1, int((next_monday - now).total_seconds()))


def fetch_f1_races(team: str) -> list[dict]:
    # F1 teams all race at the same events, so team is unused by design.
    iso_week = datetime.now().isocalendar().week
    cache_key = f"matches:f1:{iso_week}"
    cached_matches = get_cache(cache_key)
    if cached_matches:
        return json.loads(cached_matches)

    now = datetime.now()
    today = now.date()
    next_monday = (now + timedelta(days=(7 - now.weekday()) % 7 or 7)).date()

    response = requests.get(
        "https://api.openf1.org/v1/meetings",
        params={"year": now.year},
        timeout=30,
    )
    response.raise_for_status()

    races = []
    for meeting in response.json():
        date_start = meeting.get("date_start")
        if not date_start:
            continue

        meeting_date = date.fromisoformat(date_start[:10])
        if not today <= meeting_date < next_monday:
            continue

        races.append(
            {
                "race_name": meeting.get("meeting_name"),
                "country": meeting.get("country_name"),
                "circuit": meeting.get("circuit_short_name"),
                "date": date_start,
            }
        )

    set_cache(cache_key, json.dumps(races), _seconds_until_next_monday())
    return races
