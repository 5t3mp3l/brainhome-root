# 🏠 BrainHome Infrastructure — Übersicht

**Stand**: 25. März 2026  
**Subnetz**: `192.168.188.0/24`

**Lessons Learned (aktuell)**: `/home/ERLERNTES-WISSEN.md`

---

## 🖥️ Hosts & IP-Adressen

| Host | IP | Typ | CT/VM-ID | Node | Dienst | SSH |
|------|----|-----|----------|------|--------|-----|
| proxmox-dev | 192.168.188.254 | Proxmox Bare Metal | — | — | Hypervisor (Master/Dev) | `ssh proxmox-dev` |
| proxmox-workstation | 192.168.188.247 | Proxmox Bare Metal | — | — | Hypervisor Workstation | `ssh proxmox-workstation` |
| proxmox-ug | 192.168.188.248 | Proxmox Bare Metal | — | — | Hypervisor UG | `ssh proxmox-ug` |
| proxmox-eg | 192.168.188.253 | Proxmox Bare Metal | — | — | Hypervisor EG | `ssh proxmox-eg` |
| proxmox-og | 192.168.188.252 | Proxmox Bare Metal | — | — | Hypervisor OG | `ssh proxmox-og` |
| pihole | 192.168.188.251 | LXC | CT100 | proxmox-ug | Pi-hole v6 + DNS (master) | `ssh pihole` |
| pihole-og | 192.168.188.249 | LXC | CT111 | proxmox-og | Pi-hole (OG, Sync) | `ssh pihole-og` |
| pihole-eg | 192.168.188.245 | LXC | CT114 | proxmox-eg | Pi-hole (EG, Sync) | `ssh pihole-eg` |
| caddy VIP | 192.168.188.200 | Keepalived floating | — | — | Reverse Proxy Einstiegspunkt | `ssh caddy` |
| caddy-backup | 192.168.188.202 | LXC | CT110 | proxmox-ug | Reverse Proxy MASTER | `ssh caddy-backup` |
| caddy-og | 192.168.188.201 | LXC | CT120 | proxmox-og | Reverse Proxy BACKUP (OG) | `ssh caddy-og` |
| caddy-eg | 192.168.188.203 | LXC | CT117 | proxmox-eg | Reverse Proxy BACKUP (EG) | `ssh caddy-eg` |
| keycloak | 192.168.188.107 | VM | VM107 | proxmox-ug | Keycloak SSO | `ssh keycloak` |
| monitoring | 192.168.188.108 | VM | VM219 | proxmox-workstation | Grafana + Prometheus + Loki | `ssh monitoring` |
| ha-master | 192.168.188.142 | VM | VM101 | proxmox-workstation | Home Assistant Master | `ssh ha-master` |
| ha-ug | 192.168.188.152 | VM | VM106 | proxmox-ug | Home Assistant UG | `ssh ha-ug` |
| ha-eg | 192.168.188.194 | VM | VM102 | proxmox-eg | Home Assistant EG | `ssh ha-eg` |
| ha-og | 192.168.188.143 | VM | VM103 | proxmox-og | Home Assistant OG | `ssh ha-og` |
| ha-ga | 192.168.188.191 | VM | VM115 | proxmox-ug | Home Assistant GA | `ssh ha-ga` |
| brainhome-dev | 192.168.188.112 | LXC | CT112 | proxmox-workstation | Webserver Dev (Quarkus + Angular) | `ssh brainhome-dev` |
| brainhome-prod | 192.168.188.116 | LXC | CT116 | proxmox-ug | Webserver Prod | `ssh brainhome-prod` |
| brainhome-workstation | 192.168.188.193 | VM | VM113 | proxmox-workstation | VS Code Remote + XRDP Workstation (Ubuntu 24.04 GNOME) | `ssh brainhome-workstation` |
| pxe-stack | 192.168.188.250 | LXC | CT130 | proxmox-ug | PXE DHCP/TFTP + iPXE HTTP | `ssh pxe-stack` |
| nextcloud | 192.168.188.121 | VM | VM121 | proxmox-ug | Nextcloud | `ssh nextcloud` |
| brainpi | 192.168.188.155 | Raspberry Pi | — | — | Türklingel/Kamera | `ssh brain@192.168.188.155` |
| nas | 192.168.188.42 | NAS | — | — | Netzwerkspeicher | `ssh nas` |
| fritzbox | 192.168.188.1 | Router | — | — | Default Gateway | http://fritzbox.brain |

## �️ Proxmox Cluster

