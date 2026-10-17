"""Async Modbus TCP API for Wavin WTC-3 through WTC-NET."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient

from .const import *  # noqa: F403

_LOGGER = logging.getLogger(__name__)


class WavinWTC3Error(Exception):
    """Raised when WTC-3 communication or verification fails."""


@dataclass(slots=True)
class ZoneState:
    """One TH zone state."""

    index: int
    temperature: float | None = None
    humidity: float | None = None
    dewpoint: float | None = None
    wheel_offset: float | None = None
    dewpoint_resistance: int | None = None
    lux: int | None = None
    cool_setpoint: float | None = None
    heat_setpoint: float | None = None
    economy_heat_setpoint: float | None = None
    economy_cool_setpoint: float | None = None
    wheel_position: int | None = None
    dry: bool | None = None
    output: bool | None = None
    condensation: bool | None = None
    dwp_input: bool | None = None
    on: bool | None = None
    comfort: bool | None = None
    cooling: bool | None = None
    live: bool | None = None
    locked: bool | None = None


@dataclass(slots=True)
class WavinState:
    """Complete WTC-3 state snapshot."""

    water_temp: float | None = None
    wtc_humidity: float | None = None
    wtc_room_temp: float | None = None
    pi_output: float | None = None
    dewpoint: float | None = None
    program_dip: int | None = None
    control_state: int | None = None
    firmware: str | None = None
    serial: int | None = None
    global_on: bool | None = None
    global_comfort: bool | None = None
    global_cooling: bool | None = None
    heat_output: bool | None = None
    cool_output: bool | None = None
    emergency_water_temp: bool | None = None
    water_sensor_fault: bool | None = None
    zones: dict[int, ZoneState] = field(default_factory=dict)


def _s16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def _temp(value: int | None) -> float | None:
    if value is None or value in (0xFFFF, 0xFFFE):
        return None
    return round(_s16(value) / 10, 1)


def _setpoint_temp(value: int | None) -> float | None:
    """Decode WTC-3 room setpoint registers for Home Assistant.

    Field testing showed that WTC-NET returns the writable room setpoint
    registers 1.0 °C higher than the value shown on the DRT-300/TH room
    unit. Home Assistant should display and control the room-unit value,
    therefore the integration compensates the Modbus value here.
    """
    decoded = _temp(value)
    if decoded is None:
        return None
    return round(decoded - 1.0, 1)


def _setpoint_register_value(temperature: float) -> int:
    """Encode a Home Assistant room setpoint into the WTC-3 register value."""
    return int(round((float(temperature) + 1.0) * 10))


def _wheel_offset_from_position(position: int | None) -> float | None:
    """Convert DRT-300 wheel position 0..12 to a signed +/-6 °C offset."""
    if position is None:
        return None
    position = int(position)
    if position < 0 or position > 12:
        return None
    return float(position - 6)


def _wheel_position_from_offset(offset: float) -> int:
    """Convert signed +/-6 °C offset to DRT-300 wheel position 0..12."""
    return max(0, min(12, int(round(float(offset) + 6))))


def _decode_wheel_position_words(words: list[int], zone: int) -> int | None:
    """Decode packed DRT-300 wheel position codes from registers 4600..4603.

    The manual exposes read-only wheel position codes packed as low/high bytes:
    4600 = TH1/TH2, 4601 = TH3/TH4, 4602 = TH5/TH6, 4603 low byte = TH7.
    """
    idx = int(zone) - 1
    word_index = idx // 2
    if word_index >= len(words):
        return None
    word = int(words[word_index])
    return (word & 0xFF) if idx % 2 == 0 else ((word >> 8) & 0xFF)


def _pct(value: int | None) -> float | None:
    if value is None or value in (0xFFFF, 0xFFFE):
        return None
    return round(value / 10, 1)


def _raw(value: int | None) -> int | None:
    if value is None or value in (0xFFFF, 0xFFFE):
        return None
    return value


class WavinWTC3Api:
    """Modbus TCP client for the WTC-NET gateway."""

    def __init__(self, host: str, port: int, slave_id: int, timeout: int, address_offset: int = 0) -> None:
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.timeout = timeout
        self.address_offset = address_offset
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()

    def _addr(self, address: int) -> int:
        return int(address) + int(self.address_offset)

    async def _ensure_client(self) -> AsyncModbusTcpClient:
        if self._client is None:
            self._client = AsyncModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
        if not self._client.connected:
            connected = await self._client.connect()
            if not connected:
                raise WavinWTC3Error(f"Nem sikerült csatlakozni: {self.host}:{self.port}")
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    async def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        # SECURITY: Only explicitly permitted Modbus read operations.
        # All Modbus writes are blocked.
        allowed_methods = {"read_holding_registers", "read_coils"}

        if method not in allowed_methods:
            raise WavinWTC3Error(
                f"SECURITY: Modbus operation blocked: {method}"
            )

        client = await self._ensure_client()
        func = getattr(client, method)
        try:
            result = await func(*args, slave=self.slave_id, **kwargs)
        except TypeError:
            result = await func(*args, device_id=self.slave_id, **kwargs)
        if hasattr(result, "isError") and result.isError():
            raise WavinWTC3Error(f"Modbus hiba: {method} {args}: {result}")
        return result

    async def read_holding(self, start: int, count: int) -> list[int]:
        async with self._lock:
            result = await self._call("read_holding_registers", self._addr(start), count=count)
        return list(result.registers)

    async def read_holding_chunked(self, start: int, count: int, chunk_size: int = 15) -> list[int]:
        """Read holding registers in small chunks.

        WTC-NET answers reliably to shorter Modbus TCP requests, while larger
        requests (for example all 7 TH blocks = 42 registers) may time out or
        leave late frames in pymodbus' receive buffer.
        """
        values: list[int] = []
        remaining = int(count)
        current = int(start)
        while remaining > 0:
            size = min(int(chunk_size), remaining)
            values.extend(await self.read_holding(current, size))
            current += size
            remaining -= size
            # Give the WTC-NET bridge a tiny breathing room between frames.
            await asyncio.sleep(0.05)
        return values

    async def read_coils(self, start: int, count: int) -> list[bool]:
        async with self._lock:
            result = await self._call("read_coils", self._addr(start), count=count)
        return [bool(x) for x in result.bits[:count]]

    async def read_coils_chunked(self, start: int, count: int, chunk_size: int = 16) -> list[bool]:
        """Read coils/discrete bits in small chunks for WTC-NET stability."""
        values: list[bool] = []
        remaining = int(count)
        current = int(start)
        while remaining > 0:
            size = min(int(chunk_size), remaining)
            values.extend(await self.read_coils(current, size))
            current += size
            remaining -= size
            await asyncio.sleep(0.05)
        return values[:count]

    async def write_register(self, address: int, value: int, verify: bool = True) -> None:
        async with self._lock:
            await self._call("write_register", self._addr(address), int(value))
            if verify:
                result = await self._call("read_holding_registers", self._addr(address), count=1)
        if verify and int(result.registers[0]) != int(value):
            raise WavinWTC3Error(f"Visszaellenőrzési hiba: {address} != {value}, olvasott: {result.registers[0]}")

    async def write_coil(
        self,
        address: int,
        value: bool,
        verify_address: int | None = None,
        verify: bool = True,
    ) -> None:
        read_addr = address if verify_address is None else verify_address
        async with self._lock:
            await self._call("write_coil", self._addr(address), bool(value))
            if verify:
                result = await self._call("read_coils", self._addr(read_addr), count=1)
        if verify and bool(result.bits[0]) != bool(value):
            raise WavinWTC3Error(f"Bit visszaellenőrzési hiba: {read_addr} != {value}, olvasott: {result.bits[0]}")

    async def write_setpoint(self, zone: int, kind: str, temperature: float) -> None:
        value = _setpoint_register_value(float(temperature))
        if kind == "cool":
            if not 100 <= value <= 500:
                raise WavinWTC3Error("A hűtési alapjel 10,0 és 50,0 °C között lehet")
            address = REG_SETPOINT_BASE + (zone - 1) * REG_SETPOINT_STRIDE
        elif kind == "heat":
            if not 100 <= value <= 500:
                raise WavinWTC3Error("A fűtési alapjel 10,0 és 50,0 °C között lehet")
            address = REG_SETPOINT_BASE + (zone - 1) * REG_SETPOINT_STRIDE + 1
        elif kind == "economy_heat":
            if not 50 <= value <= 500:
                raise WavinWTC3Error("Az economy fűtési alapjel 5,0 és 50,0 °C között lehet")
            address = REG_SETPOINT_BASE + (zone - 1) * REG_SETPOINT_STRIDE + 2
        elif kind == "economy_cool":
            if not 100 <= value <= 500:
                raise WavinWTC3Error("Az economy hűtési alapjel 10,0 és 50,0 °C között lehet")
            address = REG_ECO_COOL_BASE + zone - 1
        else:
            raise WavinWTC3Error(f"Ismeretlen alapjel típus: {kind}")
        await self.write_register(address, value, verify=True)

    async def write_wheel_offset(self, zone: int, offset: float) -> None:
        """Write the DRT-300 virtual potentiometer offset for a zone.

        Home Assistant temperature changes should behave like turning the room
        unit wheel, not like rewriting the WTC-3 program/reference setpoints.
        The DRT-300 offset is signed and uses 0.1 °C units.  The default Wavin
        room-unit adjustment range is +/- 6 °C, so we clamp to that range.
        """
        offset = max(WHEEL_OFFSET_MIN, min(WHEEL_OFFSET_MAX, round(float(offset))))
        value = _wheel_position_from_offset(offset)
        address = REG_WHEEL_WRITE_BASE + zone - 1
        # The writable DRT-300 wheel registers are 4604..4610 and expect
        # the physical wheel position code, not a signed 0.1 °C value:
        # 0 = far left (-6 °C), 6 = centre (0 °C), 12 = far right (+6 °C).
        await self.write_register(address, value, verify=False)

    async def set_zone_on(self, zone: int, value: bool) -> None:
        await self.write_coil(COIL_ZONE_WRITE_BASE + (zone - 1) * COIL_ZONE_WRITE_STRIDE, value,
                              verify_address=COIL_ZONE_STATUS_BASE + (zone - 1) * COIL_ZONE_STATUS_STRIDE + 4)

    async def set_zone_comfort(self, zone: int, value: bool) -> None:
        await self.write_coil(COIL_ZONE_WRITE_BASE + (zone - 1) * COIL_ZONE_WRITE_STRIDE + 1, value,
                              verify_address=COIL_ZONE_STATUS_BASE + (zone - 1) * COIL_ZONE_STATUS_STRIDE + 5)

    async def set_zone_cooling(self, zone: int, value: bool) -> None:
        await self.write_coil(COIL_ZONE_WRITE_BASE + (zone - 1) * COIL_ZONE_WRITE_STRIDE + 2, value,
                              verify_address=COIL_ZONE_STATUS_BASE + (zone - 1) * COIL_ZONE_STATUS_STRIDE + 6)

    async def set_zone_locked(self, zone: int, value: bool) -> None:
        """Lock or unlock a DRT-300 room unit.

        The WTC-NET applies the lock command, but the 4186..4192 read-back
        status bits can lag behind or report the previous state immediately
        after writing.  Earlier versions treated that immediate mismatch as a
        hard error, even though the physical lock/unlock action succeeded.
        For lock commands we therefore write the command without immediate
        bit verification and let the coordinator refresh read the actual state.
        """
        await self.write_coil(COIL_LOCK_WRITE_BASE + zone - 1, value, verify_address=None, verify=False)

    async def set_global_on(self, value: bool) -> None:
        await self.write_coil(COIL_GLOBAL_ONOFF, value)

    async def set_global_comfort(self, value: bool) -> None:
        await self.write_coil(COIL_GLOBAL_CE, value)

    async def set_global_cooling(self, value: bool) -> None:
        await self.write_coil(COIL_GLOBAL_HC, value)

    async def read_all(self, zone_count: int) -> WavinState:
        """Read all important WTC registers/coils in WTC-NET-safe chunks."""
        state = WavinState()

        regs_4121 = await self.read_holding_chunked(4121, 15)
        def r(addr: int) -> int | None:
            idx = addr - 4121
            return regs_4121[idx] if 0 <= idx < len(regs_4121) else None

        state.water_temp = _temp(r(4121))
        state.wtc_humidity = _pct(r(4127))
        state.wtc_room_temp = _temp(r(4128))
        state.pi_output = _pct(r(4132))
        state.dewpoint = _temp(r(4133))
        state.program_dip = _raw(r(4134))
        state.control_state = _raw(r(4135))

        zone_regs = await self.read_holding_chunked(REG_ZONE_BASE, REG_ZONE_STRIDE * zone_count)
        setpoint_regs = await self.read_holding_chunked(REG_SETPOINT_BASE, REG_SETPOINT_STRIDE * zone_count)
        wheel_position_regs = await self.read_holding_chunked(REG_WHEEL_POSITION_BASE, 4)
        eco_cool_regs = await self.read_holding_chunked(REG_ECO_COOL_BASE, zone_count)

        try:
            fw_regs = await self.read_holding(REG_FIRMWARE, 4)
            firmware_raw = fw_regs[0]
            state.firmware = f"{firmware_raw // 100}.{firmware_raw % 100:02d}"
            state.serial = (fw_regs[2] << 16) | fw_regs[1]
        except WavinWTC3Error as err:
            _LOGGER.debug("Firmware/serial read skipped: %s", err)

        global_bits = await self.read_coils_chunked(COIL_GLOBAL_ONOFF, 3)
        state.global_on, state.global_comfort, state.global_cooling = global_bits
        
        status_bits = await self.read_coils_chunked(COIL_ZONE_STATUS_BASE, COIL_ZONE_STATUS_STRIDE * zone_count)
        lock_bits = await self.read_coils_chunked(COIL_LOCK_READ_BASE, zone_count)
        fault_bits = await self.read_coils_chunked(COIL_HEAT_OUT, 7)
        state.heat_output = fault_bits[0]
        state.cool_output = fault_bits[1]
        state.emergency_water_temp = fault_bits[5]
        state.water_sensor_fault = fault_bits[6]

        for zone in range(1, zone_count + 1):
            z = ZoneState(index=zone)
            zi = (zone - 1) * REG_ZONE_STRIDE
            z.temperature = _temp(zone_regs[zi])
            z.humidity = _pct(zone_regs[zi + 1])
            z.dewpoint = _temp(zone_regs[zi + 2])
            z.wheel_offset = _temp(zone_regs[zi + 3])
            z.dewpoint_resistance = _raw(zone_regs[zi + 4])
            z.lux = _raw(zone_regs[zi + 5])

            si = (zone - 1) * REG_SETPOINT_STRIDE
            z.cool_setpoint = _setpoint_temp(setpoint_regs[si])
            z.heat_setpoint = _setpoint_temp(setpoint_regs[si + 1])
            z.economy_heat_setpoint = _setpoint_temp(setpoint_regs[si + 2])
            z.economy_cool_setpoint = _setpoint_temp(eco_cool_regs[zone - 1])
            z.wheel_position = _decode_wheel_position_words(wheel_position_regs, zone)
            wheel_position_offset = _wheel_offset_from_position(z.wheel_position)
            if wheel_position_offset is not None:
                z.wheel_offset = wheel_position_offset

            bi = (zone - 1) * COIL_ZONE_STATUS_STRIDE
            z.dry = status_bits[bi]
            z.output = status_bits[bi + 1]
            z.condensation = status_bits[bi + 2]
            z.dwp_input = status_bits[bi + 3]
            z.on = status_bits[bi + 4]
            z.comfort = status_bits[bi + 5]
            z.cooling = status_bits[bi + 6]
            z.live = status_bits[bi + 7]
            z.locked = lock_bits[zone - 1]
            state.zones[zone] = z

        return state
