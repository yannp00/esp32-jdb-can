# JBD→CAN Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer un firmware ESPHome sur ESP32 qui lit un BMS JBD via UART et émet les données batterie sur un bus CAN 500 kbps au format Pylontech, pour le Cerbo GX et le Scotty AI V3.

**Architecture:** ESPHome avec le composant externe `syssi/esphome-jbd-bms` pour la lecture UART du BMS, le composant natif `esp32_can` (TWAI) pour l'émission CAN, et un lambda C++ 1Hz qui encode les 6 trames Pylontech.

**Tech Stack:** ESPHome (framework Arduino), composant `syssi/esphome-jbd-bms`, SN65HVD230 (transceiver CAN 3.3V)

## Global Constraints

- ESP32-WROOM (esp32dev board), framework Arduino
- ESPHome installé localement ou via CLI (`pip install esphome`)
- GPIO UART : TX=GPIO17 (→ BMS RXD), RX=GPIO16 (← BMS TXD)
- GPIO CAN : TX=GPIO5 (→ SN65HVD230 CTX), RX=GPIO4 (← SN65HVD230 CRX)
- Bus CAN : 500 kbps, protocole Pylontech "Pylon LV"
- Pack batterie : 16S LiFePO4 48V 50Ah (DC House)
- Le module Bluetooth JBD doit être retiré du port UART avant tout câblage

---

## Fichiers du projet

```
esp32-jdb-can/
├── jbd-can-bridge.yaml      # Config ESPHome principale (créer)
├── secrets.yaml             # Credentials WiFi (créer, ne jamais committer)
├── .gitignore               # Exclure secrets.yaml (créer)
└── docs/
    └── superpowers/
        ├── specs/2026-06-27-jbd-can-bridge-design.md
        └── plans/2026-06-27-jbd-can-bridge.md
```

---

## Task 1 : ESPHome de base — WiFi + web_server

**Files:**
- Create: `jbd-can-bridge.yaml`
- Create: `secrets.yaml`
- Create: `.gitignore`

**Interfaces:**
- Produit: ESP32 accessible sur le réseau à `http://jbd-can-bridge.local`, page web vide mais fonctionnelle, OTA activé

**Note WiFi provisioning :** le YAML inclut un bloc `ap:` + `captive_portal:`. Si l'ESP32 ne trouve pas le réseau WiFi configuré (voyage, nouveau réseau), il crée automatiquement un hotspot "jbd-can-bridge-fallback". En se connectant à ce hotspot depuis un téléphone, une page s'ouvre pour configurer le réseau WiFi cible. L'ESP32 continue à fonctionner (CAN) même sans WiFi — c'est juste un bonus. Pour le **premier flash**, les credentials doivent quand même être dans `secrets.yaml`.

- [ ] **Étape 0 : Initialiser le dépôt git**

```bash
cd C:\Users\yport\Documents\Projects\esp32-jdb-can
git init
git add docs/
git commit -m "chore: init — spec et plan de design"
```

- [ ] **Étape 1 : Créer `.gitignore`**

```
secrets.yaml
.esphome/
```

- [ ] **Étape 2 : Créer `secrets.yaml`** (remplacer avec tes valeurs réelles)

```yaml
wifi_ssid: "NomDeTonReseau"
wifi_password: "MotDePasseWifi"
```

- [ ] **Étape 3 : Créer `jbd-can-bridge.yaml`**

```yaml
esphome:
  name: jbd-can-bridge

esp32:
  board: esp32dev
  framework:
    type: arduino

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "jbd-can-bridge-fallback"
    password: "configmode"

captive_portal:

web_server:
  port: 80

logger:

api:

ota:
  password: "ota-password"
```

Note : le bloc `ap:` + `captive_portal:` crée un réseau WiFi de secours si le réseau principal est absent (utile en voyage).

- [ ] **Étape 4 : Compiler et flasher via USB**

```bash
esphome run jbd-can-bridge.yaml
```

Sélectionner le port série USB quand demandé. La première fois, le flash prend ~2 minutes.

- [ ] **Étape 5 : Vérifier la connectivité**

