# BrainHome – Master TODO

> Alle offenen Aufgaben der gesamten Infrastruktur.
> Status: `[ ]` offen | `[x]` erledigt | `[-]` in Arbeit

---

## Workspace Modularisierung (DDB696)

- [x] Pro Modul eigene VS Code Umgebung ausgerollt: `.code-workspace` + `.vscode/settings.json` + `.vscode/extensions.json`
- [x] HomeAssistant Submodule separat gemacht: `haos`, `haos-eg`, `haos-og`, `haos-ug`
- [x] BrainHome zentral bleibt unveraendert nutzbar; Module koennen jetzt einzeln in passender Umgebung geoeffnet werden
- [x] Lessons aus Infra-Migration eingearbeitet (Pre-Flight, Verbindungs-Kontext, DNS-Fallback)

### Modul-spezifische Verbesserungen (naechste Schritte)

- [x] webserver: Runbook fuer sichere Migrationen als Task-Flow standardisieren (`Pre-Flight -> Migrate -> Verify -> Ticket done`)
- [ ] HomeAssistant/haos*: pro Instanz eigene Validierungs-Tasks (Config-Check, Template-Check, Service-Restart)
- [ ] caddy: Workspace-Task fuer Keepalived/Caddy Health + VIP-Pruefung nach jeder Aenderung
- [ ] pihole: Workspace-Task fuer DNS-Health auf beiden Instanzen (`pihole-1`, `pihole-og`) + Sync-Check
- [ ] keycloak: Export/Import + Realm-Backup Tasks als Standard aufnehmen
- [ ] grafana: Dashboard-Lint/Provisioning-Check als Task aufnehmen
- [ ] pxe-boot/fritzbox/autarkie/system-monitor: je Modul 2-3 Kern-Tasks fuer Health und Logs vereinheitlichen

## Aktuelle Log-Probleme
- [ ] PXE-HTTP Deployment: Port-80-Konflikt im Docker-Host-Netzwerk erkennen und dokumentieren.
- [ ] PXE-HTTP Loghinweis: `directory index of "/usr/share/nginx/html/" is forbidden` ist kein Blocker, solange die Boot-Assets direkt erreichbar sind.
- [ ] Backup-Problem: NFS-gehostete LXC-Container fallen bei `vzdump --mode snapshot` auf `suspend` zurück und können Keepalived einfrieren.
- [ ] Kurzfristige Backup-Schutzmaßnahmen dokumentieren: `vzdump --nofreeze`, gestaffelte Backup-Fenster, Backup-Jobs entkoppeln, Backup-Streams priorisieren.
- [ ] Langfristige Lösung: LXC-Storage von NFS auf `local-lvm` migrieren oder PBS einführen.

---

## 🔴 Prio 1 – Grundfundament

### Keycloak
- [x] Realm `brainhome` anlegen
- [x] Admin-User konfigurieren (brain, stef)
- [x] Keycloak über Caddy erreichbar machen (`keycloak.brain`)
- [x] Client `caddy-sso` angelegt
- [x] Client `homeassistant-ug` anlegen (war bereits vorhanden)
- [x] Clients `homeassistant-master`, `homeassistant-eg`, `homeassistant-og` (waren vorhanden)
- [x] HA-UG mit Keycloak SSO verbinden (`hass-oidc-auth` v0.6.5-alpha, Provider aktiv)
- [x] HA-Master, HA-EG, HA-OG mit Keycloak SSO verbinden (alle 4 Instanzen aktiv)

### DNS (Pi-hole)
- [x] Pi-hole läuft bereits (192.168.188.251, v5.18.4)
- [x] SSH-Key von Proxmox auf Pi-hole eingerichtet (`ssh pihole`)
- [x] `brain.local` + `brain` als lokale Domains konfiguriert
- [x] Hostnamen eingetragen: proxmox, ha-ug, keycloak, pihole, strommeter, ap-eg, ap-og, nas
- [x] Router/DHCP: Pi-hole als primären DNS eintragen (FritzBox → 192.168.188.251)
- [x] Zweiten Pi-hole als Fallback (pihole-2 → 192.168.188.249)
- [x] Caddy / portal.brain DNS-Eintrag ergänzen → 192.168.188.200 portal.brain (Pi-hole + Caddy, März 2026)

