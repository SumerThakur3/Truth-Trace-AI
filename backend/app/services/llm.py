"""Gemini API integration for generated verification content."""

import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import logger

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Fallback models when primary hits quota or is unavailable
FALLBACK_MODELS = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.0-flash-lite",
]


def _gemini_url(model: str, method: str) -> str:
    return f"{GEMINI_BASE}/{model}:{method}"


def _extract_text(data: dict[str, Any]) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        block_reason = data.get("promptFeedback", {}).get("blockReason")
        if block_reason:
            raise RuntimeError(f"Gemini blocked the request: {block_reason}")
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    return "\n".join(text_parts).strip()


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    temperature: float = 0.2,
) -> str:
    """Generate content with Gemini, trying fallback models on quota errors."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Add it to backend/.env"
        )

    generation_config: dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": settings.gemini_max_output_tokens,
    }
    if json_mode:
        generation_config["responseMimeType"] = "application/json"

    payload: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": generation_config,
    }

    models_to_try = [settings.gemini_model] + [
        m for m in FALLBACK_MODELS if m != settings.gemini_model
    ]
    last_error: Exception | None = None

    for model in models_to_try:
        try:
            data = await _post_gemini(model, "generateContent", payload)
            text = _extract_text(data)
            if text:
                if model != settings.gemini_model:
                    logger.info("gemini_fallback_model_used", model=model)
                return text
            logger.warning("gemini_empty_response", model=model)
        except RuntimeError as e:
            last_error = e
            msg = str(e).lower()
            if "429" in msg or "quota" in msg or "404" in msg:
                logger.warning("gemini_model_unavailable", model=model, error=str(e)[:200])
                continue
            raise

    raise last_error or RuntimeError(
        "All Gemini models failed. Check your API key quota at https://aistudio.google.com"
    )


async def call_grounded_gemini(prompt: str, temperature: float = 0.1) -> dict[str, Any]:
    """Ask Gemini for a grounded response with Google Search."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is required for Gemini source retrieval.")

    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": settings.gemini_max_output_tokens,
        },
    }
    return await _post_gemini(settings.gemini_model, "generateContent", payload)


async def _post_gemini(model: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    params = {"key": settings.gemini_api_key}
    url = _gemini_url(model, method)

    last_error: Exception | None = None
    for verify_ssl in (True, False):
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout, verify=verify_ssl) as client:
                response = await client.post(url, params=params, json=payload)
                if response.status_code == 400:
                    detail = response.text[:500]
                    logger.error("gemini_bad_request", model=model, detail=detail)
                    raise RuntimeError(f"Gemini rejected the request: {detail}")
                if response.status_code == 429:
                    detail = response.text[:300]
                    raise RuntimeError(f"Gemini quota exceeded (429): {detail}")
                if response.status_code in (401, 403):
                    raise RuntimeError(
                        "Gemini API key is invalid or unauthorized. "
                        "Get a key from https://aistudio.google.com/apikey"
                    )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            logger.error("gemini_http_error", status=exc.response.status_code, model=model, detail=detail)
            raise RuntimeError(f"Gemini API error ({exc.response.status_code}): {detail}") from exc
        except httpx.HTTPError as exc:
            last_error = exc
            if verify_ssl:
                logger.warning("gemini_ssl_retry", error=str(exc))
                continue
            logger.error("gemini_request_error", error=str(exc))
            raise RuntimeError(f"Gemini API request failed: {exc}") from exc

    raise RuntimeError(f"Gemini API request failed: {last_error}")


async def validate_gemini_connection() -> dict[str, Any]:
    """Test Gemini API connectivity at startup."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return {"status": "missing_key", "message": "GEMINI_API_KEY not set"}

    models_to_try = [settings.gemini_model] + [
        m for m in FALLBACK_MODELS if m != settings.gemini_model
    ]

    for model in models_to_try:
        try:
            payload = {
                "contents": [{"role": "user", "parts": [{"text": "Reply with exactly: OK"}]}],
                "generationConfig": {"maxOutputTokens": 10, "temperature": 0},
            }
            data = await _post_gemini(model, "generateContent", payload)
            text = _extract_text(data)
            return {"status": "ok", "model": model, "response": text[:50]}
        except RuntimeError as e:
            if "429" in str(e) or "quota" in str(e).lower():
                continue
            return {"status": "error", "message": str(e)}

    return {
        "status": "quota_exceeded",
        "message": "Gemini API quota exceeded for all models. Check billing at https://aistudio.google.com",
    }


def parse_json_response(text: str) -> dict:
    """Safely parse JSON from Gemini output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        logger.error("gemini_json_parse_failed", response=text[:500])
        raise ValueError("Gemini did not return valid JSON.")
