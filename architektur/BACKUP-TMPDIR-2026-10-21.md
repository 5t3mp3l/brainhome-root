# Lokales Backup-Tempverzeichnis: Umsetzung 21.10.2026

## Umfang und Freigabe

Freigegeben: EG/OG/UG nach Kapazitaetspruefung konfigurieren, genau einen
kleinen Container testen. Nach festgestelltem aktivem UG-Backup wurde separat
freigegeben, CT117 parallel mit Bandbreitenlimit zu sichern; UG bleibt unveraendert.
Keine Job-Auswahl, Retention, NFS-Rechte oder Paketstaende geaendert.

## Konfiguration

| Node | Ergebnis | Rueckrollkopie |
|---|---|---|
| proxmox-eg | `tmpdir: /var/tmp/brainhome-vzdump` aktiv | `/etc/vzdump.conf.before-local-tmp.4JC3GksX` |
| proxmox-og | `tmpdir: /var/tmp/brainhome-vzdump` aktiv | `/etc/vzdump.conf.before-local-tmp.VdPhoLsI` |
| proxmox-ug | Zurueckgestellt: Backup-Task weiterhin aktiv | Keine Aenderung |

EG und OG: lokales ext4, jeweils mehr als 70 GiB frei vor Einrichtung.
Temp-Elternverzeichnis `root:root`, Modus `0711`: gemappte Benutzer
unprivilegierter Container koennen bekannte Unterverzeichnisse erreichen,
aber den Elterninhalt nicht auflisten. Unterverzeichnisse verwaltet Proxmox.

Das versionierte [Einrichtungsskript](configure-backup-tmpdir.sh) prueft
Node-Namen, aktive lokale vzdump-Tasks, lokales Dateisystem und mindestens
20 GiB freien Platz. Diese Untergrenze ersetzt keine gastbezogene
Kapazitaetsplanung. Bestehende abweichende tmpdir-Konfigurationen werden
abgelehnt; vor Aenderung wird die Originaldatei gesichert. Kein Scheduler.

Rueckrollen nur ohne laufende Sicherung: node-spezifische Originaldatei mit
`cp -p` nach `/etc/vzdump.conf` zurueckkopieren. Das leere Tempverzeichnis kann
bestehen bleiben; keine pauschale rekursive Loeschung von Backup-Daten.

## Test CT117 auf EG

CT117 `caddy-eg`: etwa 1,1 GiB belegt, 4-GiB-Rootvolume auf NFS,
unprivilegiert. Caddy und Keepalived aktiv; VIP `.200` lag vor und nach dem
Test nicht auf EG. Test mit `snapshot` angefordert, Proxmox fiel wegen
fehlender Volume-Snapshot-Unterstuetzung erwartungsgemaess auf `suspend` zurueck.

```bash
vzdump 117 --storage backup-daily --mode snapshot --compress zstd \
  --bwlimit 10240 --lockwait 0 --remove 0 --prune-backups keep-all=1
```

Der erste Versuch 11:11:08 bis 11:13:14 Ortszeit synchronisierte lokal ohne
den alten NFS-chown-Fehler. Er scheiterte beim Archivieren, weil das zunaechst
mit `0700` angelegte Temp-Elternverzeichnis fuer den LXC-Usernamespace nicht
durchquerbar war. Gast nach einer Sekunde fortgesetzt, Dienste danach aktiv.
Elternrechte auf `0711` korrigiert, Einrichtungsskript entsprechend angepasst.

Der identische Wiederholungstest **11:13:37 bis 11:17:12 Ortszeit** war erfolgreich:

- Dauer 3 Minuten 35 Sekunden, Gastpause weniger als eine Sekunde.
- Archiv `backup-daily:backup/vzdump-lxc-117-2026_10_21-11_13_37.tar.zst`.
- Dateigroesse 327242677 Bytes, etwa 312 MiB.
- Vollstaendige `zstd -t`-Pruefung erfolgreich; unkomprimiert 1094410240 Bytes.
- CT117 running, Caddy und Keepalived active; keine VIP-Uebernahme auf EG.
- Tempverzeichnis danach nur 4 KiB, keine aktiven EG-vzdump-Tasks.
- Kein Pruning, keine alten Sicherungen oder fehlgeschlagenen Artefakte manuell geloescht.

Das ist ein erfolgreicher Backup- und Kompressionsintegritaetstest, **kein
Restore-Test**. OG ist eingerichtet, wurde aber nicht durch ein weiteres
Backup getestet, um die Freigabe fuer genau einen Testgast einzuhalten.

## Offen

1. Aktiven UG-Lauf separat untersuchen; nicht ungeprueft abbrechen. UG-tmpdir
   erst nach dessen Ende, erneuter Kapazitaetspruefung und ohne konkurrierenden
   Task konfigurieren.
2. Ergebnisse der naechsten regulaeren EG-/OG-Sicherungen pruefen.
3. Isolierten Restore ohne Produktions-IP/VIP und ohne angeschlossenes
   Produktionsnetz gesondert planen und freigeben lassen.
4. Nextcloud-NAS-I/O-Fehler und fehlende Backup-Abdeckung bleiben eigene Aufgaben.