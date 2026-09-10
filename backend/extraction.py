import json
import re

import google.generativeai as genai


def extract_follows(text: str, api_key: str) -> dict:
    if not text or not text.strip():
        raise ValueError("text cannot be empty")
    if not api_key or not api_key.strip():
        raise ValueError("api_key cannot be empty")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-3.6-flash",
        generation_config={"response_mime_type": "application/json"},
    )

    prompt = (
        "Extract sports follows from the text and return valid JSON only with this exact shape: "
        '{"follows": [{"sport": "string", "team_or_player": "string"}, ...]}.'
        "Only include relevant sports teams or players mentioned. "
        "If none are found, return {\"follows\": []}. "
        "Use the original text as the source; do not include explanations or markdown.\n\n"
        f"Text:\n{text}"
    )

    try:
        response = model.generate_content(prompt)
        raw_text = getattr(response, "text", None) or str(response)
    except Exception as exc:
        raise RuntimeError("Gemini API call failed") from exc

    if raw_text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            raw_text = match.group(1)

    try:
        if hasattr(response, "parsed") and response.parsed is not None:
            parsed = response.parsed
        else:
            parsed = json.loads(raw_text)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini response was not valid JSON") from exc

    if not isinstance(parsed, dict) or "follows" not in parsed or not isinstance(parsed["follows"], list):
        raise RuntimeError("Gemini response format was invalid")

    normalized = {"follows": []}
    for item in parsed["follows"]:
        if not isinstance(item, dict):
            continue
        sport = str(item.get("sport", "")).strip()
        team_or_player = str(item.get("team_or_player", "")).strip()
        if sport and team_or_player:
            normalized["follows"].append({"sport": sport, "team_or_player": team_or_player})

    return normalized
