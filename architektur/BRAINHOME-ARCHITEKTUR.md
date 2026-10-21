# BrainHome – Gesamtarchitektur

> **Aktueller Einstieg, 21.10.2026:** Der live gepruefte Cluster hat fuenf
> Online-Nodes und 25 Gaeste. Hardware, Platzierungen, Backup-Luecken und
> Architekturentscheidung stehen in der
> [physischen Architektur](PHYSISCHE-ARCHITEKTUR.md). Die folgenden Abschnitte
> dokumentieren den historischen Stand Maerz 2026; ihre IPs, VLANs, Versions-
> und Dienststatusangaben gelten nicht als Ist-Inventar.

**Stand**: März 2026 | **Version**: in Aufbau | **Prinzip**: dezentral, lokal,
offen

**Status-Legende**: ✅ vorhanden & aktiv | ⚙️ vorhanden, in Konfiguration | 🔲
geplant, noch nicht umgesetzt

---

## 1. Prinzipien

```text
Edge Nodes (pro Etage/Zone)
        ↓
  MQTT Backbone
        ↓
  Service Layer (HA, Frigate, NodeRed...)
        ↓
  Identity Layer (Keycloak → SSO)
        ↓
  Portal Layer (BrainPortal)
```

- Dezentrale Nodes pro Etage / Zone
- Proxmox Virtualisierung auf jedem Node
- MQTT als zentrales Messaging-System
- Home Assistant pro Bereich (UG / EG / OG / WS)
- Zentrale Identität via Keycloak (OIDC / SSO)
- Lokale AI-Services (kein Cloud-Zwang)
- Git-Versionierung aller Konfigurationen

---

## 2. Zonen

| Zone   | Bereich                             | Proxmox Node | HA Instanz | Status |
| ------ | ----------------------------------- | ------------ | ---------- | ------ |
| **UG** | Technik / Server / Werkstatt-Keller | proxmox-ug   | haos-ug    | ✅     |
| **EG** | Wohnbereich Erdgeschoss             | proxmox-eg   | haos-eg    | 🔲     |
| **OG** | Wohnbereich Obergeschoss            | proxmox-og   | haos-og    | 🔲     |
| **GA** | Garage                              | –            | –          | 🔲     |
| **WS** | Werkstatt                           | proxmox-ws   | haos-ws    | 🔲     |

---

## 3. Proxmox Cluster

### Cluster

|                 |                                       |
| --------------- | ------------------------------------- |
| Name            | `brainhome`                           |
| Status          | ✅ aktiv (19.03.2026)                 |
| Nodes           | 4 (quorate, 4 Votes)                  |
| Transport       | knet                                  |
| Proxmox Version | PVE 9.1.6 (alle Nodes, Debian Trixie) |

### Nodes

| Node           | Hardware               | IP              | DNS                                   | Funktion                                  | Status |
| -------------- | ---------------------- | --------------- | ------------------------------------- | ----------------------------------------- | ------ |
| **proxmox**    | ThinkCentre M920Q (i7) | 192.168.188.254 | `proxmox.brain` / `proxmox-dev.brain` | Hauptserver (Auth, Dev, Proxy) — NodeID 1 | ✅     |
| **proxmox-eg** | ThinkCentre M920Q      | 192.168.188.253 | `proxmox-eg.brain`                    | EG-Node (HA-Instanzen, DNS) — NodeID 3    | ✅     |
| **proxmox-og** | ThinkCentre M920Q      | 192.168.188.252 | `proxmox-og.brain`                    | OG-Node (HA-OG, DNS-2) — NodeID 2         | ✅     |
| **proxmox-ug** | ThinkCentre M920Q (i9) | 192.168.188.248 | `proxmox-ug.brain` (.249)             | UG-Node (HA-UG, hohe Last) — NodeID 4     | ✅     |
| **proxmox-ws** | ThinkCentre empfohlen  | geplant         | –                                     | Werkstatt                                 | 🔲     |
| **proxmox-se** | ThinkCentre empfohlen  | geplant         | –                                     | Edge/Netzwerk                             | 🔲     |

### proxmox (lokal, NodeID 1) — CTs & VMs (192.168.188.254)

> ⚠️ Ressourcen freigeräumt für Workstation-Setup (März 2026)

