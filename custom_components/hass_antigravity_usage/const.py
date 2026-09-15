"""Constants for Antigravity Pulse."""

from homeassistant.const import Platform

DOMAIN = "hass_antigravity_usage"
PLATFORMS = [Platform.SENSOR]

DEFAULT_UPDATE_INTERVAL = 300
MIN_UPDATE_INTERVAL = 60
MAX_UPDATE_INTERVAL = 3600

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
QUOTA_API_URL = "https://daily-cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels"
QUOTA_USER_AGENT = "antigravity/ide/2.11.0 (aidev_client; os_type=darwin; arch=arm64)"

# Client credentials Antigravity's own installed-app OAuth client uses. Every
# user still signs in with their own Google account and pastes their own
# access/refresh token in the config flow — this only identifies the client
# software to Google, the same way it's public in Google's own open-source
# gemini-cli (packages/core/src/code_assist/oauth2.ts). Installed-app secrets
# are not confidential by Google's own classification (they identify the app,
# not a user), which is why Google lets gemini-cli ship this in the open too.
OAUTH_CLIENT_ID = "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
OAUTH_CLIENT_SECRET = "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"

CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ACCOUNT_EMAIL = "account_email"
CONF_PROJECT_ID = "project_id"
CONF_UPDATE_INTERVAL = "update_interval"

SENSOR_DEFINITIONS = (
    ("api_error", "API errors", "errors", "mdi:alert-circle-outline", None),
)
