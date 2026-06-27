# Design : ESP32 JBD→CAN Bridge (émulateur Pylontech)

## Contexte

Pack batterie DC House 48V 50Ah LiFePO4 (16S) équipé d'un BMS JBD/Jiabaida (clone Xiaoxiang).
Le BMS expose ses données via un port UART (connecteur JST 4 pins VCC/RXD/TXD/GND) sur lequel
était branché un module Bluetooth — ce module est retiré, l'ESP32 prend le port seul.

Appareils à alimenter en données batterie :
- **Victron Cerbo GX** : monitoring, DVCC, intégration Home Assistant via WiFi
- **Safiery Scotty AI V3** : optimisation de charge depuis l'alternateur 12V

## Objectif

Construire un module ESP32 qui lit le BMS JBD via UART et émet en temps réel les données batterie
sur un bus CAN 500 kbps au format Pylontech ("Pylon LV"), protocole reconnu nativement par le
Cerbo GX (port BMS-CAN) et le Scotty AI V3 (CAN Hi/Lo câblé du harnais).

## Architecture matérielle

### Topologie du bus CAN

```
[BMS JBD 48V]
      │ UART 3.3V (TXD→GPIO16, RXD→GPIO17, GND commun)
      ▼
[ESP32-WROOM] ── [SN65HVD230] ──────────────────────────────────
                   (120Ω)          CANH / CANL 500 kbps
                                         │
                          ┌──────────────┴──────────────┐
                   [Cerbo GX]                    [Scotty AI V3]
                   port BMS-CAN                  CAN Hi/Lo harnais
                   (bouchon 120Ω fourni)         (120Ω à ajouter)
```

**Trois nœuds sur un seul bus 500 kbps.**
- L'ESP32 est le seul émetteur de trames batterie.
- Le Cerbo et le Scotty sont récepteurs.
- Le Scotty fonctionne indépendamment du Cerbo (pas de dépendance).
- Quand le Cerbo est allumé, il affiche batterie + Scotty dans son interface.

### Terminaison 120Ω

