# ✅ ABGESCHLOSSEN: proxmox-ug Analyse und Bereinigung

> Historisches Runbook vom 19.03.2026, keine aktuelle Bestandsliste. Der
> damalige Node `.254` ist heute kein Cluster-Mitglied mehr. Aktueller
> gepruefter Stand: [Physische Architektur](PHYSISCHE-ARCHITEKTUR.md).

## Status: Vollständig gelöst — 19.03.2026

- Alle 4 Nodes auf PVE 9.1.6 (Trixie), Cluster quorate, `proxmox-ug` status:
  online mit vollen Metriken.

## Ziel

`proxmox-ug` lieferte im Proxmox-API-Output nur Minimaldaten (`status: unknown`)
statt CPU/Memory/Disk wie die aktiven Nodes.

## Aktueller Befund

- `node/proxmox-ug` ist in `pvesh get /nodes` auf `proxmox` nur als
  `status: unknown` sichtbar.
- Corosync zeigt 4 Nodes, darunter `proxmox-ug` mit
  `ring0_addr: 192.168.188.248`.
- Aktiver lokaler Hostname ist `proxmox` auf `192.168.188.254`.

## Verifizierte Ursache

- `proxmox-ug` ist erreichbar (Ping + SSH erfolgreich) und liefert lokal volle
  Node-Metriken.
- In derselben Cluster-Ansicht liefern `proxmox`, `proxmox-eg`, `proxmox-og`
  volle Metriken.
- Versionsmix im Cluster:
  - `proxmox`, `proxmox-eg`, `proxmox-og`: Proxmox 8.3.2 (RRD: `pve2-*`)
  - `proxmox-ug`: Proxmox 9.1.6 (RRD: `pve-*-9.0`)
- Der unknown-Eintrag ist damit kein Reachability-Problem, sondern ein
  Telemetrie-/Kompatibilitaetsproblem durch Major-Version-Mix (8 vs 9).

## Konkrete Arbeitspakete

1. Ist-Zustand sichern

- [x] Snapshot von `/etc/pve/corosync.conf` anlegen
- [x] Ausgabe von `pvecm status` und `pvesh get /nodes` archivieren

1. Erreichbarkeit prüfen

- [x] Ping auf `192.168.188.248` testen
- [x] SSH auf `proxmox-ug` testen
- [x] Ergebnis: Node ist online und liefert lokal Metriken

1. Versionskonsistenz herstellen (Prio 1)

- [x] Entscheidung treffen: kompletter Cluster auf Proxmox 9 heben
- [x] `proxmox`, `proxmox-eg`, `proxmox-og` auf 9.x upgraded (proxmox-eg/og
      waren bereits auf 9.1.6; proxmox lokal am 19.03.2026 upgraded)
- [x] Alle Nodes: `pveversion` = 9.1.6, RRD-Schema einheitlich pve-\*-9.0
- [x] `pvesh get /cluster/resources --type node`: alle 4 Nodes status: online
      mit CPU/MEM/DISK/Uptime ✅

1. Cluster-Konsistenz nur wenn noetig (Prio 2)

- [x] Nicht noetig — Node ist online und funktional, kein delnode

1. Namenskonzept dokumentieren

- [x] `proxmox` bleibt produktiver Node auf `.254` (kein Rename)
- [x] DNS-Aliases gesetzt: `proxmox-dev.brain` → .253, `proxmox-ug.brain` → .249
- [ ] API-/Frontend-Texte auf konsistente Namen anpassen (`proxmox-dev`,
      `proxmox-eg`, `proxmox-og`)

1. Monitoring validieren

- [x] `pvesh get /cluster/resources --type node`: alle 4 Nodes status: online ✅
- [x] BrainHome Dashboard: kein unknown-Node mehr
- [ ] Alert-Regel ergänzen: unknown Node > 10 min => Warnung

## Kurzfristiger Workaround (obsolet)

- [x] Workaround nicht mehr noetig — alle Nodes auf PVE 9.1.6, vollstaendige
      Metriken verfuegbar

## Konkretes Runbook: Alle anderen auf Proxmox 9 nachziehen

### Zielbild

- `proxmox`, `proxmox-eg`, `proxmox-og` auf Proxmox VE 9 (Trixie)
- Einheitliches RRD-Schema im Cluster
- `proxmox-ug` nicht mehr als `unknown` in Sammelansichten

### Reihenfolge (risikoarm)

1. `proxmox-og` (geringste Abhaengigkeiten)
2. `proxmox-eg`
3. `proxmox` (lokaler Node zuletzt)

### Vor jedem Node-Upgrade (Pflicht)

- [x] Backups gemacht (corosync.conf, apt sources)
- [x] pvecm status quorate bestätigt
- [x] VMs/CTs migriert / gestoppt

### Repo-Umstellung pro Node

- [x] Alle Nodes: trixie Repos gesetzt
- [x] Alte Bookworm-Listen deaktiviert

### Upgrade-Kommandos pro Node

- [x] `apt full-upgrade` auf proxmox (19.03.2026) mit
      `DEBIAN_FRONTEND=noninteractive`
- [x] proxmox-eg und proxmox-og waren bereits auf 9.1.6
- [x] Reboots abgeschlossen

### Cluster-Abschlusscheck

- [x] `pvesh get /cluster/resources --type node`: alle 4 Nodes `status: online`
      ✅
- [x] proxmox-ug liefert CPU/MEM/DISK/Uptime ✅

### Locale-Fix proxmox-og

- [x] `de_DE.UTF-8` in `/etc/locale.gen` aktiviert und generiert (19.03.2026)
- [x] `/etc/default/locale`: `LANG=de_DE.UTF-8`

## Erfolgskriterien ✅ ALLE ERFÜLLT

- [x] Kein `status: unknown` Eintrag mehr fuer `proxmox-ug`.
- [x] Alle 4 Nodes liefern CPU, RAM, Disk und Uptime.
- [x] Dokumentation und DNS-Namen sind konsistent mit dem Clusterzustand.
