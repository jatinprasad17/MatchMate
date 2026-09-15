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


def _last_week_date_range() -> tuple[str, str]:
    today = datetime.now().date()
    current_monday = today - timedelta(days=today.weekday())
    last_monday = current_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday.isoformat(), last_sunday.isoformat()


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


def fetch_f1_results(team: str) -> list[dict]:
    date_from, date_to = _last_week_date_range()
    last_iso_week = datetime.strptime(date_from, "%Y-%m-%d").date().isocalendar().week
    cache_key = f"results:f1:{team}:{last_iso_week}"
    cached_results = get_cache(cache_key)
    if cached_results:
        return json.loads(cached_results)

    now = datetime.now()
    meetings_response = requests.get(
        "https://api.openf1.org/v1/meetings",
        params={"year": now.year},
        timeout=30,
    )
    meetings_response.raise_for_status()

    meeting = next(
        (
            item
            for item in meetings_response.json()
            if date_from <= item.get("date_start", "")[:10] <= date_to
        ),
        None,
    )
    if not meeting:
        set_cache(cache_key, json.dumps([]), 3 * 24 * 60 * 60)
        return []

    sessions_response = requests.get(
        "https://api.openf1.org/v1/sessions",
        params={"meeting_key": meeting["meeting_key"], "session_type": "Race"},
        timeout=30,
    )
    sessions_response.raise_for_status()
    sessions = sessions_response.json()
    if not sessions:
        set_cache(cache_key, json.dumps([]), 3 * 24 * 60 * 60)
        return []

    session_key = sessions[0]["session_key"]
    drivers_response = requests.get(
        "https://api.openf1.org/v1/drivers",
        params={"session_key": session_key, "team_name": team},
        timeout=30,
    )
    drivers_response.raise_for_status()
    drivers = {
        driver["driver_number"]: driver["full_name"]
        for driver in drivers_response.json()
    }

    results_response = requests.get(
        "https://api.openf1.org/v1/session_result",
        params={"session_key": session_key},
        timeout=30,
    )
    results_response.raise_for_status()

    results = [
        {
            "driver_name": drivers[result["driver_number"]],
            "position": result.get("position"),
            "race_name": meeting.get("meeting_name"),
            "date": meeting.get("date_start"),
        }
        for result in results_response.json()
        if result.get("driver_number") in drivers
    ]

    set_cache(cache_key, json.dumps(results), 3 * 24 * 60 * 60)
    return results