### Caddy Reverse Proxy
- [x] Caddy LXC Container 110 angelegt (192.168.188.200, Debian 12)
- [x] Caddy v2.11.2 installiert, läuft
- [x] `caddy.brain` DNS-Eintrag gesetzt
- [x] SSH-Key eingerichtet (`ssh caddy`)
- [x] Routing konfiguriert: ha-ug, keycloak, pihole, proxmox, strommeter
- [x] `local_certs` TLS aktiv
- [x] Root-CA-Zertifikat auf Server-Systeme verteilt (`distribute-ca.sh`, gültig bis 2036)
- [x] Root-CA in Browser/Clients importieren → `http://caddy.brain/` (Anleitung + Download, März 2026)
- [x] `portal.brain` Route hinzufügen → reverse_proxy CT116:8081, Alias für brainhome-prod (März 2026)
- [x] `grafana.brain`, `nextcloud.brain` → bereits im Caddyfile aktiv (März 2026)

---

## 🟠 Prio 2 – Home Automation

### haos-master
- [x] Keycloak SSO (`hass-oidc-auth`, client: homeassistant-master, aktiv)
- [x] remote_homeassistant: EG (`.194`), OG (`.143`), UG (`.152`), GA (`.191`) alle connected und `loaded` (26.03.2026)
- [x] remote_homeassistant Verbindungen nach VM-Resets re-verifiziert: EG/OG/UG/GA alle `loaded` (27.03.2026)
- [x] **ha-master IP statisch setzen** — DHCP-Reservation in FritzBox für MAC `02:01:04:25:6E:45` → `.142` gesetzt, oauth2-proxy + Pi-hole bereits korrekt konfiguriert (27.03.2026)
- [ ] Erste Automationen / zentrale Logik einrichten

### haos-eg
- [x] Keycloak SSO (`hass-oidc-auth`, client: homeassistant-eg, aktiv)
- [x] Config aus `haos-configs/haos-eg/` übernehmen (Mar 2026, ha core check ✓)
- [x] IP korrigiert: `.148` → `.194` via REST-API-Flow (26.03.2026, Entry `01KMNT410RGERBG5B5CW9EXRGJ`)
- [x] Bluetooth-USB Passthrough gesetzt (`usb1: host=2357:0604,usb3=1`) auf VM102/proxmox-eg (27.03.2026)
- [x] HA Core erreichbar (8123 OPEN, 27.03.2026 nach Backup-Incident Wiederherstellung)
- [x] MQTT (core-mosquitto) läuft auf ha-eg: Integration `loaded` (27.03.2026)
- [x] Zigbee2MQTT Bridge auf ha-eg aktiv: `connection_state = on`, Version 2.9.1 (27.03.2026)
- [x] ZHA-Leiche entfernt (war nie konfiguriert, `data={}`) – Z2M bleibt Zigbee-Stack auf ha-eg (27.03.2026)
- [x] **Bluetooth Integration** eingerichtet: hci0 TP-Link RTL8761BU `3C:6A:D2:B5:82:F6`, entry `01KMQ6HEETYK87GM1CKTBFWD7E`, state `loaded` (27.03.2026)
- [ ] Erste Entitäten (Licht, Sensoren EG) einrichten

### haos-og
- [x] Keycloak SSO (`hass-oidc-auth`, client: homeassistant-og, aktiv)
- [x] Config aus `haos-configs/haos-og/` übernehmen (Mar 2026, ha core check ✓)
- [x] Bluetooth-USB Passthrough gesetzt (`usb1: host=2357:0604,usb3=1`) auf VM103/proxmox-og (27.03.2026)
- [x] HA Core erreichbar (8123 OPEN, 27.03.2026 nach Backup-Incident Wiederherstellung)
- [x] MQTT (core-mosquitto) läuft auf ha-og: Integration `loaded` (27.03.2026)
- [x] Zigbee2MQTT Bridge auf ha-og aktiv: `connection_state = on` (27.03.2026)
- [x] ZHA-Leiche entfernt (war nie konfiguriert, `data={}`) – Z2M bleibt Zigbee-Stack auf ha-og (27.03.2026)
- [x] **Bluetooth Integration** eingerichtet: hci0 TP-Link RTL8761BU `50:3D:D1:BC:20:F0`, entry `01KMQ6HE8GNA38EMCRM1KEB710`, state `loaded` (27.03.2026)
- [ ] Erste Entitäten OG einrichten

