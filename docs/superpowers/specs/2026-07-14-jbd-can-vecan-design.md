# jbd-can-vecan: variante VE.Can 250kbps (REC-BMS) pour bus partagé Scotty + Cerbo

## Contexte

Le firmware existant (`jbd-can-bridge.yaml`) émule le protocole Pylontech BMS-CAN à 500 kbps sur le
port BMS-Can dédié du Cerbo GX. Cela fonctionne pour un Cerbo seul, mais un Safiery Scotty AI
(convertisseur DC-DC bidirectionnel) ne lit que son port CAN à 250 kbps, avec un protocole parmi une
liste fixe qu'il reconnaît nativement (Safiery, MG Energy, Lithium Werks, Victron Lynx BMS, REC BMS,
Orion Jr BMS, SIMP BMS).

Objectif : permettre à l'ESP32 d'émettre sur le bus **VE.Can 250 kbps** partagé, avec un protocole que
le Scotty ET le Cerbo (si présent) reconnaissent tous les deux nativement — pour n'avoir qu'un seul bus
CAN dans le van (Scotty + batterie, avec ou sans Cerbo).

## Choix du protocole : REC BMS

Recherche confirmée : le protocole "Victron BMS-CAN" (0x351/0x355/0x356/...) que `jbd-can-bridge.yaml`
émule déjà à 500 kbps est la même famille de protocole que **REC BMS**, disponible à 250 kbps sur le
port VE.Can standard du Cerbo (mode *"VE.Can & CAN-bus BMS (250kbit/s)"*), et REC BMS figure dans la
liste des protocoles reconnus par le Scotty. Pas besoin d'émuler Lynx BMS (protocole Victron natif non
documenté officiellement, sous NDA, reverse-engineered uniquement) ni un autre protocole de la liste.

