import os
import secrets
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from db import get_supabase_client
from extraction import extract_follows
from fetch_f1 import fetch_f1_races
from fetch_football import fetch_football_matches
from teams_data import TEAMS_BY_SPORT

app = FastAPI()
logger = logging.getLogger(__name__)

OAUTH_STATE_BY_USER: dict[str, str] = {}
STATE_TO_USER: dict[str, str] = {}


class FollowCreate(BaseModel):
    user_id: str
    sport: str
    team_or_player: str


class FollowExtractionRequest(BaseModel):
    text: str
    api_key: str


class GeminiKeyRequest(BaseModel):
    api_key: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/users/{user_id}")
def get_user(user_id: str):
    supabase = get_supabase_client()
    response = supabase.table("users").select("*").eq("id", user_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="User not found")

    return response.data[0]


@app.post("/users/{user_id}/gemini-key")
def save_gemini_key(user_id: str, payload: GeminiKeyRequest):
    if not payload.api_key or not payload.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key cannot be empty")

    supabase = get_supabase_client()
    user_check = supabase.table("users").select("id").eq("id", user_id).execute()
    if not user_check.data:
        raise HTTPException(status_code=404, detail="User not found")

    supabase.table("user_secrets").upsert(
        {
            "user_id": user_id,
            "encrypted_gemini_key": encrypt_value(payload.api_key.strip()),
        },
        on_conflict="user_id",
    ).execute()

    return {"status": "saved"}


@app.post("/follows", status_code=201)
def create_follow(payload: FollowCreate):
    sport = payload.sport.strip()
    team_or_player = payload.team_or_player.strip()

    if not sport or not team_or_player:
        raise HTTPException(status_code=400, detail="sport and team_or_player cannot be empty")

    sport_key = sport.lower()
    valid_sports = ["football", "cricket", "f1"]
    if sport_key not in valid_sports:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sport. Valid options: {', '.join(valid_sports)}",
        )

    valid_teams = TEAMS_BY_SPORT.get(sport_key, [])
    if team_or_player not in valid_teams:
        raise HTTPException(
            status_code=400,
            detail=f"{team_or_player} is not a valid team/player for sport '{sport_key}'",
        )

    supabase = get_supabase_client()

    user_check = supabase.table("users").select("id").eq("id", payload.user_id).execute()
    if not user_check.data:
        raise HTTPException(status_code=404, detail="User not found")

    insert_response = (
        supabase.table("follows")
        .insert({
            "user_id": payload.user_id,
            "sport": sport_key,
            "team_or_player": team_or_player,
        })
        .execute()
    )

    if not insert_response.data:
        raise HTTPException(status_code=400, detail="Failed to create follow")

    return insert_response.data[0]


@app.get("/follows/{user_id}")
def get_follows(user_id: str):
    supabase = get_supabase_client()

    user_check = supabase.table("users").select("id").eq("id", user_id).execute()
    if not user_check.data:
        raise HTTPException(status_code=404, detail="User not found")

    response = supabase.table("follows").select("*").eq("user_id", user_id).execute()
    return response.data or []


@app.get("/matches/{user_id}")
def get_matches(user_id: str):
    supabase = get_supabase_client()

    user_check = supabase.table("users").select("id").eq("id", user_id).execute()
    if not user_check.data:
        raise HTTPException(status_code=404, detail="User not found")

    follows = supabase.table("follows").select("*").eq("user_id", user_id).execute().data or []
    matches = []

    for follow in follows:
        sport = follow.get("sport")
        followed_team = follow.get("team_or_player")

        try:
            if sport == "football":
                fetched_matches = fetch_football_matches(followed_team)
            elif sport == "f1":
                fetched_matches = fetch_f1_races(followed_team)
            else:
                logger.warning("Skipping unsupported sport %s for user %s", sport, user_id)
                continue
        except Exception:
            logger.exception("Failed to fetch matches for %s: %s", sport, followed_team)
            continue

        matches.extend(
            {
                **match,
                "sport": sport,
                "followed_team": followed_team,
            }
            for match in fetched_matches
        )

    return {"user_id": user_id, "matches": matches}