### haos-ga
- [x] VM115 auf proxmox-ug angelegt (192.168.188.191), HAOS 2026.3.2
- [x] SSH-Addon aktiviert (Port 22, Passwort-Auth)
- [x] `remote_homeassistant` Custom Component von ha-master übertragen + als Remote Node eingerichtet (26.03.2026)
- [x] Discovery-Endpoint aktiv: `http://192.168.188.191:8123/api/remote_homeassistant/discovery` → 200 OK
- [x] Keycloak-Client `homeassistant-ga` anlegen + SSO einrichten (ausstehend)
- [x] LLT-Token erstellt, gespeichert in `grafana/docker/secrets/ha_ga_token`
- [x] ha-master verbunden: zeroconf-Flow bestätigt, Entry `01KMNT0F2Y5Y0R5J3H802V0NNB`, state `loaded` (26.03.2026)
- [x] Keycloak SSO (`auth_oidc` v0.6.5, client `homeassistant-ga`) – BrainHome SSO Button aktiv (27.03.2026)
- [x] Prometheus-Scraping: ha_ga_token Secret-Bug behoben (war Verzeichnis statt Datei), ha-ga jetzt `up` (27.03.2026)
- [ ] Erste Entitäten (Licht, Sensoren GA/Garage) einrichten

### haos-ug (Erweiterungen)
- [x] HA Core erreichbar (8123 OPEN, 27.03.2026 nach Backup-Incident Wiederherstellung)
- [x] Energie-Dashboard einrichten (Strommeter `sensor.strommeter_main_value`) – `.storage/energy` korrigiert: Grid auf `strommeter_main_value`, Solar auf Solarman `192_168_188_88/97_total_production` (27.03.2026)
- [x] Keycloak SSO integrieren (`hass-oidc-auth`, BrainHome SSO Button aktiv)
- [x] Grafana-Anbindung für Sensor-Daten (Prometheus scrapet ha-ug: 501 Entities, Energy-Dashboard deployt 27.03.2026)
- [x] Zigbee-USB Passthrough gesetzt (`usb2: host=10c4:ea60,usb3=1`) auf VM106/proxmox-ug (27.03.2026)
- [x] **Bluetooth Integration** eingerichtet: hci0 Intel AX210 `AC:45:EF:A2:81:85`, entry `01KMQ6HEN6MKR8WMCX1T4NSHKM`, state `loaded` (27.03.2026)

### ☀️ Solaranlage & Autarkie (haos-ug)
- [x] Solarman-Integration: davidrapan v25.08.16 migriert (15.03.2026)
- [x] `/home/autarkie/` Workspace-Ordner angelegt (Docs, Scripts, Daten)
- [x] **Solarman Cloud API**: APP_ID + APP_SECRET eintragen → `solarman-api.env` (bereits vorhanden, März 2026)
- [x] **Historische Daten laden**: `fetch-solarman-cloud.py --start 2023` – Süd: 2150 kWh, West: 1642 kWh (34 Monate je, 2023-06 bis 2026-03) in `/home/autarkie/data/cloud/` (27.03.2026)
- [x] **HA Statistics importieren**: `import-ha-statistics.py` – 68 Datenpunkte in `sensor.192_168_188_88/97_total_production` via WebSocket recorder/import_statistics (27.03.2026); ENTITY_MAP auf neue Solarman-Sensor-IDs aktualisiert
- [x] `_2`-Duplikat-Entities auf HA-Master bereinigen – entity_filters auf alle 4 RHA-Verbindungen angewandt, 1108 verwaiste Registry-Einträge entfernt, True-Dups von 161–336 → 29 reduziert (26.03.2026, Details: ERLERNTES-WISSEN.md §15)
- [x] **ha-eg**: Rolladen-Duplikate behoben – 56 veraltete Registry-Einträge (alte Z2M-Kurzname-Entities vor dem Umbenennen) auf ha-eg + 53 weitergeleitete auf ha-master gelöscht; `automation`-Domain zu ha-eg exclude_domains hinzugefügt (27.03.2026)
- [x] **ha-og**: Küchenlicht-Duplikat behoben – `switch.og_kuche_deckenlicht` war stale Z2M-Rename-Relikt (uid=`3_switch_zigbee2mqtt`), auf ha-og + ha-master gelöscht (27.03.2026)
- [x] **ha-ug**: Solarman `_2/_3`-Entities sind **False Positives** – `sensor.*_today/total_production_2/3` sind MPPT-Tracker-Entities (MPPT 2, MPPT 3), nicht echte Duplikate; kein Fix nötig
- [x] **ha-master**: Template-Konflikt `sensor.fenster_2` behoben – `name: Fenster` in `templates/wohnzimmer.yaml` → `name: EG Wohnzimmer Fenster` umbenannt, Registry-Eintrag gelöscht (27.03.2026)
- [x] **ha-og**: `switch.og_kuche_deckenlicht_2` behoben – Ursache war Z2M-Gruppe (Group 3 `og_küche_deckenlicht`) + physikalisches Gerät mit identischem Namen; Gruppe via Z2M MQTT API zu `og_küche_deckenlicht_gruppe` umbenannt, Registry auf ha-og + ha-master bereinigt (27.03.2026)

