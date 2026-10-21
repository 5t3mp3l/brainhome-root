# Historische Hardwareplanung und Netzwerk-Roadmap

> **Einordnung: 21.10.2026.** Die folgenden Kaufempfehlungen, IP-Tabellen,
> Platzierungen und Statusangaben sind eine historische Planung, kein aktuelles
> Cluster-Inventar. Live wurden am 21.10.2026 fuenf Online-Knoten im Cluster
> `brainhome` mit Quorum bestaetigt; der alte Node `.254` gehoert nicht dazu.
> Bestehende Platzierungen stehen in den `paths.toml` der Node- und Gastordner.
> Siehe auch [Infrastruktur-Uebersicht](../INFRASTRUCTURE.md) und
> [Gesamtarchitektur](BRAINHOME-ARCHITEKTUR.md). Aktuelle Hardware und Empfehlung:
> [Physische Architektur](PHYSISCHE-ARCHITEKTUR.md).

✅ 1) Was du bereits besitzt
2× Lenovo ThinkCentre M920Q (i7-9700T, 32 GB, NVMe)

Aktuell darauf:

4× Home Assistant OS Instanzen (haos)

Pi-hole

Das sind sehr starke Mini-Server – perfekt für HAOS oder leichte VM-Dienste.

📦 2) Was du daraus bauen willst (Ziel-Plan)
🎯 EG ThinkCentre #1

haos-eg (dedizierter Node)

🎯 OG ThinkCentre #2

haos-og (dedizierter Node)

Diese beiden sind perfekt dimensioniert. HAOS braucht nicht viel CPU, nur stabile RAM & SSD → passt.

🆕 3) UG-Pläne – 4 neue Geräte (ThinkCentre empfohlen)

Du willst im UG vier neue Systeme, jeweils dedizierte Proxmox-Nodes:

UG-#1: Pi-hole + HAOS

🟩 Hardware-Anforderung: sehr gering
🟩 Empfehlung: ThinkCentre M720q / M920q / M90q / M710q
🟩 RAM: 8–16 GB reichen komplett
🟩 NVMe: 256–512 GB reicht

➡️ Pi-hole + Home Assistant brauchen fast nichts → min. Ausstattung reicht.

UG-#2: Proxmox Backup Server (PBS)

🟥 Wichtig: PBS braucht Storage-I/O, nicht CPU.

Empfohlen:

ThinkCentre SFF (nicht Tiny!) falls möglich
→ Platz für 2× 3.5" HDD + 1× NVMe (Perfekt für Backups)

Oder:

ThinkCentre Tiny (M920q, M720q)
→ Dann externes USB-SSD-RAID oder NAS als Backup-Speicher verwenden.

PBS Anforderungen:

✔ CPU: egal → sogar i5 reicht
✔ RAM: 16 GB
✔ STORAGE: sehr wichtig

1× NVMe für Boot

1× SSD/HDD RAID für Dedupe-Thin-Storage

UG-#3: Caddy + Keycloak

🟩 CPU kaum relevant
🟩 RAM 16 GB
🟩 NVMe 256–512 GB

Empfehlung: ThinkCentre M720q oder M920q Tiny

➡️ Beide Dienste laufen super leicht, aber stabil.

UG-#4: Nextcloud Server

➡️ Wichtig: Nextcloud ist dein schwerstes System
➡️ Viele Dateien → Storage, RAM, CPU nötig.

Beste Hardware für Nextcloud:

Kategorie	Empfehlung
CPU	i7-8700T / i9-9900T / Ryzen 5 5600G
RAM	32 GB Minimum, besser 64 GB
SSD	1–2 TB NVMe
Storage	Optional HDD-Storage für Massendaten
Netzwerk	2.5GbE sehr zu empfehlen

Optimal:
👉 ThinkCentre M920q i7-8700T oder i9-9900T
ODER
👉 ThinkCentre SFF (größer, aber perfektes Storage-NAS)

🖥️ 4) Dein Tower-Proxmox-Server (AMD FX-8370E + RX 570)