| Node | IP | Rolle | Hosts (wichtig) |
|------|----|-------|----------------|
| proxmox-dev | 192.168.188.254 | Master / Dev Orchestrierung | `devctl.sh` wird hier ausgeführt |
| proxmox-workstation | 192.168.188.247 | Workstation + Dev CTs | CT112 brainhome-dev, VM113 brainhome-workstation, VM101 ha-master, VM219 monitoring |
| proxmox-ug | 192.168.188.248 | UG Services | CT100 pihole, CT110 caddy-backup, CT116 brainhome-prod, CT130 pxe-stack, VM106–115 |
| proxmox-eg | 192.168.188.253 | EG Services | CT114 pihole-eg, CT117 caddy-eg, VM102 haos-eg, VM108 openwrt-eg |
| proxmox-og | 192.168.188.252 | OG Services | CT111 pihole-og, CT120 caddy-og, VM103 haos-og, VM109 openwrt-og |

> Cluster-Inventar live: `bash /home/workstation/tools/cluster-inventory.sh`  
> Tags setzen: `pct set <VMID> --tags "brainhome;..."`  
> devctl-target CT finden: `pvesh get /cluster/resources --type lxc | grep devctl-target`

---

## 🔑 SSH Konfiguration

**SSH Key (Infra)**: `/root/.ssh/pihole_key` (ed25519) — auf allen Proxmox-Nodes  
**SSH Key (HA)**: `/home/haos-configs/.ssh/vscode_rsa` (ed25519)  
**SSH Key (Workstation)**: `/home/brain/.ssh/brainhome_ws` (ed25519) — auf brainhome-workstation VM  
**SSH Config**: `/root/.ssh/config` (auf Proxmox-Nodes identisch), `/home/brain/.ssh/config` (auf Workstation-VM)

> **brainhome_ws Pubkey**:  
> `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIK1PXQ2VV/mpxOqu0XBurzXcnyzfU87RIx1kiQQTZ9hh brain@brainhome-workstation`  
> Muss in `root@proxmox-workstation:~/.ssh/authorized_keys` und `root@proxmox-ug:~/.ssh/authorized_keys` eingetragen sein.

Alle Hosts sind in `/root/.ssh/config` konfiguriert (versioniert in `/home/workstation/`):  

```bash
# Proxmox-Nodes
ssh proxmox-dev          # root@192.168.188.254 (pihole_key)
ssh proxmox-workstation  # root@192.168.188.247 (pihole_key) — alias: proxmox-ws
ssh proxmox-ug           # root@192.168.188.248 (pihole_key)
ssh proxmox-eg           # root@192.168.188.253 (pihole_key)
ssh proxmox-og           # root@192.168.188.252 (pihole_key)

# DNS / Proxy
ssh pihole               # root@192.168.188.251 (pihole_key)
ssh pihole-og            # root@192.168.188.249 (pihole_key)
ssh pihole-eg            # root@192.168.188.245 (pihole_key)
ssh caddy                # VIP 192.168.188.200 (pihole_key)
ssh caddy-backup         # root@192.168.188.202 (pihole_key) — HA Master (alias: caddy-1)
ssh caddy-og             # root@192.168.188.201 (pihole_key) — HA Backup OG
ssh caddy-eg             # root@192.168.188.203 (pihole_key) — HA Backup EG

# Services
ssh keycloak             # brain@192.168.188.107 (pihole_key)
ssh monitoring           # root@192.168.188.108 (id_rsa)
ssh nextcloud            # brain@192.168.188.121 (pihole_key)
ssh pxe-stack            # root@192.168.188.250 (pihole_key)

# Webserver
ssh brainhome-dev        # root@192.168.188.112 (pihole_key)
ssh brainhome-prod       # root@192.168.188.116 (pihole_key)
ssh brainhome-workstation # brain@192.168.188.193 (id_ed25519/brainhome_ws) — VS Code Remote Host, XRDP :3389

# Endgeräte (Clients)
ssh eg-stefan-lp         # stefan@192.168.188.58 — Stefan's Laptop (RDP → CT113)
ssh ug-buero-tc          # brain@192.168.188.148 — Thin Client UG/Büro (RDP → CT113)

# Home Assistant
ssh ha-master            # root@192.168.188.142 (vscode_rsa)
ssh ha-ug                # root@192.168.188.152 (vscode_rsa)
ssh ha-eg                # root@192.168.188.194 (vscode_rsa)
ssh ha-og                # root@192.168.188.143 (vscode_rsa)
ssh ha-ga                # root@192.168.188.191 (vscode_rsa)

# NAS & Sonstiges
ssh nas                  # sshd@192.168.188.42 (pihole_key)
```

