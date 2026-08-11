# BrainHome – Erlerntes Wissen (Lessons Learned)

> Stand: 26.03.2026
> Zweck: Zentrale, langfristige Betriebs- und Engineering-Erkenntnisse aus den letzten Migrationen, Tooling- und Workspace-Arbeiten.

---

## 1) Betriebsrelevante Kern-Erkenntnisse

### 1.1 Live-Migration ist nicht immer "live"
- LXC mit `local-lvm` ist **nicht shared storage**.
- Ergebnis: echte unterbrechungsfreie Live-Migration ist nicht möglich.
- Praxis: `pct migrate ... --restart` oder Stop + Migrate führt zu Downtime.
- NFS-gehostete LXC-Backups mit `vzdump --mode snapshot` können auf `suspend` zurückfallen. Das friert Keepalived ein, verhindert VRRP-Failover und kann wie kompletter Dienst-Ausfall erscheinen.

### 1.2 DNS ist ein Single Point of Pain bei Wartungen
- Wenn `pihole-1` primär genutzt wird und kurz ausfällt, verlieren WLAN-Clients DNS.
- Das kann wie kompletter WLAN-Ausfall wirken, obwohl Layer-2 noch steht.
- Besonders kritisch: Arbeiten von einem WLAN-Client aus, der selbst auf DNS angewiesen ist.

### 1.3 Vor jeder Migration: Kontext prüfen
- Wo arbeite ich (LAN/WLAN)?
- Welche DNS-Instanz ist primär/sekundär?
- Ist Fallback wirklich erreichbar?
- Maintenance-Fenster und Auswirkungen auf aktive Nutzer klären.

### 1.4 Migrationszeit realistisch planen
- CT100 (Pi-hole, 10G): ~97s Transferzeit + Stop/Start + Verifikation.
- CT110 (Caddy, 4G): ~45s Transferzeit + Stop/Start + Verifikation.
- Netto-Beeinträchtigung liegt über reiner Kopierzeit (Service-Neustarts, DNS/Caches, Client-Verhalten).

---

## 2) Architektur- und Service-Erkenntnisse

### 2.1 Pi-hole v6 lokale DNS-Pflege
- In diesem Setup werden lokale Einträge wirksam über `/etc/pihole/pihole.toml` (`dns.hosts`) verwaltet.
- `custom.list` alleine ist in v6-Setups oft nicht die zuverlässige Quelle für aktive Antworten.

### 2.2 Namenskonsistenz ist essenziell
- Umbenennungen (z. B. `pihole-2` → `pihole-og`) müssen vollständig durchgezogen werden:
  - Container-Hostname
  - Proxmox-Config (`pct set --hostname`)
  - `/etc/hosts`
  - Scripts/Kommentare
  - DNS-Namen
  - Doku/TODO/Tickets

### 2.3 Caddy-HA sauber trennen
- caddy-master auf CT110 und Backup auf CT120 klar dokumentieren.
- Nach Node-Migration immer prüfen:
  - Caddy läuft
  - 80/443 listen
  - Keepalived-Rollen konsistent

---

## 3) Tooling- und Prozess-Erkenntnisse

### 3.1 Crash-safe Agent-Workflow reduziert Risiko
- Schrittweise Ausführung mit persistentem Status verhindert Kontrollverlust bei VS Code/Remote-Abbrüchen.
- Muster:
  1. Schritt starten
  2. exakt eine Aktion
  3. Ergebnis markieren
  4. weiter

### 3.2 Pre-Flight Checks als Standard
- Ein dedizierter Pre-Flight (Verbindung, DNS-Fallback, kritische Services) vor produktionsnahen Eingriffen ist Pflicht.
- Pre-Flight sollte menschlich lesbare Warnungen und optional maschinenlesbaren Output liefern.

### 3.3 Terminal-/Shell-Learnings
- Für JSON-Pipelines niemals vorher abschneiden/trunkieren.
- Bei Exit-Code-Validierung keine verfälschenden Pipelines verwenden.
- In shell-notes keine Backticks verwenden (Command-Substitution-Risiko).

### 3.4 Git-Safety bei Multi-Repo-Arbeit
- Nur gezielte Dateien committen (z. B. `.gitignore`), nie pauschal alles.
- Bei Non-fast-forward: sauber rebasen, lokale WIP sichern.
- Bei Stash-Restore-Konflikten: dateigenaue Wiederherstellung ist sicherer als blindes `stash pop`.

---

## 4) Workspace-Architektur-Erkenntnisse

### 4.1 Modular vor monolithisch
- Jedes Modul braucht eigene VS-Code-Umgebung:
  - eigene `.code-workspace`
  - eigene `.vscode/settings.json`
  - eigene `.vscode/extensions.json`
- Vorteil: weniger kognitive Last, weniger Nebenwirkungen, passende Umgebung pro Domäne.

### 4.2 Zentraler BrainHome-Workspace bleibt Orchestrator
- Der große Root-Workspace ist weiterhin sinnvoll für Gesamtbetrieb.
- Er soll aber auf modulare Teil-Workspaces und standards basieren, nicht auf ad-hoc Sonderfällen.

### 4.3 Konfigurations-Guardrail
- Beim Generieren von `.code-workspace` per heredoc immer **quoted heredoc** nutzen (`<<'EOF'`), damit `${workspaceFolder}` nicht durch die Shell kaputt expandiert.

---

## 5) Konkrete Verbesserungen pro Modul (priorisiert)

### webserver
- Standard-Runbook als Task-Flow: `Pre-Flight -> Migrate -> Verify -> Ticket Done`.
- Einheitliche Health-Checks als ausführbare Tasks.

### pihole
- DNS-Health beider Instanzen als Standardtask.
- Sync-Prüfung als Routine (inkl. Namenskonsistenz).
- Doku klar auf v6-Realität (`pihole.toml`) ausrichten.

### caddy
- Keepalived + Caddy Health als Pflichtcheck nach jeder Infrastrukturänderung.
- VIP-Verhalten regelmäßig verifizieren.

### HomeAssistant / haos*
- Je Instanz eigene Validierungs-Tasks (Config, Templates, Neustart-Checks).
- Runtime-Artefakte konsequent aus Git heraushalten.

### keycloak
- Wiederherstellbare Export/Import-Backups als Standardprozess.

### nextcloud
- VMID immer cluster-global prüfen (nicht nur auf dem Ziel-Node).
- Volume-Pfade in docker-compose.yml immer via Env-Variable parametrisieren.
- occ ist der offizielle Konfigurationsweg – niemals direkt `config.php` editieren.
- Background-Jobs nach Erstinstallation auf Cron umstellen (`occ background:cron`).
- trusted_domains nach IP-Wechsel immer explizit bereinigen.

### grafana
- Provisioning-Validierung und Dashboard-Konsistenz als wiederholbarer Check.

### pxe-boot / autarkie / system-monitor / fritzbox / appstore
- Je Modul 2-3 Kern-Tasks (Health, Logs, Config-Check) standardisieren.

