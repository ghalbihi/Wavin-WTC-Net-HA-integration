"""Guarded thermostat target controls for heating + Comfort only."""
from __future__ import annotations
import logging
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError
from .api import WavinWTC3Error
from .const import DOMAIN, DRT300_VERIFIED_HEAT_CENTER, WAVIN_ALLOW_SETPOINT_WRITES, WAVIN_ALLOWED_WRITE_ZONES
from .entity import WavinEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    stored = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WavinTargetNumber(stored["coordinator"], entry, stored, i, stored["zone_names"][i - 1]) for i in range(1, stored["zone_count"] + 1)])

class WavinTargetNumber(WavinEntity, NumberEntity):
    """Physical thermostat equivalent; no switching of modes."""
    _attr_native_min_value = 15
    _attr_native_max_value = 27
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, entry, stored, zone, zone_name):
        super().__init__(coordinator, entry, stored, f"zone_{zone}_target_control", zone=zone, zone_name=zone_name)
        self._attr_name = "Célhőmérséklet állítása (fűtés)"
        self.zone = zone
        self.stored = stored

    @property
    def available(self):
        if not WAVIN_ALLOW_SETPOINT_WRITES or self.zone not in WAVIN_ALLOWED_WRITE_ZONES or not super().available:
            return False
        state = self.coordinator.data
        z = state.zones.get(self.zone)
        return bool(z and state.global_on is True and state.global_comfort is True and state.global_cooling is False and state.control_state == 1 and z.on is True and z.comfort is True and z.cooling is False and z.live is True and z.wheel_offset is not None)

    @property
    def native_value(self):
        z = self.coordinator.data.zones.get(self.zone)
        return round(DRT300_VERIFIED_HEAT_CENTER + z.wheel_offset, 1) if z and z.wheel_offset is not None and z.comfort is True and z.cooling is False else None

    async def async_set_native_value(self, value):
        if not self.available:
            raise HomeAssistantError("Wavin target change unavailable in current mode")
        try:
            await self.stored["api"].set_safe_target(self.zone, value, self.stored["zone_count"])
        except WavinWTC3Error as exc:
            raise HomeAssistantError(str(exc)) from exc
        await self.coordinator.async_request_refresh()