Ouvrir `http://jbd-can-bridge.local` dans un navigateur sur le même réseau WiFi.
Résultat attendu : page ESPHome vide avec le nom "jbd-can-bridge" et un uptime.

Dans les logs (visibles dans le terminal ou via la page web) :
```
[I] WiFi: Connected to "NomDeTonReseau"
[I] WiFi: IP Address: 192.168.x.x
[I] web_server: Started web server on port 80
```

- [ ] **Étape 6 : Vérifier l'OTA**

Déconnecter le câble USB. Modifier une ligne du YAML (ex. changer le nom du ap en "fallback-v2"), puis :

```bash
esphome run jbd-can-bridge.yaml
```

Sélectionner l'option réseau (OTA) au lieu du port série.
Résultat attendu : flash réussi sans câble USB.

- [ ] **Étape 7 : Commit**

```bash
git init
git add jbd-can-bridge.yaml .gitignore docs/
git commit -m "feat: ESPHome base — WiFi, web_server, OTA"
```

---

## Task 2 : Lecture BMS JBD via UART

**Files:**
- Modify: `jbd-can-bridge.yaml`

**Interfaces:**
- Consomme: Task 1 (ESP32 connecté au réseau)
- Produit: Sensors ESPHome exposant SOC, tension, courant, températures, tensions des 16 cellules, états d'alarme — visibles sur `http://jbd-can-bridge.local` et dans les logs

**Pré-requis matériel :** Câbler ESP32 ↔ BMS JBD avant cette étape :
- BMS TXD → ESP32 GPIO16
- BMS RXD → ESP32 GPIO17
- BMS GND → ESP32 GND
- Module Bluetooth retiré du port UART BMS

- [ ] **Étape 1 : Ajouter UART et composant JBD au YAML**

Ajouter après le bloc `ota:` :

```yaml
uart:
  - id: jbd_uart
    tx_pin: GPIO17
    rx_pin: GPIO16
    baud_rate: 9600

external_components:
  - source: github://syssi/esphome-jbd-bms@main

jbd_bms:
  - platform: jbd_bms
    uart_id: jbd_uart
    id: bms0
    state_of_charge:
      name: "BMS SOC"
      id: bms_soc
    total_voltage:
      name: "BMS Voltage"
      id: bms_voltage
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
    cell_voltage_3:
      name: "Cell 3"
    cell_voltage_4:
      name: "Cell 4"
    cell_voltage_5:
      name: "Cell 5"
    cell_voltage_6:
      name: "Cell 6"
    cell_voltage_7:
      name: "Cell 7"
    cell_voltage_8:
      name: "Cell 8"
    cell_voltage_9:
      name: "Cell 9"
    cell_voltage_10:
      name: "Cell 10"
    cell_voltage_11:
      name: "Cell 11"
    cell_voltage_12:
      name: "Cell 12"
    cell_voltage_13:
      name: "Cell 13"
    cell_voltage_14:
      name: "Cell 14"
    cell_voltage_15:
      name: "Cell 15"
    cell_voltage_16:
      name: "Cell 16"
    charging_mosfet_enabled:
      name: "Charging MOSFET"
    discharging_mosfet_enabled:
      name: "Discharging MOSFET"
    errors_bitmask:
      name: "BMS Errors"
      id: bms_errors
```

Note : seuls `bms_soc`, `bms_voltage`, `bms_current`, `bms_temp1`, `bms_errors` ont un `id:` — ce sont les sensors utilisés dans le lambda CAN de la Task 3.

- [ ] **Étape 2 : Compiler et flasher (OTA)**

```bash
esphome run jbd-can-bridge.yaml
```

- [ ] **Étape 3 : Vérifier les valeurs dans la page web**

Ouvrir `http://jbd-can-bridge.local`. Les sensors doivent apparaître avec des valeurs :
- BMS SOC : une valeur entre 0 et 100 (%)
- BMS Voltage : autour de 48-58V
- BMS Current : positif si décharge, négatif si charge, ~0 si au repos
- BMS Temperature 1 et 2 : température ambiante (~20-30°C)
- Cell 1 à 16 : tensions autour de 3.2-3.4V (LiFePO4 au repos)

Si les valeurs sont "unavailable" ou NaN, vérifier le câblage UART et que les fils TX/RX sont bien croisés (BMS TXD → ESP32 RX, BMS RXD → ESP32 TX).

