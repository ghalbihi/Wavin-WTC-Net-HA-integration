# Changelog

## [1.0.3] - 2026-10-17

### Security
- Added a read-only Modbus operation allowlist.
- Blocked all Modbus write operations.
- Removed automatic setpoint writes during polling.
- Prevented Home Assistant from changing global
  heating/cooling, comfort/economy and ON/OFF settings
  through the existing Wavin API.

### Notes
- Initial read-only version for testing.
- Temperature and system status monitoring only.
- Setpoint control intentionally disabled.
- Not yet validated on the target WTC-3 hardware.

## [1.0.2] - 2026-09-30

### Fixed
- Corrected the forced heating comfort/reference register value from raw 260 to raw 250.
- Field verification showed raw 260 displays 26 °C on the physical DRT-300 with the wheel centred; raw 250 is required for a physical 25 °C centre.
- Home Assistant heating centre remains 25 °C; Economy behaviour remains untouched.

## [1.0.1] - 2026-09-30

### Fixed
- Heating comfort/reference setpoint is now continuously kept at 25.0 °C for every configured TH zone while the WTC-3 is in heating mode.
- Home Assistant heating target changes now use 25 °C as the DRT-300 wheel centre, so 25 °C = centre, 24 °C = -1 and 26 °C = +1.
- Removed the duplicated cooling setpoint enforcement block and duplicated cooling constant.

### Unchanged
- Cooling keeps the existing fixed-reference/wheel behaviour.
- Economy setpoints are not forced or modified.

## [1.0.0] - Stable release

- Stable 1.0 release based on the verified v0.4.8 functionality.
- Version bumped to `1.0.0`.

## [0.4.8] - DRT-300 lock verification fix

### Fixed
- DRT-300 thermostat lock/unlock commands no longer fail in Home Assistant when the WTC-NET read-back bit still shows the previous value immediately after a successful write.
- Lock state is refreshed through the normal coordinator read-back instead of treating the immediate 4186..4192 status bit mismatch as a hard error.

## [0.4.8] - Target read-back refresh after DRT-300 wheel change

### Changed
- After a Home Assistant target temperature change, the integration still debounces rapid changes for 3 seconds and writes only the final value.
- After writing the DRT-300 wheel position, the integration waits another 3 seconds and then forces an immediate Home Assistant refresh outside the normal 30 second polling cycle.
- This makes the displayed target temperature update from the read-back wheel/potmeter value instead of waiting for the next scheduled poll.


## v0.4.8

- Javítva: a DRT-300 potméter állítás most a 4604–4610 wheel pozíció regiszterekbe 0..12 kódot ír.
- A climate target hőmérséklet kijelzése a kiolvasott potméter/wheel pozíció alapján történik.
- Hőmérséklet módosításnál 3 másodperces debounce került be; gyors egymás utáni módosításoknál csak a végső érték kerül kiírásra.
- A hűtési középérték továbbra is 24 °C, fűtési középérték 21 °C.

## 0.4.4

- Fixed options flow opening on existing integrations in newer Home Assistant versions.
- Avoid assigning to the read-only `config_entry` property in the options flow, which caused `500 Internal Server Error` when modifying an existing Wavin WTC-3 configuration.

## 0.4.3 - 2026-06-25

### Fixed

- Climate target temperature now includes the current DRT-300 wheel offset, so a local room-unit adjustment is reflected in Home Assistant.
- Home Assistant setpoint writes preserve the current DRT-300 wheel offset by writing the WTC-3 base/reference setpoint as `requested target - wheel offset`.
- Kept whole-degree Home Assistant setpoint steps.

## 0.4.2 - 2026-06-25

### Fixed

- Corrected WTC-NET target temperature display by applying a -1.0 °C compensation when reading room setpoint registers.
- Setpoint writes now apply the matching +1.0 °C Modbus compensation before writing back to WTC-3.

### Changed

- Climate target temperature step changed from 0.5 °C to 1.0 °C.
- Requested target temperatures are rounded to whole degrees before writing.

## 0.4.1 - 2026-06-25

### Fixed

- Updated all GitHub repository links to `https://github.com/trtk/Wavin-WTC-Net-HA-integration`.
- Updated README badge links and HACS custom repository URL.
- Updated manifest documentation and issue tracker URLs.

## 0.4.0 - 2026-06-24

- Version bumped to `0.4.0`.
- HACS/GitHub release package refreshed.

## 0.2.1

- Fixed HACS validation: removed unsupported `domains` and `iot_class` keys from `hacs.json`.
- Added local brand assets under `custom_components/wavin_wtc3/brand/`.
- Updated manifest version to `0.2.1`.

A projekt [Semantic Versioning](https://semver.org/) szerinti verziózást használ: `MAJOR.MINOR.PATCH`.

## 0.2.0 - 2026-06-24

### Added

- HACS-kompatibilis repository struktúra.
- `hacs.json` metadata.
- GitHub Actions ellenőrzések:
  - HACS validation
  - Hassfest validation
- GitHub release workflow.
- Issue template-ek és pull request template.
- `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `CODEOWNERS`.

### Changed

- Manifest verzió: `0.2.0`.
- Dokumentáció frissítve HACS telepítési lépésekkel és release/tag szabályokkal.

## 0.1.3 - 2026-06-24

### Changed

- A climate célhőmérséklet állítása 0,5 °C-os lépésekben történik.
- Írás előtt az integráció 0,5 °C-ra kerekíti a kért alapjelet.

## 0.1.2 - 2026-06-24

### Added

- Zónánként külön Home Assistant device, így TH1–TH7 külön Area-ba osztható.
- Fix 30 másodperces polling minden kiolvasott adatra.

### Changed

- Ismert kódok szöveges megjelenítése.
- Kódérték csak ott marad, ahol a Wavin dokumentáció nem ad jelentéstáblát.

## 0.1.1 - 2026-06-24

### Fixed

- Nagy Modbus read blokkok bontása kisebb lekérdezésekre a WTC-NET stabilitása miatt.

## 0.1.0 - 2026-06-24

### Added

- Első natív Home Assistant custom integration Wavin WTC-3 / WTC-NET rendszerhez.
- UI config flow.
- 1–7 konfigurálható TH zóna.
- Modbus TCP olvasás/írás.
- Climate, sensor és switch entity-k.
- Írás utáni visszaolvasásos ellenőrzés.