### Zigbee
- [x] Zigbee-Dongle an ha-ug durchgereicht (Sonoff/CP210x `10c4:ea60`, VM106 `usb2`) (27.03.2026)
- [x] MQTT (Mosquitto broker) läuft auf ha-ug: Integration `loaded` (27.03.2026)
- [ ] **Zigbee2MQTT Addon auf ha-ug einrichten** — Dongle `/dev/ttyUSB0` (Sonoff CP210x) bereit; Z2M Addon über Supervisor installieren + serial port `/dev/ttyUSB0` konfigurieren (wie ha-og/ha-eg)

### MQTT (dediziert)
- [ ] Separaten Mosquitto-Container anlegen (aktuell: HA Add-On)
- [ ] Topic-Schema `brainhome/{zone}/{gerät}/...` einführen
- [ ] Alle HA-Instanzen auf zentralen Broker umstellen

---

## 🟡 Prio 3 – Services & Monitoring

### Grafana + Prometheus
- [x] **TICKET BH-GRAFANA-001**: Grafana Workspace-Geruest unter `/home/grafana/` erstellt (README, TODO, docker, config, scripts, docs)
- [x] VM `monitoring.brain` (192.168.188.108, VM-ID 118) angelegt und Stack deployed (`/home/grafana/scripts/deploy.sh start`)
- [x] Prometheus Container anlegen
- [x] Node Exporter auf proxmox, proxmox-eg, proxmox-og, proxmox-ug installieren
- [x] Proxmox-Metriken scrapen (node-exporter auf allen 4 Nodes aktiv)
- [x] Grafana Container anlegen + Datasource konfigurieren
- [x] Dashboard: Server CPU / RAM / Temp (Temperatur-Section in proxmox.json, Provisioning-Fix, SSO-Fix)
- [x] Dashboard: Energie (Strommeter + Solaranlage + Heizkessel — 20 Panels, deployt 2026-04)
- [x] Grafana mit Keycloak SSO verbinden (SSO aktiv → `grafana.brain` via Keycloak)

### Nextcloud
> Workspace: `/home/nextcloud/` | Repo: https://github.com/5t3mp3l/nextcloud
- [x] VM 121 angelegt auf proxmox-dev (4 GB RAM, 100 GB, IP: 192.168.188.121) 2026-03-21
- [x] Docker Compose Stack deployed: Nextcloud 29.0.16 + PostgreSQL 16 + Redis 7 + Collabora
- [x] Caddy-Route: `nextcloud.brain` → 192.168.188.121:80 (mit Security-Headern)
- [x] Caddy-Route: `office.brain` → 192.168.188.121:9980
- [x] Pi-hole DNS: `nextcloud.brain`, `nextcloud-core.brain`, `office.brain`
- [x] `nextcloud.brain` via Caddy erreichbar, Status: healthy
- [ ] Keycloak SAML 2.0 SSO (Client `nextcloud`, Realm `brainhome`) → **SAML-Client & Provider konfiguriert** (21.03.2026)
  - user_saml 6.6.1 aktiv, IdP-URL+Zertifikat gesetzt, Mapper: uid/email/groups
  - Ausstehend: manueller Login-Test + User-Provisioning
- [ ] User anlegen: brain, stef, willy, gast → nach SSO-Setup

### NodeRed
- [ ] Container anlegen
- [ ] MQTT-Verbindung konfigurieren
- [ ] Erste Flows: Automationen zwischen HA-Instanzen

---

## 🔵 Prio 4 – BrainPortal (Webserver)

> Code-Basis: `/home/webserver/` | Umbauplan: `/home/webserver/TODO.md`