---

## 🌐 DNS-Einträge (Pi-hole — beide Instanzen)

Alle `*.brain` Dienste über Caddy (.200):

| Domain | IP | Dienst |
|--------|----|--------|
| ha-ug.brain | 192.168.188.200 | HA UG (via Caddy) |
| ha-eg.brain | 192.168.188.200 | HA EG (via Caddy) |
| ha-og.brain | 192.168.188.200 | HA OG (via Caddy) |
| ha-ga.brain | 192.168.188.200 | HA GA (via Caddy) |
| ha-master.brain | 192.168.188.200 | HA Master (via Caddy) |
| keycloak.brain | 192.168.188.200 | Keycloak SSO (via Caddy) |
| proxmox.brain | 192.168.188.200 | Proxmox DEV (via Caddy) |
| pihole.brain | 192.168.188.200 | Pi-hole Admin (via Caddy) |
| grafana.brain | 192.168.188.200 | Grafana (via Caddy) |
| strommeter.brain | 192.168.188.200 | Strommeter (via Caddy) |
| auth.brain | 192.168.188.200 | oauth2-proxy (via Caddy) |
| caddy.brain | 192.168.188.200 | Caddy direkt |
| pxe.brain | 192.168.188.250 | PXE Host (dedizierter LXC/VM, Phase 1 auf proxmox-dev) |
| monitoring.brain | 192.168.188.108 | Monitoring VM direkt |
| proxmox-eg.brain | 192.168.188.253 | Proxmox EG (direkt) |
| pihole-og.brain | 192.168.188.249 | Pi-hole 2 Admin (direkt) |
| ap-eg.brain | 192.168.188.70 | WiFi AP EG (direkt) |
| ap-og.brain | 192.168.188.71 | WiFi AP OG (direkt) |
| nas.brain | 192.168.188.42 | NAS (direkt) |
| fritzbox.brain | 192.168.188.1 | Fritzbox (direkt) |

---

## 🔒 Caddy Reverse Proxy (CT110)

**IP**: 192.168.188.200  
**Config**: `/etc/caddy/Caddyfile`  
**CA-Cert**: `/home/caddy/caddy-root-ca.crt` (in Chrome als Trusted importiert)

Jede HA-Site hat eine eigene oauth2-proxy Instanz (vollständiger Reverse Proxy, **kein** `forward_auth`):

```caddyfile
{ local_certs }

ha-ug.brain     { reverse_proxy localhost:4181 }   # oauth2-proxy-ha-ug
ha-eg.brain     { reverse_proxy localhost:4182 }   # oauth2-proxy-ha-eg
ha-og.brain     { reverse_proxy localhost:4183 }   # oauth2-proxy-ha-og
ha-master.brain { reverse_proxy localhost:4184 }   # oauth2-proxy-ha-master
auth.brain      { redir https://ha-master.brain{uri} 302 }  # legacy → Weiterleitung zu ha-master
keycloak.brain  { reverse_proxy 192.168.188.107:8080 }
pihole.brain    { reverse_proxy 192.168.188.251:80 }
grafana.brain   { reverse_proxy 192.168.188.108:3000 }
proxmox.brain   { reverse_proxy https://192.168.188.254:8006 { tls_insecure_skip_verify } } # proxmox-dev
strommeter.brain { reverse_proxy 192.168.188.115:80 }
```

HTTPS ist für alle Domains aktiv. CA-Zertifikat einmalig in den Browser importieren.

---

## 🔐 Keycloak SSO (VM107)

**URL**: https://keycloak.brain  
**Admin**: `admin` / `0248Brain8579`  
**Realm**: `brainhome`

### Clients

| Client ID | Secret | Redirect URI |
|-----------|--------|--------------|
| homeassistant-ug | `brainhome-homeassistant-ug-secret` | https://ha-ug.brain/* |
| homeassistant-eg | `brainhome-homeassistant-eg-secret` | https://ha-eg.brain/* |
| homeassistant-og | `brainhome-homeassistant-og-secret` | https://ha-og.brain/* |
| homeassistant-ga | `brainhome-homeassistant-ga-secret` | https://ha-ga.brain/* |
| homeassistant-master | `brainhome-homeassistant-master-secret` | https://ha-master.brain/* |
| caddy-sso | `brainhome-caddy-sso-secret` | https://auth.brain/oauth2/callback, https://ha-ug.brain/oauth2/callback, https://ha-eg.brain/oauth2/callback, https://ha-og.brain/oauth2/callback, https://ha-master.brain/oauth2/callback |
| grafana | `brainhome-grafana-secret` | https://grafana.brain/* |

