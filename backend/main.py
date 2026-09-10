from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from db import get_supabase_client
from extraction import extract_follows

app = FastAPI()


class FollowCreate(BaseModel):
    user_id: str
    sport: str
    team_or_player: str


class FollowExtractionRequest(BaseModel):
    text: str
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


@app.post("/follows", status_code=201)
def create_follow(payload: FollowCreate):
    sport = payload.sport.strip()
    team_or_player = payload.team_or_player.strip()

    if not sport or not team_or_player:
        raise HTTPException(status_code=400, detail="sport and team_or_player cannot be empty")

    supabase = get_supabase_client()

    user_check = supabase.table("users").select("id").eq("id", payload.user_id).execute()
    if not user_check.data:
        raise HTTPException(status_code=404, detail="User not found")

    insert_response = (
        supabase.table("follows")
        .insert({
            "user_id": payload.user_id,
            "sport": sport,
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


