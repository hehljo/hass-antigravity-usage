"""Antigravity Pulse Home Assistant integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AntigravityAuthenticationError, account_email, parse_usage
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_EMAIL,
    CONF_PROJECT_ID,
    CONF_REFRESH_TOKEN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    GOOGLE_TOKEN_URL,
    OAUTH_CLIENT_ID,
    OAUTH_CLIENT_SECRET,
    PLATFORMS,
    QUOTA_API_URL,
    QUOTA_USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

type AntigravityUsageConfigEntry = ConfigEntry["AntigravityUsageCoordinator"]


async def async_setup_entry(hass, entry: AntigravityUsageConfigEntry) -> bool:
    """Set up Antigravity Pulse from one config entry."""
    coordinator = AntigravityUsageCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass, entry: AntigravityUsageConfigEntry) -> bool:
    """Unload an Antigravity Pulse config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass, entry: AntigravityUsageConfigEntry) -> None:
    """Apply an option change without reloading the integration."""
    entry.runtime_data.update_interval = timedelta(
        seconds=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    )
    await entry.runtime_data.async_request_refresh()


class AntigravityUsageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch the Antigravity 5-hour quota window with one coordinated poll."""

    config_entry: AntigravityUsageConfigEntry

    def __init__(self, hass, entry: AntigravityUsageConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            ),
            config_entry=entry,
            always_update=False,
        )
        # access_token is refreshed eagerly on every poll: Google gives no
        # reliable expiry here (Antigravity's own token file only carries
        # one, not both, in every version seen so far), and a spare refresh
        # call is cheap next to a failed quota poll.

    async def _async_update_data(self) -> dict[str, Any]:
        """Refresh the access token, then fetch the current quota snapshot."""
        access_token = await self._async_refresh_access_token()

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            async with session.post(
                QUOTA_API_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "User-Agent": QUOTA_USER_AGENT,
                },
                json={"project": self.config_entry.data.get(CONF_PROJECT_ID, "")},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status in (401, 403):
                    raise ConfigEntryAuthFailed("Antigravity authentication has expired")
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except aiohttp.ClientResponseError as err:
            raise UpdateFailed(f"Unable to fetch Antigravity usage: HTTP {err.status}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Unable to fetch Antigravity usage: {err}") from err

        if not isinstance(payload, dict):
            raise UpdateFailed("Antigravity usage returned invalid data")
        return parse_usage(payload)

    async def _async_refresh_access_token(self) -> str:
        """Exchange the stored refresh token for a fresh access token."""
        refresh_token = self.config_entry.data.get(CONF_REFRESH_TOKEN)
        if not refresh_token:
            raise ConfigEntryAuthFailed("No Antigravity refresh token is available")

        try:
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
                    raise AntigravityAuthenticationError
                response.raise_for_status()
                tokens = await response.json(content_type=None)
        except AntigravityAuthenticationError as err:
            raise ConfigEntryAuthFailed("Reconnect Antigravity to continue") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Unable to refresh Antigravity token: {err}") from err

        access_token = tokens.get("access_token") if isinstance(tokens, dict) else None
        if not isinstance(access_token, str) or not access_token:
            raise ConfigEntryAuthFailed("Antigravity token response is incomplete")

        new_refresh_token = tokens.get("refresh_token")
        id_token = tokens.get("id_token")
        email = account_email(id_token) if isinstance(id_token, str) else None
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                CONF_ACCESS_TOKEN: access_token,
                CONF_REFRESH_TOKEN: (
                    new_refresh_token
                    if isinstance(new_refresh_token, str) and new_refresh_token
                    else refresh_token
                ),
                CONF_ACCOUNT_EMAIL: email or self.config_entry.data.get(CONF_ACCOUNT_EMAIL),
            },
        )
        return access_token
