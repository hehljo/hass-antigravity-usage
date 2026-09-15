"""Small, dependency-free client helpers for Antigravity Pulse."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Any

# Google quota pools this integration groups models into; mirrors what the
# Antigravity IDE's own /usage screen shows ("GEMINI MODELS" vs. "CLAUDE AND
# GPT MODELS"). A model not covered by any prefix is ignored, not guessed.
QUOTA_POOL_PREFIXES: dict[str, tuple[str, ...]] = {
    "gemini": ("gemini-",),
    "claude_gpt": ("claude-", "gpt-oss-"),
}


class AntigravityUsageError(Exception):
    """Base error for an Antigravity usage request."""


class AntigravityAuthenticationError(AntigravityUsageError):
    """The stored Antigravity authorization is no longer valid."""


def decode_jwt_claims(token: str | None) -> dict[str, Any]:
    """Return unverified claims used only to identify a token's account."""
    if not isinstance(token, str):
        return {}
    try:
        _header, payload, _signature = token.split(".", 2)
        padded_payload = payload + "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(padded_payload)
        claims = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError):
        return {}
    return claims if isinstance(claims, dict) else {}


def account_email(id_token: str | None) -> str | None:
    """Extract the account email from an unverified ID token."""
    claims = decode_jwt_claims(id_token)
    email = claims.get("email")
    return email if isinstance(email, str) and email else None


def _quota_pool_for_model(model_id: str) -> str | None:
    for pool, prefixes in QUOTA_POOL_PREFIXES.items():
        if model_id.startswith(prefixes):
            return pool
    return None


def parse_usage(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a fetchAvailableModels response into entity-ready values.

    Google's quotaInfo only ever carries the 5-hour rolling window here (the
    IDE's own /usage screen also shows a separate weekly window, but that
    comes from an endpoint this integration does not call yet — verified by
    comparing a live poll against /usage on 2026-09-15). Do not synthesize a
    weekly percentage from this response.
    """
    models = payload.get("models")
    if not isinstance(models, dict):
        return {}

    pool_worst: dict[str, dict[str, Any]] = {}
    for model_id, info in models.items():
        if not isinstance(info, dict):
            continue
        pool = _quota_pool_for_model(model_id)
        if pool is None:
            continue
        quota_info = info.get("quotaInfo")
        if not isinstance(quota_info, dict):
            continue
        remaining = quota_info.get("remainingFraction")
        if not isinstance(remaining, (int, float)):
            continue

        current = pool_worst.get(pool)
        if current is None or remaining < current["remaining_fraction"]:
            pool_worst[pool] = {
                "remaining_fraction": float(remaining),
                "reset_time": quota_info.get("resetTime"),
                "model_id": model_id,
            }

    result: dict[str, Any] = {}
    for pool, details in pool_worst.items():
        used_percent = round((1 - details["remaining_fraction"]) * 100, 2)
        result[f"{pool}_5h_used_percent"] = used_percent
        result[f"{pool}_5h_remaining_percent"] = round(100 - used_percent, 2)
        result[f"{pool}_5h_reset_time"] = _iso_timestamp(details["reset_time"])
        result[f"{pool}_5h_limiting_model"] = details["model_id"]

    return {key: value for key, value in result.items() if value is not None}


def _iso_timestamp(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    return None