---

## 6) Git- und Repo-Hygiene Standard

- `.gitignore` über alle Repos harmonisieren.
- Lokale Runtime-/Cache-/Log-Artefakte aus Commits fernhalten.
- `.vscode` differenziert behandeln:
  - lokale State-Dateien ignorieren
  - geteilte Team-Dateien (`settings.json`, `extensions.json`, `tasks.json`) erlauben

---

## 7) Betriebsprinzipien (kurz)

1. Sicherheit vor Geschwindigkeit.
2. Vor Änderung immer Kontext + Fallback prüfen.
3. Kleine, reversible Schritte statt großer Aktionen.
4. Doku und Ticket-Status sind Teil der Umsetzung, nicht Nacharbeit.
5. Multi-Repo-Änderungen nur dateigenau und nachvollziehbar.

---

## 8) HomeAssistant – remote_homeassistant Deep Dive (März 2026)

### 8.1 Niemals core.config_entries manuell editieren
- HA 2026+ erwartet in jedem Entry-Objekt: `created_at`, `modified_at`, `discovery_keys`, `subentries`.
- Fehlen diese → HA-Master geht in Crash-Loop (`Home Assistant has crashed!`).
- **Fix**: Backup wiederherstellen. Danach NUR über die REST-API-Flows arbeiten.
- **Backup läuft automatisch** (`core.config_entries.bak.*`), aber es revertiert **alle** zwischenzeitlichen Änderungen — auch unabhängige wie IP-Korrekturen.

### 8.2 HA 2026 REST API – richtige Pfade
- Config Entry **löschen**: `DELETE /api/config/config_entries/entry/{entry_id}` (nicht `/api/config/config_entries/{entry_id}` — 404!)
- Flow **abbrechen/löschen**: `DELETE /api/config/config_entries/flow/{flow_id}`
- Flow **inspizieren** (aktueller Step): `GET /api/config/config_entries/flow/{flow_id}`
- Flow **vorwärtsbewegen**: `POST /api/config/config_entries/flow/{flow_id}` mit Payload

### 8.3 In-Progress-Flows via WebSocket auflisten
```python
ws.send(json.dumps({'id': 1, 'type': 'config_entries/flow/progress'}))
# Gibt alle laufenden Flows zurück — einschließlich source/unique_id/step_id
```

### 8.4 remote_homeassistant auf frischer HA-Instanz einrichten
Reihenfolge strikt einhalten:
1. **Component kopieren** von einer vorhandenen Instanz via SSH-Pipe:
   ```bash
   ssh root@ha-master "tar czf - /config/custom_components/remote_homeassistant" | \
     sshpass -p 'password' ssh root@ha-ga "cat > /tmp/rha.tar.gz && tar xzf /tmp/rha.tar.gz -C /config/custom_components"
   ```
2. **HA neu starten** (damit Component geladen wird)
3. **Config Flow ausführen**: `POST /api/config/config_entries/flow {"handler":"remote_homeassistant"}` → Typ `"Setup as remote node"` wählen
4. Erst **danach** ist der Discovery-Endpoint aktiv: `GET /api/remote_homeassistant/discovery` → muss 200 zurückgeben
5. Discovery-Endpoint ist nur aktiv, wenn ein geladener Config-Entry für die Domain existiert; ohne Entry → 404

### 8.5 Zeroconf Auto-Discovery
- Sobald eine HA-Instanz als Remote Node konfiguriert ist, advertised sie sich via `_home-assistant._tcp.local.` (mDNS).
- ha-master's Zeroconf-Integration erkennt das und startet **automatisch** einen Flow mit `source: "zeroconf"`.
- Eigenen manuellen Flow starten führt zu `abort: already_in_progress`.
- **Lösung**: Den bestehenden zeroconf-Flow via WebSocket (`config_entries/flow/progress`) finden und direkt befüllen — er hat den richtigen Host schon vorausgefüllt.

### 8.6 IP-Fix für bestehende Entries
Da `remote_homeassistant` kein Reconfigure unterstützt:
1. Alten Entry löschen: `DELETE /api/config/config_entries/entry/{entry_id}`
2. Warten (ca. 3–10 Sek.) — Zeroconf entdeckt die Instanz mit neuer IP neu und startet Flow
3. Den neuen zeroconf-Flow inspizieren (`GET /api/config/config_entries/flow/{id}`) — hat neue IP vorausgefüllt
4. Token-Payload einsenden: `POST /api/config/config_entries/flow/{id}` mit `host`, `port`, `access_token`, `max_message_size`

### 8.7 entity_registry/remove: korrekte WS-Befehlsform in HA 2026
- **Falsch**: `{"type": "entity_registry/remove", ...}` → `unknown_command`
- **Richtig**: `{"type": "config/entity_registry/remove", "entity_id": "..."}` → success

### 8.8 RHA Entry Reload: korrekte REST-Pfade in HA 2026
- **Falsch**: `POST /api/config/config_entries/{id}/reload` → 404
- **Richtig**: `POST /api/config/config_entries/entry/{id}/reload` → `{"require_restart": false}`

### 8.9 Orphaned Entity Registry Entries nach Entry-Delete
- Wenn ein `remote_homeassistant` Config-Entry gelöscht wird, bleiben seine Registry-Einträge als Orphans (`config_entry_id = None`) erhalten.
- Diese können entity_ids "blockieren" → neu einkommende Remote-Entities bekommen `_2`-Suffix.
- **Cleanup-Workflow**:
  1. Alle `remote_homeassistant` Entities mit `config_entry_id = None` aus Registry ermitteln
  2. Batch-Löschen via `config/entity_registry/remove` WS-API
  3. Alle aktiven RHA-Entries reloaden via `POST /api/config/config_entries/entry/{id}/reload`
  4. Schritt 1–3 bis keine Orphans mehr übrig (2–3 Runden nötig, Reload produziert neue Orphans)
- **Achtung**: Nach Reload entstehen typischerweise neue Orphans — mindestens 2–3 Cleanup-Iterationen nötig bis Konvergenz.

### 8.10 `_2`-Duplikate: zwei verschiedene Ursachen
1. **Orphaned Registry Entries** (behebbar): Entities aus gelöschten Config-Entries, die entity_ids blockieren → via `config/entity_registry/remove` bereinigen
2. **Entity-ID-Konflikte zwischen Remotes** (Design-Entscheidung): Wenn zwei Remote-Instanzen dieselbe entity_id haben (z.B. `binary_sensor.zigbee2mqtt_bridge_connection_state` auf ha-ug UND ha-og), erscheint eine als `_2`. Fix via `entity_filters` in der remote_homeassistant-Konfiguration.

---

## 9) Referenz auf begleitende Doku

- Root-Infra Übersicht: `/home/INFRASTRUCTURE.md`
- Master-Aufgaben: `/home/TODO.md`
- Modulwissen:
  - `/home/pihole/ENTWICKLER-WISSEN.md`
  - `/home/caddy/ENTWICKLER-WISSEN.md`
  - `/home/HomeAssistant/**/ENTWICKLER-WISSEN.md`
  - `/home/nextcloud/ENTWICKLER-WISSEN.md`