| ID  | Typ | Name                      | RAM  | IP              | Status     | Funktion                                                   |
| --- | --- | ------------------------- | ---- | --------------- | ---------- | ---------------------------------------------------------- |
| 113 | VM  | **brainhome-workstation** | 8 GB | 192.168.188.178 | ✅ running | Workstation (Ubuntu 24.04 GNOME, basiert auf EG-stefan-lp) |
| 104 | VM  | pibrain                   | 4 GB | –               | ⚙️ stopped | Raspberry-Emulation / Tests                                |
| 105 | VM  | debian                    | 2 GB | –               | ⚙️ stopped | Allgemein / Tests                                          |
| 112 | CT  | **brainhome-dev**         | 4 GB | 192.168.188.112 | ⚙️ stopped | BrainHome Dev (Quarkus + Angular) – pausiert               |

### proxmox-eg — CTs & VMs (192.168.188.253)

| ID  | Typ | Name              | RAM    | IP              | Status     | Funktion                                |
| --- | --- | ----------------- | ------ | --------------- | ---------- | --------------------------------------- |
| 101 | VM  | **haos** (Master) | 11 GB  | 192.168.188.142 | ✅ running | Home Assistant Master                   |
| 102 | VM  | **haos-eg**       | 11 GB  | 192.168.188.194 | ✅ running | Home Assistant EG                       |
| 106 | VM  | **haos-ug**       | 8 GB   | 192.168.188.152 | ✅ running | Home Assistant UG                       |
| 108 | VM  | **openwrt-eg**    | 256 MB | 192.168.188.149 | ✅ running | WLAN AP EG (OpenWRT)                    |
| 100 | CT  | **pihole**        | 512 MB | 192.168.188.251 | ✅ running | Primär DNS                              |
| 110 | CT  | **caddy**         | 256 MB | 192.168.188.200 | ✅ running | Reverse Proxy (migriert von proxmox-ug) |

### proxmox-og — CTs & VMs (192.168.188.252)

| ID  | Typ | Name             | RAM    | IP              | Status     | Funktion                                              |
| --- | --- | ---------------- | ------ | --------------- | ---------- | ----------------------------------------------------- |
| 103 | VM  | **haos-og**      | 11 GB  | 192.168.188.143 | ✅ running | Home Assistant OG                                     |
| 107 | VM  | **idp-keycloak** | 8 GB   | 192.168.188.107 | ✅ running | Identity Provider (OIDC/SSO, migriert von proxmox-ug) |
| 109 | VM  | **openwrt-og**   | 256 MB | 192.168.188.144 | ✅ running | WLAN AP OG (OpenWRT)                                  |
| 111 | CT  | **pihole-2**     | 512 MB | 192.168.188.249 | ✅ running | Sekundär DNS (Fallback)                               |

### Geplante VMs / Container (noch nicht erstellt)

| VM/CT          | Funktion                     | Ziel-Node  |
| -------------- | ---------------------------- | ---------- |
| vm-postgres    | Zentrale Datenbank           | proxmox-ug |
| vm-redis       | Cache / Session              | proxmox-ug |
| vm-mqtt        | Mosquitto Broker (dediziert) | proxmox-ug |
| vm-grafana     | Monitoring Dashboard         | proxmox-ug |
| vm-prometheus  | Metriken                     | proxmox-ug |
| vm-nextcloud   | Dateispeicher                | proxmox-ug |
| vm-caddy       | Reverse Proxy                | proxmox-ug |
| vm-brainportal | Admin-Weboberfläche          | proxmox-ug |
| vm-pihole      | DNS / Werbeblocker           | proxmox-ug |
| vm-frigate     | Kamera / AI-Detection        | proxmox-ws |
| vm-nodered     | Automationen                 | proxmox-ug |
| vm-zigbee2mqtt | Zigbee Coordinator           | proxmox-ug |
| vm-llm         | Lokales LLM (Llama/DeepSeek) | proxmox-ug |

---

## 4. Netzwerkplan

### Aktueller Stand (Ist-Zustand, März 2026)