- [ ] `npm install` im `frontend/` ausführen
- [ ] `./gradlew quarkusDev` testen – Backend starten
- [ ] Versand-spezifische Module entfernen (business-partner, transmissions)
- [ ] Modul `infrastructure/` anlegen → Proxmox-Node Status
- [ ] Modul `smart-home/` anlegen → HA-Instanzen Status
- [ ] Modul `devices/` anlegen → Strommeter, APs, ESP32
- [ ] Modul `energy/` anlegen → Energie-Verlauf
- [ ] Deployment VM einrichten
- [ ] Keycloak OIDC Integration
- [x] `portal.brain` via Caddy erreichbar → reverse_proxy CT116:8081 (März 2026)

---

## 🟣 Prio 5 – Netzwerk (VLAN)

- [ ] Router VLAN-fähig machen oder ersetzen
- [ ] VLANs anlegen: 10 (mgmt), 20 (server), 30 (iot), 40 (cams), 50 (guest), 60 (ws), 70 (auto)
- [ ] Proxmox vmbr-Bridges pro VLAN konfigurieren
- [ ] IoT-Geräte (ESP32, Shelly) in VLAN 30 isolieren
- [ ] Kameras in VLAN 40 isolieren
- [ ] WLAN SSIDs: BrainWLAN-EG/OG/UG, BrainIoT, BrainGuest
- [ ] APs (192.168.188.70/71) VLAN-fähig konfigurieren

---

## ⚫ Prio 6 – KI / Vision / Voice

- [ ] Frigate Container einrichten (proxmox-ws oder proxmox-dev)
- [ ] Coral TPU oder GPU für Frigate konfigurieren
- [ ] Erste Kamera anbinden
- [ ] Person-Detection testen
- [ ] Frigate → HA Integration
- [ ] LLM Server aufsetzen (Ollama + Llama 3 oder DeepSeek)
- [ ] Voice Pipeline in HA konfigurieren

---

## 🏗️ Prio 7 – Neue Proxmox Nodes

- [x] ThinkCentre EG → proxmox-eg (192.168.188.253) **aktiv** ✅
- [x] ThinkCentre OG → proxmox-og (192.168.188.252) **aktiv** ✅
- [x] ThinkCentre WS → proxmox-ws (192.168.188.247) **aktiv** ✅ (hostet ha-master VM101, grafana VM219, brainhome-workstation VM113)
- [ ] ThinkCentre SE kaufen / einrichten → proxmox-se (Edge/Router)
- [x] Proxmox Cluster `brainhome-cluster` aktiv (4 Nodes)
- [ ] Storage: ZFS auf den Nodes (→ wird durch proxmox-dt gelöst, TICKET DT0001)
- [ ] PBS (Proxmox Backup Server) VM einrichten (→ auf proxmox-dt, TICKET DT0001)

### proxmox-dt: Daten-/Storage-Server (TICKET `DT0001`) — kommt ~29.03.2026

> Geplante Inbetriebnahme: übermorgen (~29.03.2026)
> Rolle: Shared Storage + Nextcloud + PBS + Fileserver — **kein** Rechen-/AI-Server

**Aufgaben von proxmox-dt:**
- NFS-Shares ersetzen (aktuell: NAS als `shared-storage`, `backup-daily`, `backup-monthly`)
- Proxmox Backup Server (PBS) — dedizierte Backups aller Nodes/VMs/CTs mit Versionierung
- Nextcloud — Dateisync, Webzugriff, Familienfreigaben
- Fileserver — NFS + SMB zentral für BrainHome

**Geplante VMs/CTs auf proxmox-dt:**
| CT/VM | Dienst             | Storage-Bedarf         | Prio |
|-------|--------------------|------------------------|------|
| VM1   | Nextcloud           | SSD (schnell) + HDD (Daten) | hoch |
| VM2   | Proxmox Backup Server (PBS) | große HDD-Pool (ZFS) | hoch |
| CT3   | Fileserver (NFS+SMB)| HDD-Pool               | hoch |
| CT4   | Hilfsdienste (rsync, cron) | klein | niedrig |

**Storage-Architektur proxmox-dt (empfohlen):**

**Benötigter Storage-Typ: ZFS**
- Warum ZFS?
  - Daten-Integrität via Checksummen (CoW) — ideal für Backup-Server und Nextcloud
  - Snapshot-Support nativ → PBS profitiert direkt
  - RAID-ähnliche Redundanz (RAIDZ1/2) ohne Hardware-RAID
  - Kompression + Deduplizierung → spart Platz bei PBS
  - Scrub → automatische Fehlererkennung im Hintergrund