Un bus CAN nécessite exactement deux résistances de 120Ω, une à chaque extrémité physique du câble :
- **Côté ESP32** : jumper à activer sur le module SN65HVD230 (résistance intégrée).
- **Côté Scotty** : résistance 120Ω à souder entre CAN Hi et CAN Lo du harnais (le Scotty n'en a pas).
- **Cerbo** : bouchon de terminaison 120Ω fourni par Victron sur le port BMS-CAN — à utiliser
  seulement si le Cerbo est en bout de bus physiquement, sinon ne pas l'utiliser.

La position physique des appareils déterminera les deux extrémités réelles. À ajuster lors du câblage.

### Bus CAN séparé (Huawei R4850G2)

Un ESP32 distinct gère déjà un Huawei R4850G2 sur son propre bus CAN isolé (2 fils, SN65HVD230
dédié). Aucune connexion avec le bus Pylontech décrit ici.

### Connexion UART BMS

- BMS TXD → ESP32 GPIO16 (RX)
- BMS RXD → ESP32 GPIO17 (TX)
- BMS GND → ESP32 GND
- Niveaux 3.3V des deux côtés, pas d'adaptateur de niveau nécessaire.
- VCC du connecteur BMS non connecté à l'ESP32.
- Module Bluetooth retiré du port UART.

### Connexion CAN

- ESP32 GPIO5 (TX) → SN65HVD230 CTX
- ESP32 GPIO4 (RX) ← SN65HVD230 CRX
- SN65HVD230 CANH/CANL → bus

## Architecture logicielle

### Stack : ESPHome sur ESP32 (framework Arduino)

Choix retenu pour :
- Composant `syssi/esphome-jbd-bms` mature (lecture UART JBD, expose tous les sensors)
- Composant `esp32_can` natif ESPHome (contrôleur TWAI intégré)
- OTA WiFi (mise à jour sans débrancher)
- `web_server` embarqué (debug en temps réel depuis navigateur)
- Intégration Home Assistant automatique quand WiFi disponible

### Flux de données

```
[BMS JBD]
    │ polling UART 1Hz
    ▼
[jbd_bms component]
    │ sensors : SOC, tension pack, courant, températures,
    │           tensions 16 cellules, flags alarme/protection
    ▼
[interval: 1s → lambda C++]
    │ encode 6 trames Pylontech
    ▼
[esp32_can / TWAI 500kbps]
    │
    └── bus CAN → Cerbo GX + Scotty AI
```

### Trames Pylontech émises (1 Hz, 500 kbps)

| ID CAN | Contenu | Valeurs |
|--------|---------|---------|
| `0x351` | CVL / CCL / DCL | Limites charge/décharge (fixes + BMS) |
| `0x355` | SOC / SOH | SOC lu BMS ; SOH = 100 (JBD ne le calcule pas) |
| `0x356` | Tension / courant / température | Lecture BMS temps réel |
| `0x359` | Flags alarme et protection | États BMS |
| `0x35C` | Flags demande de charge | Dérivé des alarmes BMS |
| `0x35E` | Nom fabricant | Chaîne fixe "PYLON" |

Référence d'implémentation : `martc55/Jbd2Solis` (mapping C++ complet des 6 trames).
Référence encodage octets : `ArminJo/JK-BMS-ToPylontechCAN` (`Pylontech_CAN.h`).

### Valeurs fixes (pack DC House 48V 50Ah, 16S LiFePO4)

À renseigner lors de la mise en service selon datasheet du pack :

| Paramètre | Valeur typique 16S LiFePO4 | À confirmer |
|-----------|---------------------------|-------------|
| CVL (charge voltage limit) | 58.4V (3.65V × 16) | oui |
| Min discharge voltage | 44.8V (2.8V × 16) | oui |
| CCL (max charge current) | ~50A | selon BMS/datasheet |
| DCL (max discharge current) | ~100A | selon BMS/datasheet |

### Watchdog données UART

Si le BMS ne répond plus, les sensors ESPHome conservent leur dernière valeur. Le lambda devra
vérifier que les données ne sont pas obsolètes (via `isnan()` ou timestamp) avant d'émettre,
pour éviter d'envoyer des valeurs figées au Scotty.

### Structure du fichier ESPHome

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

web_server:
  port: 80

logger:
api:
ota:

uart:
  - id: jbd_uart
    tx_pin: GPIO17    # → BMS RXD
    rx_pin: GPIO16    # ← BMS TXD
    baud_rate: 9600

external_components:
  - source: github://syssi/esphome-jbd-bms

jbd_bms:
  uart_id: jbd_uart

canbus:
  - platform: esp32_can
    tx_pin: GPIO5     # → SN65HVD230 CTX
    rx_pin: GPIO4     # ← SN65HVD230 CRX
    can_id: 0
    bit_rate: 500kbps
    id: can_bus

interval:
  - interval: 1s
    then:
      - lambda: |-
          // Encode et envoie les 6 trames Pylontech
          // (implémentation dans le plan)
```

## Étapes de mise en œuvre

1. **Flash ESPHome de base** (WiFi + web_server) → vérifier que `http://jbd-can-bridge.local`
   est accessible depuis un appareil sur le même réseau.

2. **Ajouter UART + jbd_bms** → vérifier dans les logs et la page web que toutes les valeurs
   JBD arrivent (SOC, tension pack, courant, températures, 16 tensions de cellules, alarmes).

3. **Ajouter canbus** → vérifier qu'il n'y a pas d'erreur de démarrage CAN dans les logs.
   (bus non connecté à ce stade, erreurs CAN normales, on vérifie juste que le composant init).

4. **Écrire et tester le lambda Pylontech** → connecter un second ESP32 (disponible) avec un
   firmware `candump` simple pour vérifier que les 6 trames sortent à 1Hz avec des valeurs
   plausibles, avant de brancher Cerbo et Scotty.

5. **Brancher sur le bus CAN réel** → vérifier côté Cerbo (Settings → Devices, ou `candump`
   sur le Cerbo) que la batterie apparaît, puis côté Scotty que la section CAN BATTERY se remplit.

## Points de vigilance

- **Collision d'IDs CAN** : les IDs Pylontech (0x351–0x35E) ne chevauchent pas les IDs Huawei
  R4850G2 — les deux bus sont physiquement séparés, aucun risque.
- **Connexion BLE SerialBattery** (Cerbo ↔ BMS via Bluetooth) : peut rester active en parallèle
  comme monitoring de secours, indépendamment du bridge CAN.
- **Specs pack** : les valeurs CVL/CCL/DCL doivent correspondre aux specs réelles du pack DC House.
  Une tension max trop haute risque d'endommager les cellules.
- **Terminaison bus** : vérifier avec un multimètre entre CANH et CANL à l'arrêt (bus hors tension) :
  doit lire ~60Ω (deux 120Ω en parallèle). Si ~120Ω, une terminaison manque. Si <60Ω, trop de résistances.
