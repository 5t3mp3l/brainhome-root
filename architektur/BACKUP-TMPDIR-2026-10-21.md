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
| proxmox-ug | Nach separat freigegebenem Task-Stopp ebenfalls aktiv | `/etc/vzdump.conf.before-local-tmp.QhAJyGfz` |

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

1. UG ist nach Untersuchung und freigegebenem regulaerem Task-Stopp eingerichtet;
   Ergebnisse der naechsten regulaeren Sicherung pruefen. Kein neuer UG-Test gestartet.
2. Ergebnisse der naechsten regulaeren EG-/OG-Sicherungen pruefen.
3. Isolierten Restore ohne Produktions-IP/VIP und ohne angeschlossenes
   Produktionsnetz gesondert planen und freigeben lassen.
4. Nextcloud-NAS-I/O-Fehler und fehlende Backup-Abdeckung bleiben eigene Aufgaben.

## Nachtrag: UG-Lauf untersucht und regulaer gestoppt

Um 11:20 Ortszeit lief der UG-Job seit ueber zehn Stunden. Beim Backup von
CT116 wartete ein rsync-Empfaenger zeitweise im Zustand `D` auf NFS-RPCs.
Der Kernelstack zeigte `nfs3_proc_setattr`, `nfs3_proc_create` und
`rpc_wait_bit_killable`; gleichzeitig erschienen weiterhin neue
`chown ... Operation not permitted`-Fehler im NFS-Tempverzeichnis. Damit war
der Lauf fehlerhaft und von langsamen/blockierenden NFS-Metadatenzugriffen
betroffen, nicht nachweislich vollstaendig ohne Fortschritt eingefroren.
Die genaue NAS-seitige Ursache wurde nicht untersucht.

Nach ausdruecklicher Freigabe wurde ausschliesslich dieser Task ueber den
regulaeren Proxmox-Endpunkt gestoppt:

```text
UPID:proxmox-ug:001F27F9:01C26FC3:6AD7F278:vzdump::root@pam:
```

Ergebnis: `status=stopped`, `exitstatus=unexpected status`. Der Prozessbaum
war beendet; die kurzzeitig veraltete Aktivliste war bei erneuter Pruefung
leer. CT116 blieb running, die Backup-Sperre wurde automatisch entfernt,
`systemctl --failed` meldete keine fehlgeschlagenen Units. Das ist keine
vollstaendige Pruefung des Webserver-Endpunkts und kein erfolgreicher Backup-Abschluss.
Kein `kill -9`, kein Neustart und kein manuelles `pct unlock` eingesetzt.

Anschliessend lokales tmpdir auf UG eingerichtet und direkt verifiziert:
ext4, `root:root 0711`, rund 45,8 GiB frei vor Einrichtung. CT116 hatte rund
3,1 GiB belegten Rootspeicher. Das ist fuer diesen Gast ausreichend Reserve,
aber keine Kapazitaetsgarantie fuer beliebige parallele oder kuenftige Sicherungen.
Keine alten Archive, fehlgeschlagenen Tempdateien oder Retention-Einstellungen
geaendert und kein weiteres Backup gestartet.

Zusaetzlicher Befund: CT116 bindet `/home/webserver` als Host-Bind-Mount ein.
Dieser Inhalt ist im untersuchten Backup explizit ausgeschlossen und braucht
einen getrennten Sicherungs-/Restore-Nachweis; das Rootvolume allein deckt ihn
nicht ab.