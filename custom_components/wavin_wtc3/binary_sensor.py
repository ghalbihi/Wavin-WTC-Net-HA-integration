"""Read-only binary sensors for Wavin WTC-3 / WTC-NET."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
from .entity import WavinEntity


async def async_setup_entry(hass, entry, async_add_entities):
    stored = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WavinPumpBinarySensor(stored["coordinator"], entry, stored)])


class WavinPumpBinarySensor(WavinEntity, BinarySensorEntity):
    """DO8 commanded pump output; not proof of physical water circulation."""

    def __init__(self, coordinator, entry, stored):
        super().__init__(coordinator, entry, stored, "system_pump_output")
        self._attr_name = "Szivattyúkimenet"
        self._attr_icon = "mdi:pump"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.pump_output