**Empfohlenes ZFS-Layout:**
```
SSD-Pool (mirror oder single):          # schnell
  → Proxmox OS (root)
  → VM-Disks (Nextcloud-VM, PBS-VM)
  → CT-Disks

HDD-Pool RAIDZ1 oder mirror:            # groß
  → PBS Datastore (/var/lib/proxmox-backup/datastore/)
  → Nextcloud-Daten (/data)
  → NFS/SMB Freigaben
  → (optional) Archiv-Medien
```

**Mindest-Ausstattung (Empfehlung):**
- 2× SSD (mind. 256GB, mirror) → OS + VM-Disks
- 2–4× HDD (mind. 2TB, RAIDZ1 bei 3-4 Stück oder mirror bei 2) → Daten/Backup
- RAM: mind. 16GB (ZFS mag RAM — ARC-Cache)

**Verzahnung mit B4CK01 (LXC-Migration):**
- Sobald proxmox-dt läuft und PBS aktiv ist:
  - Backup-Jobs aller Nodes von vzdump-NFS → PBS umstellen
  - PBS kennt Snapshots nativ → kein NFS-Suspend-Problem mehr
  - `shared-storage` NFS kann dann aufgeräumt/ersetzt werden

**Nächste Schritte (nach Anlieferung proxmox-dt):**
- [ ] Proxmox auf proxmox-dt installieren
- [ ] ZFS-Pools anlegen (SSD + HDD)
- [ ] proxmox-dt in `brainhome-cluster` aufnehmen
- [ ] PBS VM anlegen und Datastores konfigurieren
- [ ] Backup-Jobs aller Nodes auf PBS umstellen (löst B4CK01 langfristig)
- [ ] Nextcloud CT/VM anlegen
- [ ] NFS/SMB Fileserver CT anlegen
- [ ] DNS-Eintrag: `dt.brain`, `nextcloud.brain`, `backup.brain`

### Backup-Konzept optimieren: LXC auf lvmthin migrieren (TICKET `B4CK01`)

> Erstellt: 27.03.2026 | Auslöser: CT117 (caddy-eg) Suspend-Lock → 502 Bad Gateway auf ha-ug/og/eg

**Problem (Root Cause):**
- Alle LXC-Container liegen auf `shared-storage` (NFS) → kein Snapshot-Support
- vzdump konfiguriert mit `mode snapshot` → fällt bei NFS **automatisch auf `suspend` zurück**
- Suspend friert Keepalived ein → VRRP Failover funktioniert nicht → Caddy-Backup übernimmt VIP nicht
- Heutige Auswirkung: ha-ug, ha-og, ha-eg ~4h lang nicht erreichbar (03:00–07:20 Uhr)

**Analyse — alle LXC-Container:**
| Node       | CTID | Name          | Storage        | Snapshot möglich? |
|------------|------|---------------|----------------|-------------------|
| proxmox-ug | 100  | pihole        | shared-storage (NFS) | ❌ |
| proxmox-ug | 110  | caddy         | shared-storage (NFS) | ❌ → MASTER VIP |
| proxmox-ug | 116  | brainhome-prod| shared-storage (NFS) | ❌ |
| proxmox-ug | 130  | pxe-stack     | shared-storage (NFS) | ❌ |
| proxmox-og | 111  | pihole-og     | shared-storage (NFS) | ❌ |
| proxmox-og | 120  | caddy-og      | shared-storage (NFS) | ❌ → BACKUP VIP |
| proxmox-eg | 114  | pihole-eg     | shared-storage (NFS) | ❌ |
| proxmox-eg | 117  | caddy-eg      | shared-storage (NFS) | ❌ → eg/og/ug Proxy |

**Lösung (Umsetzungsplan):**

- [ ] **Phase 1: Infrastruktur** — LXC-Storage auf `local-lvm` (lvmthin) pro Node umstellen
  - Alle 3 Nodes haben bereits `local-lvm` (lvmthin) — Snapshot-fähig ✅
  - Caddy + Pihole CTs von NFS auf lvmthin migrieren (Disk-Move via Proxmox UI oder `qm/pct move-disk`)
  - Priorität: CT110 (caddy/proxmox-ug), CT117 (caddy-eg), CT120 (caddy-og), CT100/111/114 (pihole)

- [ ] **Phase 2: Verifikation** — Snapshot-Backup testen
  - Nach Migration: `vzdump <ctid> --mode snapshot --storage backup-daily` manuell ausführen
  - Prüfen: kein `Lock: backup` mehr → Keepalived läuft durch