- Tooling:
  - `/home/webserver/tools/migration-preflight.sh`
  - `/home/webserver/tools/agent-state.sh`
  - `/home/webserver/tools/devctl.sh` (Cross-Node Dev-Steuerung, dynamisch via pvesh)
  - `/home/workstation/tools/cluster-inventory.sh` (Cluster-Inventar via pvesh)
  - `/home/workstation/docs/ssh-config.md` (SSH-Config Snapshot mit Annotationen)

---

## 9) Webserver/CT-Learnings (21.03.2026)

### 9.1 Dual-Proxmox bewusst trennen
- Editor/Workspace laufen auf `proxmox`, Container-Betrieb auf `proxmox-ug`.
- Lokale Annahmen ueber `pct`, Logs und Runtime-Dateien sind ohne SSH-Routing unzuverlaessig.

### 9.2 Script-Sync ist Teil des Deployments
- Tooling-Aenderungen gelten erst nach Sync auf den Runtime-Host.
- Standardisiert: `sync-scripts` muss alle produktiven Skripte enthalten (`ct-runner.sh`, `ct116-runner.sh`, `port-inspect.sh`, `devctl.sh`).

### 9.3 Service-Port-Mapping muss operational korrekt sein
- `backend-dev` ist operational auf `8440` und darf nicht als `8080` geprueft werden.
- Prod und Dev muessen auf unterschiedliche CTs/Ports gemappt sein (CT116:8081 vs CT112:8440).

### 9.4 Flyway-History kann logisch korrupt sein trotz `success=true`
- Doppelte/inkonsistente `flyway_schema_history`-Ranks koennen zu erneuter Ausfuehrung alter Migrationen fuehren.
- Bei scheinbar paradoxen Migrationsfehlern immer Rank-Reihenfolge und Duplikate pruefen, nicht nur `success`-Flag.

### 9.5 Quartz-Integration: Framework-Factory nicht ueberfahren
- Eigene JobFactory darf Quarkus-interne `InvokerJob`-Instanzierung nicht selbst nachbauen.
- Robust ist: eigene CDI-Jobs bedienen, alle anderen Jobs an die originale Scheduler-Factory delegieren.

### 9.6 Build-Status-Transitions sind gewollte Guardrails
- `running -> starting` ohne `--force` soll blockieren (Schutz vor Doppelstarts).
- Exit-Code `1` bei `start-*` kann damit ein erwartetes, korrektes Verhalten sein.

---

## 10) Infra-Learnings (21.03.2026 - Caddy/OpenWrt/Shared-Storage)

### 10.1 Ticket-Workflow ist zustandsbasiert
- `migration-checks` und `migration-finish` funktionieren nur bei `state=in-progress`.
- Sauberes Muster: `claim -> migration-checks -> migration-finish`.
- Direktes `migration-finish` auf `open` fuehrt zu validem, aber vermeidbarem Fehlerpfad.

### 10.2 Caddy HA in 3-Node-Topologie funktioniert stabil
- CT110 (MASTER), CT120 (BACKUP), CT117 (BACKUP) mit identischem VRRP (`virtual_router_id 51`).
- Prioritaeten steuern Fallback deterministisch (110 > 105 > 100).
- `keepalived` bleibt `inactive`, wenn `/etc/keepalived/keepalived.conf` leer ist (ConditionFileNotEmpty).

### 10.3 Caddy Reload-Falle: Admin Host-Check
- `caddy reload --config ...` kann mit `HTTP 403 host not allowed: :2019` fehlschlagen, wenn Admin nur lokal/strict gebunden ist.
- Ein `systemctl restart caddy` laedt die Disk-Config robust, auch wenn Admin-Reload blockiert ist.

### 10.4 OpenWrt-UG ist hardware-abhaengig
- Ohne USB-WLAN-Adapter (hier: `0e8d:7961`) kann ein OpenWrt-Repeater-Ticket nicht funktional abgeschlossen werden.
- "VM/CT erstellt" ist ohne Funkhardware kein fachlich gueltiges Ergebnis.

### 10.5 Shared-Storage Migrationen: robuste Praxis
- `qmmove` kann bei aktiven VMs mit `broken pipe`, `storage ... locked timeout` oder `Need a root block node` scheitern.
- Fuer grosse Disks ist ein kontrollierter Offline-Pfad stabiler:
  1) VM sauber stoppen (notfalls `qm stop`),
  2) `qm move_disk ... shared-storage --delete 1`,
  3) Cloud-Init auf shared umhaengen,
  4) VM starten und sofort verifizieren.
- Bei Teilfehlern hilft ein kontrollierter Recovery-Pfad:
  - bereits kopierte RAW-Disk auf shared direkt als `scsi0` setzen,
  - alte `local-lvm`-Disk erst nach erfolgreichem Start entfernen.

---

## 11) Proxmox Paket-Update Learnings (21.03.2026)

### 11.1 Enterprise-Repos liegen in deb822-Format vor
- Proxmox liefert Enterprise-Quellen als `.sources` (deb822) aus, **nicht** als klassische `deb ...` Zeile in `.list`.
- Datei: `/etc/apt/sources.list.d/pve-enterprise.sources`
- Rein auf `.list`-Dateien zu prüfen reicht nicht, um aktive Enterprise-Quellen zu erkennen.
- **Diagnostik**: `apt-cache policy | grep enterprise` zeigt auch deb822-Quellen.

### 11.2 Repo-Konsolidierung vor Cluster-Updates
- Reihenfolge: Enterprise + Test-Repos deaktivieren → no-subscription aktivieren → `apt update` → dann Updates einspielen.
- Bei `401 Unauthorized` während `apt update`: immer zuerst Enterprise-Quelle prüfen und deaktivieren.
  ```bash
  mv /etc/apt/sources.list.d/pve-enterprise.sources \
    /etc/apt/sources.list.d/pve-enterprise.sources.disabled
  mv /etc/apt/sources.list.d/pvetest-for-beta.list \
    /etc/apt/sources.list.d/pvetest-for-beta.list.disabled
  ```

### 11.3 pve-cluster Updates sind node-lokal, aber cluster-weit konsistent halten
- `libpve-cluster-*`, `pve-cluster` müssen auf **allen Nodes** auf gleicher Version laufen.
- Nach Update-Nachlauf immer `pvecm status` prüfen: `Quorate: Yes`, alle Nodes `online`.

---

## 12) Nextcloud Deployment Learnings (21.03.2026)

### 12.1 VMIDs sind cluster-global – nicht nur Node-lokal prüfen
- VMID 120 war lokal auf proxmox-dev frei, aber cluster-weit durch `caddy-og` auf proxmox-og belegt.
- VMIDs sind im gesamten Proxmox-Cluster eindeutig – bei Neuanlage immer cluster-weit prüfen:
  ```bash
  pvesh get /cluster/resources --type vm | grep '"vmid"' | sort -t: -k2 -n
  pvesh get /cluster/nextid   # nächste freie VMID direkt zurückgeben lassen
  ```