Dieser soll werden:

GPU-VM Host

Multi-User-RDP Server

Nextcloud-Client Sync

Benutzerverwaltung: brain, stef, willy, gast

⚠️ Einschätzung:

Der FX-8370E ist alt → funktioniert, aber ineffizient.

Die RX570 passt perfekt für Proxmox GPU Passthrough.

Multi-User-RDP → CPU schafft das, aber nicht perfekt bei hoher Last.

Für Nextcloud Sync reicht es locker.

➡️ Es wird funktionieren, aber irgendwann wirst du auf Ryzen umsteigen wollen.

🧭 5) Gesamtübersicht deiner geplanten Infrastruktur
🟦 Home Assistant Infrastruktur

haos-eg → ThinkCentre #1

haos-og → ThinkCentre #2

haos-ug → ThinkCentre UG-#1

haos-ha → Tower-VM oder extra Node

🟨 Netzwerk / Gateway

Pi-hole auf UG-#1

Caddy Reverse Proxy auf UG-#3

Keycloak auf UG-#3

🟥 Storage

Nextcloud Node (UG-#4)

Proxmox Backup Server (UG-#2)

Tower synchronisiert Nextcloud Daten je User

🟪 Monitoring

Prometheus

Grafana
(UG-#3 oder eigener Container)

🌟 6) Was dir tatsächlich noch fehlt (kurz & klar!)

Du hast schon:

✔ ThinkCentre for EG
✔ ThinkCentre for OG
✔ Tower Proxmox
✔ DNS, Proxy, SSO, HAOS

Dir fehlen GENAU diese Komponenten:

🟩 (1) ThinkCentre UG-#1 → HAOS + Pi-hole

→ Klein & günstig reicht

🟥 (2) ThinkCentre UG-#2 → Proxmox Backup Server

→ Wenn möglich SFF statt Tiny → besser für Storage

🟦 (3) ThinkCentre UG-#3 → Caddy + Keycloak

→ Tiny reicht

🟨 (4) ThinkCentre UG-#4 → Nextcloud Server

→ der stärkste ThinkCentre muss hier hin!

🧠 7) Meine klare Hardware-Empfehlung pro Node
💡 Empfehlungen Tiny-Modelle
Dienst	Empfohlene Hardware
HAOS	ThinkCentre M720q / M920q / M710q
Pi-hole	mini-M720q
Caddy	M720q Tiny
Keycloak	M720q Tiny
Prometheus/Grafana	M920q Tiny
PBS	Besser SFF → ThinkCentre M920 SFF
Nextcloud	ThinkCentre M920q (i7-8700T / i9-9900T) oder M720 SFF
🔥 8) Meine Empfehlung (perfekte Lösung für dich)

Da du Zuverlässigkeit + saubere Architektur + Wachstum willst:

🟦 UG-Setup:

1️⃣ ThinkCentre M720q (8–16 GB) → Pi-hole + HAOS
2️⃣ ThinkCentre M920 SFF (32 GB) → Proxmox Backup Server
3️⃣ ThinkCentre M720q (16 GB) → Caddy + Keycloak + Monitoring
4️⃣ ThinkCentre M920q i7-8700T / i9-9900T (32–64 GB) → Nextcloud Server

🔥 Tower-Proxmox:

weiter als GPU-VM Host

Multi-User RDP

User-Sync via Nextcloud

Damit hast du:

Trennung aller Dienste

maximale Stabilität

Backup-Sicherheit

Wachstumsoptionen

---

# 🌐 BrainHome Netzwerk-Architektur & Infrastruktur-Roadmap

> Gesamtarchitektur – Netzwerktopologie, VLANs, DNS, Server-Rollen, Geräteverwaltung.
> Stand: März 2026. Die FritzBox ist **heute** der Router + DHCP + WLAN-Manager.
> **Langfristig**: ersetzt durch eigenen OpenWrt-Stack → BrainHome Admin Panel übernimmt die Verwaltung.

---

## 9. Grundprinzipien der Architektur