### Benutzer

| Benutzer | Passwort | E-Mail | Gruppe |
|----------|----------|--------|--------|
| brain | `0248Brain8579` | brain@brain.local | **admin** (Zugriff alle Sites) |

### Gruppen & Zugriffsrechte

| Gruppe | ha-ug | ha-eg | ha-og | ha-ga | ha-master |
|--------|-------|-------|-------|-------|----------|
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `eg-user` | ❌ | ✅ | ❌ | ❌ | ✅ |
| `og-user` | ❌ | ❌ | ✅ | ❌ | ✅ |
| `gast-user` | ❌ | ❌ | ❌ | ❌ | ✅ |

Gruppe zu User hinzufügen (Keycloak Admin UI oder API):
```bash
# Beispiel: neuen eg-user anlegen
curl -sk -X POST https://keycloak.brain/admin/realms/brainhome/users \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username":"max","email":"max@brain.local","emailVerified":true,"enabled":true,"credentials":[{"type":"password","value":"Passwort123","temporary":false}]}'
# Dann User → Gruppe zuweisen via Admin UI
```

**Group-Mapper**: `oidc-group-membership-mapper` auf Client `caddy-sso` → Claim `groups` in Token

---

## 🔄 oauth2-proxy (CT110 — ✅ aktiv)

**Binary**: `/usr/local/bin/oauth2-proxy` v7.7.1  
**Cookie Secret**: `Ntb0R-fr5aajX2gcsV2wYl9L2Mh6sUxdEkbEnRrF2G0=`

### Instanzen (je eine pro HA-Site)

| Service | Config | Port | Upstream | allowed_groups |
|---------|--------|------|----------|----------------|
| `oauth2-proxy-ha-ug` | `/etc/oauth2-proxy/ha-ug.cfg` | 4181 | 192.168.188.152:8123 | `admin` |
| `oauth2-proxy-ha-eg` | `/etc/oauth2-proxy/ha-eg.cfg` | 4182 | 192.168.188.194:8123 | `eg-user`, `admin` |
| `oauth2-proxy-ha-og` | `/etc/oauth2-proxy/ha-og.cfg` | 4183 | 192.168.188.143:8123 | `og-user`, `admin` |
| `oauth2-proxy-ha-ga` | `/etc/oauth2-proxy/ha-ga.cfg` | 4185 | 192.168.188.191:8123 | `admin` |
| `oauth2-proxy-ha-master` | `/etc/oauth2-proxy/ha-master.cfg` | 4184 | 192.168.188.142:8123 | `admin`, `eg-user`, `og-user`, `gast-user` |
| ~~`oauth2-proxy` (legacy)~~ | — | ~~4180~~ | — | **gestoppt & deaktiviert** |

**Architektur**: Vollständiger Reverse Proxy (nicht `forward_auth`) — Cookie liegt pro Site auf der jeweiligen Domain (z.B. `ha-ug.brain`). Nötig wegen Chrome-Restriction für Single-Label-TLD Cookies (`.brain` wurde blockiert).

**Fixes die nötig waren:**
- Caddy CA-Cert in CT110 System-Trust installiert (`update-ca-certificates`)
- Keycloak Realm `frontendUrl` auf `https://keycloak.brain` gesetzt (issuer-Claim fix)
- `auth.brain` DNS-Eintrag in beiden Pi-hole `pihole.toml` eingetragen
- Keycloak User `brain`: `emailVerified=true` gesetzt
- Keycloak Client `caddy-sso`: Wildcard-redirectUri entfernt, explizite URIs pro Site
- Chrome blockiert `Domain=.brain` Cookie → Lösung: oauth2-proxy als RP, Cookie auf jeweiliger Domain

---

## 💻 VS Code Development Setup (proxmox-dev + proxmox-eg)

Beide Proxmox-Nodes haben identisches Dev-Setup:

| Komponente | Version | Pfad |
|------------|---------|------|
| Java (JDK) | OpenJDK 17.0.18 | `/usr/lib/jvm/java-17-openjdk-amd64` |
| Python venv | 3.11 | `/home/.venv` |
| SSH Keys | pihole_key + vscode_rsa | `/root/.ssh/` + `/home/haos-configs/.ssh/` |
| SSH Config | alle Shortcuts | `/root/.ssh/config` |

