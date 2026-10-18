"""Sensor entities for Wavin WTC-3."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature, LIGHT_LUX

from .const import CONTROL_STATE_TEXT, DOMAIN, DRT300_VERIFIED_HEAT_CENTER
from .entity import WavinEntity


def _control_state_text(value: int | None) -> str | None:
    if value is None:
        return None
    return CONTROL_STATE_TEXT.get(value, f"Ismeretlen ({value})")


@dataclass(frozen=True)
class SensorDescription:
    key: str
    name: str
    value_fn: Callable
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT
    icon: str | None = None
    options: list[str] | None = None


SYSTEM_SENSORS = [
    SensorDescription("water_temp", "Előremenő vízhőmérséklet", lambda data: data.water_temp, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDescription("wtc_room_temp", "WTC helyiség-hőmérséklet", lambda data: data.wtc_room_temp, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDescription("wtc_humidity", "WTC relatív páratartalom", lambda data: data.wtc_humidity, PERCENTAGE, SensorDeviceClass.HUMIDITY),
    SensorDescription("dewpoint", "Harmatpont", lambda data: data.dewpoint, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDescription("pi_output", "PI kimenet", lambda data: data.pi_output, PERCENTAGE, None),
    # There is no meaning table for the DIP4 combinations in the supplied manual, so this remains a code.
    SensorDescription("program_dip", "Programválasztó DIP kód", lambda data: data.program_dip, None, None, None, "mdi:dip-switch"),
    SensorDescription(
        "control_state",
        "Vezérlés állapota",
        lambda data: _control_state_text(data.control_state),
        None,
        getattr(SensorDeviceClass, "ENUM", None),
        None,
        "mdi:state-machine",
        list(CONTROL_STATE_TEXT.values()),
    ),
    SensorDescription("firmware", "Firmware", lambda data: data.firmware, None, None, None, "mdi:chip"),
    SensorDescription("global_on", "Rendszer állapota", lambda data: None if data.global_on is None else ("Bekapcsolva" if data.global_on else "Kikapcsolva"), None, None, None, "mdi:power"),
    SensorDescription("global_comfort", "Üzemmód", lambda data: None if data.global_comfort is None else ("Komfort" if data.global_comfort else "Economy"), None, None, None, "mdi:weather-sunny"),
]

ZONE_SENSORS = [
    SensorDescription("temperature", "Helyiség-hőmérséklet", lambda z: z.temperature, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    # WTC-3 setpoint registers. These are NOT necessarily the effective
    # DRT-300 knob-adjusted target temperatures; compare on actual hardware.
    SensorDescription("heat_setpoint", "Fűtési alapjel", lambda z: z.heat_setpoint, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDescription("cool_setpoint", "Hűtési alapjel", lambda z: z.cool_setpoint, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDescription("economy_heat_setpoint", "Economy fűtési alapjel", lambda z: z.economy_heat_setpoint, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDescription("economy_cool_setpoint", "Economy hűtési alapjel", lambda z: z.economy_cool_setpoint, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDescription("zone_comfort_status", "Helyiségi üzemmód", lambda z: None if z.comfort is None else ("Komfort" if z.comfort else "Economy"), None, None, None, "mdi:weather-sunny"),
    SensorDescription("active_heat_target", "Aktív fűtési célhőmérséklet", lambda z: (round(DRT300_VERIFIED_HEAT_CENTER + z.wheel_offset, 1) if z.wheel_offset is not None and z.comfort is True and z.cooling is False and z.on is True else None), UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDescription("humidity", "Relatív páratartalom", lambda z: z.humidity, PERCENTAGE, SensorDeviceClass.HUMIDITY),
    SensorDescription("dewpoint", "Harmatpont", lambda z: z.dewpoint, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDescription("wheel_offset", "Potméter eltérés", lambda z: z.wheel_offset, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDescription("lux", "Fényerő", lambda z: z.lux, LIGHT_LUX, SensorDeviceClass.ILLUMINANCE),
    # The manual only gives this as a value/register, without a decoded meaning table.
    SensorDescription("wheel_position", "Potméter pozíció kód", lambda z: z.wheel_position, None, None, None, "mdi:knob"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    stored = hass.data[DOMAIN][entry.entry_id]
    coordinator = stored["coordinator"]
    entities = [WavinSystemSensor(coordinator, entry, stored, desc) for desc in SYSTEM_SENSORS]
    for zone in range(1, stored["zone_count"] + 1):
        for desc in ZONE_SENSORS:
            entities.append(WavinZoneSensor(coordinator, entry, stored, zone, stored["zone_names"][zone - 1], desc))
    async_add_entities(entities)


class WavinSystemSensor(WavinEntity, SensorEntity):
    """System-level Wavin sensor."""

    def __init__(self, coordinator, entry, stored, desc: SensorDescription) -> None:
        super().__init__(coordinator, entry, stored, f"system_{desc.key}")
        self.desc = desc
        self._attr_name = desc.name
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_device_class = desc.device_class
        self._attr_state_class = desc.state_class
        self._attr_icon = desc.icon
        if desc.options:
            self._attr_options = desc.options

    @property
    def native_value(self):
        return self.desc.value_fn(self.coordinator.data)


class WavinZoneSensor(WavinEntity, SensorEntity):
    """Zone-level Wavin sensor."""

    def __init__(self, coordinator, entry, stored, zone: int, zone_name: str, desc: SensorDescription) -> None:
        super().__init__(coordinator, entry, stored, f"zone_{zone}_{desc.key}", zone=zone, zone_name=zone_name)
        self.zone = zone
        self.desc = desc
        self._attr_name = desc.name
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_device_class = desc.device_class
        self._attr_state_class = desc.state_class
        self._attr_icon = desc.icon
        if desc.options:
            self._attr_options = desc.options

    @property
    def native_value(self):
        zone = self.coordinator.data.zones.get(self.zone)
        return self.desc.value_fn(zone) if zone else None
