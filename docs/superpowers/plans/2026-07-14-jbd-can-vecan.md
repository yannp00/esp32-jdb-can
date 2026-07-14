# jbd-can-vecan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second ESPHome firmware variant (`jbd-can-vecan.yaml`) that emulates the REC BMS
protocol on a 250 kbps VE.Can bus, so a Safiery Scotty AI and an optional Victron Cerbo GX can share
one physical CAN bus with the JBD BMS — without disturbing the existing 500 kbps `jbd-can-bridge.yaml`.

**Architecture:** Extract everything shared between the two firmwares (BMS UART read, sensors,
watchdog, wifi/ota/logger) into `common.yaml`, included via ESPHome `packages:` from both top-level
files. Each top-level file keeps only its `canbus:` block and its own `interval:` lambda that builds
and sends protocol-specific CAN frames.

**Tech Stack:** ESPHome (esp-idf framework), esp32_can component, C++ lambdas inline in YAML.

## Global Constraints

- Byte layouts for 0x351/0x355/0x356/0x35A/0x373/0x35E: exact scales and bit positions specified in
  `docs/superpowers/specs/2026-07-14-jbd-can-vecan-design.md`, cross-checked against
  [`lltjbd_can.py`](https://github.com/mr-manuel/venus-os_dbus-serialbattery/blob/master/dbus-serialbattery/bms/lltjbd_can.py).
  Do not deviate from these without re-checking that source.
- `jbd-can-bridge.yaml` must keep identical runtime behavior after the Task 1 refactor — verified via
  a full `esphome config` output diff, not just "it compiles."
- Substitution names in `jbd-can-vecan.yaml`: `charge_current_limit_a`, `discharge_current_limit_a`,
  `cell_taper_start_v`, `cell_taper_end_v` — exact names, used verbatim in later tasks' lambda code.
- CCL/DCL alarm-zero bit masks are scoped exactly as approved in the spec — do not add extra
  conditions (e.g. overcurrent, short-circuit) to the CCL/DCL zeroing logic; those stay in-scope only
  for the 0x35A alarm frame.
- All `esphome config` / `esphome compile` commands below run via `python -m esphome` (the `esphome`
  binary is not on PATH in this environment, but the Python module is installed and confirmed working).
- `secrets.yaml` already exists locally (gitignored) with `wifi_ssid` / `wifi_password` — required for
  every `esphome config`/`compile` run in this plan.

---

## File Structure

```
common.yaml           ← NEW: esp32/wifi/ota/logger, UART+jbd_bms, all sensors (with explicit ids on
                         all 16 cell voltages), watchdog global
jbd-can-bridge.yaml    ← MODIFIED: refactored to include common.yaml via packages:, keeps its own
                         esphome:/canbus:/interval: (500kbps, Pylontech-style frames) — behavior
                         unchanged
jbd-can-vecan.yaml     ← NEW: includes common.yaml via packages:, own esphome:/canbus:/interval:
                         (250kbps, REC-BMS-style frames)
can-listener.yaml      ← MODIFIED: debug listener adapted to 250kbps + new frame set
README.md              ← MODIFIED: document the new variant, wiring reuse, Cerbo VE.Can mode
```

---

### Task 1: Extract `common.yaml`, refactor `jbd-can-bridge.yaml`

**Files:**
- Create: `common.yaml`
- Modify: `jbd-can-bridge.yaml`

**Interfaces:**
- Produces: sensor ids consumed by later tasks — `bms_soc`, `bms_voltage`, `bms_current`, `bms_temp1`,
  `bms_temp2`, `bms_errors`, `cell_v1`..`cell_v16` (all 16 cells now have explicit `id:`, only
  `cell_v1` had one before), global `last_bms_update_ms`.

- [ ] **Step 1: Capture baseline resolved config**

```bash
cd "C:\Users\yport\Documents\Projects\esp32-jdb-can"
python -m esphome config jbd-can-bridge.yaml > "$TMPDIR/before_bridge.txt" 2>&1
tail -5 "$TMPDIR/before_bridge.txt"
```
Expected: last line `INFO Configuration is valid!` (confirms current baseline still validates before
touching anything).

- [ ] **Step 2: Create `common.yaml`**

```yaml
esp32:
  board: esp32dev
  framework:
    type: esp-idf

captive_portal:

web_server:
  port: 80

logger:

api:

ota:
  - platform: esphome
    password: "ota-password"

globals:
  - id: last_bms_update_ms
    type: uint32_t
    restore_value: false
    initial_value: '0'

uart:
  - id: jbd_uart
    tx_pin: GPIO17
    rx_pin: GPIO16
    baud_rate: 9600

external_components:
  - source: github://syssi/esphome-jbd-bms@main

jbd_bms:
  - id: bms0
    uart_id: jbd_uart
    update_interval: 5s

sensor:
  - platform: jbd_bms
    jbd_bms_id: bms0
    state_of_charge:
      name: "BMS SOC"
      id: bms_soc
    total_voltage:
      name: "BMS Voltage"
      id: bms_voltage
      on_value:
        then:
          - lambda: 'id(last_bms_update_ms) = millis();'
    current:
      name: "BMS Current"
      id: bms_current
    power:
      name: "BMS Power"
    temperature_1:
      name: "BMS Temperature 1"
      id: bms_temp1
    temperature_2:
      name: "BMS Temperature 2"
      id: bms_temp2
    cell_voltage_1:
      name: "Cell 1"
      id: cell_v1
    cell_voltage_2:
      name: "Cell 2"
      id: cell_v2
    cell_voltage_3:
      name: "Cell 3"
      id: cell_v3
    cell_voltage_4:
      name: "Cell 4"
      id: cell_v4
    cell_voltage_5:
      name: "Cell 5"
      id: cell_v5
    cell_voltage_6:
      name: "Cell 6"
      id: cell_v6
    cell_voltage_7:
      name: "Cell 7"
      id: cell_v7
    cell_voltage_8:
      name: "Cell 8"
      id: cell_v8
    cell_voltage_9:
      name: "Cell 9"
      id: cell_v9
    cell_voltage_10:
      name: "Cell 10"
      id: cell_v10
    cell_voltage_11:
      name: "Cell 11"
      id: cell_v11
    cell_voltage_12:
      name: "Cell 12"
      id: cell_v12
    cell_voltage_13:
      name: "Cell 13"
      id: cell_v13
    cell_voltage_14:
      name: "Cell 14"
      id: cell_v14
    cell_voltage_15:
      name: "Cell 15"
      id: cell_v15
    cell_voltage_16:
      name: "Cell 16"
      id: cell_v16
    errors_bitmask:
      name: "BMS Errors"
      id: bms_errors
```

- [ ] **Step 3: Rewrite `jbd-can-bridge.yaml` to consume `common.yaml`**

Replace the entire file content with:

```yaml
esphome:
  name: jbd-can-bridge

packages:
  common: !include common.yaml

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "jbd-can-bridge"
    password: "jbd-can-bridge"

canbus:
  - platform: esp32_can
    tx_pin: GPIO23
    rx_pin: GPIO22
    can_id: 0
    bit_rate: 500kbps
    id: can_bus
    on_frame:
      - can_id: 0x000
        can_id_mask: 0x000
        then:
          - lambda: |-
              ESP_LOGI("canrx", "Frame reçue id=0x%03X len=%d", can_id, x.size());

interval:
  - interval: 1s
    then:
      - lambda: |-
          // Watchdog: données BMS
          float soc     = id(bms_soc).state;
          float voltage = id(bms_voltage).state;
          float current = id(bms_current).state;
          float temp    = id(bms_temp1).state;
          float errors  = id(bms_errors).state;

          // Arrêt si données jamais reçues
          if (isnan(soc) || isnan(voltage)) {
            ESP_LOGW("pylontech", "Données BMS invalides, trames CAN non émises");
            return;
          }

          // Arrêt si données trop anciennes (>10s sans mise à jour du BMS)
          if (id(last_bms_update_ms) > 0 && (millis() - id(last_bms_update_ms) > 10000)) {
            ESP_LOGW("pylontech", "BMS silencieux depuis >10s, trames CAN suspendues");
            return;
          }

          // --- 0x351 : Limites tension/courant ---
          uint16_t cvl = 584;
          uint16_t ccl = 50;
          uint16_t dcl = 100;
          uint16_t dvl = 448;
          std::vector<uint8_t> f351 = {
            (uint8_t)(cvl & 0xFF), (uint8_t)(cvl >> 8),
            (uint8_t)(ccl & 0xFF), (uint8_t)(ccl >> 8),
            (uint8_t)(dcl & 0xFF), (uint8_t)(dcl >> 8),
            (uint8_t)(dvl & 0xFF), (uint8_t)(dvl >> 8)
          };
          id(can_bus).send_data(0x351, false, false, f351);

          // --- 0x355 : SOC / SOH ---
          uint16_t soc_i = (uint16_t)soc;
          uint16_t soh_i = 100;
          std::vector<uint8_t> f355 = {
            (uint8_t)(soc_i & 0xFF), (uint8_t)(soc_i >> 8),
            (uint8_t)(soh_i & 0xFF), (uint8_t)(soh_i >> 8)
          };
          id(can_bus).send_data(0x355, false, false, f355);

          // --- 0x356 : Tension / Courant / Température ---
          int16_t v_raw = (int16_t)(voltage * 100);
          int16_t i_raw = (int16_t)(current * 10);
          int16_t t_raw = (int16_t)(temp * 10);
          std::vector<uint8_t> f356 = {
            (uint8_t)(v_raw & 0xFF), (uint8_t)((uint16_t)v_raw >> 8),
            (uint8_t)(i_raw & 0xFF), (uint8_t)((uint16_t)i_raw >> 8),
            (uint8_t)(t_raw & 0xFF), (uint8_t)((uint16_t)t_raw >> 8)
          };
          id(can_bus).send_data(0x356, false, false, f356);

          // --- 0x359 : Alarmes et protections ---
          uint32_t err = (uint32_t)errors;
          uint8_t alarm0 = 0x00;
          uint8_t alarm1 = 0x00;
          if (err & 0x0001) alarm0 |= 0x04;
          if (err & 0x0002) alarm0 |= 0x08;
          if (err & 0x0004) alarm1 |= 0x01;
          if (err & 0x0008) alarm1 |= 0x02;
          if (err & 0x0100) alarm1 |= 0x04;
          std::vector<uint8_t> f359 = {alarm0, alarm1, 0x00, 0x00};
          id(can_bus).send_data(0x359, false, false, f359);

          // --- 0x35C : Flags demande de charge ---
          uint8_t req = 0xC0;
          if (err != 0) req = 0x00;
          std::vector<uint8_t> f35c = {req, 0x00};
          id(can_bus).send_data(0x35C, false, false, f35c);

          // --- 0x35E : Nom fabricant "PYLON   " ---
          std::vector<uint8_t> f35e = {'P','Y','L','O','N',' ',' ',' '};
          id(can_bus).send_data(0x35E, false, false, f35e);

          ESP_LOGD("pylontech", "CAN: SOC=%.0f%% V=%.2fV I=%.1fA T=%.1f°C",
                   soc, voltage, current, temp);
```

- [ ] **Step 4: Verify behavior-preserving refactor via config diff**

```bash
cd "C:\Users\yport\Documents\Projects\esp32-jdb-can"
python -m esphome config jbd-can-bridge.yaml > "$TMPDIR/after_bridge.txt" 2>&1
diff "$TMPDIR/before_bridge.txt" "$TMPDIR/after_bridge.txt"
```
Expected: **no differences** except sensor entries for `cell_v2`..`cell_v16` now show an explicit
`id:` field in the dumped config where they previously showed an auto-generated one — this is fine
(cosmetic, `id:` is an internal YAML reference, not the Home Assistant entity id, which is derived
from `name:` and is unchanged). If any other section differs (frame content, watchdog logic, pins,
bit rate), stop and fix before proceeding — that would mean the refactor changed real behavior.

- [ ] **Step 5: Commit**

```bash
git add common.yaml jbd-can-bridge.yaml
git commit -m "refactor: extract common.yaml package from jbd-can-bridge.yaml

Add explicit ids to all 16 cell voltage sensors (needed by the
upcoming jbd-can-vecan variant) and split shared BMS-read/watchdog/
wifi/ota config into common.yaml, included via packages:. No runtime
behavior change, verified via esphome config diff."
```

---

### Task 2: Scaffold `jbd-can-vecan.yaml`

**Files:**
- Create: `jbd-can-vecan.yaml`

**Interfaces:**
- Consumes: `common.yaml` (Task 1) — sensor ids `bms_soc`, `bms_voltage`, `bms_current`, `bms_temp1`,
  `bms_temp2`, `bms_errors`, `cell_v1`..`cell_v16`, global `last_bms_update_ms`.
- Produces: `substitutions` block with `charge_current_limit_a`, `discharge_current_limit_a`,
  `cell_taper_start_v`, `cell_taper_end_v` — used verbatim by Task 3.

- [ ] **Step 1: Write the scaffold**

Note : ESPHome rejette les noms d'appareil contenant des majuscules (validateur `name`),
d'où `jbd_battery` en minuscules au lieu de la casse initialement demandée (`JBD_BATTERY`).

```yaml
esphome:
  name: "jbd_battery"

packages:
  common: !include common.yaml

substitutions:
  charge_current_limit_a: "50"
  discharge_current_limit_a: "100"
  cell_taper_start_v: "3.45"
  cell_taper_end_v: "3.65"

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "jbd-can-vecan"
    password: "jbd-can-vecan"

canbus:
  - platform: esp32_can
    tx_pin: GPIO23
    rx_pin: GPIO22
    can_id: 0
    bit_rate: 250kbps
    id: can_bus
    on_frame:
      - can_id: 0x000
        can_id_mask: 0x000
        then:
          - lambda: |-
              ESP_LOGI("canrx", "Frame reçue id=0x%03X len=%d", can_id, x.size());

interval:
  - interval: 1s
    then:
      - lambda: |-
          // Watchdog: données BMS
          float soc     = id(bms_soc).state;
          float voltage = id(bms_voltage).state;
          float current = id(bms_current).state;
          float errors  = id(bms_errors).state;

          if (isnan(soc) || isnan(voltage)) {
            ESP_LOGW("recbms", "Données BMS invalides, trames CAN non émises");
            return;
          }

          if (id(last_bms_update_ms) > 0 && (millis() - id(last_bms_update_ms) > 10000)) {
            ESP_LOGW("recbms", "BMS silencieux depuis >10s, trames CAN suspendues");
            return;
          }

          uint32_t err = (uint32_t)errors;

          ESP_LOGD("recbms", "CAN: SOC=%.0f%% V=%.2fV I=%.1fA", soc, voltage, current);
```

- [ ] **Step 2: Validate config**

```bash
cd "C:\Users\yport\Documents\Projects\esp32-jdb-can"
python -m esphome config jbd-can-vecan.yaml
```
Expected: ends with `INFO Configuration is valid!`, no errors about missing pins/substitutions.

- [ ] **Step 3: Full compile (catches lambda C++ errors, ESP-IDF build)**

```bash
python -m esphome compile jbd-can-vecan.yaml
```
Expected: build succeeds (`SUCCESS` / non-zero exit only on real errors). This is the first real C++
compile of the file's lambda, worth doing now before adding frame logic on top of it.

- [ ] **Step 4: Commit**

```bash
git add jbd-can-vecan.yaml
git commit -m "feat: scaffold jbd-can-vecan.yaml (250kbps VE.Can, common.yaml package)"
```

---

### Task 3: 0x351 frame with voltage-tapered CCL and alarm-zeroed DCL

**Files:**
- Modify: `jbd-can-vecan.yaml`

**Interfaces:**
- Produces (local lambda variables, scoped to the `interval:` lambda, reused by Task 6):
  `min_cell_v` (float, Volts), `max_cell_v` (float, Volts).

- [ ] **Step 1: Desk-check the taper formula in a throwaway script**

Write `SCRATCH/taper_check.py` (scratchpad, not committed):

```python
def ccl(max_cell_v, taper_start, taper_end, current_limit, charge_alarm):
    if charge_alarm:
        return 0.0
    ratio = (taper_end - max_cell_v) / (taper_end - taper_start)
    ratio = max(0.0, min(1.0, ratio))
    return current_limit * ratio

cases = [
    (3.30, False, 50.0),   # below taper start -> full current
    (3.55, False, 25.0),   # midpoint -> half current
    (3.65, False, 0.0),    # at taper end -> zero
    (3.70, False, 0.0),    # past taper end (defensive, clamp) -> zero
    (3.30, True, 0.0),     # alarm active overrides everything -> zero
]

for max_v, alarm, expected in cases:
    result = ccl(max_v, 3.45, 3.65, 50.0, alarm)
    status = "OK" if abs(result - expected) < 0.01 else "MISMATCH"
    print(f"max_cell_v={max_v} alarm={alarm} -> ccl={result:.2f}A (expected {expected}) {status}")
```

Run: `python "$SCRATCH_DIR/taper_check.py"`

Expected: all 5 lines print `OK`. If any prints `MISMATCH`, fix the formula here before transcribing
to C++ — do not debug this in embedded lambda code.

- [ ] **Step 2: Add min/max cell voltage computation + 0x351 frame**

In `jbd-can-vecan.yaml`, replace the line `uint32_t err = (uint32_t)errors;` (and everything after it
in the lambda) with:

```yaml
          uint32_t err = (uint32_t)errors;

          // --- Min/Max tension cellule (réutilisé par 0x351 et 0x373) ---
          float cell_v[16] = {
            id(cell_v1).state,  id(cell_v2).state,  id(cell_v3).state,  id(cell_v4).state,
            id(cell_v5).state,  id(cell_v6).state,  id(cell_v7).state,  id(cell_v8).state,
            id(cell_v9).state,  id(cell_v10).state, id(cell_v11).state, id(cell_v12).state,
            id(cell_v13).state, id(cell_v14).state, id(cell_v15).state, id(cell_v16).state,
          };
          float min_cell_v = cell_v[0];
          float max_cell_v = cell_v[0];
          for (int i = 1; i < 16; i++) {
            if (cell_v[i] < min_cell_v) min_cell_v = cell_v[i];
            if (cell_v[i] > max_cell_v) max_cell_v = cell_v[i];
          }

          // --- 0x351 : Limites tension/courant ---
          uint16_t cvl = 584;   // 58.4V, cohérent avec cell_taper_end_v (16S × 3.65V)
          uint16_t dvl = 448;   // 44.8V

          const float charge_current_limit_a = ${charge_current_limit_a};
          const float discharge_current_limit_a = ${discharge_current_limit_a};
          const float cell_taper_start_v = ${cell_taper_start_v};
          const float cell_taper_end_v = ${cell_taper_end_v};

          bool charge_alarm = (err & (1 << 0)) || (err & (1 << 2)) || (err & (1 << 4));
          bool discharge_alarm = (err & (1 << 1)) || (err & (1 << 3)) || (err & (1 << 6));

          float ccl_ratio = (cell_taper_end_v - max_cell_v) / (cell_taper_end_v - cell_taper_start_v);
          if (ccl_ratio < 0.0f) ccl_ratio = 0.0f;
          if (ccl_ratio > 1.0f) ccl_ratio = 1.0f;

          uint16_t ccl = charge_alarm ? 0 : (uint16_t)(charge_current_limit_a * ccl_ratio * 10.0f);
          uint16_t dcl = discharge_alarm ? 0 : (uint16_t)(discharge_current_limit_a * 10.0f);

          std::vector<uint8_t> f351 = {
            (uint8_t)(cvl & 0xFF), (uint8_t)(cvl >> 8),
            (uint8_t)(ccl & 0xFF), (uint8_t)(ccl >> 8),
            (uint8_t)(dcl & 0xFF), (uint8_t)(dcl >> 8),
            (uint8_t)(dvl & 0xFF), (uint8_t)(dvl >> 8)
          };
          id(can_bus).send_data(0x351, false, false, f351);

          ESP_LOGD("recbms", "CAN: SOC=%.0f%% V=%.2fV I=%.1fA maxCell=%.3fV minCell=%.3fV CCL=%.1fA DCL=%.1fA",
                   soc, voltage, current, max_cell_v, min_cell_v,
                   ccl / 10.0f, dcl / 10.0f);
```

- [ ] **Step 3: Validate + compile**

```bash
cd "C:\Users\yport\Documents\Projects\esp32-jdb-can"
python -m esphome config jbd-can-vecan.yaml
python -m esphome compile jbd-can-vecan.yaml
```
Expected: both succeed. If compile fails on the `cell_v[16] = { ... }` array initializer, replace it
with 16 individual assignments (`cell_v[0] = id(cell_v1).state;` etc.) — some ESP-IDF C++ dialects
are stricter about mixed designated/positional init; the array-literal form above is standard C++11
and should work, but this is the one place in this task worth double-checking against the actual
compiler output.

- [ ] **Step 4: Commit**

```bash
git add jbd-can-vecan.yaml
git commit -m "feat: 0x351 frame with cell-voltage-tapered CCL and alarm-zeroed DCL"
```

---

### Task 4: 0x355 (SOC/SOH) and 0x356 (V/I/T) frames

**Files:**
- Modify: `jbd-can-vecan.yaml`

- [ ] **Step 1: Add both frames**

Insert after the `id(can_bus).send_data(0x351, ...)` line (before the `ESP_LOGD` line from Task 3):

```yaml
          // --- 0x355 : SOC / SOH ---
          uint16_t soc_i = (uint16_t)soc;
          uint16_t soh_i = 100;  // JBD ne calcule pas le SOH
          std::vector<uint8_t> f355 = {
            (uint8_t)(soc_i & 0xFF), (uint8_t)(soc_i >> 8),
            (uint8_t)(soh_i & 0xFF), (uint8_t)(soh_i >> 8)
          };
          id(can_bus).send_data(0x355, false, false, f355);

          // --- 0x356 : Tension / Courant / Température ---
          float temp = id(bms_temp1).state;
          int16_t v_raw = (int16_t)(voltage * 100);
          int16_t i_raw = (int16_t)(current * 10);
          int16_t t_raw = (int16_t)(temp * 10);
          std::vector<uint8_t> f356 = {
            (uint8_t)(v_raw & 0xFF), (uint8_t)((uint16_t)v_raw >> 8),
            (uint8_t)(i_raw & 0xFF), (uint8_t)((uint16_t)i_raw >> 8),
            (uint8_t)(t_raw & 0xFF), (uint8_t)((uint16_t)t_raw >> 8)
          };
          id(can_bus).send_data(0x356, false, false, f356);
```

- [ ] **Step 2: Validate + compile**

```bash
cd "C:\Users\yport\Documents\Projects\esp32-jdb-can"
python -m esphome config jbd-can-vecan.yaml
python -m esphome compile jbd-can-vecan.yaml
```
Expected: both succeed.

- [ ] **Step 3: Commit**

```bash
git add jbd-can-vecan.yaml
git commit -m "feat: 0x355 (SOC/SOH) and 0x356 (V/I/T) frames"
```

---

### Task 5: 0x35A alarm frame

**Files:**
- Modify: `jbd-can-vecan.yaml`

- [ ] **Step 1: Add the frame**

Insert after the `id(can_bus).send_data(0x356, ...)` line:

```yaml
          // --- 0x35A : Alarmes/warnings (bits dédiés, cf. lltjbd_can.py) ---
          uint8_t a0 = 0x00, a1 = 0x00, a2 = 0x00;
          if (err & ((1 << 0) | (1 << 2))) a0 |= (1 << 2);  // surtension cellule/pack
          if (err & ((1 << 1) | (1 << 3))) a0 |= (1 << 4);  // sous-tension cellule/pack
          if (err & (1 << 6))              a0 |= (1 << 6);  // surtempérature (décharge)
          if (err & (1 << 7))              a1 |= (1 << 0);  // sous-température (décharge)
          if (err & (1 << 4))              a1 |= (1 << 2);  // surtempérature charge
          if (err & (1 << 5))              a1 |= (1 << 4);  // sous-température charge
          if (err & (1 << 9))              a1 |= (1 << 6);  // surintensité décharge
          if (err & (1 << 8))              a2 |= (1 << 0);  // surintensité charge
          if (err & (1 << 10))             a2 |= (1 << 4);  // court-circuit
          std::vector<uint8_t> f35a = {a0, a1, a2, 0x00, 0x00, 0x00, 0x00, 0x00};
          id(can_bus).send_data(0x35A, false, false, f35a);
```

- [ ] **Step 2: Cross-check the bit table against the spec by hand**

Open `docs/superpowers/specs/2026-07-14-jbd-can-vecan-design.md`, section "Alarmes 0x35A", and confirm
each `if` line above matches a row of that table exactly (same byte, same bit, same source JBD bit).
This is a manual review step — no command to run, but do not skip it: a single wrong shift here means
a real BMS fault could be silently misreported to the Scotty/Cerbo.

- [ ] **Step 3: Validate + compile**

```bash
cd "C:\Users\yport\Documents\Projects\esp32-jdb-can"
python -m esphome config jbd-can-vecan.yaml
python -m esphome compile jbd-can-vecan.yaml
```
Expected: both succeed.

- [ ] **Step 4: Commit**

```bash
git add jbd-can-vecan.yaml
git commit -m "feat: 0x35A alarm frame (dedicated bit per condition, mapped from JBD errors_bitmask)"
```

---

### Task 6: 0x373 (min/max cell voltage + temperature) frame

**Files:**
- Modify: `jbd-can-vecan.yaml`

**Interfaces:**
- Consumes: `min_cell_v`, `max_cell_v` (float, Volts) computed in Task 3.

- [ ] **Step 1: Add the frame**

Insert after the `id(can_bus).send_data(0x35A, ...)` line:

```yaml
          // --- 0x373 : Min/Max tension cellule (mV) + température (Kelvin) ---
          uint16_t min_cell_mv = (uint16_t)(min_cell_v * 1000.0f);
          uint16_t max_cell_mv = (uint16_t)(max_cell_v * 1000.0f);
          float temp2 = id(bms_temp2).state;
          float min_temp_c = temp < temp2 ? temp : temp2;
          float max_temp_c = temp > temp2 ? temp : temp2;
          uint16_t min_temp_k = (uint16_t)(min_temp_c + 273.0f);
          uint16_t max_temp_k = (uint16_t)(max_temp_c + 273.0f);
          std::vector<uint8_t> f373 = {
            (uint8_t)(min_cell_mv & 0xFF), (uint8_t)(min_cell_mv >> 8),
            (uint8_t)(max_cell_mv & 0xFF), (uint8_t)(max_cell_mv >> 8),
            (uint8_t)(min_temp_k & 0xFF),  (uint8_t)(min_temp_k >> 8),
            (uint8_t)(max_temp_k & 0xFF),  (uint8_t)(max_temp_k >> 8)
          };
          id(can_bus).send_data(0x373, false, false, f373);
```

- [ ] **Step 2: Validate + compile**

```bash
cd "C:\Users\yport\Documents\Projects\esp32-jdb-can"
python -m esphome config jbd-can-vecan.yaml
python -m esphome compile jbd-can-vecan.yaml
```
Expected: both succeed. `temp` and `temp2` must resolve to the `bms_temp1`/`bms_temp2` variables
already declared in Task 4's step — if compile fails with "temp2 used before declaration" or similar,
confirm this block was inserted after Task 4's `float temp = id(bms_temp1).state;` line, not before.

- [ ] **Step 3: Commit**

```bash
git add jbd-can-vecan.yaml
git commit -m "feat: 0x373 min/max cell voltage + temperature frame"
```

---

### Task 7: 0x35E manufacturer name frame + final review

**Files:**
- Modify: `jbd-can-vecan.yaml`

- [ ] **Step 1: Add the frame**

Insert after the `id(can_bus).send_data(0x373, ...)` line, right before the final `ESP_LOGD` line:

```yaml
          // --- 0x35E : Nom "JBD_BATT" (8 caractères, troncature de JBD_BATTERY) ---
          std::vector<uint8_t> f35e = {'J','B','D','_','B','A','T','T'};
          id(can_bus).send_data(0x35E, false, false, f35e);
```

- [ ] **Step 2: Full validate + compile of the complete file**

```bash
cd "C:\Users\yport\Documents\Projects\esp32-jdb-can"
python -m esphome config jbd-can-vecan.yaml
python -m esphome compile jbd-can-vecan.yaml
```
Expected: both succeed — this is the complete `jbd-can-vecan.yaml` with all 6 frames (0x351, 0x355,
0x356, 0x35A, 0x373, 0x35E).

- [ ] **Step 3: Read the full file back and sanity-check frame order and DLC sizes**

```bash
cat jbd-can-vecan.yaml
```
Confirm: 6 `send_data` calls, each vector literal has exactly as many elements as documented in the
spec table (0x351→8, 0x355→4, 0x356→6, 0x35A→8, 0x373→8, 0x35E→8).

- [ ] **Step 4: Commit**

```bash
git add jbd-can-vecan.yaml
git commit -m "feat: 0x35E manufacturer name frame, jbd-can-vecan.yaml frame set complete"
```

---

### Task 8: Adapt `can-listener.yaml` debug tool for the new variant

**Files:**
- Modify: `can-listener.yaml`

- [ ] **Step 1: Rewrite the file**

```yaml
esphome:
  name: can-listener

esp32:
  board: esp32dev
  framework:
    type: arduino

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

logger:
  level: DEBUG

api:

ota:
  - platform: esphome
    password: "ota-password"

canbus:
  - platform: esp32_can
    tx_pin: GPIO5
    rx_pin: GPIO4
    can_id: 0
    bit_rate: 250kbps
    id: can_listen
    on_frame:
      - can_id: 0x351
        then:
          - lambda: |-
              ESP_LOGI("can", "0x351: CVL=%.1fV CCL=%.1fA DCL=%.1fA DVL=%.1fV",
                (x[0] | (x[1]<<8)) * 0.1f,
                (x[2] | (x[3]<<8)) * 0.1f,
                (x[4] | (x[5]<<8)) * 0.1f,
                (x[6] | (x[7]<<8)) * 0.1f);
      - can_id: 0x355
        then:
          - lambda: |-
              ESP_LOGI("can", "0x355: SOC=%d%% SOH=%d%%",
                (int)(x[0] | (x[1]<<8)),
                (int)(x[2] | (x[3]<<8)));
      - can_id: 0x356
        then:
          - lambda: |-
              ESP_LOGI("can", "0x356: V=%.2fV I=%.1fA T=%.1f°C",
                (int16_t)(x[0] | (x[1]<<8)) * 0.01f,
                (int16_t)(x[2] | (x[3]<<8)) * 0.1f,
                (int16_t)(x[4] | (x[5]<<8)) * 0.1f);
      - can_id: 0x35A
        then:
          - lambda: |-
              ESP_LOGI("can", "0x35A: alarms=%02X %02X %02X warnings=%02X %02X %02X",
                x[0], x[1], x[2], x[4], x[5], x[6]);
      - can_id: 0x373
        then:
          - lambda: |-
              ESP_LOGI("can", "0x373: minCell=%.3fV maxCell=%.3fV minTemp=%dK maxTemp=%dK",
                (x[0] | (x[1]<<8)) / 1000.0f,
                (x[2] | (x[3]<<8)) / 1000.0f,
                (int)(x[4] | (x[5]<<8)),
                (int)(x[6] | (x[7]<<8)));
      - can_id: 0x35E
        then:
          - lambda: |-
              ESP_LOGI("can", "0x35E: manufacturer=%c%c%c%c%c%c%c%c",
                x[0],x[1],x[2],x[3],x[4],x[5],x[6],x[7]);
```

Note: `0x359`/`0x35C` decoding removed (not part of the REC-BMS frame set); pins kept at GPIO5/GPIO4
as this listener is a separate physical debug ESP32, unrelated to the GPIO23/22 wiring of the main
bridge boards — do not change these pins without checking which board is actually being flashed.

- [ ] **Step 2: Validate**

```bash
cd "C:\Users\yport\Documents\Projects\esp32-jdb-can"
python -m esphome config can-listener.yaml
```
Expected: `INFO Configuration is valid!`

- [ ] **Step 3: Commit**

```bash
git add can-listener.yaml
git commit -m "chore: adapt can-listener.yaml to 250kbps REC-BMS frame set"
```

---

### Task 9: Document the new variant in README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a new section** after the existing "## Setup" section (or before it — place it so
  the two variants are clearly presented as alternatives, not as a linear sequence):