**JAVA_HOME** gesetzt in `/etc/environment` und `/root/.bashrc`:
```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

**Python venv aktivieren:**
```bash
source /home/.venv/bin/activate
```

**VS Code Remote SSH Verbindung:**  
- VS Code → Remote SSH → `root@192.168.188.254` (proxmox-dev)
- VS Code → Remote SSH → `root@192.168.188.253` (proxmox-eg)  
- Workspace öffnen: `/home/HomeAssistant/HomeAssistant.code-workspace`

**Workspace Tasks** (Ctrl+Shift+P → Tasks: Run Task):
- `⬇️ Pull ALL von HA` — Alle 4 HA-Configs lokal synchronisieren
- `⬆️ Push MASTER/EG/OG/UG → HA + Reload` — Config deployen + HA neu starten
- `🔌 Terminal → MASTER/EG/OG/UG` — SSH Terminal zu HA-Instanz
- `📊 HA Status alle Instanzen` — Versionsstatus aller 4 Instanzen

---

## 🏠 Home Assistant Instanzen

| Instanz | URL | IP | trusted_proxies |
|---------|-----|----|-----------------|
| ha-master | https://ha-master.brain | 192.168.188.142 | 192.168.188.200 ✓ |
| ha-ug | https://ha-ug.brain | 192.168.188.152 | 192.168.188.200 ✓ |
| ha-eg | https://ha-eg.brain | 192.168.188.194 | 192.168.188.200 ✓ |
| ha-og | https://ha-og.brain | 192.168.188.143 | 192.168.188.200 ✓ |
| ha-ga | https://ha-ga.brain | 192.168.188.191 | 192.168.188.200 ✓ |

`trusted_proxies` in `configuration.yaml` auf allen 4 Instanzen gesetzt:
```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 192.168.188.200
```

`auth_providers` auf allen 4 Instanzen konfiguriert:
```yaml
# ha-ug / ha-eg / ha-og:
homeassistant:
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - 127.0.0.1/::1
        - 192.168.188.0/24
      allow_bypass_login: false
    - type: homeassistant

# ha-master: zusätzlich allow_bypass_login: true + trusted_users (brain_id)
```
> HA hat keinen nativen OIDC-Provider — SSO-Gate läuft über oauth2-proxy als vollständiger Reverse Proxy (Port 4181–4184).

### HA Multi-Instance (remote_homeassistant)

ha-master aggregiert alle Entitäten von EG/OG/UG via `remote_homeassistant`:

| Verbindung | Status | Token-Speicherort |
|------------|--------|-------------------|
| MASTER → EG | ✅ connected | `/home/HomeAssistant/haos/secrets.yaml` |
| MASTER → OG | ✅ connected | `/home/HomeAssistant/haos/secrets.yaml` |
| MASTER → UG | ✅ connected | `/home/HomeAssistant/haos/secrets.yaml` |

**Konfiguration** auf ha-master:
```yaml
# configuration.yaml
remote_homeassistant:
  instances: !include instances.yaml

# instances.yaml
- host: 192.168.188.194  # EG
  port: 8123
  access_token: !secret ha_eg_token
- host: 192.168.188.143  # OG  
  port: 8123
  access_token: !secret ha_og_token
- host: 192.168.188.152  # UG
  port: 8123
  access_token: !secret ha_ug_token
```

> EG/OG/UG haben **kein** `remote_homeassistant` — der Block wurde dort entfernt (war fehlerhaft und zeigte auf sich selbst).

---

## � HA Addon Sync (proxmox-dev)

**Script**: `/usr/local/bin/ha-addon-update-sync.py`  
**Log**: `/var/log/ha-addon-sync.log`  
**Cron**: `30 3 * * *` auf proxmox-dev

Synct Addon-Versionen von ha-master auf alle Remote-Instanzen (ha-ug, ha-eg, ha-og).

**Strategie:**
1. Addon-Liste von ha-master via SSH + `ha apps list` holen
2. Addon-Liste von jedem Remote holen
3. Addon auf Remote installiert UND Version ≠ Master → `ha apps update <slug>` auf Remote ausführen

**Voraussetzung**: SSH-Key `/root/.ssh/pihole_key` muss auf alle HA-Instanzen passen (ist der Fall).

```bash
# Manuell testen:
python3 /usr/local/bin/ha-addon-update-sync.py --dry-run

