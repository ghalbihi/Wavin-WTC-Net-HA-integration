"""Security regression checks for the opt-in heating controls."""
import ast
import unittest
from pathlib import Path
BASE = Path(__file__).resolve().parents[1] / "custom_components" / "wavin_wtc3"
class SecurityChecks(unittest.TestCase):
    def test_restricted_platforms(self):
        tree=ast.parse((BASE / "const.py").read_text())
        values={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ("PLATFORMS","WAVIN_ALLOW_SETPOINT_WRITES","WAVIN_ALLOWED_WRITE_ZONES","COIL_PUMP_OUT")}
        self.assertEqual(values["PLATFORMS"],["sensor","binary_sensor","number"])
        self.assertIs(values["WAVIN_ALLOW_SETPOINT_WRITES"],True)
        self.assertEqual(values["WAVIN_ALLOWED_WRITE_ZONES"],(1,2,3))
        self.assertEqual(values["COIL_PUMP_OUT"],4119)
    def test_write_methods_locked(self):
        source=(BASE / "api.py").read_text()
        self.assertIn('if method == "write_register":',source)
        self.assertIn('address not in (4604, 4605, 4606)',source)
        self.assertIn('getattr(self, "_authorized_wheel_write", False)',source)
        self.assertIn('self.address_offset != 0',source)
        self.assertIn('if not WAVIN_ALLOW_SETPOINT_WRITES:',source)
    def test_polling_contains_no_writes(self):
        tree=ast.parse((BASE / "api.py").read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="WavinWTC3Api")
        polling=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=="read_all")
        calls=[n.func.attr for n in ast.walk(polling) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertFalse(set(calls)&{"write_register","write_coil","set_safe_target","write_wheel_offset"})
    def test_no_control_platform(self):
        src=(BASE / "const.py").read_text()
        self.assertNotIn('"climate"',src.split('PLATFORMS = ',1)[1].splitlines()[0])
        self.assertNotIn('"switch"',src.split('PLATFORMS = ',1)[1].splitlines()[0])
    def test_targets_and_zone_status(self):
        src=(BASE / "sensor.py").read_text()
        self.assertIn('"zone_comfort_status"',src)
        self.assertIn('"active_heat_target"',src)
if __name__=='__main__':unittest.main()
