"""Gemini client with a client-side rate limiter (free tier) and retries."""

import json
import logging
import threading
import time

from google import genai
from google.genai import errors, types

from rag_m2.settings import settings

log = logging.getLogger(__name__)


class RateLimiter:
    """Spaces calls at least 60/rpm seconds apart; thread-safe."""

    def __init__(self, rpm: int) -> None:
        self.interval, self.next_slot, self.lock = 60.0 / rpm, 0.0, threading.Lock()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_slot)
            self.next_slot = slot + self.interval
        if slot > now:
            time.sleep(slot - now)


limiter = RateLimiter(settings.llm_requests_per_minute)
_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY missing: put it in a .env file at the repo root")
        _client = genai.Client(api_key=settings.google_api_key)
    return _client


def generate(prompt: str, system: str | None = None, as_json: bool = False, retries: int = 4) -> str:
    """Single-turn completion. `as_json` forces a JSON answer."""
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0.0,
        response_mime_type="application/json" if as_json else None,
    )
    for attempt in range(retries):
        limiter.wait()
        try:
            resp = client().models.generate_content(model=settings.llm_model, contents=prompt, config=config)
            return resp.text or ""
        except errors.APIError as e:
            if e.code not in (429, 500, 503) or attempt == retries - 1:
                raise
            delay = 15 * (attempt + 1)
            log.warning("Gemini %s, retry in %ss", e.code, delay)
            time.sleep(delay)
    return ""


def generate_json(prompt: str, system: str | None = None) -> dict:
    text = generate(prompt, system, as_json=True).strip().removeprefix("```json").strip("`\n ")
    return json.loads(text)