# Live-Lauf:
python3 /usr/local/bin/ha-addon-update-sync.py
```

> Hinweis: HA REST API (`/api/`) und Supervisor-API (`/api/hassio/`) sind von extern über Bearer-Tokens aus `.storage/auth` **nicht** nutzbar (Refresh-Token-Format, kein Direct-Bearer). Die `ha` CLI via SSH ist der einzig zuverlässige Weg.

---

## �🖥️ Locale (System-Einstellung)

`de_DE.UTF-8` wurde auf allen Debian-Hosts aktiviert und generiert:

| Host | Status |
|------|--------|
| proxmox-dev | ✅ OK |
| proxmox-eg | ✅ OK |
| CT110 (caddy) | ✅ OK |
| CT111 (pihole-og) | ✅ OK |
| CT100 (pihole) | ✅ OK |
| VM107 (keycloak) | ✅ OK |

Befehl: `sed -i 's/^# de_DE.UTF-8/de_DE.UTF-8/g' /etc/locale.gen && locale-gen && update-locale LANG=de_DE.UTF-8 LC_ALL=de_DE.UTF-8`

---

## 📋 Nächste Schritte (TODO)

- [x] oauth2-proxy: 4 Instanzen aktiv (CT110, Ports 4181–4184)
- [x] Keycloak Login → HA funktioniert für alle 4 Sites ✅
- [x] `auth.brain` DNS-Eintrag in beiden Pi-hole eingetragen
- [x] Caddy reverse_proxy für alle 4 HA-Sites (oauth2-proxy als RP)
- [x] `auth.brain` → redir zu ha-master (legacy oauth2-proxy Port 4180 deaktiviert)
- [x] Pi-hole Sync: `pihole-sync.py` aktiv (cron: */5 DNS, 03:00 Gravity)
- [x] Keycloak-Gruppen: admin / eg-user / og-user / gast-user mit allowed_groups ✅
- [x] HA Addon Sync: `ha-addon-update-sync.py` aktiv (cron: 03:30, via SSH + ha CLI) ✅
- [x] HA MASTER: `remote_homeassistant` → EG/OG/UG alle 3 `connected`, 1380+ Entities aggregiert ✅
- [x] JDK 17 + Python venv + SSH Config auf proxmox-dev ✅
- [x] JDK 17 + Python venv + SSH Config auf proxmox-eg ✅
- [x] VS Code Dev-Setup: Workspace mit 14 Tasks (Pull/Push/SSH/Status) ✅

---

## ☀️ Solaranlage & Autarkie

> Workspace-Ordner: `/home/autarkie/` | Dokumentation: `/home/autarkie/ENTWICKLER-WISSEN.md`

### Geräte
| Inverter | IP | Serial | Cloud-ID | Typ |
|---|---|---|---|---|
| West | 192.168.188.88 | 3923624894 | 2303017373 | Deye SUN2000G3 Microinverter |
| Süd | 192.168.188.97 | 3923704974 | 2303017127 | Deye SUN2000G3 Microinverter |

### Integration
- **HA-Instanz**: HA-UG (192.168.188.152) → `custom_components/solarman` (davidrapan v25.08.16)
- **Protokoll lokal**: SolarmanV5 / Modbus RTU über TCP Port 8899
- **Cloud API**: Solarman OpenAPI v1.1.6 → `https://globalapi.solarmanpv.com`
- **Entities**: 100 Solarman-Entities auf HA-UG, auf HA-Master per `remote_homeassistant`

### Historische Daten & NAS-Backup
```bash
# Alle historischen Daten von der Cloud laden + auf NAS sichern
python3 /home/autarkie/scripts/fetch-solarman-cloud.py --start 2023-01-01 --sync-nas

# In HA-Statistiken importieren (Energie-Dashboard)
python3 /home/autarkie/scripts/import-ha-statistics.py --all --start 2023-01-01
```
- **Lokale Daten**: `/home/autarkie/data/cloud/{west,sued}/YYYY-MM-DD.json`
- **NAS-Ziel**: `//192.168.188.42/Family Account/Wohnungen/Elmshausen_&_Wiesenberg/Solaranlage/Daten/`

### Status (15.03.2026)
- [x] Solarman-Migration auf davidrapan v25.08.16 abgeschlossen
- [x] Scripts `fetch-solarman-cloud.py` + `import-ha-statistics.py` bereit
- [ ] Cloud-API-Credentials (APP_ID/SECRET) noch einzutragen
- [ ] Historischer Datenabruf + NAS-Sync noch ausstehend