### 12.2 Docker Compose: Bind-Mount-Pfade immer parametrisieren
- **Problem**: Hardcoded `/home/nextcloud/data/` passt auf Management-Host, aber nicht auf VM (`/home/brain/nextcloud/data/`).
- Container startet ohne Fehler, Nextcloud kann aber nicht schreiben → schwer debugbar.
- **Lösung**: Alle hostbezogenen Pfade als `${VAR:-default}` in Compose parametrisieren.
- `.env.example` muss alle solchen Variablen dokumentiert und mit Standardwert enthalten.
- **Merksatz**: Wenn ein Repo auf mehreren Hosts deployt wird → 0 hardcoded Pfade.

### 12.3 cloud-init auf Ubuntu 24.04: 1 Reboot, dann SSH stabil
- Ubuntu 24.04 cloud-init führt nach erstem Start automatisch einen Reboot durch.
- SSH schlägt in den ersten ~2 Min fehl → kein Bug, kein Fehler in der Konfiguration.
- Warte-Muster:
  ```bash
  until ssh -o ConnectTimeout=3 nextcloud 'uptime' 2>/dev/null; do
    echo "SSH not ready, waiting..."; sleep 10
  done
  ```

### 12.4 SSH-Heredocs scheitern an Sonderzeichen bei Caddy-Konfiguration
- `ssh host "cat << EOF > /etc/caddy/Caddyfile"` bricht bei `$`, `{`, `}`, `"` in Caddy-Blöcken.
- **Bewährtes Muster**: lokal in `/tmp/` schreiben (quoted `<< 'HEREDOC'`), dann scp + `cat >>` auf Zielhost.
  ```bash
  cat > /tmp/block.txt << 'HEREDOC'
  ... Caddy-Block mit Sonderzeichen ...
  HEREDOC
  scp /tmp/block.txt caddy:/tmp/
  ssh caddy 'cat /tmp/block.txt >> /etc/caddy/Caddyfile && caddy validate --config /etc/caddy/Caddyfile'
  ssh caddy 'systemctl reload caddy'
  ```

### 12.5 `/etc/cron.d/` erfordert explizites User-Feld
- Crontab-Syntax und `/etc/cron.d/`-Syntax sind verschieden.
- `/etc/cron.d/`-Dateien brauchen ein explizites User-Feld zwischen Zeitangabe und Befehl:
  ```
  # FALSCH (in /etc/cron.d/ ohne User):
  */5 * * * * docker exec ...

  # RICHTIG (in /etc/cron.d/ mit User):
  */5 * * * * root docker exec -u www-data nextcloud php -f /var/www/html/cron.php
  ```
- Datei muss `chmod 644` haben (nicht executable).

### 12.6 Nextcloud: occ ist der einzige sichere Konfigurationsweg
- Direkte `config/config.php` Bearbeitung kann Array-Integrität brechen und ist nicht cache-aware.
- `occ config:system:set/get/delete` schreibt korrekt und invalidiert den Cache.
- Immer als `www-data` ausführen: `docker exec -u www-data nextcloud php occ ...`

### 12.7 OVERWRITECLIURL hinterlässt Zombie-trusted_domain bei IP-Wechsel
- Wenn `OVERWRITECLIURL` im Compose die alte IP enthielt, bleibt nach IP-Änderung ein verwaister
  `trusted_domains`-Eintrag in der Datenbank.
- **Nach jedem IP-Wechsel** immer prüfen und bereinigen:
  ```bash
  sudo docker exec -u www-data nextcloud php occ config:system:get trusted_domains
  sudo docker exec -u www-data nextcloud php occ config:system:delete trusted_domains <index>
  ```

### 12.8 Collabora und Background-Cron sofort nach Erstinstallation konfigurieren
- Background-Jobs stehen nach Nextcloud-Erstinstallation auf "AJAX" → in Produktion sofort auf Cron umstellen:
  ```bash
  sudo docker exec -u www-data nextcloud php occ background:cron
  ```
- Collabora WOPI-URL via occ setzbar ohne Admin-UI-Klick:
  ```bash
  sudo docker exec -u www-data nextcloud php occ app:enable richdocuments
  sudo docker exec -u www-data nextcloud php occ config:app:set richdocuments wopi_url --value='https://office.brain'
  ```
  Beide Schritte wirken sofort ohne Container-Neustart.

---

## 13) BrainHome Dev-Stack Learnings (22.03.2026)

### 13.1 Keycloak: Audience Mapper ist Pflicht für Multi-Client-Setups

Wenn Angular (`brainhome-frontend`, public client) einen Token holt und das Backend (`brainhome-backend`, confidential) diesen validiert, muss der Token `aud=brainhome-backend` enthalten. Standardmäßig ist `aud=account` gesetzt.

**Symptom:** Quarkus blockiert alle Requests mit HTTP 401, obwohl Token gültig und Keycloak erreichbar ist.

**Fix:** Audience-Mapper im `brainhome-frontend`-Client anlegen:
- Keycloak Admin → Client `brainhome-frontend` → Client Scopes → Add Mapper
- Typ: `Audience`, `included.client.audience = brainhome-backend`, `access.token.claim = true`

**Nebeneffekt:** `dev.env` auf CT112 hatte `KEYCLOAK_CLIENT_ID=brainhome-portal` (falsch) → muss `brainhome-backend` sein.

---

### 13.2 Jackson vs. JSON-B (Yasson): Niemals beide gleichzeitig

Wenn `quarkus-resteasy-reactive-jackson` AND `quarkus-resteasy-reactive-jsonb` im Classpath sind, übernimmt **Yasson die Kontrolle** — Jackson-Annotationen (`@JsonIgnore`, `@JsonIgnoreProperties`) werden ignoriert.

**Resultat:** Yasson versucht alle Getter zu serialisieren, inkl. Java-Reflection-Getter wie `getEnclosingConstructor()` auf `Class<?>`:
```
jakarta.json.bind.JsonbException: Error accessing getter 'getEnclosingConstructor' declared in 'class java.lang.Class'
```

**Lösung:** `quarkus-resteasy-reactive-jsonb` aus `build.gradle` entfernen. Jackson ist dann alleiniger Serialisierer.

---

### 13.3 Jackson GETTER-only: DTOs brauchen Getter oder @JsonAutoDetect

`ResteasyModuleProvider` konfiguriert Jackson so, dass **nur Getter sichtbar** sind:
```java
mapper.setVisibility(PropertyAccessor.ALL, Visibility.NONE);
mapper.setVisibility(PropertyAccessor.GETTER, Visibility.ANY);
```

DTOs mit `public String field;` ohne Getter werden als `{}` serialisiert oder erzeugen 500.

**Zwei gültige Patterns:**

Option A – Getter/Setter (für komplexere DTOs):
```java
public String getStreamUrl() { return streamUrl; }
public void setStreamUrl(String v) { this.streamUrl = v; }
```

