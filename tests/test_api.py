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


def _bucket(bucket_id: str, window: str, remaining: float | None, reset: str | None = None) -> dict:
    bucket: dict = {"bucketId": bucket_id, "window": window}
    if remaining is not None:
        bucket["remainingFraction"] = remaining
    if reset is not None:
        bucket["resetTime"] = reset
    return bucket


# Shape copied from a live retrieveUserQuotaSummary response (2026-10-02).
LIVE_SHAPE = {
    "groups": [
        {
            "displayName": "Gemini Models",
            "buckets": [
                _bucket("gemini-weekly", "weekly", 0.7762013, "2026-10-08T18:37:23Z"),
                _bucket("gemini-5h", "5h", 0.8678547, "2026-10-03T02:03:18Z"),
            ],
        },
        {
            "displayName": "Claude and GPT models",
            "buckets": [
                _bucket("3p-weekly", "weekly", 1, "2026-10-09T21:29:34Z"),
                _bucket("3p-5h", "5h", 1, "2026-10-03T02:29:34Z"),
            ],
        },
    ]
}


class ApiTests(unittest.TestCase):
    def test_usage_reads_both_windows_per_pool(self) -> None:
        result = parse_usage(LIVE_SHAPE)

        self.assertEqual(result["gemini_5h_used_percent"], 13.21)
        self.assertEqual(result["gemini_5h_remaining_percent"], 86.79)
        self.assertEqual(result["gemini_5h_reset_time"], "2026-10-03T02:03:18Z")
        self.assertEqual(result["gemini_weekly_used_percent"], 22.38)
        self.assertEqual(result["gemini_weekly_reset_time"], "2026-10-08T18:37:23Z")

        self.assertEqual(result["claude_gpt_5h_used_percent"], 0.0)
        self.assertEqual(result["claude_gpt_weekly_used_percent"], 0.0)

    def test_untouched_window_has_no_reset_time(self) -> None:
        # Google moves an unused window's reset time forward on every poll.
        result = parse_usage(LIVE_SHAPE)
        self.assertNotIn("claude_gpt_5h_reset_time", result)
        self.assertNotIn("claude_gpt_weekly_reset_time", result)

    def test_usage_ignores_unknown_groups_windows_and_missing_fractions(self) -> None:
        result = parse_usage(
            {
                "groups": [
                    {"buckets": [_bucket("future-5h", "5h", 0.5)]},
                    {"buckets": [_bucket("gemini-monthly", "monthly", 0.5)]},
                    {"buckets": [_bucket("gemini-5h", "5h", None, "2026-10-03T02:03:18Z")]},
                ]
            }
        )
        self.assertEqual(result, {})

    def test_usage_returns_empty_dict_for_malformed_payload(self) -> None:
        self.assertEqual(parse_usage({}), {})
        self.assertEqual(parse_usage({"groups": "not-a-list"}), {})
        self.assertEqual(parse_usage({"groups": [None, {"buckets": "x"}, {"buckets": [None]}]}), {})

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
