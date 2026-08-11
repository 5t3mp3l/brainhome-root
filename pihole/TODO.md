# Pi-hole – TODO & Roadmap

> **pihole-ug** (ehem. pihole-1): CT100, IP 192.168.188.251 (primär, aktuell proxmox-eg → Migration nach proxmox-ug geplant)
> **pihole-og** (ehem. pihole-2): CT111, IP 192.168.188.249 (fallback, proxmox-og)
> **pihole-eg**: geplant, proxmox-eg, IP noch zu vergeben
> **Rolle**: DNS-Resolver + Werbeblocker (Multi-Node-Setup mit Sync)  
> **Zusammenspiel mit BrainHome**: Pi-hole ist der **DNS-Backbone** – jeder neue Dienst braucht einen DNS-Eintrag hier. BrainHome Dashboard kann Pi-hole Statistiken live anzeigen.

---

## 🔴 INFRA-MIGRATION (offen)

### pihole CT100 → proxmox-ug migrieren `[Ticket 0C63E3]`
- [ ] CT100 auf proxmox-eg stoppen + nach proxmox-ug migrieren
- [ ] Hostname: `pihole-ug` (statt `pihole-1`)
- [ ] Sync-Script `sync-pihole.sh` auf neuen Node anpassen
- [ ] DNS-Einträge in pihole selbst aktualisieren (pihole-ug.brain → neue IP wenn geändert)
- [ ] ENTWICKLER-WISSEN.md + README + TODO aktualisieren

### pihole-2 CT111 umbenennen zu pihole-og `[Ticket 7DA07B]`
- [ ] Hostname in CT111 ändern: `hostnamectl set-hostname pihole-og`
- [ ] Proxmox-Beschriftung (Notes/Name) auf proxmox-og updaten
- [ ] `pihole-og.brain` DNS-Eintrag anlegen / `pihole-2.brain` behalten?
- [ ] sync-pihole.sh: Host-Referenz von pihole-2 auf pihole-og aktualisieren
- [ ] ENTWICKLER-WISSEN.md + TODO aktualisieren

### pihole-eg auf proxmox-eg erstellen `[Ticket 78C8F2]`
- [ ] Neuen CT auf proxmox-eg erstellen (CT-Nummer vergeben, IP z.B. 192.168.188.250)
- [ ] Pi-hole v6 installieren + Unbound konfigurieren
- [ ] DNSSEC aktivieren
- [ ] Sync mit pihole-ug (3-Node-Setup: ug=primär, og=fallback, eg=EG-lokal)
- [ ] FritzBox DNS für EG-Netz auf pihole-eg zeigen
- [ ] `pihole-eg.brain` DNS-Eintrag anlegen
- [ ] ENTWICKLER-WISSEN.md + TODO + DNS-EINTRAEGE.md aktualisieren

---

## ✅ ABGESCHLOSSEN

- [x] Pi-hole v6.4 auf beiden Instanzen installiert
- [x] Unbound als rekursiver Resolver (127.0.0.1:5335) konfiguriert
- [x] DNSSEC aktiv
- [x] Sync-Script `sync-pihole.sh` (gravity.db + pihole.toml)
- [x] Cron alle 30 Minuten (eingerichtet)
- [x] DNS-Rebind-Schutz Ausnahme `brain` in FritzBox
- [x] Alle aktuellen `*.brain` Hostnamen eingetragen

---

## 🔄 LAUFEND – DNS-Einträge ergänzen (bei jedem neuen Dienst!)

> **Regel**: Immer auf pihole-1 eintragen – Sync überträgt auf pihole-2 automatisch.

### Einzutragende Hostnamen (sobald Dienste live)
- [ ] `appstore.brain` → 192.168.188.200 (Dashy App-Store VM)
- [ ] `portainer.brain` → 192.168.188.200
- [ ] `uptime.brain` → IP sobald bekannt (Uptime Kuma)
- [ ] `grafana.brain` → IP sobald bekannt
- [ ] `nextcloud.brain` → IP sobald bekannt
- [ ] `frigate.brain` → IP sobald bekannt
- [x] `proxmox-dev.brain` → 192.168.188.254 (gesetzt)
- [x] `proxmox-ug.brain` → 192.168.188.248 (gesetzt)
- [x] `proxmox-eg.brain` → 192.168.188.253 (gesetzt)
- [x] `proxmox-og.brain` → 192.168.188.252 (gesetzt)

### Bestehende Einträge verifizieren
- [ ] Alle aktuell eingetragenen `*.brain` Einträge in `DNS-EINTRAEGE.md` dokumentieren (vollständige Liste)
- [ ] Prüfen ob `brainhome.brain` und `brainhome-dev.brain` korrekt auf CT112 (192.168.188.112) zeigen

---

## PHASE 2 – BrainHome Dashboard-Integration

> BrainHome Angular-Modul `src/app/pihole/` zeigt Pi-hole Statistiken live an.  
> **Frontend: ✅ implementiert** | **Backend: ⏳ noch nicht implementiert**

### BrainHome Angular Frontend (`src/app/pihole/`) – ✅ DONE

- [x] `pihole/stats` – Live-Statistiken: Queries/Tag, Block-Rate%, blockierte Queries, Domains auf Blockliste, Clients + Enable/Disable-Button
- [x] `pihole/top-blocked` – Top 10 blockierte Domains (Balken-Visualisierung) + Top Clients mit Block-Rate
- [x] `pihole/sync` – Sync-Status pihole-1 ↔ pihole-2: Online-Status, Gravity-DB-Größen, Sync-Zeitpunkt, Divergenz-Warnung
- [ ] Dashboard-Widget: **Pi-hole Status** – Queries/Tag, Block-Rate%, Donut-Chart Top blocked