Référence de structure de trames : implémentation open source
[diyBMSv4ESP32 `victron_canbus.cpp`](https://github.com/stuartpittaway/diyBMSv4ESP32/blob/master/ESPController/src/victron_canbus.cpp),
recoupée avec la documentation REC BMS (`rec-bms.com`).

## Architecture repo

```
common.yaml           ← nouveau : partie partagée entre les deux variantes
jbd-can-bridge.yaml    ← existant, INCHANGÉ (BMS-Can dédié 500kbps, Cerbo seul)
jbd-can-vecan.yaml     ← nouveau (VE.Can partagé 250kbps, REC-BMS)
```

`common.yaml` regroupe, via `packages:`, tout ce qui est identique entre les deux configs :
- `esp32:` (board, framework)
- `wifi:`, `captive_portal:`, `web_server:`, `logger:`, `api:`, `ota:`
- `uart:` (lecture BMS JBD) + `jbd_bms:` + tous les `sensor:` (SOC, tension, courant, températures,
  16 cellules, errors_bitmask)
- `globals:` (watchdog `last_bms_update_ms`)

Chaque fichier top-level (`jbd-can-bridge.yaml`, `jbd-can-vecan.yaml`) inclut `common.yaml` via
`packages:` et ne définit que :
- son propre `esphome: name:` et point d'accès AP
- sa section `canbus:` (vitesse de bus, pins — identiques dans les deux cas : GPIO23/GPIO22)
- son `interval:` de construction/émission des trames, spécifique au protocole ciblé

## Contenu de `jbd-can-vecan.yaml`

### esphome

```yaml
esphome:
  name: "JBD_BATTERY"
```

### Bus CAN

```yaml
canbus:
  - platform: esp32_can
    tx_pin: GPIO23
    rx_pin: GPIO22
    can_id: 0
    bit_rate: 250kbps
    id: can_bus
```

### Substitutions

```yaml
substitutions:
  charge_current_limit_a: "50"
  discharge_current_limit_a: "100"
  cell_taper_start_v: "3.45"   # début de réduction douce du CCL (≈ 55.2V pack 16S)
  cell_taper_end_v: "3.65"     # CCL=0 (≈ 58.4V pack 16S, cohérent avec CVL)
```

> Ces valeurs sont des repères génériques pour du LiFePO4 16S, **à confirmer contre le matériel réel** :
> - `charge_current_limit_a` / `discharge_current_limit_a` doivent rester **strictement inférieures**
>   au seuil de protection surintensité (OCC/OCD) réellement configuré dans le BMS JBD (app Bluetooth
>   JBD, "Basic Parameters"). Le composant `esphome-jbd-bms` ne lit pas ce seuil automatiquement —
>   seuls des compteurs de déclenchement et des flags binaires sont exposés, jamais la valeur en ampères.
> - `cell_taper_end_v` doit rester **en dessous** du seuil OVP réel du BMS, sinon la protection
>   matérielle coupe avant que le tapering CAN ait fini son travail. 3.65V/cellule correspond au
>   `cvl=584` (58.4V pack) déjà utilisé dans `jbd-can-bridge.yaml`.

### Trames CAN émises (1 Hz)

| ID    | Contenu | Détail |
|-------|---------|--------|
| 0x351 | CVL, CCL, DCL, DVL | CCL/DCL **dynamiques** (voir ci-dessous), 0.1V/0.1A LSB, little-endian |
| 0x355 | SOC, SOH | uint16, 1%/LSB |
| 0x356 | Tension, Courant, Température | int16, 0.01V / 0.1A / 0.1°C LSB |
| 0x35A | Alarmes/warnings | bits dédiés par condition sur 3 octets (voir détail plus bas), remplace 0x359 |
| 0x373 | Min/Max tension cellule + température | uint16 little-endian, cellule en **mV** (1 mV/LSB), température en **Kelvin entier** |
| 0x35E | Nom | `"JBD_BATT"` (8 car. ASCII, troncature de "JBD_BATTERY") |

`0x35C` (flags demande charge/décharge, spécifique à la convention Pylontech) est **retiré** dans cette
variante — absent des IDs REC documentés. Le pilotage passe uniquement par CCL/DCL dans 0x351.

### CCL/DCL dynamiques

**Important — comportement Scotty confirmé par la doc Safiery** : *"where a Charge Current Limit and
Charge Voltage Limit is communicated, these values override any programming values in Scotty. This
means the BMS takes control of the charging profile transitions."* Autrement dit, quand une source CAN
publie CCL/CVL, **c'est elle qui pilote la transition de fin de charge**, pas le Scotty via sa propre
tension configurée. Un CCL fixe qui tombe brutalement à 0 provoquerait donc une coupure nette plutôt
qu'une transition douce — d'où le tapering ci-dessous.

**DCL** : zeroing simple sur alarme, réutilise `errors_bitmask` déjà lu par `common.yaml` :

```
si (sous-tension pack OU sous-tension cellule OU surtempérature décharge) → DCL = 0
sinon → DCL = discharge_current_limit_a
```

**CCL** : combine un tapering par tension de cellule (transition douce en fin de charge) et un zeroing
immédiat sur alarme (filet de sécurité en cas de déclenchement réel) :

```
max_cell_v = max(cell_voltage_1..16)

si (surtension pack OU surtension cellule OU surtempérature charge)      → CCL = 0   [alarme, prioritaire]
sinon si max_cell_v < cell_taper_start_v                                  → CCL = charge_current_limit_a
sinon si max_cell_v >= cell_taper_end_v                                   → CCL = 0
sinon                                                                       → CCL = charge_current_limit_a
                                                                                × (cell_taper_end_v - max_cell_v)
                                                                                / (cell_taper_end_v - cell_taper_start_v)
```

### Alarmes 0x35A

Référence de structure confirmée par une implémentation open source dédiée au JBD-over-CAN
([`lltjbd_can.py`, projet dbus-serialbattery](https://github.com/mr-manuel/venus-os_dbus-serialbattery/blob/master/dbus-serialbattery/bms/lltjbd_can.py)) :
octets 0-3 = alarmes (bit=1 actif), octets 4-7 = warnings (même position de bit, non utilisés ici —
le composant `esphome-jbd-bms` n'expose pas de seuil de pré-alarme distinct, seulement les flags de
déclenchement de protection).

| Octet | Bit | Condition | Source `errors_bitmask` JBD (bit) |
|---|---|---|---|
| 0 | 2 | Surtension cellule | 0 (cell_overvoltage) OU 2 (pack_overvoltage) |
| 0 | 4 | Sous-tension cellule | 1 (cell_undervoltage) OU 3 (pack_undervoltage) |
| 0 | 6 | Surtempérature | 6 (discharge_overtemperature) |
| 1 | 0 | Sous-température | 7 (discharge_undertemperature) |
| 1 | 2 | Surtempérature charge | 4 (charge_overtemperature) |
| 1 | 4 | Sous-température charge | 5 (charge_undertemperature) |
| 1 | 6 | Surintensité décharge | 9 (discharge_overcurrent) |
| 2 | 0 | Surintensité charge | 8 (charge_overcurrent) |
| 2 | 4 | Court-circuit | 10 (short_circuit) |

## Configuration côté Victron / Scotty

- **Scotty** : aucune configuration — détection automatique du protocole REC BMS sur son port CAN
  250 kbps standard.
- **Cerbo GX (si présent sur le même bus)** : port VE.Can → mode **"VE.Can & CAN-bus BMS (250kbit/s)"**
  (au lieu du port BMS-Can dédié utilisé par `jbd-can-bridge.yaml`).
- **Câblage/terminaison** : mêmes principes déjà documentés dans le README (broches 7/8 RJ45,
  ~60 Ω mesurés entre CANH/CANL, un seul jumper actif si un bouchon Victron est déjà en place ailleurs
  sur le bus).

## Tests / validation

`can-listener.yaml` (outil de debug existant) à adapter :
- `bit_rate: 250kbps`
- décodage de 0x35A (bit-paire, pas bitmask simple)
- décodage de 0x373 (min/max cellule)
- retrait du décodage 0x359/0x35C (absents de cette variante)

Validation terrain : observer dans l'IHM Cerbo (si présent) que la batterie est reconnue "REC BMS" (ou
équivalent) avec SOC/tension corrects ; observer côté Scotty que le CCL est bien lu (comportement de
charge cohérent, arrêt si CCL retombe à 0 lors d'un test de déclenchement d'alarme BMS).

## Hors périmètre

- Lecture réelle du seuil OCC/OCD programmé dans le BMS JBD (non exposé par le composant ESPHome
  utilisé) — les limites restent des constantes réglables en substitution, à fixer manuellement sous
  le seuil réel.
- Tapering du DCL (courant de décharge) à l'approche de la tension basse — seul un zeroing simple sur
  alarme est prévu pour la décharge.
- Émulation d'autres protocoles de la liste Scotty (Lynx BMS, SIMP BMS, etc.).