```text
Netzwerk:       192.168.188.0/24  (flach, kein VLAN)
DNS:            192.168.188.251  (pihole.brain, Pi-hole v6) ✅
DNS-Fallback:   192.168.188.249  (pihole-2.brain, Pi-hole v6) ✅
Domain:         brain  (DNS-Suffix über Pi-hole)
Router:         192.168.188.1    (brainhome.fritzbox) ✅
Proxmox:        192.168.188.254  (proxmox.brain / proxmox-dev.brain) ✅
Proxmox-EG:     192.168.188.253  (proxmox-eg.brain) ✅
Proxmox-OG:     192.168.188.252  (proxmox-og.brain) ✅
Proxmox-UG:     192.168.188.248  (proxmox-ug.brain → .249) ✅
HA-Master:      192.168.188.142  (ha-master.brain) ✅
HA-UG:          192.168.188.152  (ha-ug.brain) ✅
HA-OG:          192.168.188.143  (ha-og.brain) ✅
HA-EG:          192.168.188.194  (ha-eg.brain) ✅  ← IP korrigiert (war .148)
HA-GA:          192.168.188.191  (ha-ga.brain) ✅  VM115, proxmox-ug, Remote Node
Keycloak:       192.168.188.107  (keycloak.brain) ✅
Caddy:          192.168.188.200  (caddy.brain) ✅
NAS:            192.168.188.42   (nas.brain) ✅
Strommeter:     192.168.188.115  (strommeter.brain) ✅
AP EG:          192.168.188.70   (ap-eg.brain) ✅
AP OG:          192.168.188.71   (ap-og.brain) ✅
```

### Geplante VLAN-Struktur

| VLAN | Subnetz      | Zweck                              | Status |
| ---- | ------------ | ---------------------------------- | ------ |
| 10   | 10.10.0.0/24 | Management (Proxmox, SSH, Admin)   | 🔲     |
| 20   | 10.20.0.0/24 | Server (VMs, Services)             | 🔲     |
| 30   | 10.30.0.0/24 | IoT-Geräte (ESP32, Zigbee, Shelly) | 🔲     |
| 40   | 10.40.0.0/24 | Kameras (Frigate, IP-Cams)         | 🔲     |
| 50   | 10.50.0.0/24 | Gäste-WiFi                         | 🔲     |
| 60   | 10.60.0.0/24 | Werkstatt (CNC, Drucker)           | 🔲     |
| 70   | 10.70.0.0/24 | Automation (HA, MQTT intern)       | 🔲     |

### WLAN SSIDs (geplant)

| SSID         | Band          | Zweck          | Status |
| ------------ | ------------- | -------------- | ------ |
| BrainWLAN-EG | 5GHz / 2.4GHz | Wohnen EG      | 🔲     |
| BrainWLAN-OG | 5GHz / 2.4GHz | Wohnen OG      | 🔲     |
| BrainWLAN-UG | 5GHz / 2.4GHz | Keller/Server  | 🔲     |
| BrainIoT     | 2.4GHz        | IoT-Geräte     | 🔲     |
| BrainGuest   | 2.4GHz        | Gäste isoliert | 🔲     |

---

## 5. DNS & Naming Schema

|               |                                            |
| ------------- | ------------------------------------------ |
| Lokale Domain | `brain` (Short-Domain via Pi-hole)         |
| DNS Server    | Pi-hole v6 ✅ aktiv                        |
| Konfiguration | `/etc/pihole/pihole.toml` → `dhcp.hosts[]` |

### Hostname-Schema (Ist-Zustand)

```text
proxmox.brain        → 192.168.188.254  (lokaler Cluster-Node)
proxmox-dev.brain    → 192.168.188.253  (DNS-Alias, ehemals proxmox-eg)
proxmox-eg.brain     → 192.168.188.253  (Cluster-Node EG)
proxmox-og.brain     → 192.168.188.252  (Cluster-Node OG)
proxmox-ug.brain     → 192.168.188.249  (DNS-Alias für proxmox-ug)
pihole.brain         → 192.168.188.251
pihole-2.brain       → 192.168.188.249
keycloak.brain       → 192.168.188.107
caddy.brain          → 192.168.188.200
nas.brain            → 192.168.188.42
```

### Naming-Prinzip

- **Cluster-Node-Namen** spiegeln die physische Zone wider: `proxmox-eg`,
  `proxmox-og`, `proxmox-ug`
- **Lokaler Node** (`proxmox`) bleibt Cluster-intern `proxmox`; DNS-Alias
  `proxmox-dev.brain` für Entwicklungszugriff
- **Kein Cluster-Node-Rename** — zu riskant (Corosync/Quorum), DNS-Aliases
  stattdessen