Option B – `@JsonAutoDetect` (für einfache Datenklassen):
```java
@JsonAutoDetect(fieldVisibility = JsonAutoDetect.Visibility.PUBLIC_ONLY)
public class MeinDTO { public String field; }
```

---

### 13.4 Git-Objekt-Korruption durch unterbrochenen Schreibvorgang

`git commit` während Proxy-Neustart → leere Dateien in `.git/objects/`. Erkennung:
```
git log → fatal: bad object HEAD
git fsck --full → empty loose object
```

Recovery (wenn `rm` und `find -delete` per Policy blockiert):
```python
import os, glob
for o in glob.glob('.git/objects/*/*'):
    if os.path.getsize(o) == 0:
        os.remove(o)
```
```bash
git fetch origin main && git reset --hard origin/main
```

---

### 13.5 Flyway + Hibernate: snake_case Spalten-Divergenz

Hibernate `SpringPhysicalNamingStrategy` generiert `camelCase → snake_case` Spaltennamen automatisch (z.B. `clientId → client_id`). Ältere manuell erstellte Migrationen können davon abweichen.

**Diagnose:** `SchemaManagementException: Schema-validation: missing column`

**Fix:** Flyway-Migration anlegen, die `ALTER TABLE ... RENAME COLUMN` durchführt, um die DB-Spalten an die Hibernate-Erwartungen anzupassen.

---

### 13.6 MQTT in Quarkus Dev: DevServices deaktivieren + Channels abschalten

Bei fehlenden MQTT-Credentials spammt Quarkus-Dev automatisch mit Reconnect-Fehlern.

```properties
# application.properties
%dev.quarkus.devservices.enabled=false
%dev.mp.messaging.incoming.energy-meter.enabled=false
%dev.mp.messaging.incoming.zigbee-status.enabled=false
%dev.mp.messaging.incoming.ha-events.enabled=false
```

DevServices versucht sonst einen lokalen MQTT-Broker zu starten (Docker) – unerwünscht in LXC-Dev-Containern ohne Docker.

---

## 14) Proxmox-Cluster Infra-Learnings (25.03.2026)

### 14.1 `/home` ist auf jedem Proxmox-Node ein separates lokales Filesystem

- `/home` ist auf keinem Node automatisch NFS-synchronisiert. Jeder Node hat seine eigene Kopie.
- Skript-Änderungen auf proxmox-master liegen **nicht automatisch** auf proxmox-ug/eg/og/ws vor.
- Konsequenz: Nach jeder Änderung an Tools wie `devctl.sh` explizit auf alle Nodes deployen:
  ```bash
  for NODE in proxmox-workstation proxmox-ug proxmox-eg proxmox-og; do
    scp /home/webserver/tools/devctl.sh ${NODE}:/home/webserver/tools/devctl.sh
  done
  ```
- Langfristig: `git` auf allen Nodes installieren oder ein Deploy-Skript standardisieren.

### 14.2 pvesh `--type lxc` ist nur auf neueren PVE-Versionen gültig

- Neuere PVE (proxmox-master, proxmox-ws): `pvesh get /cluster/resources --type lxc` ✅
- Ältere PVE (proxmox-ug): nur `vm`, `storage`, `node`, `sdn` als Type unterstützt → `400 Parameter verification failed`
- **Portable Lösung**: kein `--type`-Flag verwenden, stattdessen im Python-Code nach `item['type'] == 'lxc'` filtern:
  ```bash
  pvesh get /cluster/resources --output-format json | python3 -c "
  import json, sys
  data = json.load(sys.stdin)
  for item in data:
      if item.get('type') != 'lxc': continue
      ...
  "
  ```

### 14.3 `ssh-keyscan -H` schreibt nur Kommentare, keine echten Key-Einträge

- `ssh-keyscan -H 192.168.188.247 >> ~/.ssh/known_hosts` schrieb nur Kommentarzeilen (`#`).
- SSH betrachtete den Host daher weiterhin als unbekannt → `Host key verification failed`.
- **Korrekte Verwendung** ohne `-H` (unhashed) oder mit UserKnownHostsFile-Bypass:
  ```bash
  # Option A: keys wirklich eintragen
  ssh-keyscan 192.168.188.247 2>/dev/null | grep -v "^#" >> ~/.ssh/known_hosts
  # Option B: für Scripts, die keine interaktive Bestätigung wollen
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@IP ...
  ```
- In automatisierten Dispatch-Skripten ist Option B robuster, da sie auch bei korrupten oder veralteten known_hosts-Einträgen funktioniert.

### 14.4 Proxmox-Tag-Konventionen sind cluster-weit relevant

Tags sind das primäre Discovery-Mechanismus für dynamische Infrastruktur-Tools. Einmal vergeben, müssen sie gepflegt werden:

| Tag | Bedeutung |
|-----|-----------|
| `devctl-target` | LXC-Container der von devctl.sh gesteuert wird |
| `brainhome` | Teil der BrainHome-Infrastruktur |
| `production` | Produktiv-Workload (nicht für Dev-Umgebungen) |
| `dev` | Entwicklungsumgebung |
| `infrastructure` | Infrastruktur-Dienst (Proxy, DNS, etc.) |

- Fehlende oder falsche Tags können Discovery-Skripte fehlleiten.
- `production`-Tag auf Dev-VMs (wie VM113 `brainhome-workstation`) ist irreführend → entfernen.
- Nach jedem Backup-Lock-Ende vergessene Tag-Änderungen nachholen.

### 14.5 devctl.sh Cross-Node Dispatch: Architektur

```
proxmox-ug$ devctl.sh status
  → Discovery via pvesh: CT112 liegt auf proxmox-ws
  → hostname=proxmox-ug ≠ proxmox-ws
  → exec ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
         root@192.168.188.247 "bash /home/webserver/tools/devctl.sh" status
       → hostname=proxmox-ws == proxmox-ws
       → pct exec 112 -- bash ct-runner.sh status
```

- Das Skript dispatcht sich via `exec ssh` selbst auf den richtigen Node.
- IP-Map ist nötig weil SSH-Aliases (`proxmox-ws`) nur auf proxmox-master in `~/.ssh/config` bekannt sind.
- Auf dem Ziel-Node läuft das Skript erneut, entscheidet "ich bin korrekt" und führt `pct exec` aus.

### 14.6 brainhome-root `.gitignore` verwendet Whitelist-Muster

- Das Root-Repo (`/home`) liegt auf proxmox-master und enthält viele Unterverzeichnisse (alle Dienste).
- `.gitignore` ignoriert standardmäßig **alles** (`*`) und erlaubt nur explizit aufgeführte Dateien:
  ```
  *
  !.gitignore
  !INFRASTRUCTURE.md
  !ERLERNTES-WISSEN.md
  !TODO.md
  ...
  ```
