"""Isolated runtime assertions using actual method bodies and mock Modbus client."""
import ast, asyncio, copy, types, unittest
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock
API_FILE=Path(__file__).resolve().parents[1]/"custom_components"/"wavin_wtc3"/"api.py"
class WavinWTC3Error(Exception):pass
class Dummy:
    pass
def load_methods(enabled):
    tree=ast.parse(API_FILE.read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="WavinWTC3Api")
    methods=[copy.deepcopy(n) for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name in ("_call","set_safe_target")]
    module=ast.Module(body=methods,type_ignores=[]);ast.fix_missing_locations(module)
    env={"Any":Any,"WavinWTC3Error":WavinWTC3Error,"WAVIN_ALLOW_SETPOINT_WRITES":enabled,"DRT300_VERIFIED_HEAT_CENTER":21.0,"REG_CONTROL_STATE":4135,"COIL_ZONE_STATUS_BASE":4130,"COIL_ZONE_STATUS_STRIDE":8,"REG_WHEEL_WRITE_BASE":4604,"WAVIN_ALLOWED_WRITE_ZONES":(1,2,3)}
    exec(compile(module,str(API_FILE),"exec"),env)
    return env
class TestGuard(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env=load_methods(True)
        self.client=types.SimpleNamespace(read_coils=AsyncMock(),read_holding_registers=AsyncMock(),write_register=AsyncMock(),write_coil=AsyncMock(),write_registers=AsyncMock())
        self.api=Dummy();self.api.slave_id=1;self.api.address_offset=0;self.api._lock=asyncio.Lock();self.api._ensure_client=AsyncMock(return_value=self.client)
        self.api._call=types.MethodType(self.env['_call'],self.api)
        self.api.set_safe_target=types.MethodType(self.env['set_safe_target'],self.api)
        self.client.read_coils.side_effect=[types.SimpleNamespace(bits=[True,True,False],isError=lambda:False),types.SimpleNamespace(bits=[True,True,False,True],isError=lambda:False)]
        self.client.read_holding_registers.return_value=types.SimpleNamespace(registers=[1],isError=lambda:False)
        self.client.write_register.return_value=types.SimpleNamespace(isError=lambda:False)
    async def test_direct_write_denied(self):
        with self.assertRaises(WavinWTC3Error):await self.api._call("write_register",4604,6)
        self.client.write_register.assert_not_awaited()
    async def test_other_write_methods_denied(self):
        for name in ("write_coil","write_registers","mask_write_register"):
            with self.subTest(name=name),self.assertRaises(WavinWTC3Error):await self.api._call(name,4604,6)
    async def test_restricted_write_once(self):
        await self.api.set_safe_target(2,23,3)
        self.client.write_register.assert_awaited_once_with(4605,8,slave=1)
        self.assertFalse(getattr(self.api,'_authorized_wheel_write',False))
    async def test_bad_targets_rejected(self):
        for target in (14,28,21.5,True):
            with self.subTest(target=target),self.assertRaises(WavinWTC3Error):await self.api.set_safe_target(1,target,3)
        self.client.write_register.assert_not_awaited()
    async def test_offset_guard(self):
        self.api.address_offset=-1
        with self.assertRaises(WavinWTC3Error):await self.api.set_safe_target(2,22,3)
        self.client.write_register.assert_not_awaited()
    async def test_global_economy_blocks(self):
        self.client.read_coils.side_effect=[types.SimpleNamespace(bits=[True,False,False],isError=lambda:False)]
        with self.assertRaises(WavinWTC3Error):await self.api.set_safe_target(2,22,3)
        self.client.write_register.assert_not_awaited()
    async def test_zone_economy_blocks(self):
        self.client.read_coils.side_effect=[types.SimpleNamespace(bits=[True,True,False],isError=lambda:False),types.SimpleNamespace(bits=[True,False,False,True],isError=lambda:False)]
        with self.assertRaises(WavinWTC3Error):await self.api.set_safe_target(2,22,3)
        self.client.write_register.assert_not_awaited()
    async def test_all_three_zone_addresses(self):
        for zone in (1, 2, 3):
            with self.subTest(zone=zone):
                self.client.write_register.reset_mock()
                self.client.read_coils.side_effect = [
                    types.SimpleNamespace(bits=[True,True,False],isError=lambda:False),
                    types.SimpleNamespace(bits=[True,True,False,True],isError=lambda:False),
                ]
                await self.api.set_safe_target(zone, 23, 3)
                self.client.write_register.assert_awaited_once_with(4603 + zone, 8, slave=1)
                self.assertFalse(getattr(self.api, '_authorized_wheel_write', False))

    async def test_outside_configured_zones_rejected(self):
        for zone in (0, 4, -1):
            with self.subTest(zone=zone), self.assertRaises(WavinWTC3Error):
                await self.api.set_safe_target(zone, 23, 3)
        self.client.write_register.assert_not_awaited()
    async def test_default_disabled(self):
        env=load_methods(False)
        disabled=types.MethodType(env['set_safe_target'],self.api)
        with self.assertRaises(WavinWTC3Error):await disabled(2,22,3)
        self.client.write_register.assert_not_awaited()
if __name__=='__main__':unittest.main()
