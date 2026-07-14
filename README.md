# esp32-jbd-can

ESP32 + ESPHome bridge between a LiFePO4 battery with a JBD BMS and a CAN "BMS CAN" network — the 500 kbps CAN bus standardized by Pylontech.

Allows JBD BMS data to be used in a Victron Cerbo GX via CAN bus (a Bluetooth connection would also be possible), and more importantly in a **Safiery Scotty AI**, which only supports BMS CAN input.

The ESP32 replaces the small JBD Bluetooth module. A parallel connection is likely also possible if you want to keep the JBD app instead of connecting to the ESP32.

## Two Firmware Variants

This repo builds two independent ESPHome firmwares from the same JBD BMS wiring, sharing
`common.yaml` for BMS reading. Flash only the one matching your setup — they are not meant to run
simultaneously on the same ESP32.

| File | CAN bus | Protocol | Use case |
|------|---------|----------|----------|
| `jbd-can-bridge.yaml` | 500 kbps, dedicated BMS-Can port | Pylontech-style | Cerbo GX only |
| `jbd-can-vecan.yaml` | 250 kbps, shared VE.Can port | REC BMS-style | Safiery Scotty AI, with or without a Cerbo GX on the same bus |

### jbd-can-vecan.yaml specifics

- **Scotty AI:** no configuration needed, auto-detects the REC BMS protocol.
- **Cerbo GX + Scotty on the same CAN bus:** both must use the **same physical VE.Can
  port** on the Cerbo, with profile **"VE.Can & CAN-bus BMS (250 kbit/s)"** (not plain
  `VE.Can`, and not a BMS-only profile). That profile runs both Venus drivers on that
  interface (`vecan-dbus` for the Scotty/alternator, `can-bus-bms` for the battery).
  - On a Cerbo with two CAN ports (e.g. MK2), check which port the Scotty cable is on
    (`Settings → Connectivity → VE.Can port N`). If `can-bus-bms` is only active on the
    *other* port, the battery never appears even though the Scotty already sees it.
  - After changing the profile, reboot the Cerbo. You should then see **both** the
    battery and the Scotty/alternator on the main Device list. The battery often shows
    on the home screen / Device list, not only under the VE.Can port device list.
  - Wrong profile symptoms: Scotty alone (plain `VE.Can`) → Cerbo never registers the
    battery; BMS-only profile → battery appears but Scotty/alternator disappears.
- **Wiring/termination:** identical to the wiring section below (same GPIO23/GPIO22,
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

  The CCL taper formula (ramping charge current down between `cell_taper_start_v` and
  `cell_taper_end_v`) can be re-verified with `python scripts/taper_check.py` whenever these
  substitutions or the formula itself change.

## Hardware

- ESP32 (esp32dev)
- SN65HVD230 CAN transceiver module (VD230), powered at **3.3 V**

## Wiring

### ESP32 → VD230

| ESP32   | VD230          |
|---------|----------------|
| GPIO23  | TX (D / CTX)   |
| GPIO22  | RX (R / CRX)   |
| 3.3 V   | VCC            |
| GND     | GND            |

### VD230 → Cerbo GX (VE.Can 2) via RJ45 cable

Victron VE.Can ports use **pins 7 and 8** for the CAN bus (T568B wiring):

| VD230 | Wire color   | RJ45 pin | Cerbo signal |
|-------|--------------|----------|--------------|
| CANH  | white/brown  | 7        | CAN-H        |
| CANL  | brown        | 8        | CAN-L        |

> ⚠️ **Common mistake**: pins 4/5 (blue pair) are sometimes used on the battery side in the official Victron "Type B" cable, but the Cerbo itself reads CAN on pins **7/8**. Wiring to 4/5 results in RX=0 on the Cerbo with no visible error.

### BMS JBD

| ESP32       | JBD BMS |
|-------------|---------|
| GPIO17 (TX) | RX      |
| GPIO16 (RX) | TX      |
| GND         | GND     |

UART: 9600 baud, polled every 5 s.

### 120 Ω Termination

CAN bus requires a 120 Ω termination resistor at **each end**.

The VD230 module I used includes a built-in termination resistor.

## CAN Frames Sent

Standard Pylontech frames at **1 Hz**:

| ID    | Content |
|-------|---------|
| 0x351 | CVL, CCL, DCL, DVL (voltage/current limits) |
| 0x355 | SOC, SOH |
| 0x356 | Voltage, Current, Temperature |
| 0x359 | Alarms (mapped from JBD errors_bitmask) |
| 0x35C | Charge/discharge request flags |
| 0x35E | Manufacturer name (`PYLON   `) |

## Setup

### 1. Install ESPHome

```bash
pip install esphome
```

### 2. Create `secrets.yaml`

ESPHome uses a `secrets.yaml` file (never committed) to keep credentials out of the main config. Create it alongside `jbd-can-bridge.yaml`:

```yaml
# secrets.yaml
wifi_ssid: "YourNetworkName"
wifi_password: "YourWifiPassword"
```

### 3. Flash

```bash
esphome run jbd-can-bridge.yaml
```

On first flash, connect the ESP32 via USB. Subsequent updates are done over-the-air (OTA).