```markdown
## Two Firmware Variants

This repo builds two independent ESPHome firmwares from the same JBD BMS wiring, sharing
`common.yaml` for BMS reading. Flash only the one matching your setup — they are not meant to run
simultaneously on the same ESP32.

| File | CAN bus | Protocol | Use case |
|------|---------|----------|----------|
| `jbd-can-bridge.yaml` | 500 kbps, dedicated BMS-Can port | Pylontech-style | Cerbo GX only |
| `jbd-can-vecan.yaml` | 250 kbps, shared VE.Can port | REC BMS-style | Safiery Scotty AI, with or without a Cerbo GX on the same bus |

### jbd-can-vecan.yaml specifics

- **Cerbo GX (if present on the same bus):** set the VE.Can port mode to **"VE.Can & CAN-bus BMS
  (250kbit/s)"** instead of the dedicated BMS-Can port used by `jbd-can-bridge.yaml`.
- **Scotty AI:** no configuration needed, auto-detects the REC BMS protocol.
- **Wiring/termination:** identical to the `jbd-can-bridge.yaml` section above (same GPIO23/GPIO22,
  same RJ45 pins 7/8, same ~60 Ω termination check).
- **Tunable limits** (`substitutions:` block in `jbd-can-vecan.yaml`):

  | Substitution | Default | Meaning |
  |---|---|---|
  | `charge_current_limit_a` | 50 | Max charge current (A), full value below `cell_taper_start_v` |
  | `discharge_current_limit_a` | 100 | Max discharge current (A) |
  | `cell_taper_start_v` | 3.45 | Cell voltage where CCL starts ramping down |
  | `cell_taper_end_v` | 3.65 | Cell voltage where CCL reaches 0 (keep below your BMS's real OVP threshold) |

  > These are generic LiFePO4 defaults, not your battery's real limits. Cross-check
  > `charge_current_limit_a` / `discharge_current_limit_a` against the OCC/OCD threshold actually
  > configured in the JBD Bluetooth app ("Basic Parameters") — the values here must stay strictly
  > below it, since this component cannot read that threshold automatically.
```

