# esp32-jbd-can

ESP32 + ESPHome bridge between a LiFePO4 battery with a JBD BMS and a CAN "BMS CAN" network — the 500 kbps CAN bus standardized by Pylontech.

Allows JBD BMS data to be used in a Victron Cerbo GX via CAN bus (a Bluetooth connection would also be possible), and more importantly in a **Safiery Scotty AI**, which only supports BMS CAN input.

The ESP32 replaces the small JBD Bluetooth module. A parallel connection is likely also possible if you want to keep the JBD app instead of connecting to the ESP32.

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