- **Domain**: `brain` (kurz, kein `.local` wegen mDNS-Konflikten)

---

## 6. Identity & Auth (Keycloak)

|             |                                            |
| ----------- | ------------------------------------------ |
| VM          | idp-keycloak (VMID 107)                    |
| Status      | ✅ VM läuft                                |
| Integration | ⚙️ noch nicht mit Services verbunden       |
| Realm       | `brainhome`                                |
| URL         | 192.168.188.107 / keycloak.brain (geplant) |

### Geplante Clients (OIDC)

| Client        | Service           | Status |
| ------------- | ----------------- | ------ |
| homeassistant | alle HA Instanzen | 🔲     |
| grafana       | Monitoring        | 🔲     |
| nextcloud     | Dateispeicher     | 🔲     |
| brainportal   | Admin-UI          | 🔲     |
| frigate       | Kamera            | 🔲     |

### Login-Flow

```text
User
 ↓
Keycloak (OIDC)
 ↓
Access Token
 ↓
Service (HA / Grafana / Portal / Nextcloud...)
```

---

## 7. Reverse Proxy (Caddy)

|          |                         |
| -------- | ----------------------- |
| Status   | ✅ aktiv                |
| CT-ID    | 110                     |
| IP       | 192.168.188.200         |
| Hostname | caddy.brain             |
| Version  | v2.11.2                 |
| TLS      | local_certs (lokale CA) |
| SSH      | `ssh caddy`             |

### Routing (aktiv)

```text
ha-ug.brain      →  192.168.188.152:8123
keycloak.brain   →  192.168.188.107:8080
pihole.brain     →  192.168.188.251:80
proxmox.brain    →  192.168.188.254:8006
strommeter.brain →  192.168.188.115:80
```

---

## 8. Home Automation Stack

### Home Assistant Instanzen

| Instanz     | Zone | IP              | Status              | Config                        |
| ----------- | ---- | --------------- | ------------------- | ----------------------------- |
| **haos-ug** | UG   | 192.168.188.145 | ✅ aktiv            | `/home/haos-configs/haos-ug/` |
| haos-eg     | EG   | –               | ⚙️ Config vorhanden | `/home/haos-configs/haos-eg/` |
| haos-og     | OG   | –               | ⚙️ Config vorhanden | `/home/haos-configs/haos-og/` |
| haos-ws     | WS   | –               | 🔲                  | –                             |

### MQTT

|                   |                     |
| ----------------- | ------------------- |
| Broker            | Mosquitto           |
| Aktuell läuft auf | haos-ug (Add-On)    |
| Geplant           | dedizierter vm-mqtt |
| Status            | ✅ aktiv            |

**Topic-Schema:**

```text
brainhome/{zone}/{gerät}/state
brainhome/{zone}/{gerät}/set
brainhome/{zone}/sensor/{name}

Beispiele:
aionthedge/strommeter          → ✅ aktiv (Energiezähler)
brainhome/eg/kitchen/light     → 🔲
brainhome/ws/cnc/status        → 🔲
brainhome/garden/water         → 🔲
```

### Zigbee

|             |                      |
| ----------- | -------------------- |
| Software    | Zigbee2MQTT          |
| Coordinator | Sonoff Zigbee Dongle |
| Status      | 🔲 geplant           |

**Geräteklassen:** Buttons, Relais, Sensoren, Licht, Rollos

---

## 9. Physische Geräte (aktuell vorhanden)

| Gerät              | Typ                      | IP              | Zone | Status              |
| ------------------ | ------------------------ | --------------- | ---- | ------------------- |
| **Strommeter**     | ESP32-CAM AI-on-the-Edge | 192.168.188.115 | UG   | ✅ aktiv, 35505 kWh |
| **NAS**            | Synology / QNAP          | 192.168.188.42  | UG   | ✅ (Proxmox Backup) |
| **AP EG**          | OpenWRT Repeater         | 192.168.188.70  | EG   | ✅                  |
| **AP OG**          | OpenWRT Repeater         | 192.168.188.71  | OG   | ✅                  |
| **brainPiEingang** | Raspberry Pi             | –               | EG   | ⚙️                  |

---

## 10. AI / Vision / Voice Stack

### Frigate (Kamera + AI-Detection)

