"""
ai_search_service.py — Natural-language query → English tool keywords via Gemini AI.

Uses Google Gemini Flash Lite (free tier) via direct REST call.
Falls back gracefully to None if the API key is missing or the call fails,
so the caller can use the raw query as-is without breaking anything.
"""
import json
import re

import requests
from django.conf import settings


_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-lite-latest:generateContent"
)

_PROMPT = """You are a search assistant for Rentora, a peer-to-peer tool rental platform.
The user types what they need in colloquial Arabic, English, or a mix of both.
Your job: extract 1-4 English keywords that describe the TOOL they need to rent.

Rules:
- Return ONLY a JSON object with one key: "keywords"
- Focus on the tool name, not the task description
- Keep it short and searchable (1-4 words)
- If input is already English and clear, just clean/simplify it

Examples:
  "بدي اشي يحفر الجدار"        → {{"keywords": "hammer drill"}}
  "شيء احفر فيه الارض"         → {{"keywords": "jackhammer"}}
  "بدي مقدح"                    → {{"keywords": "drill"}}
  "محتاج ارش الحديقة"           → {{"keywords": "garden sprayer"}}
  "I need something to cut wood" → {{"keywords": "circular saw"}}
  "pressure wash my driveway"   → {{"keywords": "pressure washer"}}
  "شيء لتنظيف السيارة بالضغط"  → {{"keywords": "pressure washer"}}
  "اداة لقطع الخشب"             → {{"keywords": "wood saw"}}

User query: {query}

Return ONLY valid JSON, no explanation, no markdown:"""


def extract_search_keywords(user_query: str) -> str | None:
    """
    Converts a natural-language query to English tool search keywords using Gemini AI.

    Returns a keyword string on success, or None on any failure
    (missing key, rate limit, network error, bad JSON, etc.).
    Caller should fall back to using the raw query when None is returned.
    """
    query = (user_query or '').strip()
    if not query:
        return None

    api_key = getattr(settings, 'GEMINI_API_KEY', '').strip()
    if not api_key:
        return None

    try:
        payload = {
            "contents": [{"parts": [{"text": _PROMPT.format(query=query)}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 60},
        }
        resp = requests.post(
            _GEMINI_URL,
            params={"key": api_key},
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()

        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

        raw = re.sub(r'^```[a-z]*\s*', '', raw, flags=re.IGNORECASE)
        raw = re.sub(r'\s*```$', '', raw)

        data = json.loads(raw)
        result = str(data.get("keywords", "")).strip()
        return result or None

    except Exception:
        return None