- Neue Dateien in `workstation/`, `webserver/` etc. sind **standardmäßig ignoriert**.
- Müssen explizit per `!dir/`, `dir/*`, `!dir/file` eingetragen werden.
- Pattern für Unterverzeichnisse:
  ```
  !workstation/
  workstation/*
  !workstation/tools/
  workstation/tools/*
  !workstation/tools/cluster-inventory.sh
  ```

### 14.7 cluster-inventory.sh: zentrales Cluster-Inventar-Tool

Neu erstellt in `/home/workstation/tools/cluster-inventory.sh`. Überblick aller VMs/CTs im Cluster mit Node, Status und Tags:

```bash
bash cluster-inventory.sh              # Tabelle aller 23 VMs/CTs
bash cluster-inventory.sh --json       # JSON-Output
bash cluster-inventory.sh --tag devctl-target    # Filter nach Tag
bash cluster-inventory.sh --missing    # Alle ohne Tags
```

Basiert auf `pvesh get /cluster/resources` (ohne `--type`, portabel auf allen PVE-Versionen).

---

## 15) Home Assistant – remote_homeassistant `_2`-Duplikat-Bereinigung

### 15.1 Problem: `_X`-Entities auf ha-master

- `remote_homeassistant` registriert jede weitergeleitete Entity im Entity-Registry via `async_get_or_create`
- Unique-ID-Format: `{entry.unique_id[:16]}_{entity_id}` — d. h. **pro Remote-Verbindung eine eigene UID-Gruppe**
- Existiert eine Entity-ID schon (andere UID), erzeugt HA automatisch `entity_id_2`, `entity_id_3` usw.
- **Bekannte Ursache 1**: Alte/gelöschte RHA-Verbindungen hinterlassen Einträge mit `config_entry_id=None` im Registry
- **Bekannte Ursache 2**: Remote-Instanzen haben intern eigene `_2`-Entities (aus früheren Cross-Verbindungen) und leiten diese weiter
- **Bekannte Ursache 3**: Mehrere Remotes leiten dieselbe Entity (z.B. Zigbee-Bridge-Entities)
- **Bekannte Ursache 4**: Die native HA-Instanz hat eine Entity (ESPHome, BraviaTV, etc.) und ein Remote leitet sie auch weiter
- **Bekannte Ursache 5**: Zigbee2MQTT-Geräte werden in der Z2M-UI umbenannt (`friendly_name`). HA registriert die neuen langen Entity-IDs neu — die alten Kurznamen bleiben aber als **veraltete Registry-Einträge** erhalten und werden von ha-master als Stale-Entries importiert. Fix: stop → alte Einträge manuell löschen (nach IEEE-MAC-Adresse des Geräts identifizierbar) → start (auf Remote-Instanz UND auf ha-master)
- **Bekannte Ursache 6**: Z2M-**Gruppe** und physikalisches **Gerät** mit identischem `friendly_name` → beide erzeugen denselben Entity-ID-Basis (z.B. `switch.og_kuche_deckenlicht`). Fix: Z2M-Gruppe über MQTT-API umbenennen: `POST /api/services/mqtt/publish` mit topic `zigbee2mqtt/bridge/request/group/rename` und payload `{"from": "...", "to": "..._gruppe", "homeassistant_rename": true}`. Danach Registry auf HA-Instanz + ha-master bereinigen.

### 15.2 Diagnose

```python
# True Dups zählen (auf ha-master per SSH)
import json, re
entities = json.load(open("/config/.storage/core.entity_registry"))["data"]["entities"]
all_eids = {e["entity_id"] for e in entities}
true_dups = sorted([eid for eid in all_eids if re.match(r'^(.+)_2$', eid) and re.match(r'^(.+)_2$', eid).group(1) in all_eids])
print(f"True dups: {len(true_dups)}")
```

```python
# Quelle einer _2-Entity ermitteln (uid-Prefix = erste 16 Zeichen des Remote-uuid)
uid_pfx = {"42b098d87fd14698": "ha-ug", "19c1f4ca1167432e": "ha-eg",
           "6ff613dcb3a54fde": "ha-og", "82c391027d534569": "ha-ga"}
# RHA-Config-Entry unique_ids stehen in core.config_entries unter entry.unique_id[:16]
```

### 15.3 Fix-Strategie (hierarchisch)

1. **Entity-Filter in RHA-Config setzen** (`exclude_entities`, `exclude_domains` in `core.config_entries`)
   - Filter blockiert `state_changed`-Registrierung (wirkt bei initialem Sync und Live-Updates)
   - Wirkt NUR bei `ha core stop` → Datei editieren → `ha core start` (bei laufendem HA wird Datei beim Shutdown überschrieben!)
2. **Veraltete Registry-Einträge entfernen** (bei gestopptem HA)
   - Alle `platform=remote_homeassistant, config_entry_id=None` Einträge löschen
   - `_2`-Einträge löschen, deren Base-Entity noch existiert
3. **Aktive `_2`-Einträge von nativen Integrationen reparieren**: Basis-Entity löschen (die alte RHA-Registrierung), native Integration re-registriert sich beim Start mit korrekter entity_id
4. **Remote-interne Konflikte**: müssen auf der Remote-Instanz selbst gelöst werden (Device umbenennen)

### 15.4 Kritischer Ablauf (Stop/Edit/Start)

```bash
# HA stoppen (watchdog ist deaktiviert auf ha-master!)
ssh -i /home/brain/.ssh/pihole_key root@192.168.188.142 'ha core stop'

# Dateien editieren (auf ha-master):
# /config/.storage/core.config_entries  → entity_filter-Optionen
# /config/.storage/core.entity_registry → veraltete Einträge entfernen

# HA starten
ssh -i /home/brain/.ssh/pihole_key root@192.168.188.142 'ha core start'
# Hinweis: watchdog=false → manuelles ha core start nötig!
```

### 15.5 RHA Config Entries auf ha-master (Stand 2026)

| Title | Entry-ID | IP | Domains ausgeschlossen | Entities ausgeschlossen |
|-------|----------|----|------------------------|------------------------|
| Home-UG | `01JZV9DYK7XQHB8PSQ0M0AYTMP` | .152 | 10 (inkl. automation,script) | 130 |
| Home-EG | `01KMNT410RGERBG5B5CW9EXRGJ` | .194 | 9 (inkl. automation) | 38 |
| Home-OG | `01JHGTVPMR64DX87XS6Q6P0XA5` | .143 | 8 | 30 |
| Home (GA)| `01KMNT0F2Y5Y0R5J3H802V0NNB` | .191 | 8 | 17 |

### 15.6 ha-eg Rolladen-Fix (27.03.2026)

Die 24 ha-eg-Dups waren **keine echten Device-Konflikte**, sondern **veraltete Z2M-Rename-Relikte**:
- Z2M-Geräte wurden von `balkontur` / `fenster_ne` / `fenster_se` zu langen Raum-Präfix-Namen umbenannt
- HA registrierte die neuen langen Entity-IDs neu, löschte aber die alten kurzen **nicht** aus dem Registry
- Ein übersehener 4. Rolladen-Koordinator erzeugte zusätzlich `_3`-Entities auf ha-master
- `automation.neue_automation_2` von ha-eg: `automation`-Domain zu ha-eg `exclude_domains` hinzugefügt