|           |                                     |
| --------- | ----------------------------------- |
| Status    | 🔲 geplant                          |
| Hardware  | Coral TPU oder RX570 GPU (im Tower) |
| Ziel-Node | proxmox-ws                          |
| Features  | Person / Fahrzeug / Tier Erkennung  |

### LLM (Lokal)

|          |                                                 |
| -------- | ----------------------------------------------- |
| Status   | 🔲 geplant                                      |
| Hostname | llm.brain                                       |
| Modelle  | Llama 3, DeepSeek, Code-Modell                  |
| Hardware | Tower GPU (RX570 oder upgrade)                  |
| Aufgaben | Coding-Assistent, Automation-Hilfe, BrainGarden |

### Voice

|          |                                   |
| -------- | --------------------------------- |
| Status   | 🔲 geplant                        |
| Option   | Home Assistant Voice Pipeline     |
| Hardware | Raspberry Pi + Mikrofon + Speaker |

---

## 11. Werkstatt / Maker Integration (proxmox-ws)

| Service           | Funktion                          | Status |
| ----------------- | --------------------------------- | ------ |
| cnc-control       | CNC-Maschinen-Status & Steuerung  | 🔲     |
| cad-storage       | CAD-Dateien via Nextcloud         | 🔲     |
| print-server      | 3D-Drucker / Papierdrucker        | 🔲     |
| camera            | Werkstatt-Kamera (Frigate)        | 🔲     |
| ha-ws             | Home Assistant Werkstatt          | 🔲     |
| Energy Monitoring | Stromverbrauch Maschinen per MQTT | 🔲     |
| Dust Automation   | Absauganlage via HA               | 🔲     |

---

## 12. BrainPortal (Adminfrontend)

|           |                                                                                      |
| --------- | ------------------------------------------------------------------------------------ |
| Code      | `/home/webserver/`                                                                   |
| Status    | ✅ Angular 16 kompiliert, ng-serve läuft (CT112 :4200)                               |
| Dev-URL   | <http://192.168.188.112:4200>                                                        |
| Ziel-URL  | portal.brain                                                                         |
| Stack     | Angular 16 (Frontend) + Quarkus Java (Backend) + PostgreSQL                          |
| Submodule | `frontend/projects/webBase` (GitHub), `frontend/projects/formantic-ui-less` (GitHub) |

### Dev-Umgebung (CT112 – brainhome-dev)

```bash
# ng serve Status prüfen
pct exec 112 -- systemctl status ng-serve16

# Build-Log
pct exec 112 -- tail -f /tmp/ng-dev16.log

# Neuen ng serve starten (N = nächste Zahl)
pct exec 112 -- systemd-run --unit=ng-serve17 \
  --property="WorkingDirectory=/home/webserver/frontend" \
  --property="StandardOutput=file:/tmp/ng-dev17.log" \
  --property="StandardError=file:/tmp/ng-dev17.log" \
  /home/webserver/frontend/node_modules/.bin/ng serve \
  --proxy-config proxy.conf.develop.json --host 0.0.0.0
```

**Durchgeführte Umbenennung** (März 2026):

- ✅ `vce` → `brainhome` Klassen-/Komponenten-Rename abgeschlossen
- ✅ Alle Angular NG5002 HTML-Parser-Fehler behoben
- ✅ ng-serve16 kompiliert erfolgreich (Compilation Hash: 13816aebafe2cd16)
- ✅ `@ngx-translate/core` Sub-Path Exports gepatcht
- ✅ `brainhome-*` CSS-Klassen in formantic-ui-less
- ⚠️ `vceEnum` Pipe bewusst NICHT umbenannt (alle Templates referenzieren
  `| vceEnum`)

**Aktive Module (Dashboard):**

- Smart Home Dashboard (HA-Integration)
- Server / VM Status (Proxmox API)
- Geräte-Übersicht (Strommeter, APs, ESP32)
- Energie-Monitoring (Verlauf, Statistiken)
- Kamera-Übersicht (Frigate)
- Werkstatt-Status (CNC, 3D-Drucker)
- AI Interface (LLM Chat)
- User-Verwaltung (via Keycloak)

**Docs:**

- Umbauplan: `/home/webserver/TODO.md`
- Entwickler-Wissen: `/home/webserver/ENTWICKLER-WISSEN.md`
- Frontend: `/home/webserver/frontend/README.md`

---

## 13. Monitoring Stack