- [ ] **Étape 4 : Vérifier les logs**

Dans les logs, on doit voir des trames JBD décodées :
```
[D] jbd_bms: SOC: 75.0%
[D] jbd_bms: Voltage: 52.4V
```
Absence de messages d'erreur UART répétés.

- [ ] **Étape 5 : Commit**

```bash
git add jbd-can-bridge.yaml
git commit -m "feat: lecture BMS JBD via UART — sensors SOC, V, I, T, cellules"
```

---

## Task 3 : Émission CAN Pylontech

**Files:**
- Modify: `jbd-can-bridge.yaml`

**Interfaces:**
- Consomme: sensors `bms_soc`, `bms_voltage`, `bms_current`, `bms_temp1`, `bms_errors` (Task 2)
- Produit: 6 trames CAN Pylontech émises à 1Hz sur GPIO5/GPIO4 via SN65HVD230

**Pré-requis matériel :** Câbler ESP32 ↔ SN65HVD230 :
- ESP32 GPIO5 → SN65HVD230 CTX (D)
- ESP32 GPIO4 ← SN65HVD230 CRX (R)
- ESP32 3.3V → SN65HVD230 VCC (3.3V — ne pas mettre 5V)
- ESP32 GND → SN65HVD230 GND
- Activer la résistance de terminaison intégrée du SN65HVD230 (jumper ou solder bridge "120R" selon le module)
- Pour les tests Task 3, connecter un second ESP32 avec son propre SN65HVD230 sur les mêmes CANH/CANL

**Valeurs fixes du pack (à ajuster si specs différentes) :**
- CVL (charge voltage limit) : 58.4V → 584 en unités 0.1V
- DVL (discharge voltage limit) : 44.8V → 448 en unités 0.1V
- CCL (max charge current) : 50A (à confirmer sur datasheet DC House)
- DCL (max discharge current) : 100A (à confirmer)

- [ ] **Étape 1 : Ajouter le bus CAN et le lambda au YAML**

Ajouter après le bloc `jbd_bms:` :

```yaml
canbus:
  - platform: esp32_can
    tx_pin: GPIO5
    rx_pin: GPIO4
    can_id: 0
    bit_rate: 500kbps
    id: can_bus

interval:
  - interval: 1s
    then:
      - lambda: |-
          // Vérifier que les données BMS sont valides
          float soc     = id(bms_soc).state;
          float voltage = id(bms_voltage).state;
          float current = id(bms_current).state;
          float temp    = id(bms_temp1).state;
          float errors  = id(bms_errors).state;

          if (isnan(soc) || isnan(voltage)) {
            ESP_LOGW("pylontech", "Données BMS invalides, trames CAN non émises");
            return;
          }

          // --- 0x351 : Limites tension/courant ---
          // CVL=58.4V (584×0.1V), CCL=50A, DCL=100A, DVL=44.8V (448×0.1V)
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
          uint16_t soh_i = 100;  // JBD ne calcule pas le SOH
          std::vector<uint8_t> f355 = {
            (uint8_t)(soc_i & 0xFF), (uint8_t)(soc_i >> 8),
            (uint8_t)(soh_i & 0xFF), (uint8_t)(soh_i >> 8)
          };
          id(can_bus).send_data(0x355, false, false, f355);

          // --- 0x356 : Tension / Courant / Température ---
          int16_t v_raw = (int16_t)(voltage * 100);   // 0.01V/LSB
          int16_t i_raw = (int16_t)(current * 10);    // 0.1A/LSB (négatif = charge)
          int16_t t_raw = (int16_t)(temp * 10);       // 0.1°C/LSB
          std::vector<uint8_t> f356 = {
            (uint8_t)(v_raw & 0xFF), (uint8_t)(v_raw >> 8),
            (uint8_t)(i_raw & 0xFF), (uint8_t)(i_raw >> 8),
            (uint8_t)(t_raw & 0xFF), (uint8_t)(t_raw >> 8)
          };
          id(can_bus).send_data(0x356, false, false, f356);

          // --- 0x359 : Alarmes et protections ---
          // Bits mappés depuis errors_bitmask JBD
          // Bit 0x0004 = overvoltage, 0x0008 = undervoltage, 0x0100 = overcurrent charge
          uint32_t err = (uint32_t)errors;
          uint8_t alarm0 = 0x00;
          uint8_t alarm1 = 0x00;
          if (err & 0x0001) alarm0 |= 0x04;  // cell overvoltage → high voltage alarm
          if (err & 0x0002) alarm0 |= 0x08;  // cell undervoltage → low voltage alarm
          if (err & 0x0004) alarm1 |= 0x01;  // pack overvoltage
          if (err & 0x0008) alarm1 |= 0x02;  // pack undervoltage
          if (err & 0x0100) alarm1 |= 0x04;  // overcurrent charge
          std::vector<uint8_t> f359 = {alarm0, alarm1, 0x00, 0x00};
          id(can_bus).send_data(0x359, false, false, f359);

          // --- 0x35C : Flags demande de charge ---
          // 0xC0 = demande charge ET décharge autorisées
          uint8_t req = 0xC0;
          if (err != 0) req = 0x00;  // si alarme active, couper les demandes
          std::vector<uint8_t> f35c = {req, 0x00};
          id(can_bus).send_data(0x35C, false, false, f35c);

          // --- 0x35E : Nom fabricant "PYLON   " ---
          std::vector<uint8_t> f35e = {'P','Y','L','O','N',' ',' ',' '};
          id(can_bus).send_data(0x35E, false, false, f35e);

          ESP_LOGD("pylontech", "CAN: SOC=%.0f%% V=%.2fV I=%.1fA T=%.1f°C",
                   soc, voltage, current, temp);
```