@app.post("/sync-calendar/{user_id}")
def sync_calendar(user_id: str):
    matches_response = get_matches(user_id)
    supabase = get_supabase_client()

    token_response = (
        supabase.table("oauth_tokens")
        .select("*")
        .eq("user_id", user_id)
        .eq("provider", "google")
        .execute()
    )
    if not token_response.data:
        raise HTTPException(
            status_code=400,
            detail="Connect Google Calendar before syncing matches",
        )

    token_row = token_response.data[0]
    try:
        access_token = get_fernet().decrypt(
            token_row["encrypted_access_token"].encode("utf-8")
        ).decode("utf-8")
        refresh_token = get_fernet().decrypt(
            token_row["encrypted_refresh_token"].encode("utf-8")
        ).decode("utf-8")
        expires_at = datetime.fromisoformat(
            token_row["expires_at"].replace("Z", "+00:00")
        )
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=500, detail="Stored Google tokens are invalid") from error

    now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.utcnow()
    if expires_at <= now:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Google OAuth environment variables are not configured")

        refreshed_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        if refreshed_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to refresh Google access token")

        refreshed_data = refreshed_response.json()
        access_token = refreshed_data.get("access_token")
        expires_in = refreshed_data.get("expires_in")
        if not access_token or not expires_in:
            raise HTTPException(status_code=502, detail="Google refresh response was missing token data")

        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
        updated_tokens = (
            supabase.table("oauth_tokens")
            .update(
                {
                    "encrypted_access_token": encrypt_value(access_token),
                    "expires_at": expires_at.isoformat(),
                }
            )
            .eq("user_id", user_id)
            .eq("provider", "google")
            .execute()
        )
        if not updated_tokens.data:
            raise HTTPException(status_code=500, detail="Failed to store refreshed Google token")

    events_created = 0
    already_synced = 0
    for match in matches_response["matches"]:
        if match["sport"] == "f1":
            summary = match["race_name"]
            match_signature = f"f1:{match['race_name']}:{match['date']}"
        else:
            summary = f"{match['followed_team']} vs {match['opponent']}"
            match_signature = (
                f"{match['sport']}:{match['followed_team']}:{match['opponent']}:{match['date']}"
            )

        synced_response = (
            supabase.table("synced_events")
            .select("google_event_id")
            .eq("user_id", user_id)
            .eq("match_signature", match_signature)
            .execute()
        )
        if synced_response.data:
            already_synced += 1
            continue

        start = datetime.fromisoformat(match["date"].replace("Z", "+00:00"))
        end = start + timedelta(hours=1)
        event_response = requests.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "summary": summary,
                "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            },
            timeout=30,
        )
        if event_response.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail="Failed to create Google Calendar event")

        google_event_id = event_response.json().get("id")
        if not google_event_id:
            raise HTTPException(status_code=502, detail="Google Calendar response was missing event ID")

        synced_insert = (
            supabase.table("synced_events")
            .insert(
                {
                    "user_id": user_id,
                    "match_signature": match_signature,
                    "google_event_id": google_event_id,
                }
            )
            .execute()
        )
        if not synced_insert.data:
            raise HTTPException(status_code=500, detail="Failed to record synced calendar event")

        events_created += 1

    return {
        "user_id": user_id,
        "events_created": events_created,
        "already_synced": already_synced,
    }


@app.post("/extract-follows")
def extract_follows_route(payload: FollowExtractionRequest):
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")
    if not payload.api_key or not payload.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key cannot be empty")

    try:
        result = extract_follows(payload.text, payload.api_key)
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=502, detail="Gemini extraction failed") from None

    return result


@app.get("/teams")
def get_teams(sport: str = Query(...)):
    valid_sports = ["football", "f1"]
    if sport not in valid_sports:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sport. Valid options: {', '.join(valid_sports)}",
        )

    return {"sport": sport, "teams": TEAMS_BY_SPORT[sport]}


def get_fernet() -> Fernet:
    key = os.getenv("FERNET_KEY")
    if not key:
        raise RuntimeError("FERNET_KEY is not configured")
    return Fernet(key.encode("utf-8"))


def encrypt_value(value: str) -> str:
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


@app.get("/auth/google/start")
def google_oauth_start(user_id: str):
    supabase = get_supabase_client()
    user_check = supabase.table("users").select("id").eq("id", user_id).execute()
    if not user_check.data:
        raise HTTPException(status_code=404, detail="User not found")

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    if not client_id or not redirect_uri:
        raise HTTPException(status_code=500, detail="Google OAuth environment variables are not configured")

    state = secrets.token_urlsafe(32)
    OAUTH_STATE_BY_USER[user_id] = state
    STATE_TO_USER[state] = user_id

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email https://www.googleapis.com/auth/calendar.events",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url=google_auth_url)


@app.get("/auth/google/callback")
def google_oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is required")
    if not state:
        raise HTTPException(status_code=400, detail="State is required")

    user_id = STATE_TO_USER.get(state)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    supabase = get_supabase_client()
    user_check = supabase.table("users").select("id").eq("id", user_id).execute()
    if not user_check.data:
        raise HTTPException(status_code=404, detail="User not found")

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=500, detail="Google OAuth environment variables are not configured")

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )

    if token_response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to exchange Google OAuth code")

    token_data = token_response.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    if not access_token or not refresh_token or not expires_in:
        raise HTTPException(status_code=502, detail="Google OAuth response was missing tokens")

    expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
    encrypted_access = encrypt_value(access_token)
    encrypted_refresh = encrypt_value(refresh_token)

    insert_response = (
        supabase.table("oauth_tokens")
        .upsert(
            {
                "user_id": user_id,
                "provider": "google",
                "encrypted_refresh_token": encrypted_refresh,
                "encrypted_access_token": encrypted_access,
                "expires_at": expires_at.isoformat(),
            },
            on_conflict="user_id,provider",
        )
        .execute()
    )

    OAUTH_STATE_BY_USER.pop(user_id, None)
    STATE_TO_USER.pop(state, None)

    if not insert_response.data:
        raise HTTPException(status_code=500, detail="Failed to store Google OAuth tokens")

    return {"status": "ok", "user_id": user_id}


