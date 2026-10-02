"""Small, dependency-free client helpers for Antigravity Pulse."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Any

# Google's quota groups, keyed by the prefix of their bucketId in the
# retrieveUserQuotaSummary response ("gemini-5h", "3p-weekly", ...). The pool
# names stay stable because sensor unique IDs are built from them. A group
# not covered here is ignored, not guessed.
BUCKET_POOL_PREFIXES: dict[str, str] = {
    "gemini-": "gemini",
    "3p-": "claude_gpt",
}

# Window names as Google reports them in each bucket's "window" field.
QUOTA_WINDOWS: tuple[str, ...] = ("5h", "weekly")


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


def _pool_for_bucket(bucket_id: str) -> str | None:
    for prefix, pool in BUCKET_POOL_PREFIXES.items():
        if bucket_id.startswith(prefix):
            return pool
    return None


def parse_usage(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a retrieveUserQuotaSummary response into entity-ready values.

    Each model group carries one bucket per window ("5h" and "weekly"), the
    same two windows Antigravity's own /usage screen shows. Verified live on
    2026-10-02: the 5h values match fetchAvailableModels' quotaInfo exactly.

    An untouched window (nothing used yet) still gets a resetTime from Google,
    but it is just "now + window length" and moves forward on every poll, so
    it is dropped instead of being shown as a reset that never happens.
    """
    groups = payload.get("groups")
    if not isinstance(groups, list):
        return {}

    result: dict[str, Any] = {}
    for group in groups:
        buckets = group.get("buckets") if isinstance(group, dict) else None
        if not isinstance(buckets, list):
            continue
        for bucket in buckets:
            if not isinstance(bucket, dict):
                continue
            bucket_id = bucket.get("bucketId")
            window = bucket.get("window")
            remaining = bucket.get("remainingFraction")
            if not isinstance(bucket_id, str) or window not in QUOTA_WINDOWS:
                continue
            if not isinstance(remaining, (int, float)):
                continue
            pool = _pool_for_bucket(bucket_id)
            if pool is None:
                continue

            used_percent = round((1 - float(remaining)) * 100, 2)
            prefix = f"{pool}_{window}"
            result[f"{prefix}_used_percent"] = used_percent
            result[f"{prefix}_remaining_percent"] = round(100 - used_percent, 2)
            if used_percent > 0:
                result[f"{prefix}_reset_time"] = _iso_timestamp(bucket.get("resetTime"))

    return {key: value for key, value in result.items() if value is not None}


def _iso_timestamp(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    return None
