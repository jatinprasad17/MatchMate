import base64
import html
import json
import logging
import operator
import os
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Annotated, TypedDict

import google.generativeai as genai
import requests
from cryptography.fernet import Fernet
from langgraph.graph import END, START, StateGraph

from db import get_supabase_client
from fetch_f1 import fetch_f1_races, fetch_f1_results
from fetch_football import fetch_football_matches, fetch_football_results

logger = logging.getLogger(__name__)


class DigestState(TypedDict):
    user_id: str
    matches: Annotated[list[dict], operator.add]
    results: Annotated[list[dict], operator.add]
    digest_text: str


def _get_user_follows(user_id: str) -> list[dict]:
    supabase = get_supabase_client()
    return supabase.table("follows").select("*").eq("user_id", user_id).execute().data or []


def fetch_football_node(state: DigestState) -> dict:
    print(f"football node running at {time.perf_counter():.6f}")
    matches = []
    follows = _get_user_follows(state["user_id"])

    for follow in follows:
        if follow.get("sport") == "football":
            matches.extend(fetch_football_matches(follow["team_or_player"]))

    return {"matches": matches}


def fetch_f1_node(state: DigestState) -> dict:
    print(f"f1 node running at {time.perf_counter():.6f}")
    matches = []
    follows = _get_user_follows(state["user_id"])

    for follow in follows:
        if follow.get("sport") == "f1":
            matches.extend(fetch_f1_races(follow["team_or_player"]))

    return {"matches": matches}


def fetch_football_results_node(state: DigestState) -> dict:
    print(f"football results node running at {time.perf_counter():.6f}")
    results = []
    follows = _get_user_follows(state["user_id"])

    for follow in follows:
        if follow.get("sport") == "football":
            followed_team = follow["team_or_player"]
            results.extend(
                {
                    **result,
                    "sport": "football",
                    "followed_team": followed_team,
                }
                for result in fetch_football_results(followed_team)
            )

    return {"results": results}


def fetch_f1_results_node(state: DigestState) -> dict:
    print(f"f1 results node running at {time.perf_counter():.6f}")
    results = []
    follows = _get_user_follows(state["user_id"])

    for follow in follows:
        if follow.get("sport") == "f1":
            followed_team = follow["team_or_player"]
            results.extend(
                {
                    **result,
                    "sport": "f1",
                    "followed_team": followed_team,
                }
                for result in fetch_f1_results(followed_team)
            )

    return {"results": results}


def combine_node(state: DigestState) -> dict:
    return {}


def write_digest_node(state: DigestState) -> dict:
    supabase = get_supabase_client()
    secret_response = (
        supabase.table("user_secrets")
        .select("encrypted_gemini_key")
        .eq("user_id", state["user_id"])
        .execute()
    )
    if not secret_response.data:
        return {"digest_text": "No Gemini key configured — digest not generated."}

    if not state["results"]:
        return {"digest_text": "No matches last week."}

    fernet_key = os.getenv("FERNET_KEY")
    if not fernet_key:
        raise RuntimeError("FERNET_KEY is not configured")

    encrypted_key = secret_response.data[0]["encrypted_gemini_key"]
    api_key = Fernet(fernet_key.encode("utf-8")).decrypt(
        encrypted_key.encode("utf-8")
    ).decode("utf-8")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.6-flash")
    prompt = (
        "Write a natural, readable recap of last week's sports results from this JSON list. "
        "Write 1-2 sentences per match or race, not a labeled field-by-field list. "
        "Convert football home_or_away and score into a natural result statement; "
        "for example, write \"Manchester City lost 2-0 away to FC Porto\" instead "
        "of listing Home/Away and Score separately. "
        "Group the recap by sport with a short heading, but use no other structural labels. "
        "Use a casual tone, like a friend giving a quick recap, not a database printout. "
        "If a sport has zero results, skip that section entirely and do not mention its absence. "
        "Do not invent details and return plain text only.\n\n"
        f"Results:\n{json.dumps(state['results'])}"
    )
    response = model.generate_content(prompt)
    return {"digest_text": response.text}