| Service         | Funktion                         | Status             |
| --------------- | -------------------------------- | ------------------ |
| Prometheus      | Metriken-Sammlung                | 🔲                 |
| Grafana         | Dashboards                       | 🔲                 |
| Node Exporter   | Server-Metriken (CPU, RAM, Temp) | 🔲                 |
| HA Sensor-Daten | Energie, Temp, MQTT              | ⚙️ in HA vorhanden |

---

## 14. Storage & Backup

|                             |                                  |
| --------------------------- | -------------------------------- | --- |
| NAS                         | 192.168.188.42 (Synology/QNAP)   | ✅  |
| Proxmox Backup              | NFS-Mount auf NAS                | ✅  |
| ZFS                         | geplant für VM-Storage auf Nodes | 🔲  |
| Ceph                        | optional für Cluster-Storage     | 🔲  |
| PBS (Proxmox Backup Server) | dedizierte VM/Node               | 🔲  |

---

## 15. Git Repositories (geplant)

| Repo                   | Inhalt                             | Aktuell                                                               |
| ---------------------- | ---------------------------------- | --------------------------------------------------------------------- |
| `brainhome-infra`      | Proxmox-Configs, Netzwerk, Scripts | `/home/` (lokal)                                                      |
| `brainhome-automation` | HA-Configs, YAML, Automationen     | `${BRAINHOME_ROOT}/HomeAssistant/`, `${BRAINHOME_ROOT}/haos-configs/` |
| `brainhome-portal`     | BrainPortal Frontend + Backend     | `/home/webserver/`                                                    |
| `brainhome-docs`       | Architektur, Planung, Checklisten  | `${BRAINHOME_ROOT}/architektur/`                                      |

---

## 16. Gesamtübersicht – Was ist vorhanden?

```text
✅ = vorhanden & funktioniert
⚙️ = vorhanden, noch nicht fertig
🔲 = geplant, noch nicht gestartet
```

### Infrastruktur

```text
✅  proxmox-ug  (192.168.188.254) — ThinkCentre M920Q: Keycloak, Caddy, BrainHome Dev
✅  proxmox-eg  (192.168.188.253) — ThinkCentre M920Q: HA-Master/EG/UG, pihole, openwrt-eg
✅  proxmox-og  (192.168.188.252) — ThinkCentre M920Q: HA-OG, pihole-2, openwrt-og
✅  NAS (192.168.188.42, Proxmox-Backup eingerichtet)
✅  VM idp-keycloak (läuft, noch nicht integriert)
🔲  Proxmox Cluster (mehrere Nodes zusammenschalten)
🔲  proxmox-ws, proxmox-se (geplant)
```

### Netzwerk

```text
✅  Flaches Netz 192.168.188.0/24
✅  AP EG (192.168.188.70, OpenWRT)
✅  AP OG (192.168.188.71, OpenWRT)
✅  Pi-hole DNS (192.168.188.251, v5.18.4)
✅  brain.local + brain Hostnamen konfiguriert
✅  SSH-Key Proxmox → Pi-hole
🔲  VLANs (10/20/30/40/50/60/70)
🔲  Caddy Reverse Proxy
```

### Home Automation

```text
✅  haos-ug (192.168.188.145, aktiv, 35+ Entities)
✅  MQTT Mosquitto (auf haos-ug)
✅  Strommeter (192.168.188.115, AI-on-the-Edge, MQTT→HA)
⚙️  haos-eg (Config vorhanden, VM noch nicht final)
⚙️  haos-og (Config vorhanden, VM noch nicht final)
⚙️  brainPiEingang (Raspberry Pi, in Konfiguration)
🔲  haos-ws
🔲  Zigbee2MQTT + Coordinator
🔲  NodeRed
```

### Services

```text
✅  Keycloak (VM läuft, Realm noch nicht konfiguriert)
🔲  PostgreSQL (dediziert)
🔲  Grafana / Prometheus
🔲  Nextcloud
🔲  Frigate
🔲  LLM Server
🔲  Caddy
🔲  Pi-hole
```

### BrainPortal

```text
⚙️  Code-Basis vorhanden (/home/webserver/)
⚙️  Angular Frontend + Quarkus Backend (umbau nötig)
🔲  Deployment auf VM
🔲  Integration mit Keycloak / HA / Proxmox-API
```