| Prinzip | Warum |
|---|---|
| **Dezentral pro Etage** | Kein Single Point of Failure – EG, OG, UG laufen unabhängig |
| **Zentrale Authentifizierung** | Einmal anmelden (Keycloak SSO) → überall eingeloggt |
| **Zentraler DNS + Adblock** | Pi-hole verwaltet alle internen Hostnamen + filtert Werbung |
| **Edge Automation** | Home Assistant läuft lokal → keine Cloud-Abhängigkeit, keine Latenz |
| **VLAN-Segmentierung** | IoT kann nicht ins Server-Netz – Sicherheit durch Netztrennung |
| **Eigenes Netz statt FritzBox** | BrainHome wird selbst Gateway/Firewall/DHCP/DNS/WLAN-Controller |

---

## 10. Physische Netzwerktopologie

```
                           Internet
                               │
                               │
                       ISP Router / Modem
                               │
                               │
                    ┌──────────────────────┐
                    │  Core Switch         │
                    │  (BrainLAN Core)     │
                    │  + VLAN Trunk Ports  │
                    └──────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          │                    │                    │
    proxmox-eg            proxmox-og           proxmox-ug
   (ThinkCentre #1)      (ThinkCentre #2)   (ThinkCentre UG-#1..#4)
          │                    │                    │
          │                    │                    │
  ┌─────────────┐      ┌─────────────┐      ┌─────────────────────┐
  │ haos-eg     │      │ haos-og     │      │ haos-ug             │
  │ pihole-eg   │      │ Grafana     │      │ pihole-ug           │
  │ NodeRed     │      │ Prometheus  │      │ Frigate / AI / NVR  │
  │ Zigbee2MQTT │      │ PBS         │      │ MQTT Broker         │
  └─────────────┘      └─────────────┘      │ Caddy               │
                                             │ Keycloak            │
                                             │ Nextcloud           │
                                             │ BrainHome Webserver │
                                             └─────────────────────┘
                               │
                    ┌──────────────────┐
                    │  OpenWrt VMs     │
                    │  (Gateway + FW)  │
                    │  EG + OG + UG    │
                    └──────────────────┘
                               │
                    ┌──────────────────────────┐
                    │  Access Points           │
                    │  OpenWrt-AP-EG           │
                    │  OpenWrt-AP-OG           │
                    └──────────────────────────┘
                               │
                    ┌──────────────────┐
                    │  NAS / Storage   │
                    │  nas.brain       │
                    └──────────────────┘
```

**Tower-Proxmox (AMD FX-8370E + RX570):**
```
Tower → GPU Passthrough VM
      → Multi-User RDP (brain, stef, willy, gast)
      → Nextcloud Client Sync
      → CAD / 3D-Druck / Maschinensteuerung
```

---

## 11. VLAN-Struktur

```
                        BrainLAN Core Switch
                               │
          ┌──────────┬─────────┴───────┬──────────┬──────────┐
          │          │                 │          │          │
       VLAN10      VLAN20           VLAN30      VLAN40     ...
   Infrastruktur  Server          User-Geräte    IoT
```

| VLAN | Name | Zweck | Beispiel-Geräte |
|---|---|---|---|
| **VLAN10** | Infrastruktur | Core-Netz-Geräte | Switches, APs, Management-Interfaces |
| **VLAN20** | Server | Alle Proxmox-Nodes, VMs, LXCs | proxmox-eg, haos-eg, pihole, caddy |
| **VLAN30** | User | Personengeräte – Laptops, Phones, TV | PCs, Handys, Smart-TV |
| **VLAN40** | IoT | Smart-Home-Geräte | Zigbee-Relais, ESP32, Sensoren, Rolläden |
| **VLAN50** | Kameras | NVR + Kamera-Stream | BrainPi, Frigate-Feeds |
| **VLAN60** | Werkstatt | CNC, 3D-Druck, Maschinensteuerung | Tower-Proxmox, CNC-PC |
| **VLAN70** | Gäste | Gast-WLAN – kein Zugriff auf interne Netze | Besucher-Geräte |