def send_email_node(state: DigestState) -> dict:
    supabase = get_supabase_client()
    token_response = (
        supabase.table("oauth_tokens")
        .select("encrypted_access_token, encrypted_refresh_token, expires_at")
        .eq("user_id", state["user_id"])
        .eq("provider", "google")
        .execute()
    )
    if not token_response.data:
        logger.warning("No Google OAuth connection for user %s; email skipped", state["user_id"])
        return {}

    user_response = (
        supabase.table("users")
        .select("email")
        .eq("id", state["user_id"])
        .execute()
    )
    if not user_response.data or not user_response.data[0].get("email"):
        logger.warning("No email address for user %s; email skipped", state["user_id"])
        return {}

    fernet_key = os.getenv("FERNET_KEY")
    if not fernet_key:
        raise RuntimeError("FERNET_KEY is not configured")

    encrypted_access_token = token_response.data[0]["encrypted_access_token"]
    encrypted_refresh_token = token_response.data[0]["encrypted_refresh_token"]
    access_token = Fernet(fernet_key.encode("utf-8")).decrypt(
        encrypted_access_token.encode("utf-8")
    ).decode("utf-8")
    refresh_token = Fernet(fernet_key.encode("utf-8")).decrypt(
        encrypted_refresh_token.encode("utf-8")
    ).decode("utf-8")

    expires_at = datetime.fromisoformat(
        token_response.data[0]["expires_at"].replace("Z", "+00:00")
    )
    now = datetime.now(expires_at.tzinfo) if expires_at.tzinfo else datetime.utcnow()
    if expires_at <= now:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("Google OAuth environment variables are not configured")

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
        refreshed_response.raise_for_status()
        refreshed_data = refreshed_response.json()
        access_token = refreshed_data.get("access_token")
        expires_in = refreshed_data.get("expires_in")
        if not access_token or not expires_in:
            raise RuntimeError("Google refresh response was missing token data")

        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
        supabase.table("oauth_tokens").update(
            {
                "encrypted_access_token": Fernet(fernet_key.encode("utf-8")).encrypt(
                    access_token.encode("utf-8")
                ).decode("utf-8"),
                "expires_at": expires_at.isoformat(),
            }
        ).eq("user_id", state["user_id"]).eq("provider", "google").execute()

    digest_text = state.get("digest_text", "")
    content_parts = []
    sport_headings = {"football": "Football", "f1": "Formula 1", "formula 1": "Formula 1"}
    for line in digest_text.splitlines():
        text = line.strip()
        if not text:
            continue
        heading = sport_headings.get(text.lower())
        if heading:
            content_parts.append(
                f'<h2 style="margin:24px 0 8px;color:#1f2937;font-size:18px;">{heading}</h2>'
            )
        else:
            content_parts.append(
                f'<p style="margin:0 0 14px;color:#374151;font-size:15px;line-height:1.6;">{html.escape(text)}</p>'
            )

    content = "".join(content_parts) or (
        '<p style="margin:0 0 14px;color:#374151;font-size:15px;line-height:1.6;">'
        "No digest content was generated."
        "</p>"
    )
    html_body = (
        '<html><body style="margin:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;">'
        '<div style="max-width:600px;margin:24px auto;padding:28px;background:#ffffff;color:#111827;">'
        '<div style="border-bottom:1px solid #e5e7eb;padding-bottom:18px;margin-bottom:20px;">'
        '<h1 style="margin:0 0 6px;font-size:26px;line-height:1.2;color:#111827;">MatchMate Weekly Digest</h1>'
        '<p style="margin:0;color:#6b7280;font-size:14px;">Here\'s what happened last week</p>'
        '</div>'
        f"{content}"
        '<div style="border-top:1px solid #e5e7eb;margin-top:28px;padding-top:14px;">'
        '<p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.5;">'
        "You're receiving this because you follow these teams on MatchMate."
        "</p></div></div></body></html>"
    )
    message = MIMEText(html_body, "html")
    message["to"] = user_response.data[0]["email"]
    message["subject"] = "Your MatchMate Weekly Digest"
    message["from"] = "me"
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    email_response = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={"raw": raw_message},
        timeout=30,
    )
    print("Gmail API error response:", email_response.text)
    email_response.raise_for_status()
    return {}


builder = StateGraph(DigestState)
builder.add_node("fetch_football", fetch_football_node)
builder.add_node("fetch_f1", fetch_f1_node)
builder.add_node("fetch_football_results", fetch_football_results_node)
builder.add_node("fetch_f1_results", fetch_f1_results_node)
builder.add_node("combine", combine_node)
builder.add_node("write_digest", write_digest_node)
builder.add_node("send_email", send_email_node)
builder.add_edge(START, "fetch_football")
builder.add_edge(START, "fetch_f1")
builder.add_edge(START, "fetch_football_results")
builder.add_edge(START, "fetch_f1_results")
builder.add_edge("fetch_football", "combine")
builder.add_edge("fetch_f1", "combine")
builder.add_edge("fetch_football_results", "combine")
builder.add_edge("fetch_f1_results", "combine")
builder.add_edge("combine", "write_digest")
builder.add_edge("write_digest", "send_email")
builder.add_edge("send_email", END)
app = builder.compile()
