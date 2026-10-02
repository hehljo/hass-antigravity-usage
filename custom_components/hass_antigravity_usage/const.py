"""Constants for Antigravity Pulse."""

from homeassistant.const import Platform

DOMAIN = "hass_antigravity_usage"
PLATFORMS = [Platform.SENSOR]

DEFAULT_UPDATE_INTERVAL = 300
MIN_UPDATE_INTERVAL = 60
MAX_UPDATE_INTERVAL = 3600

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
QUOTA_API_URL = "https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary"
QUOTA_USER_AGENT = "antigravity/ide/2.11.0 (aidev_client; os_type=darwin; arch=arm64)"

# Client credentials Antigravity's own installed-app OAuth client uses. Every
# user still signs in with their own Google account and pastes their own
# refresh token in the config flow — this only identifies the client software
# to Google. Installed-app secrets are not confidential by Google's own
# classification (they identify the app, not a user).
#
# This is Antigravity's OWN client, distinct from gemini-cli's client
# (681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j...) — Google binds a refresh
# token to the client that issued it, so using gemini-cli's client ID here
# makes Google reject every Antigravity-issued refresh token with
# "401 unauthorized_client", even though the token itself is valid. Verified
# against oauth2.googleapis.com on 2026-09-15 (200 OK with this client,
# 401 with gemini-cli's).
OAUTH_CLIENT_ID = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
OAUTH_CLIENT_SECRET = "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"

CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ACCOUNT_EMAIL = "account_email"
CONF_PROJECT_ID = "project_id"
CONF_UPDATE_INTERVAL = "update_interval"

SENSOR_DEFINITIONS = (
    ("api_error", "API errors", "errors", "mdi:alert-circle-outline", None),
)