### Firewall-Regeln (Prinzip)

```
IoT (VLAN40) darf NICHT → Server (VLAN20)
IoT (VLAN40) darf NICHT → User (VLAN30)
IoT (VLAN40) darf     → MQTT Broker (VLAN20 Port 1883)
IoT (VLAN40) darf     → Home Assistant (VLAN20 Port 8123)

Gäste (VLAN70) darf   → Internet only
Gäste (VLAN70) darf NICHT → alles Interne

Kameras (VLAN50) darf → Frigate (VLAN20)
Kameras (VLAN50) darf NICHT → User / Server direkt
```

---

## 12. WLAN-Struktur

| SSID | VLAN | Zweck | Frequenz |
|---|---|---|---|
| `BrainWLAN-EG` | VLAN30 | Benutzergeräte Erdgeschoss | 2.4 + 5 GHz |
| `BrainWLAN-OG` | VLAN30 | Benutzergeräte Obergeschoss | 2.4 + 5 GHz |
| `BrainWLAN-UG` | VLAN30 | Benutzergeräte Untergeschoss | 2.4 + 5 GHz |
| `BrainIoT` | VLAN40 | Alle IoT-Geräte (2.4 GHz only) | 2.4 GHz |
| `BrainGuest` | VLAN70 | Gäste-WLAN | 2.4 + 5 GHz |

**Access Points:** OpenWrt-AP-EG + OpenWrt-AP-OG (bereits in Betrieb, §22 Webserver-Doku).
**Controller:** WLAN-APs werden über das BrainHome Admin Panel gesteuert (LuCI RPC API, keine Cloud).

---

## 13. DNS-Struktur

**Interne Domain:** `brain` (lokale TLS-CA via Caddy)
Auch historisch: `brainhome.local` – **Präferenz ist jetzt `.brain`** (Caddy-ACME funktioniert).

| Hostname | IP | Dienst |
|---|---|---|
| `proxmox-eg.brain` | 192.168.188.200 | Proxmox EG (Hypervisor) |
| `proxmox-ug.brain` | 192.168.188.254 | Proxmox UG (Hypervisor) |
| `brainhome.brain` | 192.168.188.112 | BrainHome Admin Panel (CT112) |
| `keycloak.brain` | 192.168.188.107 | Keycloak SSO (VM107) |
| `pihole.brain` | 192.168.188.100 | Pi-hole primär |
| `pihole2.brain` | 192.168.188.101 | Pi-hole sekundär |
| `nas.brain` | 192.168.188.50 | NAS (Netzwerkspeicher) |
| `ha-master.brain` | 192.168.188.142 | HA Master (VM101) |
| `ha-eg.brain` | 192.168.188.194 | HA EG (VM102) — IP korrigiert (war .148) |
| `ha-og.brain` | 192.168.188.143 | HA OG (VM103) |
| `ha-ug.brain` | 192.168.188.152 | HA UG (VM106) |
| `ha-ga.brain` | 192.168.188.191 | HA GA (VM115, proxmox-ug) |
| `caddy.brain` | 192.168.188.110 | Caddy Reverse-Proxy (CT110) |
| `mqtt.brain` | 192.168.188.xxx | MQTT Mosquitto |
| `grafana.brain` | 192.168.188.xxx | Grafana (geplant) |
| `auth.brain` | → keycloak.brain | Keycloak Alias |
| `portal.brain` | → brainhome.brain | BrainHome Portal Alias |

