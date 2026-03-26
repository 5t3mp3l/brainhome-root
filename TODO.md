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
- [ ] Root-CA in Browser/Clients importieren → `https://caddy.brain/ca.crt` oder `/home/caddy/caddy-root-ca.crt` kopieren
- [x] `portal.brain` Route hinzufügen → reverse_proxy CT116:8081, Alias für brainhome-prod (März 2026)
- [x] `grafana.brain`, `nextcloud.brain` → bereits im Caddyfile aktiv (März 2026)

---

## 🟠 Prio 2 – Home Automation

### haos-master
- [x] Keycloak SSO (`hass-oidc-auth`, client: homeassistant-master, aktiv)
- [ ] Erste Automationen / zentrale Logik einrichten

### haos-eg
- [x] Keycloak SSO (`hass-oidc-auth`, client: homeassistant-eg, aktiv)
- [ ] Config aus `/home/haos-configs/haos-eg/` übernehmen
- [ ] MQTT-Verbindung zu Mosquitto testen
- [ ] Erste Entitäten (Licht, Sensoren EG) einrichten

### haos-og
- [x] Keycloak SSO (`hass-oidc-auth`, client: homeassistant-og, aktiv)
- [ ] Config aus `/home/haos-configs/haos-og/` übernehmen
- [ ] MQTT-Verbindung testen
- [ ] Erste Entitäten OG einrichten

### haos-ug (Erweiterungen)
- [-] Energie-Dashboard einrichten (Strommeter `sensor.strommeter_main_value`)
- [x] Keycloak SSO integrieren (`hass-oidc-auth`, BrainHome SSO Button aktiv)
- [ ] Grafana-Anbindung für Sensor-Daten

### ☀️ Solaranlage & Autarkie (haos-ug)
- [x] Solarman-Integration: davidrapan v25.08.16 migriert (15.03.2026)
- [x] `/home/autarkie/` Workspace-Ordner angelegt (Docs, Scripts, Daten)
- [x] **Solarman Cloud API**: APP_ID + APP_SECRET eintragen → `solarman-api.env` (bereits vorhanden, März 2026)
- [ ] **Historische Daten laden**: `python3 /home/autarkie/scripts/fetch-solarman-cloud.py --start 2023-01-01 --sync-nas`
- [ ] **HA Statistics importieren**: `python3 /home/autarkie/scripts/import-ha-statistics.py --all`
- [ ] `_2`-Duplikat-Entities auf HA-Master bereinigen

### Zigbee
- [ ] Zigbee2MQTT Container einrichten
- [ ] Sonoff Coordinator anschließen und konfigurieren
- [ ] Erste Geräte anlernen (Buttons, Sensoren)
- [ ] Integration in HA-UG / HA-EG

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
- [ ] Dashboard: Server CPU / RAM / Temp
- [ ] Dashboard: Energie (Strommeter)
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
- [ ] ThinkCentre WS kaufen / einrichten → proxmox-ws
- [ ] ThinkCentre SE kaufen / einrichten → proxmox-se (Edge/Router)
- [x] Proxmox Cluster `brainhome-cluster` aktiv (4 Nodes)
- [ ] Storage: ZFS auf den Nodes
- [ ] PBS (Proxmox Backup Server) VM einrichten

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

*Letzte Aktualisierung: 26. März 2026*

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