**Fix-Schritte (Ursache 5 – Z2M Rename):**
```bash
# 1. Remote-Instanz (ha-eg) stoppen
ssh root@192.168.188.194 'ha core stop'
# 2. Stale-Entries im Registry nach IEEE-MAC des alten Geräts identifizieren:
#    grep unique_id mit Zigbee-MAC in /config/.storage/core.entity_registry
#    Dann alle Entries mit dieser MAC-UID löschen (Python-Skript)
# 3. ha-eg starten
# 4. ha-master stoppen
# 5. Weitergeleitete Stale-Entries auf ha-master löschen:
#    uid beginnt mit {ha_eg_hash}_ + alter kurzer entity_id (z.B. 19c1f4ca1167432e_cover.balkontur)
# 6. ha-master starten
```

**Ergebnis**: 56 Stale-Entries auf ha-eg + 53 Stale-Entries auf ha-master gelöscht. True-Dups: 29 → 7 echte Konflikte + 4 Solarman-`_3`.

### 15.7 Verbleibende Dupliate (Stand 27.03.2026) — alle False Positives

Nach vollständiger Bereinigung sind **alle verbleibenden `_2`/`_3`-Entities False Positives**:

| Entity | Instanz | Warum False Positive |
|--------|---------|----------------------|
| `sensor.192_168_188_88/97_today/total_production_2/_3` | ha-ug | Solarman MPPT-Tracker: `_2` = MPPT 2, `_3` = MPPT 3 — absichtlich nummeriert |
| `input_boolean.ga_pumpe_sun_time_2` | ha-ga | Absichtlich mit `_2` benannt |

### 15.8 Code-Fundstellen

- Filter-Check: `/config/custom_components/remote_homeassistant/__init__.py` Zeile 683
- Entity-Registrierung: Zeile 731 (`async_get_or_create`)
- Unique-ID-Bildung: Zeile 725 (`f"{self._entry.unique_id[:16]}_{entity_id}"`)
- `CONF_EXCLUDE_ENTITIES`, `CONF_EXCLUDE_DOMAINS` → in `options` des Config-Entry

---

## §16 HA Energy Dashboard – Konfiguration & Fallstricke (ha-ug, 27.03.2026)

### 16.1 Speicherort

Das Energy Dashboard speichert seine Konfiguration in `/config/.storage/energy` als JSON.
Die HA REST-API bietet **keinen** `GET /api/config/energy`-Endpoint — Lesen/Schreiben
nur via SSH oder WebSocket.

### 16.2 Konfiguration ha-ug (Stand 27.03.2026)

```json
{
  "energy_sources": [
    { "type": "gas",  "stat_energy_from": "sensor.gasmeter_gaszahlerstand" },
    { "type": "solar","stat_energy_from": "sensor.192_168_188_88_total_production" },
    { "type": "solar","stat_energy_from": "sensor.192_168_188_97_total_production" },
    { "type": "grid", "stat_energy_from": "sensor.strommeter_main_value" }
  ],
  "device_consumption": [
    { "stat_consumption": "sensor.heizkessel_energy_total" }
  ]
}
```

### 16.3 Sensor-Anforderungen für Energy Dashboard

| Sensor | Pflichtfeld | Hinweis |
|--------|-------------|---------|
| `unit_of_measurement` | `kWh` (oder `m³` für Gas) | Pflicht |
| `state_class` | `total_increasing` oder `total` | Pflicht für Statistik |
| `device_class` | `energy` (oder `gas`) | Empfohlen |

**Achtung**: `sensor.strommeter_value` hatte `state_class: total` (nicht `total_increasing`)
und `sensor.solarpanel_*_daily_production` hatten **kein** `state_class` → beide ungeeignet.

### 16.4 Fallstricke

- **`strommeter_value` vs `strommeter_main_value`**: Beide Entities existieren mit identischem
  Wert (35671.0 kWh). `_main_value` hat `state_class: total_increasing` → korrekt.
  Der alte Eintrag in `.storage/energy` verwies auf `strommeter_value` (falsch).
- **`solarpanel_sud/west_daily_production`**: Diese Sensoren haben **kein** `state_class`.
  HA kann keine Langzeit-Statistik führen → Energy Dashboard zeigt keine Daten.
  Fix: Solarman-davidrapan-Sensoren `sensor.192_168_188_88/97_total_production` verwenden.
- **Solarman `unavailable`**: Wechselrichter-Sensoren zeigen `unavailable` wenn kein Sonnen-
  scheinen/Verbindungsproblem. HA speichert trotzdem Statistik-Datenpunkte sobald Werte kommen.
- **Gasmeter `unavailable`**: `sensor.gasmeter_gaszahlerstand` hat korrektes Metadata
  (`state_class: total_increasing`, `device_class: gas`) — kann bereits in der Konfiguration
  bleiben, auch wenn der Sensor momentan `unavailable` ist.

### 16.5 Edit-Prozedur

```bash
# ha-ug stoppen
ssh root@192.168.188.152 'ha core options --watchdog=false && ha core stop'
# Datei editieren
ssh root@192.168.188.152 'python3 -c "import json; ..."'
# Starten
ssh root@192.168.188.152 'ha core start'
```

---

## §17 Grafana Provisioning & Prometheus – Erkenntnisse (April 2026)

### Prometheus Metrik-Namen in HA 2026.x
HA 2026 verwendet Unit-suffixe im Metrik-Namen (nicht mehr `hass_sensor_state`):
- `homeassistant_sensor_energy_kwh{instance="ha-ug", entity="sensor.xyz"}`
- `homeassistant_sensor_power_kw{...}`
- `homeassistant_sensor_power_w{...}`
- `homeassistant_sensor_temperature_c{...}`

### Grafana Provisioning Deploy-Workflow
Grafana läuft auf VM `monitoring.brain` (192.168.188.108), SSH-Alias: `grafana`.
Volume-Mapping: `../dashboards/provisioned → /var/lib/grafana/dashboards`
Auf dem Host: `/home/brain/grafana/dashboards/provisioned/`

Deploy:
```bash
scp dashboards/provisioned/energy.json grafana:/home/brain/grafana/dashboards/provisioned/energy.json
# Dann Provisioning reloaden:
curl -X POST -u admin:PASS http://192.168.188.108:3000/api/admin/provisioning/dashboards/reload
```
Grafana's `version`-Feld in der API gibt die interne DB-Version zurück (nicht die JSON-file-version).

### prometheus.yml Reload
```bash
ssh grafana "wget -q --post-data='' -O- http://localhost:9090/-/reload"
```
Voraussetzung: `--web.enable-lifecycle` muss im Prometheus-Start gesetzt sein (ist bei BrainHome gesetzt).

