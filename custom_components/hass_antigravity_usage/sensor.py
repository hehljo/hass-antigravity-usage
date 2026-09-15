"""Sensors for Antigravity Pulse."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AntigravityUsageConfigEntry, AntigravityUsageCoordinator
from .const import CONF_ACCOUNT_EMAIL, DOMAIN, SENSOR_DEFINITIONS

POOL_LABELS = {
    "gemini": "Gemini",
    "claude_gpt": "Claude & GPT",
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
    known_pools: set[str] = set()

    def sync_pool_entities() -> None:
        data = coordinator.data or {}
        pools = {
            key.removesuffix("_5h_used_percent")
            for key in data
            if key.endswith("_5h_used_percent")
        }
        new_entities: list[SensorEntity] = []
        for pool in pools - known_pools:
            label = POOL_LABELS.get(pool, pool.replace("_", " ").title())
            new_entities.append(
                AntigravityQuotaSensor(coordinator, entry, pool, f"{label} 5h usage")
            )
            new_entities.append(
                AntigravityResetSensor(coordinator, entry, pool, f"{label} 5h reset")
            )
        if new_entities:
            known_pools.update(pools)
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


class AntigravityQuotaSensor(_AntigravityPulseEntity, SensorEntity):
    """A discovered quota pool's 5-hour used percentage.

    Only the rolling 5-hour window is available (verified live against the
    Antigravity IDE's /usage screen on 2026-09-15). The weekly window /usage
    also shows comes from a different, not-yet-identified endpoint and is
    intentionally not represented here — do not add a fabricated weekly
    sensor without first finding and verifying that endpoint.
    """

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:gauge"

    def __init__(
        self,
        coordinator: AntigravityUsageCoordinator,
        entry: AntigravityUsageConfigEntry,
        pool: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._pool = pool
        self._attr_unique_id = f"{entry.entry_id}_quota_{pool}"
        self._attr_name = name

    @property
    def available(self) -> bool:
        return super().available and f"{self._pool}_5h_used_percent" in (
            self.coordinator.data or {}
        )

    @property
    def native_value(self) -> Any:
        return (self.coordinator.data or {}).get(f"{self._pool}_5h_used_percent")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}
        if f"{self._pool}_5h_used_percent" not in data:
            return None
        return {
            "remaining_percent": data.get(f"{self._pool}_5h_remaining_percent"),
            "limiting_model": data.get(f"{self._pool}_5h_limiting_model"),
        }


class AntigravityResetSensor(_AntigravityPulseEntity, SensorEntity):
    """When a discovered quota pool's 5-hour window resets."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-refresh"

    def __init__(
        self,
        coordinator: AntigravityUsageCoordinator,
        entry: AntigravityUsageConfigEntry,
        pool: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._pool = pool
        self._attr_unique_id = f"{entry.entry_id}_reset_{pool}"
        self._attr_name = name

    @property
    def available(self) -> bool:
        return super().available and (self.coordinator.data or {}).get(
            f"{self._pool}_5h_reset_time"
        ) is not None

    @property
    def native_value(self) -> Any:
        value = (self.coordinator.data or {}).get(f"{self._pool}_5h_reset_time")
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
