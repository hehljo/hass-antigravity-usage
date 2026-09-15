"""Config flow for Antigravity Pulse."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from .api import account_email
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_EMAIL,
    CONF_PROJECT_ID,
    CONF_REFRESH_TOKEN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    GOOGLE_TOKEN_URL,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    OAUTH_CLIENT_ID,
    OAUTH_CLIENT_SECRET,
)


class AntigravityPulseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Link an Antigravity account by pasting its local OAuth tokens.

    Antigravity's own login runs a loopback redirect to the machine that
    started it. On a headless Home Assistant host that machine is never the
    one the user's browser can reach, so there is no working device-code or
    redirect flow to run from here (verified: Google's OOB "urn:...:oob"
    fallback was retired in 2022, and a HA-hosted loopback listener only
    works when the browser and the HA host are the same machine). Instead,
    the user logs in once locally (Antigravity CLI/IDE already did this) and
    pastes the resulting access + refresh token here — the same approach
    reference tools like CodexBar and openusage use for Gemini/Antigravity.
    """

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Collect a pasted access/refresh token pair and verify it."""
        errors: dict[str, str] = {}
        if user_input is not None:
            access_token = user_input["access_token"].strip()
            refresh_token = user_input["refresh_token"].strip()
            try:
                id_token = await self._async_verify_refresh_token(refresh_token)
            except _InvalidToken:
                errors["base"] = "invalid_token"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            else:
                email = account_email(id_token)
                if email and self.source != SOURCE_REAUTH:
                    await self.async_set_unique_id(email)
                    self._abort_if_unique_id_configured()

                data = {
                    CONF_ACCESS_TOKEN: access_token,
                    CONF_REFRESH_TOKEN: refresh_token,
                    CONF_ACCOUNT_EMAIL: email,
                    CONF_PROJECT_ID: user_input.get("project_id", "").strip(),
                }
                title = "Antigravity Pulse"
                if email:
                    title = f"{title} · {email}"

                if self.source == SOURCE_REAUTH:
                    entry = self._get_reauth_entry()
                    if email:
                        await self.async_set_unique_id(email)
                        self._abort_if_unique_id_mismatch()
                    return self.async_update_and_abort(entry, data_updates=data)
                return self.async_create_entry(
                    title=title,
                    data=data,
                    options={CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("access_token"): str,
                    vol.Required("refresh_token"): str,
                    vol.Optional("project_id", default=""): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Reconnect a revoked or expired Antigravity authorization."""
        return await self.async_step_user()

    async def _async_verify_refresh_token(self, refresh_token: str) -> str | None:
        """Exchange the refresh token once to confirm it is valid."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        async with session.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": OAUTH_CLIENT_ID,
                "client_secret": OAUTH_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            if response.status in (400, 401, 403):
                raise _InvalidToken
            response.raise_for_status()
            tokens = await response.json(content_type=None)
        if not isinstance(tokens, dict) or not tokens.get("access_token"):
            raise _InvalidToken
        id_token = tokens.get("id_token")
        return id_token if isinstance(id_token, str) else None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the integration's options flow."""
        return AntigravityPulseOptionsFlow()


class AntigravityPulseOptionsFlow(OptionsFlow):
    """Tune the polling cadence."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_UPDATE_INTERVAL, default=current): vol.All(
                        int, vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)
                    )
                }
            ),
        )


class _InvalidToken(Exception):
    """The pasted refresh token was rejected by Google."""