- [ ] **Phase 3: Backup-Zeitplan staffeln** (sofort umsetzbar, unabhängig von Phase 1)
  - Principle: Nie alle 3 Caddy-Instanzen gleichzeitig backuppen
  - Staffelung vorschlagen:
    - `03:00` → proxmox-ug (CT110 caddy MASTER) — ok, BACKUP übernimmt
    - `03:30` → proxmox-og (CT120 caddy-og)
    - `04:00` → proxmox-eg (CT117 caddy-eg)
  - Analog für Pi-hole: 03:15 / 03:45 / 04:15

- [ ] **Phase 4: Sofort-Maßnahmen (heute umsetzbar)**
  - Backup-Window auf 1 Container pro Node pro Nacht beschränken
  - Für die Caddy-CTs zuerst nur `CT110`, `CT120` und `CT117` einzeln testen
  - Vor dem Backup: `pct status <ctid>` prüfen; nur ausführen, wenn kein `backup`-Lock aktiv ist
  - Nach dem Backup: `pct list | grep <ctid>` prüfen, `systemctl status keepalived` auf den Caddy-Hosts verifizieren
  - Falls das Backup wieder zu `suspend` führt: zuerst `vzdump <ctid> --mode stop --compress zstd --storage backup-daily` testen und danach mit `--mode snapshot` vergleichen
  - Falls `stop` zu teuer oder zu störend ist: Backup-Window temporär auf `04:30+` verschieben und nur ein CT pro Knoten behandeln

- [ ] **Phase 5: Keepalived Freeze-Workaround** (falls Phase 1 nicht sofort möglich)
  - In der vorhandenen Proxmox-Umgebung (PVE 9.2.10) ist `--nofreeze` nicht verfügbar; deshalb auf `--mode stop` oder auf gestaffelte Backups ausweichen
  - Alternativ: pre/post-backup Hook der Keepalived stoppt+startet (riskant)
  - Notfall-Plan: Backup nur nachts außerhalb der Haupt-HA-Window-Zeiten und mit manueller Verifikation der VIP-Failover-Status ausführen
  - Hilfsskript: [tools/bin/proxmox-backup-check.sh](tools/bin/proxmox-backup-check.sh) für schnelle Lock-/Storage-/Backup-Checks vor dem Backup-Start

**Akzeptanzkriterien:**
- CT117 Backup läuft ohne `Lock: backup` → Keepalived sendet weiter → caddy-og übernimmt VIP
- HA-Instanzen bleiben während Backup-Window erreichbar
- `pct list` zeigt nach Backup kein `backup`-Lock mehr bei Caddy-Containern

---

### PXE / Netzwerk-Boot fuer Node-Provisionierung (TICKET `3D9708`)
- [x] PXE-Server auf dediziertem LXC `CT130` (`pxe-stack`) aufgebaut (`dnsmasq` + `tftp` + `iPXE`)
- [x] `pxe.brain` DNS in beiden Pi-hole Instanzen reserviert (`192.168.188.250`)
- [x] PXE-Workspace an Grafana-Struktur angeglichen (`docker/`, `logs/`, `config/`, `scripts/`, `docs/`)
- [x] Deployment-Strategie: dedizierter LXC/VM zuerst auf `proxmox-dev`, spaeterer Umzug auf neuen `proxmox-ug`
- [x] Naechster Zielknoten `proxmox-ug` erfolgreich provisioniert und integriert (`192.168.188.248`)
- [ ] BIOS + UEFI Netzwerk-Boot fuer Ziel-PC testen
- [x] Proxmox unattended Installationspfad definiert und validiert (inkl. USB-Fallback fuer Erstaufbau)
- [ ] Migrationsfenster planen: Monitoring-VM108 (Grafana/Prometheus/Loki) auf `proxmox-eg` darf nicht beeintraechtigt werden
- [x] Betriebsdokumentation in `/home/pxe-boot/` aufgebaut und aktualisiert

---

## 📦 Erledigt

