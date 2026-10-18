"""Constants for the Wavin WTC-3 integration."""
from __future__ import annotations

DOMAIN = "wavin_wtc3"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SLAVE_ID = "slave_id"
CONF_ZONE_COUNT = "zone_count"
CONF_ZONE_NAMES = "zone_names"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ADDRESS_OFFSET = "address_offset"
CONF_TIMEOUT = "timeout"

DEFAULT_NAME = "Wavin WTC-3"
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_ZONE_COUNT = 7
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 5
DEFAULT_ADDRESS_OFFSET = 0

# The user requested a fixed 30 second polling cycle for every value.
POLL_INTERVAL_SECONDS = 30

# SECURITY: Read-only edition.
# Climate and switch platforms are intentionally disabled.
PLATFORMS = ["sensor", "binary_sensor"]

PRESET_COMFORT = "comfort"
PRESET_ECONOMY = "economy"

CONTROL_STATE_TEXT = {
    0: "Inicializálás",
    1: "Fűtés",
    2: "Hűtés",
    3: "Átkapcsolás",
}

# Holding/input register addresses from the Wavin manual.
REG_WATER_TEMP = 4121
REG_WTC_RH = 4127
REG_WTC_ROOM_TEMP = 4128
REG_PI_OUTPUT = 4132
REG_DEWPOINT = 4133
REG_PROGRAM_DIP = 4134
REG_CONTROL_STATE = 4135
REG_FIRMWARE = 4500
REG_SERIAL_LOW = 4501
REG_SERIAL_HIGH = 4502
REG_FIRMWARE_MODE = 4503

# TH1 starts at 4136 and each TH block contains 6 registers:
# measured temperature, RH, calculated dewpoint, wheel offset, dewpoint resistance, lux.
REG_ZONE_BASE = 4136
REG_ZONE_STRIDE = 6

# Writable setpoints: per zone cool/heat/economy heat are grouped by 3 regs.
REG_SETPOINT_BASE = 4178
REG_SETPOINT_STRIDE = 3
REG_ECO_COOL_BASE = 4700

# Fixed comfort/reference setpoints enforced by the integration.
# Cooling keeps the already verified raw value used by previous releases.
# Heating is intentionally raw 250: field verification on the physical DRT-300
# showed that raw 260 displays 26 °C at the centre position. The older generic
# +1.0 °C setpoint compensation must therefore not be applied to this forced
# heating reference.
FORCED_COOLING_SETPOINT_RAW = 240
FORCED_HEATING_SETPOINT_RAW = 250
REG_WHEEL_POSITION_BASE = 4600
REG_WHEEL_WRITE_BASE = 4604
REG_RH_SETPOINT = 4707

# DRT-300 reference temperatures and local wheel range.
# The user installation uses 24 °C as cooling centre/middle point.
DRT300_HEAT_CENTER_TEMP = 25.0
DRT300_COOL_CENTER_TEMP = 24.0
DRT300_ECONOMY_HEAT_CENTER_TEMP = 17.0
DRT300_ECONOMY_COOL_CENTER_TEMP = 24.0
WHEEL_OFFSET_MIN = -6.0
WHEEL_OFFSET_MAX = 6.0

# Coil/discrete bit addresses.
COIL_GLOBAL_ONOFF = 4127
COIL_GLOBAL_CE = 4128
COIL_GLOBAL_HC = 4129

# Read-only zone status bit block: DRY, OUT, DWP, DWP_DI, ONOFF, CE, HC, LIVE.
COIL_ZONE_STATUS_BASE = 4130
COIL_ZONE_STATUS_STRIDE = 8

# Writable zone control bit block mirrors ON/OFF, C/E, H/C.
COIL_ZONE_WRITE_BASE = 4604
COIL_ZONE_WRITE_STRIDE = 8

COIL_LOCK_WRITE_BASE = 4656
COIL_LOCK_READ_BASE = 4186

# DO/status coils.
COIL_DO_BASE = 4112
COIL_PUMP_OUT = 4119  # DO8: pump control output (read-only)
COIL_HEAT_OUT = 4120
COIL_COOL_OUT = 4121
COIL_EMERGENCY_WATER_TEMP = 4125
COIL_WATER_SENSOR_FAULT = 4126