- [ ] **Étape 2 : Préparer le second ESP32 pour écouter le bus CAN**

Sur le second ESP32 (avec son propre SN65HVD230 câblé en parallèle sur CANH/CANL), créer `can-listener.yaml` :

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
  password: "ota-password"

canbus:
  - platform: esp32_can
    tx_pin: GPIO5
    rx_pin: GPIO4
    can_id: 0
    bit_rate: 500kbps
    id: can_listen
    on_frame:
      - can_id: 0x351
        then:
          - lambda: |-
              ESP_LOGI("can", "0x351: CVL=%.1fV CCL=%dA DCL=%dA",
                (x[0] | (x[1]<<8)) * 0.1f,
                (int)(x[2] | (x[3]<<8)),
                (int)(x[4] | (x[5]<<8)));
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
      - can_id: 0x359
        then:
          - lambda: |-
              ESP_LOGI("can", "0x359: alarms=%02X %02X", x[0], x[1]);
      - can_id: 0x35C
        then:
          - lambda: |-
              ESP_LOGI("can", "0x35C: flags=%02X", x[0]);
      - can_id: 0x35E
        then:
          - lambda: |-
              ESP_LOGI("can", "0x35E: manufacturer=%c%c%c%c%c",
                x[0],x[1],x[2],x[3],x[4]);
