"""Unit tests for the response normalization layer."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import unittest

_API_PATH = Path(__file__).parents[1] / "custom_components" / "hass_antigravity_usage" / "api.py"
_SPEC = importlib.util.spec_from_file_location("antigravity_pulse_api", _API_PATH)
assert _SPEC and _SPEC.loader
_API = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_API)
decode_jwt_claims = _API.decode_jwt_claims
account_email = _API.account_email
parse_usage = _API.parse_usage


def _model(remaining_fraction: float | None, reset_time: str | None = None) -> dict:
    quota_info: dict = {}
    if remaining_fraction is not None:
        quota_info["remainingFraction"] = remaining_fraction
    if reset_time is not None:
        quota_info["resetTime"] = reset_time
    return {"quotaInfo": quota_info} if quota_info else {}


class ApiTests(unittest.TestCase):
    def test_usage_groups_models_into_pools_and_picks_the_worst(self) -> None:
        result = parse_usage(
            {
                "models": {
                    "gemini-3.8-flash-high": _model(0.9, "2026-09-15T21:51:46Z"),
                    "gemini-3.1-pro-high": _model(0.17, "2026-09-15T21:51:46Z"),
                    "claude-sonnet-4-6": _model(1.0, "2026-09-15T21:52:39Z"),
                    "gpt-oss-120b-medium": _model(1.0, "2026-09-15T21:52:39Z"),
                    "chat_20706": _model(1.0),  # no pool prefix match -> ignored
                    "gemini-3.7-flash-tiered": {},  # no quotaInfo -> ignored
                }
            }
        )

        # The pool is only as usable as its most exhausted member.
        self.assertEqual(result["gemini_5h_used_percent"], 83.0)
        self.assertEqual(result["gemini_5h_remaining_percent"], 17.0)
        self.assertEqual(result["gemini_5h_limiting_model"], "gemini-3.1-pro-high")
        self.assertEqual(result["gemini_5h_reset_time"], "2026-09-15T21:51:46Z")

        self.assertEqual(result["claude_gpt_5h_used_percent"], 0.0)
        self.assertEqual(result["claude_gpt_5h_remaining_percent"], 100.0)

    def test_usage_ignores_entries_without_a_numeric_remaining_fraction(self) -> None:
        result = parse_usage(
            {
                "models": {
                    "gemini-3.8-flash-high": {"quotaInfo": {"resetTime": "2026-09-15T21:51:46Z"}},
                }
            }
        )
        self.assertNotIn("gemini_5h_used_percent", result)

    def test_usage_returns_empty_dict_for_malformed_payload(self) -> None:
        self.assertEqual(parse_usage({}), {})
        self.assertEqual(parse_usage({"models": "not-a-dict"}), {})

    def test_account_email_reads_claims_without_validating_the_jwt(self) -> None:
        payload = {"email": "marktplaner.app@gmail.com"}
        payload_part = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"header.{payload_part}.signature"

        self.assertEqual(decode_jwt_claims(token)["email"], "marktplaner.app@gmail.com")
        self.assertEqual(account_email(token), "marktplaner.app@gmail.com")
        self.assertIsNone(account_email(None))
        self.assertIsNone(account_email("not-a-jwt"))


if __name__ == "__main__":
    unittest.main()