**DNS-Server:** Pi-hole primär (192.168.188.100) + Pi-hole sekundär als Fallback.
**TLS:** Caddy Root-CA – alle `*.brain` Zertifikate automatisch (kein Let's Encrypt nötig, intern).

---

## 14. Server-Rollen-Matrix (Zielzustand)

| Node | Hardware | IP | VMs / CTs | Rolle |
|---|---|---|---|---|
| **proxmox-eg** | ThinkCentre M920q #1 | 192.168.188.200 | VM101 (ha-master), VM102 (ha-eg), CT110 (Caddy), CT112 (BrainHome) | EG-Server, Reverse-Proxy, Admin Panel |
| **proxmox-og** | ThinkCentre M920q #2 | geplant | VM103 (ha-og) | OG-Server, Home Automation |
| **proxmox-ug** | ThinkCentre UG-#1..#4 | 192.168.188.254 | VM106 (ha-ug), VM107 (Keycloak), pihole-1, pihole-2 | UG-Server, Core-Dienste |
| **Tower** | AMD FX-8370E + RX570 | 192.168.188.xxx | GPU-VM, RDP, Nextcloud-Sync | Workstation, Multi-User |
| **NAS** | TBD | 192.168.188.50 | — | Storage, Backups, Kamera-Archiv |
| **OpenWrt-AP-EG** | Hardware-AP | 192.168.188.149 | — | WLAN EG (192.168.188.149) |
| **OpenWrt-AP-OG** | Hardware-AP | 192.168.188.xxx | — | WLAN OG |

---

## 15. Warum eigenes Netzwerk statt FritzBox? (Transition-Begründung)

Die FritzBox ist heute Router + DHCP + WLAN-Controller + Gerätename-Vergabe in einem Gerät.
**Wenn wir sie ersetzen, verlieren wir deren UI** – und müssen genau diese Funktionen selbst bauen.

**Was die FritzBox heute macht, das wir selbst brauchen:**

| FritzBox-Funktion | Ersatz im BrainHome-Stack |
|---|---|
| DHCP für alle Geräte | Pi-hole DHCP oder OpenWrt DHCP pro VLAN |
| Gerätename vergeben | Pi-hole Local DNS Records + DHCP-Hostname |
| WLAN SSID/Passwort | OpenWrt UCI API (LuCI RPC) |
| Gerät ins Gastnetz schieben | OpenWrt VLAN-Zuweisung per MAC |
| IP fixieren (DHCP-Reservierung) | OpenWrt/Pi-hole Static DHCP Lease |
| Alle Geräte sehen (Gerätliste) | BrainHome Admin Panel → Netzwerk-Modul |
| Elternzeitkontrolle / Firewall | OpenWrt + nftables / iptables |
| VPN | OpenWrt WireGuard |
| DNS Rebind Schutz | Pi-hole + OpenWrt |

**Schlussfolgerung**: Das BrainHome Admin Panel (Webserver) wird zur zentralen Management-Oberfläche – vergleichbar mit der FritzBox-UI, aber für unsere eigene Infrastruktur.

---

## 16. Geräteverwaltung – Modul im BrainHome Admin Panel

> **Ziel**: Alle Geräte im Netzwerk sehen und verwalten – ohne FritzBox-UI.
> **Warum nötig**: Sobald OpenWrt Gateway + Pi-hole DHCP die FritzBox ersetzen, gibt es keine zentrale Geräteliste mehr – außer wir bauen sie selbst.

### 16.1 Geräteerkennung (Device Discovery)

Quellen, aus denen der Webserver Geräte aggregiert:

| Quelle | API | Liefert |
|---|---|---|
| **FritzBox** (heute) | TR-064 SOAP `GetHostNumberOfEntries` + `GetGenericHostEntry` | Hostname, IP, MAC, WLAN/LAN, aktiv/inaktiv |
| **Pi-hole DHCP** (Ziel) | Pi-hole v6 API `GET /api/dhcp/leases` | Hostname, IP, MAC, Lease-Zeit |
| **OpenWrt APs** (aktiv) | LuCI RPC `iwinfo` + `hostapd` | WLAN-Clients pro AP, RSSI, TX/RX-Rate |
| **OpenWrt Gateway** (Ziel) | LuCI RPC `nmap` oder `arp` table | ARP-Tabelle → alle aktiven IPs |
| **Home Assistant** | `GET /api/states` → `device_tracker.*` | HA-bekannte Geräte mit Raum-Zuweisung |

**Aggregierter Geräte-Datensatz** (nach Join über MAC-Adresse):
```json
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "hostname": "esp-growbox-01",
  "ip": "192.168.188.73",
  "ip_mode": "DHCP",              // oder "STATIC"
  "vlan": 40,
  "ssid": "BrainIoT",
  "ap": "OpenWrt-AP-EG",
  "rssi": -62,
  "online": true,
  "last_seen": "2026-03-15T14:22:00Z",
  "ha_entity": "device_tracker.esp_growbox_01",
  "ha_room": "Untergeschoss",
  "vendor": "Espressif Inc."      // OUI-Lookup
}
```

### 16.2 WLAN-Einstellungen pro Gerät

Im BrainHome Admin Panel soll man für jedes Gerät einstellen können:

| Einstellung | Technisch | API |
|---|---|---|
| **Gerätename** (Hostname) | Pi-hole Static DHCP Lease Name ODER OpenWrt UCI `uci set dhcp.@host[n].name` | Pi-hole API `POST /api/dhcp/static` / OpenWrt ubus |
| **Netzwerk-Name** (VLAN-Zuweisung) | MAC-basierte VLAN-Zuweisung in OpenWrt | OpenWrt UCI `network.lan.macaddr_vlan_map` + Bridge |
| **IP-Adresse** (DHCP / Manuell) | Pi-hole Static Lease ODER OpenWrt DHCP Static | `ip_mode = DHCP` → Lease vergeben, `STATIC` → feste IP |
| **WLAN SSID** (welches Netz) | OpenWrt hostapd: SSID wird über VLAN gesteuert – Gerät bestimmt SSID durch Passwort | Passwort ändern → Gerät muss reconnecten |
| **WLAN Passwort** | OpenWrt UCI `uci set wireless.@wifi-iface[n].key=NEUES_PASSWORT && uci commit && wifi reload` | OpenWrt ubus RPC oder SSH |

**Wichtig – MAC-basierte VLAN-Zuweisung:**
OpenWrt kann ein Gerät anhand seiner MAC-Adresse in ein bestimmtes VLAN (= Netz = SSID) zwingen, unabhängig davon, mit welchem SSID es sich verbindet.
→ Das ist die sauberste Lösung: Nicht das Passwort entscheidet das Netz, sondern die MAC.

```
Gerät verbindet sich mit BrainWLAN-EG
  → OpenWrt prüft MAC
  → MAC ist in IoT-Liste → VLAN40 (IoT) egal welches SSID
```

**Alternative für ESP32/Zigbee ohne MAC-Steuerung:**
Separates IoT-SSID `BrainIoT` mit eigenem Passwort → nur VLAN40 erreichbar.

### 16.3 Backend-API (Webserver, geplant Phase 2)

```
GET  /api/network/devices             → Alle bekannten Geräte (aggregiert)
GET  /api/network/devices/{mac}       → Einzelgerät mit allen Eigenschaften
PUT  /api/network/devices/{mac}       → Gerätename ändern, IP-Mode, VLAN-Zuweisung
POST /api/network/devices/{mac}/wlan  → WLAN-SSID/Passwort zuweisen

GET  /api/network/wlan/ssids          → Alle konfigurierten SSIDs (Pro AP)
PUT  /api/network/wlan/ssid/{name}    → SSID-Passwort ändern (→ OpenWrt ubus)

GET  /api/network/dhcp/leases         → Alle DHCP-Leases (Pi-hole)
POST /api/network/dhcp/static         → Statische IP-Reservierung anlegen
DELETE /api/network/dhcp/static/{mac} → Reservierung entfernen
```

### 16.4 Frontend-Modul (Webserver, geplant)

```
/network/devices         → Geräte-Übersichtstabelle
                           Spalten: Name, IP, MAC, VLAN, SSID, AP, Online, Zuletzt gesehen
                           Filter: VLAN, SSID, Online/Offline, Hersteller
                           Aktionen: Umbenennen, IP fixieren, Netz wechseln

/network/wlan            → WLAN-Konfiguration
                           Alle SSIDs mit Passwort-Änderung (Admin-only!)
                           AP-Status pro SSID

/network/dhcp            → DHCP-Lease-Verwaltung
                           Statische IPs anlegen / bearbeiten / löschen

/network/vlan            → VLAN-Übersicht (nur lesend, Änderungen via OpenWrt direkt)
```

### 16.5 Transition FritzBox → OpenWrt (Schritt für Schritt)

```
Phase 0 (heute):
  FritzBox = Router + DHCP + WLAN
  OpenWrt-APs hängen als Access Points hinter FritzBox
  BrainHome liest Gerätedaten via FritzBox TR-064

Phase 1 (nächste):
  Pi-hole übernimmt DHCP (FritzBox deaktiviert DHCP)
  Pi-hole = DNS + DHCP + Static Leases
  BrainHome liest Gerätedaten via Pi-hole API

Phase 2 (Vollausbau):
  OpenWrt-VM als Gateway/Firewall (ersetzt FritzBox-Routing)
  VLANs aktiv (VLAN10/20/30/40/50/70)
  FritzBox nur noch als DSL-Modem (Bridged Mode) oder ganz ersetzt
  BrainHome Admin Panel = zentrale Oberfläche für alles

Phase 3 (Zielzustand):
  Kein FritzBox-UI mehr nötig
  Alle Geräteverwaltung, WLAN, DHCP, DNS über BrainHome Admin Panel
```

---

## 17. Infrastruktur-Roadmap (Phasen)

### Phase 1 – Grundsystem (aktuell weitgehend fertig)
- [x] Proxmox EG + UG aktiv
- [x] Home Assistant 4× Instanzen (master/eg/og/ug)
- [x] Pi-hole 2× (primär + sekundär, CT)
- [x] Caddy Reverse-Proxy + CA (CT110)
- [x] BrainHome Admin Panel (CT112, Angular + Quarkus)
- [x] OpenWrt APs (EG + OG)
- [ ] Keycloak installieren + konfigurieren (**BLOCKER**)
- [ ] Pi-hole DHCP aktivieren (FritzBox-DHCP deaktivieren)

### Phase 2 – Identity + Netzwerk-Eigenverantwortung
- [ ] Keycloak SSO: Quarkus + Angular Auth
- [ ] VLAN-Konfiguration am Core-Switch
- [ ] OpenWrt Gateway-VM als Firewall/Router
- [ ] Pi-hole als primärer DHCP-Server
- [ ] BrainHome: `/network/devices` Geräteverwaltung
- [ ] BrainHome: FritzBox TR-064 API-Client → Gerätedaten heute
- [ ] BrainHome: Pi-hole DHCP API → statische Leases
- [ ] BrainHome: OpenWrt LuCI API → WLAN-SSID/Passwort-Management

### Phase 3 – Automation + Monitoring
- [ ] Zigbee2MQTT zentralisiert
- [ ] ESPHome OTA via master HA
- [ ] Prometheus + Grafana (Loki)
- [ ] MQTT-Modul im BrainHome Admin Panel
- [ ] Energie-Scheduled-Job (AI-on-the-Edge → ZaehlerAblesung)
- [ ] Alerting: Uptime-Kuma Webhooks

### Phase 4 – AI + Vision
- [ ] Frigate NVR (Proxmox UG, GPU-Passthrough oder Coral TPU)
- [ ] Coral TPU für Inferenz
- [ ] Türklingel-Integration: BrainPi → HLS-Stream → BrainHome Panel

### Phase 5 – BrainPortal (Zielzustand)
- [ ] `portal.brain` = vollständige Smart-Home-Oberfläche
- [ ] Dashboard: Energie, Hausstatus, Garten, Werkstatt, Server, Netzwerk
- [ ] Nebenkostenabrechnung, Immobilienverwaltung vollständig
- [ ] Alles ohne FritzBox-UI verwaltbar

---

## 18. MQTT-Infrastruktur

```
Zigbee-Gerät (Rolllade, Sensor)
    │
Zigbee Coordinator (USB an proxmox-eg)
    │
Zigbee2MQTT
    │
MQTT Broker (Mosquitto) ← mqtt.brain
    │
    ├── Home Assistant EG/OG/UG (Subscriptions)
    ├── ESPHome-Geräte (Growbox, Sensoren)
    ├── AI-on-the-Edge (ESP32-CAM Strommeter)
    └── BrainHome Backend (geplant: SmallRye MQTT Consumer)
```

**MQTT Topics (Konventionen):**

| Topic-Muster | Produzent | Konsument |
|---|---|---|
| `zigbee2mqtt/<name>` | Zigbee2MQTT | HA-Instanzen |
| `homeassistant/<domain>/<id>/config` | ESPHome / HA | HA-Discovery |
| `aionthedge/strommeter/main/value` | AI-on-the-Edge ESP32 | HA-Master, Webserver |
| `brainhome/alerts/<service>` | Webserver Backend | Dashboard |

---

## 19. Monitoring-Stack (Zielzustand)

| Komponente | Funktion | Host |
|---|---|---|
| **Prometheus** | Metriken-Scraping (Proxmox, HA, MQTT, Caddy) | proxmox-og CT |
| **Grafana** | Dashboards für Energie, Server, Netzwerk | proxmox-og CT |
| **Loki** | Log-Aggregation aller Container | proxmox-og CT |
| **Uptime Kuma** | HTTP/TCP Verfügbarkeits-Monitoring | AppStore (CT) |
| **BrainHome Panel** | Admin-Oberfläche + Alerts-Dashboard | CT112 |
| **system_info.sh** | Shell-Skripte → JSON-Metriken | Proxmox-Nodes |

---

## 20. Backup-Strategie

| System | Was | Intervall | Ziel |
|---|---|---|---|
| Proxmox VMs | komplette VM-Snapshots | täglich | PBS (Proxmox Backup Server UG) |
| Proxmox CTs | komplette CT-Snapshots | täglich | PBS |
| NAS | Daten-Backup | wöchentlich | externes Laufwerk / Cloud |
| Home Assistant | `/config/` Verzeichnisse | täglich (git push) | GitHub (5t3mp3l/haos*) |
| BrainHome | Quellcode | bei Commit | GitHub (5t3mp3l/BrainHome) |
| PostgreSQL | pg_dump | täglich | PBS oder NAS |

---

## 21. Warum brauchen wir das alles?

> **"verstehst du warum wirs sowas brauchen?"** – Ja. Zusammengefasst:

1. **Kein Single Point of Failure**: Eine FritzBox = ein Punkt, der alles lahmlegt. Mit Proxmox-HA, Pi-hole redundant, Caddy-HA kann jede Komponente ausfallen ohne Gesamtausfall.

2. **Sicherheit durch Segmentierung**: Ein kompromittiertes IoT-Gerät (z.B. smarte Steckdose) kann durch VLAN-Trennung nicht ins Server-Netz routen. Bei FritzBox-only ist alles im gleichen Netz.

3. **Volle Kontrolle bei WLAN-Migration**: Wenn ein Gerät ins IoT-VLAN soll, brauchen wir eine eigene Oberfläche – die FritzBox kennt keine VLANs für Smart-Home-Geräte.

4. **Geräteverwaltung bei wachsendem Bestand**: 17 Liegenschaften, 30+ Zigbee-Geräte, 10+ ESP32, 4 HA-Instanzen, 2 APs → ohne zentrale Geräteverwaltung verliert man den Überblick.

5. **Unabhängigkeit von Cloud und Hersteller**: FritzBox → AVM (deutsches Unternehmen, solide, aber kein VLAN-Konzept für BrainHome). OpenWrt + eigenes Panel = 100% selbst kontrolliert.

6. **Skalierbarkeit**: Weiteres Haus (Marokko, Togo) → weitere Instanz aufschalten. Mit FritzBox nicht möglich. Mit BrainHome-Stack: neue Proxmox-Node + neue HA-Instanz → fertig.

Leise & stromsparend