```

Flasher sur le second ESP32 :
```bash
esphome run can-listener.yaml
```

- [ ] **Étape 3 : Flasher le bridge principal (OTA)**

```bash
esphome run jbd-can-bridge.yaml
```

- [ ] **Étape 4 : Vérifier les trames dans les logs du listener**

Dans les logs du second ESP32 (`esphome logs can-listener.yaml`), on doit voir toutes les secondes :
```
[I] can: 0x351: CVL=58.4V CCL=50A DCL=100A
[I] can: 0x355: SOC=75% SOH=100%
[I] can: 0x356: V=52.42V I=0.0A T=24.5°C
[I] can: 0x359: alarms=00 00
[I] can: 0x35C: flags=C0
[I] can: 0x35E: manufacturer=PYLON
```

Les valeurs V, I, T, SOC doivent correspondre à ce que la page web du bridge affiche.

- [ ] **Étape 5 : Commit**

```bash
git add jbd-can-bridge.yaml can-listener.yaml
git commit -m "feat: émission CAN Pylontech 6 trames 1Hz + listener de test"
```

---

## Task 4 : Intégration Cerbo GX

**Files:**
- Aucun fichier à modifier (test de configuration matérielle et Cerbo)

**Pré-requis :** Les 6 trames Pylontech sont validées (Task 3).

- [ ] **Étape 1 : Câbler le bus CAN définitif**

Débrancher le second ESP32 du bus. Câbler à la place :
- Cerbo GX port BMS-CAN (RJ45) sur le bus CANH/CANL
- Brancher le bouchon de terminaison 120Ω Victron sur le port BMS-CAN du Cerbo
  (seulement si le Cerbo est en bout de bus — vérifier la position physique)

Vérification électrique (bus hors tension) : mesurer entre CANH et CANL avec un multimètre.
- ~60Ω = correct (deux 120Ω en parallèle)
- ~120Ω = une terminaison manque
- <50Ω = trop de résistances

- [ ] **Étape 2 : Configurer le port BMS-CAN du Cerbo**

Sur le Cerbo GX : Settings → Services → CAN-bus profile → sélectionner **"CAN-bus BMS (500 kbit/s)"**.

- [ ] **Étape 3 : Vérifier l'apparition de la batterie sur le Cerbo**

Dans l'interface du Cerbo : Device List → vérifier qu'une entrée "Battery" ou "Pylontech" apparaît.

Les valeurs SOC, tension, courant, température doivent correspondre à celles de la page web du bridge.

- [ ] **Étape 4 : Vérifier le DVCC**

Settings → DVCC → vérifier que le Cerbo utilise les limites CVL/CCL/DCL reçues du bridge.

- [ ] **Étape 5 : Commit**

```bash
git add docs/
git commit -m "docs: notes intégration Cerbo GX validée"
```

---

## Task 5 : Intégration Scotty AI V3

**Files:**
- Aucun fichier à modifier (test de configuration matérielle et Scotty)

**Pré-requis :** Cerbo reconnaît la batterie (Task 4).

- [ ] **Étape 1 : Câbler le Scotty sur le bus CAN**

Brancher CAN Hi (pin 2 du harnais Scotty) sur CANH et CAN Lo (pin 6) sur CANL.
Ajouter une résistance 120Ω entre CAN Hi et CAN Lo côté Scotty si c'est l'extrémité du bus.

Re-vérifier avec multimètre entre CANH et CANL (bus hors tension) : doit lire ~60Ω.

- [ ] **Étape 2 : Vérifier la section CAN BATTERY sur le Scotty**

Connecter au WiFi du Scotty (SSID Scotty_xxxx, mot de passe Scottyai@0).
Ouvrir http://172.24.24.1 dans un navigateur.

Dans la page principale, section **CAN BATTERY**, vérifier que les valeurs suivantes sont présentes et cohérentes :
- SOC : correspond à la page web du bridge
- Voltage : correspond
- Current : correspond
- Charge Voltage Lim : 58.00V
- Max Charge Current : 50A
- Max Discharge Current : 100A
- Temperature : correspond

Si la section CAN BATTERY est vide : vérifier le câblage CAN Hi/Lo et rebooter le Scotty.

- [ ] **Étape 3 : Vérifier le comportement de charge**

Démarrer le moteur. Le Scotty doit commencer à charger la batterie 48V depuis l'alternateur 12V,
en respectant les limites CCL/DCL reçues via CAN.

Dans la page principale Scotty : LS Current doit augmenter, Scotty Power doit être négatif (charge).

- [ ] **Étape 4 : Commit final**

```bash
git add docs/
git commit -m "docs: intégration Scotty AI V3 validée — système complet opérationnel"
```

---

## Annexe : Ajustement des valeurs fixes CVL/CCL/DCL

Si les specs réelles du pack DC House 48V 50Ah diffèrent des valeurs par défaut, modifier dans le lambda (Task 3, Étape 1) :

```cpp
uint16_t cvl = 584;  // 58.4V = 3.65V × 16 cellules → ajuster si tension max différente
uint16_t ccl = 50;   // 50A charge max → ajuster selon datasheet
uint16_t dcl = 100;  // 100A décharge max → ajuster selon datasheet
uint16_t dvl = 448;  // 44.8V = 2.8V × 16 cellules → ajuster si tension min différente
```

Puis re-flasher via OTA :
```bash
esphome run jbd-can-bridge.yaml
```