### BrainHome Quarkus Backend (`NetworkPiholeManagement.java`) – ⏳ TODO

> `application.properties`:  
> `pihole.api.url=http://192.168.188.251`  
> `pihole.api.token=...` (Pi-hole v6: Web-GUI → Settings → API → App Passwords)  
> REST Client: `PiholeApiClient.java` mit `@RegisterRestClient(configKey="pihole")`

- [ ] Pi-hole v6 API-Token generieren: Web-GUI → Settings → API → „App Passwords" → Token kopieren
  - Pi-hole v6 API Doku: `http://192.168.188.251/api/` (Swagger UI eingebaut!)
- [ ] `PiholeApiClient.java` Interface anlegen (`@RegisterRestClient`, Auth via `Authorization: Bearer <token>` Header)
- [ ] `GET /api/network/pihole/stats` → Pi-hole v6 `GET /api/stats/summary`
  - Felder: `queriesToday`, `queriesBlocked`, `blockRatePct`, `domainsOnBlocklist`, `clientsTotal`, `status`, `instance`
- [ ] `GET /api/network/pihole/clients` → Pi-hole v6 `GET /api/stats/top_clients`
  - Felder: `ip`, `hostname`, `queriesTotal`, `queriesBlocked`, `blockRatePct`
- [ ] `GET /api/network/pihole/top-blocked` → Pi-hole v6 `GET /api/stats/top_blocked`
  - Felder: `domain`, `hits`
- [ ] `POST /api/network/pihole/disable?seconds=300` → Pi-hole v6 `POST /api/dns/blocking` `{"blocking": false, "timer": 300}`
- [ ] `POST /api/network/pihole/enable` → Pi-hole v6 `POST /api/dns/blocking` `{"blocking": true}`
- [ ] `GET /api/network/pihole/sync-status` → Backend prüft SSH-Erreichbarkeit + liest letzten Sync-Zeitpunkt aus Logfile
  - Felder: `lastSync`, `lastSyncAgo`, `pihole1Online`, `pihole2Online`, `gravitySizePihole1`, `gravitySizePihole2`, `inSync`
  - Sync-Log: `/var/log/pihole-sync.log` auf dem Server (oder Cron-Output)
- [ ] `GET /api/network/pihole/query-log?limit=100` → Pi-hole v6 `GET /api/queries?max=100`
  - Felder: `timestamp`, `type`, `domain`, `client`, `status`, `answeredBy`
- [ ] **Fallback**: wenn Pi-hole nicht erreichbar → `null` / leere Liste + `X-Backend-Warning` Header (kein 500)

### Pi-hole Blocklist Management (Phase 3, optional)
- [ ] Liste aktiver Blocklisten anzeigen: `GET /api/network/pihole/lists` → Pi-hole v6 `GET /api/lists`
- [ ] Whitelist-Einträge per BrainHome verwalten: `POST /api/network/pihole/whitelist`

---

## PHASE 3 – Robustheit & Monitoring

### Sync verbessern
- [x] Sync-Status in BrainHome sichtbar (`pihole/sync` Komponente – Online-Status, Gravity-DB-Größen, letzter Sync)
- [ ] Sync-Verifizierung: Nach Sync prüfen ob pihole-2 tatsächlich aktuelle Daten hat
- [ ] Sync per Webhook triggern: Wenn DNS-Eintrag hinzugefügt wird → Sync sofort (nicht auf Cron warten)
- [ ] `sync-pihole.sh` → Fehler per HA-Notification melden (über `/api/homeassistant/notify`)

### Failover-Logik
- [ ] Prüfen: Wenn pihole-1 down → pihole-2 automatisch primär?  
  - FritzBox DHCP: DNS 1: .251, DNS 2: .249 → Fallback ist konfiguriert ✅
  - Aber: pihole-1-Änderungen gehen verloren wenn pihole-1 nicht erreichbar war
- [ ] Alerting: Wenn pihole-1 nicht erreichbar → HA Notification + BrainHome Alert

### Logging & Statistiken
- [ ] Pi-hole Query-Log Retention Policy definieren (wie lange aufheben?)
- [ ] Historische Blockrate-Statistiken in BrainHome-Datenbank speichern (täglich snapshotten)

---

## 🐛 BEKANNTE PROBLEME / TECHNICAL DEBT

- [ ] `sync-pihole.sh` synchronisiert `gravity.db` (78 MB!) – prüfen ob diff/incremental möglich bei v6
- [ ] Pi-hole v6 API komplett neu (im Vergleich zu v5) – bestehende Skripte updaten falls nötig
- [ ] pihole-2 ist auf Debian 12, pihole-1 auf Ubuntu 24.10 – Divergenz im OS, beim nächsten Neuaufbau vereinheitlichen

---

## BEFEHLE SCHNELLREFERENZ

```bash
# SSH
ssh pihole      # pihole-1 (primär)
ssh pihole2     # pihole-2 (fallback)

# Status
ssh pihole "/usr/local/bin/pihole status"

# DNS testen
nslookup brainhome.brain 192.168.188.251
nslookup brainhome.brain 192.168.188.249

# Neuer DNS-Eintrag (auf pihole-1, dann sync!)
ssh pihole "vi /etc/pihole/pihole.toml"  # → hosts[] ergänzen
ssh pihole "systemctl restart pihole-FTL"
bash /home/pihole/scripts/sync-pihole.sh

# Sync manuell
bash /home/pihole/scripts/sync-pihole.sh

# Pi-hole API (v6)
curl -s http://192.168.188.251/api/stats/summary
```