### ha-eg Prometheus Bug (behoben April 2026)
IP in `prometheus.yml` war `.148` statt `.194` → `home_assistant_eg` war `down`.
Fix: `targets: ['192.168.188.194:8123']` in `/home/brain/brainhome-root/grafana/config/prometheus.yml`

---

## §18 HA USB Passthrough + Lock-Diagnose (27.03.2026)

### 18.1 `VM is locked (backup)` ist nicht immer ein laufendes Backup
- `pgrep -af vzdump` kann noch alte/irrelevante Prozesse zeigen, obwohl kein aktiver VM-Lock mehr existiert.
- Maßgeblich für VM-Konfig-Änderungen ist `qm config <vmid> | grep '^lock:'`.
- Wenn dort `none` (kein Lock) steht, ist `qm set -usb...` sofort wieder möglich.

### 18.2 Verlässliche Diagnose-Reihenfolge bei Lock-Problemen
1. `qm config <vmid> | grep '^lock:' || echo none`
2. `pvesh get /cluster/tasks --running 1` (zeigt echte laufende Cluster-Tasks)
3. Nur ergänzend: `pgrep -af vzdump` zur Kontextprüfung

Diese Reihenfolge verhindert Fehlannahmen durch verwaiste Prozessreste.

### 18.3 USB-Passthrough Pattern für HAOS-VMs
- Zigbee (Sonoff/CP210x): `qm set <vmid> -usbN host=10c4:ea60,usb3=1`
- Bluetooth (TP-Link): `qm set <vmid> -usbN host=2357:0604,usb3=1`
- Nach Setzen immer prüfen: `qm config <vmid> | grep '^usb'`

Stand 27.03.2026:
- ha-ug VM106: `usb2: host=10c4:ea60,usb3=1`
- ha-og VM103: `usb1: host=2357:0604,usb3=1`
- ha-eg VM102: `usb1: host=2357:0604,usb3=1`

### 18.4 Hängende `qm reboot`-Aufrufe können VM-Locks blockieren
- Unterbrochene oder hängende `qm reboot <vmid>`-Prozesse können Lockfiles halten (`lock-<vmid>.conf`).
- Symptom: `can't lock file ... got timeout` bei `qm reset/stop` trotz fehlendem `lock:` in `qm config`.
- Vorgehen:
  1. Reboot-Prozess prüfen: `pgrep -af '/usr/sbin/qm reboot <vmid>'`
  2. Stale Prozess beenden
  3. Status verifizieren: `qm status <vmid>`
  4. Danach regulär fortfahren

### 18.5 Betriebs-Hinweis
- Nach USB-Passthrough muss HA-Core im Gast vollständig hochfahren, bevor API/Integrationen verlässlich geprüft werden können.
- Ping-Erreichbarkeit allein reicht nicht; zusätzlich Port 8123 prüfen.

---

## §19 vzdump Backup-Modi + Keepalived / NFS-Snapshot-Falle (27.03.2026)

### 19.1 Root Cause: NFS zwingt zu suspend trotz `mode snapshot`
- Proxmox `jobs.cfg` kann `mode snapshot` konfigurieren — aber wenn der LXC-Container auf **NFS-Storage** liegt, hat vzdump keinen Snapshot-Mechanismus.
- vzdump fällt dann **automatisch auf suspend** zurück, ohne Fehlermeldung.
- Erkennung: `pct list` zeigt `Lock: backup` — bei echtem Snapshot-Backup erscheint dies nicht.
- Alle BrainHome LXC-Container lagen zum Zeitpunkt der Erkenntnis auf `shared-storage` (NFS):
  - proxmox-ug: CT100, CT110, CT116, CT130
  - proxmox-og: CT111, CT120
  - proxmox-eg: CT114, CT117
- Fix: LXC-Disks auf `local-lvm` (lvmthin) migrieren → dann greift echter Snapshot → kein Freeze.

### 19.2 suspend friert Keepalived / VRRP ein
- Wenn Caddy-Container (CT117 caddy-eg) eingefroren wird:
  - Keepalived sendet keine VRRP-Advertisements mehr
  - Backup-Instanz (caddy-og CT120) sollte nach 3s MASTER werden
  - **Tut es aber nicht zuverlässig** — LXC-Kernel-Bug: manchmal werden VRRP-Pakete noch durchgeleitet trotz Freeze
- Folge: VIP `.200` bleibt auf eingefrorenem Container → alle Verbindungen hängen → 502 Bad Gateway

### 19.3 Diagnose-Befehle
```bash
# Backup-Lock prüfen
ssh proxmox-eg "pct list"   # Lock: backup = suspend läuft gerade

# Hilfsskript im Workspace nutzen
bash /home/brain/brainhome-root/tools/bin/proxmox-backup-check.sh 117 proxmox-eg

# VIP-Inhaber prüfen
ssh proxmox-og "pct exec 120 -- ip addr show eth0 | grep '188\.200'"
ssh proxmox-eg "pct exec 117 -- ip addr show eth0 | grep '188\.200'"

# Storage-Typ aller CTs ermitteln
ssh proxmox-ug "pct list | awk 'NR>1 {print \$1}' | while read ct; do echo -n \"CT\$ct: \"; pct config \$ct | grep rootfs; done"

# vzdump-Prozess beobachten
ssh proxmox-eg "ps aux | grep vzdump | grep -v grep"
```

### 19.4 Lösung (kurzfristig — ohne StorageMigration)
- In der aktuellen Proxmox-Umgebung (PVE 9.2.10) gibt es kein `--nofreeze`-Flag.
- Stattdessen sind die praktikablen Workarounds:
  ```bash
  vzdump <ctid> --mode stop --compress zstd --storage backup-daily
  ```
  oder, wenn das Backup über das vorhandene `snapshot`-Mode laufen soll, es außerhalb der VRRP-/HA-Zeiten einzeln und gestaffelt ausführen.
- Oder: Backup-Zeitfenster staffeln — nie alle 3 Caddy-Instanzen gleichzeitig.

### 19.6 ha-master IP-Drift via DHCP (27.03.2026)
- ha-master (VM101 auf proxmox-ws) hat heute IP `.142` statt `.101` via DHCP erhalten
- Ursache: VM hat keine statische IP — DHCP hat andere Adresse vergeben (alte Lease abgelaufen?)
- Folge: ha.brain / Caddy-Route / Pi-hole DNS zeigen auf falsche IP
- Fix: Entweder DHCP-Reservation in FritzBox für MAC `02:01:04:25:6e:45` auf `.101` setzen, oder statische IP direkt in HAOS konfigurieren (Einstellungen → System → Netzwerk)

### 19.5 Lösung (langfristig — empfohlen, TICKET B4CK01)
- Alle Caddy + Pihole LXC-Disks auf `local-lvm` (lvmthin) migrieren:
  ```bash
  pct move-disk <ctid> rootfs local-lvm --delete 1
  ```
- Danach greift `mode snapshot` aus jobs.cfg → kein Freeze → Keepalived bleibt aktiv → VRRP funktioniert zuverlässig.

