"""Sensors for Antigravity Pulse."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AntigravityUsageConfigEntry, AntigravityUsageCoordinator
from .api import QUOTA_WINDOWS
from .const import CONF_ACCOUNT_EMAIL, DOMAIN, SENSOR_DEFINITIONS

POOL_LABELS = {
    "gemini": "Gemini",
    "claude_gpt": "Claude & GPT",
}

WINDOW_LABELS = {
    "5h": "5h",
    "weekly": "weekly",
}


async def async_setup_entry(
    hass,
    entry: AntigravityUsageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create static sensors and discover every quota pool as it appears."""
    coordinator = entry.runtime_data
    async_add_entities(
        AntigravityUsageSensor(coordinator, entry, key, name, unit, icon, device_class)
        for key, name, unit, icon, device_class in SENSOR_DEFINITIONS
    )
    known: set[tuple[str, str]] = set()

    def sync_pool_entities() -> None:
        data = coordinator.data or {}
        found = {
            (key.removesuffix(f"_{window}_used_percent"), window)
            for key in data
            for window in QUOTA_WINDOWS
            if key.endswith(f"_{window}_used_percent")
        }
        new_entities: list[SensorEntity] = []
        for pool, window in found - known:
            label = POOL_LABELS.get(pool, pool.replace("_", " ").title())
            window_label = WINDOW_LABELS.get(window, window)
            new_entities.append(
                AntigravityQuotaSensor(
                    coordinator, entry, pool, window, f"{label} {window_label} usage"
                )
            )
            new_entities.append(
                AntigravityResetSensor(
                    coordinator, entry, pool, window, f"{label} {window_label} reset"
                )
            )
        if new_entities:
            known.update(found)
            async_add_entities(new_entities)

    sync_pool_entities()
    entry.async_on_unload(coordinator.async_add_listener(sync_pool_entities))


class _AntigravityPulseEntity(CoordinatorEntity[AntigravityUsageCoordinator]):
    """Shared device definition for every Antigravity Pulse entity."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: AntigravityUsageCoordinator, entry: AntigravityUsageConfigEntry
    ) -> None:
        super().__init__(coordinator)
        account = entry.data.get(CONF_ACCOUNT_EMAIL)
        title = "Antigravity Pulse"
        if account:
            title = f"{title} · {account}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=title,
            entry_type=DeviceEntryType.SERVICE,
        )


class AntigravityUsageSensor(_AntigravityPulseEntity, SensorEntity):
    """One stable metric from Antigravity's current usage snapshot."""

    def __init__(
        self,
        coordinator: AntigravityUsageCoordinator,
        entry: AntigravityUsageConfigEntry,
        key: str,
        name: str,
        unit: str | None,
        icon: str,
        device_class: str | None,
    ) -> None:
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        if device_class == "timestamp":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def available(self) -> bool:
        if self._key == "api_error":
            return True
        return super().available

    @property
    def native_value(self) -> Any:
        if self._key == "api_error":
            return 0 if self.coordinator.last_update_success else 1
        return None


def _window_unique_id(entry_id: str, kind: str, pool: str, window: str) -> str:
    """Keep the pre-weekly IDs for the 5h window so existing entities survive."""
    if window == "5h":
        return f"{entry_id}_{kind}_{pool}"
    return f"{entry_id}_{kind}_{window}_{pool}"


class AntigravityQuotaSensor(_AntigravityPulseEntity, SensorEntity):
    """A discovered quota pool's used percentage for one window (5h or weekly)."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:gauge"

    def __init__(
        self,
        coordinator: AntigravityUsageCoordinator,
        entry: AntigravityUsageConfigEntry,
        pool: str,
        window: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._prefix = f"{pool}_{window}"
        self._attr_unique_id = _window_unique_id(entry.entry_id, "quota", pool, window)
        self._attr_name = name

    @property
    def available(self) -> bool:
        return super().available and f"{self._prefix}_used_percent" in (
            self.coordinator.data or {}
        )

    @property
    def native_value(self) -> Any:
        return (self.coordinator.data or {}).get(f"{self._prefix}_used_percent")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}
        if f"{self._prefix}_used_percent" not in data:
            return None
        return {"remaining_percent": data.get(f"{self._prefix}_remaining_percent")}


class AntigravityResetSensor(_AntigravityPulseEntity, SensorEntity):
    """When a discovered quota pool's window resets.

    Unknown while the window is untouched: Google's reset time for an unused
    window only moves forward with every poll and never actually happens.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-refresh"

    def __init__(
        self,
        coordinator: AntigravityUsageCoordinator,
        entry: AntigravityUsageConfigEntry,
        pool: str,
        window: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._prefix = f"{pool}_{window}"
        self._attr_unique_id = _window_unique_id(entry.entry_id, "reset", pool, window)
        self._attr_name = name

    @property
    def native_value(self) -> Any:
        value = (self.coordinator.data or {}).get(f"{self._prefix}_reset_time")
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
