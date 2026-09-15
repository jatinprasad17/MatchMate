import json
import logging
import os
from datetime import datetime, timedelta

import requests

from cache import get_cache, set_cache
from teams_data import FOOTBALL_TEAM_IDS

logger = logging.getLogger(__name__)


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


def fetch_football_matches(team: str) -> list[dict]:
    team_id = FOOTBALL_TEAM_IDS.get(team)
    if team_id is None:
        logger.warning("No football-data.org team ID is mapped for %s", team)
        return []

    iso_week = datetime.now().isocalendar().week
    cache_key = f"matches:football:{team}:{iso_week}"
    cached_matches = get_cache(cache_key)
    if cached_matches:
        return json.loads(cached_matches)

    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        logger.error("FOOTBALL_DATA_API_KEY is not configured")
        return []

    response = requests.get(
        f"https://api.football-data.org/v4/teams/{team_id}/matches",
        headers={"X-Auth-Token": api_key},
        params={
            "status": "SCHEDULED",
            "dateFrom": datetime.now().strftime("%Y-%m-%d"),
            "dateTo": (
                datetime.now()
                + timedelta(days=(7 - datetime.now().weekday()) % 7 or 7)
            ).strftime("%Y-%m-%d"),
        },
        timeout=30,
    )
    response.raise_for_status()

    matches = []
    for match in response.json().get("matches", []):
        home_team = match.get("homeTeam", {})
        away_team = match.get("awayTeam", {})
        is_home = home_team.get("id") == team_id
        opponent = away_team.get("name") if is_home else home_team.get("name")
        matches.append(
            {
                "opponent": opponent,
                "date": match.get("utcDate"),
                "competition": match.get("competition", {}).get("name"),
                "home_or_away": "home" if is_home else "away",
            }
        )

    set_cache(cache_key, json.dumps(matches), _seconds_until_next_monday())
    return matches


def fetch_football_results(team: str) -> list[dict]:
    team_id = FOOTBALL_TEAM_IDS.get(team)
    if team_id is None:
        logger.warning("No football-data.org team ID is mapped for %s", team)
        return []

    date_from, date_to = _last_week_date_range()
    last_iso_week = datetime.strptime(date_from, "%Y-%m-%d").date().isocalendar().week
    cache_key = f"results:football:{team}:{last_iso_week}"
    cached_results = get_cache(cache_key)
    if cached_results:
        return json.loads(cached_results)

    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        logger.error("FOOTBALL_DATA_API_KEY is not configured")
        return []

    response = requests.get(
        f"https://api.football-data.org/v4/teams/{team_id}/matches",
        headers={"X-Auth-Token": api_key},
        params={
            "status": "FINISHED",
            "dateFrom": date_from,
            "dateTo": date_to,
        },
        timeout=30,
    )
    response.raise_for_status()

    results = []
    for match in response.json().get("matches", []):
        home_team = match.get("homeTeam", {})
        away_team = match.get("awayTeam", {})
        is_home = home_team.get("id") == team_id
        results.append(
            {
                "opponent": away_team.get("name") if is_home else home_team.get("name"),
                "date": match.get("utcDate"),
                "competition": match.get("competition", {}).get("name"),
                "home_or_away": "home" if is_home else "away",
                "score": match.get("score", {}).get("fullTime", {}),
            }
        )

    set_cache(cache_key, json.dumps(results), 3 * 24 * 60 * 60)
    return results
