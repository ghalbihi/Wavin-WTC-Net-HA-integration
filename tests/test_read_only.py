"""Security regression tests for the Wavin read-only API."""

import ast
import unittest
from pathlib import Path


API_FILE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "wavin_wtc3"
    / "api.py"
)


class TestReadOnlySecurity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = API_FILE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

        cls.api_class = next(
            node for node in cls.tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "WavinWTC3Api"
        )

        cls.call_method = next(
            node for node in cls.api_class.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "_call"
        )

    def test_allowed_methods_are_read_only(self):
        """Only approved Modbus read methods may be allowed."""

        allowed = None

        for node in ast.walk(self.call_method):
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name)
                    and target.id == "allowed_methods"
                    for target in node.targets
                )
            ):
                allowed = ast.literal_eval(node.value)

        self.assertEqual(
            allowed,
            {"read_holding_registers", "read_coils"},
        )

    def test_write_methods_are_blocked(self):
        """All write operations must be rejected by _call."""

        guard_found = False

        for node in self.call_method.body:
            if not isinstance(node, ast.If):
                continue

            test = node.test

            if not isinstance(test, ast.Compare):
                continue

            if not (
                isinstance(test.left, ast.Name)
                and test.left.id == "method"
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.NotIn)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Name)
                and test.comparators[0].id == "allowed_methods"
            ):
                continue

            if any(
                isinstance(child, ast.Raise)
                for child in node.body
            ):
                guard_found = True

        self.assertTrue(
            guard_found,
            "Missing read-only security guard in _call()",
        )

    def test_no_direct_modbus_write_calls(self):
        """No direct Modbus writes may bypass the API guard."""

        forbidden = {
            "write_register",
            "write_registers",
            "write_coil",
            "write_coils",
        }

        for node in ast.walk(self.api_class):
            if not isinstance(node, ast.Call):
                continue

            func = node.func

            if not isinstance(func, ast.Attribute):
                continue

            if func.attr not in forbidden:
                continue

            if (
                isinstance(func.value, ast.Name)
                and func.value.id == "self"
            ):
                continue

            self.fail(
                f"Possible direct Modbus write: {func.attr}"
            )

    def test_no_automatic_writes_during_polling(self):
        """Periodic polling must not request write operations."""

        read_all = next(
            node for node in self.api_class.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "read_all"
        )

        forbidden_calls = {
            "write_register",
            "write_coil",
            "write_setpoint",
            "write_wheel_offset",
            "set_global_on",
            "set_global_comfort",
            "set_global_cooling",
            "set_zone_on",
            "set_zone_comfort",
            "set_zone_cooling",
            "set_zone_locked",
        }

        for node in ast.walk(read_all):
            if not isinstance(node, ast.Call):
                continue

            func = node.func

            if isinstance(func, ast.Attribute):
                self.assertNotIn(
                    func.attr,
                    forbidden_calls,
                    f"Write operation in read_all(): {func.attr}",
                )


if __name__ == "__main__":
    unittest.main()