- [x] Proxmox proxmox-dev aufgesetzt (Tower, 192.168.188.254, ehemals proxmox-ug)
- [x] Proxmox proxmox-eg aufgesetzt (192.168.188.253) — JDK 17, Python venv, SSH Config ✅
- [x] HA MASTER: remote_homeassistant → EG/OG/UG alle connected, 1380+ Entities aggregiert ✅
- [x] ha-eg IP-Fix `.148` → `.194` via REST-API (zeroconf-Flow, 26.03.2026) ✅
- [x] ha-ga als Remote Node eingerichtet + zu ha-master verbunden (26.03.2026, Entry `01KMNT0F2Y5Y0R5J3H802V0NNB`) ✅
- [x] VS Code Dev-Setup auf proxmox-dev + proxmox-eg (JDK 17, venv, SSH Shortcuts) ✅
- [x] BrainHome.code-workspace erstellt — alle Ordner + 20 Tasks (HA Pull/Push/SSH + Infra-Terminals) ✅
- [x] haos-ug deployt und aktiv (192.168.188.145)
- [x] MQTT Mosquitto auf haos-ug aktiv
- [x] Strommeter (AI-on-the-Edge) MQTT-Integration → 35 Entities in HA
- [x] Strommeter PreValue korrigiert (33397 → 35505.8 kWh)
- [x] Keycloak VM angelegt und gestartet (VMID 107)
- [x] NAS eingebunden als Proxmox-Backup-Storage
- [x] AP EG (192.168.188.70) + AP OG (192.168.188.71) OpenWRT eingerichtet
- [x] haos-eg / haos-og Configs erstellt
- [x] Git-Repos für HA-Configs (haos-ug, haos-eg, haos-og auf GitHub)
- [x] BrainPortal Code-Basis importiert (`/home/webserver/`)
- [x] Architektur-Dokumentation erstellt (`/home/architektur/`)
- [x] brainPiEingang Dokumentation erstellt
- [x] proxmox-dev befreit: VMs 104 + 105 gelöscht, Crontab bereinigt (26.03.2026)
- [x] brainhome-cron: Cron-Registry + CLI-Tool erstellt, alle 9 Jobs auf VM113 deployed (26.03.2026)
- [x] pihole-sync.py: Script nach brainhome-root migriert + SSH-Key-Pfad korrigiert (26.03.2026)
- [x] ha-addon-update-sync.py: Script nach brainhome-root migriert + SSH-Key-Pfad korrigiert (26.03.2026)

---

*Letzte Aktualisierung: 27. März 2026 (Morgen – USB Passthrough Zigbee/BT ha-ug/og/eg)*

---

## Webserver Runbook – CT/Flyway/Quartz Incident-Checklist (21.03.2026)

### 1) Schnell-Diagnose (nur devctl)
- `cd /home/webserver`
- `./tools/devctl.sh status --json --pretty`
- `./tools/devctl.sh health --json --pretty`
- `./tools/devctl.sh machine --pretty --compact`

### 2) CT-/Port-Routing validieren
- Erwartung: `backend-dev` in CT112 auf Port `8440`
- Erwartung: `backend-prod` in CT116 auf Port `8081`
- Falls Abweichung: `tools/port-inspect.sh` und `tools/devctl.sh` Mapping pruefen und korrigieren.

### 3) Runtime-Skripte synchronisieren
- Immer nach Tooling-Aenderungen ausfuehren:
- `./tools/devctl.sh sync-scripts`
- Muss mindestens syncen: `ct-runner.sh`, `ct116-runner.sh`, `port-inspect.sh`, `devctl.sh`

### 4) Flyway-Probleme (Migration paradox/erneut)
- Symptome: Migration auf bereits umbenannten Spalten, Start bricht trotz frueherer Success-Runs.
- Pruefen: `flyway_schema_history` auf inkonsistente `installed_rank`-Reihenfolge und Duplikate.
- Bei korrupten Duplikaten: defekte Ranks bereinigen, dann Backend neu starten.

### 5) Quartz-Probleme (`InvokerJob`, `SchedulerException`)
- Eigene JobFactory darf Quarkus-internen Jobbau nicht selbst instanziieren.
- Pattern: CDI-Jobs in eigener Factory, Nicht-CDI/Framework-Jobs an originale Scheduler-Factory delegieren.
- Danach Backend neu starten und Status/Health erneut validieren.

### 6) Start-Kommandos mit Exit 1 richtig interpretieren
- Wenn Dienst bereits laeuft, ist `running -> starting` ohne `--force` blockiert.
- Exit `1` kann erwarteter Guardrail sein, kein Systemausfall.

### 7) Abschlusskriterien
- `status` zeigt `backend-dev RUNNING`
- `health` ist `ok: true`
- Keine Signaturen in aktueller Ausgabe:
	- `InvokerJob`
	- `SchedulerException`
	- `set to ERROR state`
	- `An error occured instantiating job`