- [ ] **Step 2: Review rendering**

Read the file back and confirm the tables render as valid Markdown (no broken pipes/rows) and that
this section doesn't contradict the wiring section above it (it shouldn't — it explicitly reuses it).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document jbd-can-vecan.yaml variant, wiring reuse, tunable limits"
```

---

## Self-Review Notes

- **Spec coverage:** architecture (Task 1-2), protocol choice/frames 0x351/0x355/0x356/0x35A/0x373/0x35E
  (Tasks 3-7), name truncation (Task 7), CCL taper + DCL zeroing (Task 3), Cerbo/Scotty config notes
  (Task 9), can-listener adaptation (Task 8) — all spec sections have a task.
- **Out of scope, confirmed still excluded:** reading real OCC/OCD from the BMS (documented as a
  limitation in Task 9's README addition), DCL tapering (only zeroing, per spec), other Scotty
  protocols.
- **Type/name consistency checked:** `cell_v1`..`cell_v16` (Task 1) match the array literal in Task 3;
  `charge_current_limit_a`/`discharge_current_limit_a`/`cell_taper_start_v`/`cell_taper_end_v`
  (Task 2 substitutions) match the `${...}` references in Task 3; `min_cell_v`/`max_cell_v` (Task 3)
  match their reuse in Task 6; `temp`/`temp2` (Task 4/6) declared before use.