### Dokumentation & Konfiguration (in /home/)

```text
✅  ${BRAINHOME_ROOT}/architektur/ → Infrastruktur-Planung, SVG-Diagramm
✅  ${BRAINHOME_ROOT}/HomeAssistant/ → HA-Configs, Scripts, Deploy-Tools
✅  ${BRAINHOME_ROOT}/haos-configs/  → Live HA-Konfigurationen (UG/EG/OG)
✅  ${BRAINHOME_ROOT}/AI-on-the-edge/ → Strommeter-Doku + Scripts
✅  ${BRAINHOME_ROOT}/openwrt-repeater-setup/ → AP-Konfiguration
✅  ${BRAINHOME_ROOT}/../webserver/ → BrainPortal Code-Basis (unabhängiger Checkout)
✅  ${BRAINHOME_ROOT}/workstation/ → Tower-Proxmox Specs, Backup-Doku
✅  ${BRAINHOME_ROOT}/system-monitor/ → System-Monitoring Scripts
✅  ${BRAINHOME_ROOT}/appstore-system/ → App-Store / Dashy Setup
✅  /home/brainPiEingang/       → Pi Eingang-System Doku
```

---

## 17. Nächste Schritte (Priorität)

1. **Caddy einrichten** — Reverse Proxy VM/CT, TLS, erste Subdomains
   (`portal.brain`, `ha-ug.brain`)
2. **Keycloak konfigurieren** — Realm `brainhome` anlegen, ersten Client (HA-UG)
   verbinden
3. **haos-eg / haos-og** — VMs finalisieren, deployen
4. **FritzBox** — Pi-hole als primären DNS eintragen (192.168.188.251)
5. **BrainPortal** — Alten Code aufräumen, erste eigene Module bauen
6. **Energie-Dashboard HA-UG** — Strommeter entity in HA Energy Dashboard
   eintragen
7. **Grafana + Prometheus** — Proxmox-Metriken sichtbar machen
8. **VLAN-Planung** — Router konfigurieren, IoT trennen

---

## 18. Betriebsstandard: QEMU Guest Agent & Locale

Zur Vermeidung wiederkehrender Betriebsprobleme gelten clusterweit folgende
Standards:

1. **QEMU Guest Agent auf allen VMs aktiv**
2. **Locale `de_DE.UTF-8` auf allen Proxmox-Nodes, Debian/Ubuntu-VMs und CTs
   gesetzt**

### 18.1 QEMU Guest Agent (VMs)

- Proxmox-Seite (pro VM):
  `bash     pvesh set /nodes/<node>/qemu/<VMID>/config -agent enabled=1,fstrim_cloned_disks=1`
- Gast-Seite (Debian/Ubuntu):
  `bash     apt-get install -y qemu-guest-agent     systemctl enable --now qemu-guest-agent`
- Gast-Seite (OpenWRT):
  `bash     opkg update && opkg install qemu-ga     /etc/init.d/qemu-ga enable && /etc/init.d/qemu-ga start`
- HAOS: Agent ist integriert, es reicht das Proxmox-Hardware-Flag.

### 18.2 Locale-Standard (de_DE.UTF-8)

- Auf Debian/Ubuntu/Proxmox:

  ```bash
  sed -i 's/^# de_DE.UTF-8 UTF-8/de_DE.UTF-8 UTF-8/' /etc/locale.gen
  locale-gen
  cat > /etc/default/locale << 'EOF'
  LANG=de_DE.UTF-8
  LC_ALL=de_DE.UTF-8
  EOF
  ```

- Auf CTs via Proxmox-Node (C-Locale für den Befehl selbst):

  ```bash
  LC_ALL=C LANG=C pct exec <CTID> -- bash -c "...locale-gen..."
  ```

### 18.3 Rollout-Tooling & Tickets

- Standard-Rolloutscript:
  `bash /home/pxe-boot/scripts/vm-node-setup.sh --host <IP> --type <vm|ct|node> --os <debian|haos|openwrt|proxmox>`
- Tickets: - `F302E6` (QEMU Guest Agent auf allen VMs) - `1B2089`
  (Locale-Rollout auf Nodes/VMs/CTs)

---

_Letzte Aktualisierung: 20.03.2026 | Datei:
`${BRAINHOME_ROOT}/architektur/BRAINHOME-ARCHITEKTUR.md`_
