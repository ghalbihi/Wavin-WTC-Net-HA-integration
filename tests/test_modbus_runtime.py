"""Runtime tests for the Wavin Modbus read-only guard."""

import ast
import asyncio
import copy
import types
import unittest

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock


API_FILE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "wavin_wtc3"
    / "api.py"
)


class WavinWTC3Error(Exception):
    pass


def load_call_method():
    """Load the actual _call method without connecting to hardware."""

    tree = ast.parse(API_FILE.read_text(encoding="utf-8"))

    api_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "WavinWTC3Api"
    )

    method = next(
        node for node in api_class.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "_call"
    )

    module = ast.Module(
        body=[copy.deepcopy(method)],
        type_ignores=[],
    )

    ast.fix_missing_locations(module)

    namespace = {
        "Any": Any,
        "WavinWTC3Error": WavinWTC3Error,
    }

    exec(compile(module, str(API_FILE), "exec"), namespace)

    return namespace["_call"]


class TestModbusRuntime(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.client = types.SimpleNamespace()

        self.client.read_holding_registers = AsyncMock(
            return_value=types.SimpleNamespace(
                isError=lambda: False,
                registers=[123],
            )
        )

        self.client.read_coils = AsyncMock(
            return_value=types.SimpleNamespace(
                isError=lambda: False,
                bits=[True],
            )
        )

        for method in (
            "write_register",
            "write_registers",
            "write_coil",
            "write_coils",
            "mask_write_register",
        ):
            setattr(self.client, method, AsyncMock())

        self.api = types.SimpleNamespace(
            slave_id=1,
            _ensure_client=AsyncMock(return_value=self.client),
        )

        self.call = types.MethodType(
            load_call_method(),
            self.api,
        )

    async def test_register_read_allowed(self):
        await self.call(
            "read_holding_registers",
            4121,
            count=1,
        )

        self.client.read_holding_registers.assert_awaited_once()

    async def test_coil_read_allowed(self):
        await self.call(
            "read_coils",
            4127,
            count=1,
        )

        self.client.read_coils.assert_awaited_once()

    async def test_all_writes_blocked(self):

        forbidden = (
            "write_register",
            "write_registers",
            "write_coil",
            "write_coils",
            "mask_write_register",
        )

        for method in forbidden:
            with self.subTest(method=method):

                with self.assertRaises(WavinWTC3Error):
                    await self.call(method, 4129, True)

                getattr(
                    self.client, method
                ).assert_not_awaited()

        self.api._ensure_client.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
