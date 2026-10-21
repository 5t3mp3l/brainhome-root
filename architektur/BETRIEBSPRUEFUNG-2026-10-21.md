# Betriebspruefung 21.10.2026

Nextcloud-Nachtrag: DT-Kernel meldet im Fehlerzeitfenster belegte NAS-NFS-
Timeouts; anschliessend scheitert die Backup-Ausgabe mit I/O-Fehler. NAS-seitige
Ursache und weitere Zugangsvoraussetzungen:
[Nextcloud-NFS-Diagnose](NEXTCLOUD-BACKUP-NFS-2026-10-21.md).

Nachtrag: EG/OG/UG haben inzwischen ein lokales Backup-Tempverzeichnis; CT117
wurde erfolgreich mit Bandbreitenlimit gesichert und das Archiv auf
Kompressionsintegritaet geprueft. Der fehlerhafte UG-Lauf wurde nach separater
Freigabe regulaer gestoppt, CT116 blieb laufend und wurde automatisch entsperrt.
Details und Rueckrollpfade: [Umsetzungsprotokoll](BACKUP-TMPDIR-2026-10-21.md).
Die folgenden Befunde beschreiben die vorherige lesende Untersuchung.

Lesende Untersuchung nach der Architektur-Versionierung. Keine Backup-Jobs,
Paketstaende, Dienste, Mounts oder laufenden Tasks geaendert.

## Erledigt

- Architekturdateien gezielt im Root-Repository freigegeben; Caches und
  Excel-Backups bleiben ignoriert.
- Architekturstand mit Commit `3d88f47` auf `origin/main` gesichert.
- Inventory-Manager: lokal `pvesh` weiterverwenden; ohne lokales `pvesh`
  automatisch SSH nach `proxmox-ug`.
- `BRAINHOME_PROXMOX_SSH` erlaubt ein explizites Ziel, auch bei lokal
  installiertem `pvesh`.
- SSH verwendet BatchMode und strenge bekannte Hostschluessel; remote ist
  ausschliesslich `pvesh get` erlaubt.
- Zentralen lokalen Inventar-Export regeneriert: fuenf Nodes, 25 Gaeste, zehn
  Module, keine Abfragewarnungen.
- Veraltete Overrides fuer EG-HA, Workstation, Mail, Vaultwarden und fehlende
  Gast-/Node-Metadaten berichtigt und versionierbar gemacht.
- Elf Tests pruefen Architektur, Transport, Fehlerfaelle und Adresskonsistenz
  der Overrides mit Gast-/Node-Manifesten.

## Backup-Befunde

Quelle: Proxmox GET API, Task-Historie `vzdump`, konkrete Task-Logs und
Storage-Content von `backup-daily` / `backup-monthly` ueber `proxmox-ug`. Datum
der Sicherung ist API-`ctime`, keine Integritaets- oder Restore-Pruefung.

| Bereich | Befund                                                                                                                                                                                                             |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| NAS     | Etwa 392 GB / 365 GiB frei; rund 89 % belegt. Daily und monthly nutzen denselben NAS-Speicher.                                                                                                                     |
| EG      | Juengster Lauf 21.10. lokal: VM108 erfolgreich; CT114 und CT117 `rsync` exit 23.                                                                                                                                   |
| OG      | Juengster Lauf 21.10. lokal: VM109 erfolgreich; CT111 und CT120 `rsync` exit 23.                                                                                                                                   |
| UG      | Letzter untersuchter abgeschlossener Fehlerlauf: CT100/110/116 `rsync` exit 23; VM119 erfolgreich. Log wegen ueber 100000 Zeilen nur teilweise gelesen. Ein neuerer Backup-Task ist noch aktiv, nicht abgebrochen. |
| WS      | Juengste fuenf aufgelistete Backup-Tasks jeweils `OK`. Kein Beweis fuer Restore-Faehigkeit.                                                                                                                        |
| DT      | Juengster Lauf: VM107 erfolgreich; VM121 nach Datenuebertragung mit `zstd: Input/output error` beim Schreiben fehlgeschlagen.                                                                                      |

Bei den untersuchten LXC-Fehlern liegt das temporaere Verzeichnis auf NFS.
Proxmox warnt explizit davor und empfiehlt lokales `tmpdir` in
`/etc/vzdump.conf`. Die Logs enthalten `chown ... Operation not permitted` im
NFS-Tempverzeichnis. Nicht pauschal NFS-Berechtigungen aufweiten oder
`no_root_squash` einschalten.

### Juengste vorhandene taegliche Sicherungen

| Gaeste               | Juengster beobachteter Stand                                                 |
| -------------------- | ---------------------------------------------------------------------------- |
| HAOS 101/102/103/106 | 28.03.2026 UTC                                                               |
| HAOS 115             | 27.03.2026 UTC                                                               |
| 104                  | 26.03.2026 UTC; alte VMID allein belegt kein Backup des heutigen Vaultwarden |
| 105                  | 22.01.2026 UTC; alte VMID allein belegt kein Backup des heutigen Mailservers |
| 100 / 114            | 21.03.2026 UTC                                                               |
| 111                  | 27.03.2026 UTC                                                               |
| 110 / 117 / 120      | 09.08.2026 UTC                                                               |
| 130                  | 10.08.2026 UTC                                                               |
| 116                  | 17.10.2026 UTC                                                               |
| 121                  | 19.10.2026 23:08 UTC; Lauf vom folgenden Tag fehlgeschlagen                  |
| 107/108/109/112      | 20.10.2026 23:00 UTC                                                         |
| 113                  | 21.10.2026 00:57 UTC                                                         |
| 119/219              | 20.10.2026 UTC                                                               |
| 180/220              | Keine Eintraege im abgefragten daily/monthly-Bestand                         |

Die aktivierten Jobs lassen weiterhin 101/102/103/104/105/106/115/180/220 aus.
Alte Archive und vorhandene Dateinamen schliessen die aktuelle Sicherungsluecke
nicht. Andere Sicherungssysteme und applikationseigene Exporte nicht geprueft.

## RAM und Wartung

- WS: rund 4,1 GiB Swap belegt, etwa 4,5 GiB RAM verfuegbar. In zwei kurzen
  `vmstat`-Intervallen kein Swap-in/out; Memory-PSI avg10/60/300 jeweils null.
  Belegter Swap allein ist damit kein Nachweis akuten Thrashings.
- VM113 hat 23068 MiB zugewiesen, HA-Master rund 10,7 GiB; zusammen
  ueberschreiten diese Gast-Zuweisungen bereits den nutzbaren WS-RAM vor
  Host-Overhead. VM220 ist gestoppt, aber ebenfalls mit 23068 MiB konfiguriert.
  Vor gemeinsamem Start ein Kapazitaetsbudget festlegen; keine automatische
  RAM-Aenderung.
- DT: etwa 82 % RAM benutzt in der Momentaufnahme; ZFS-ARC/Cache nicht isoliert
  untersucht. Daher keine Auslastungszahl mit garantiertem RAM-Mangel
  gleichsetzen.
- DT laeuft mit PVE 9.1.1. Der vorhandene, nicht aktualisierte APT-Cache listet
  256 Pakete, darunter pve-manager 9.2.21. Cache kann veraltet sein; nicht blind
  auf exakt 9.2.10 angleichen oder ohne Wartungsplan aktualisieren.

## Naechste Entscheidungen

1. Laufenden UG-Backup-Task auslaufen lassen und Zustand vor Aenderungen erneut
   pruefen.
2. Lokale Tempkapazitaet und bestehende `vzdump.conf` pro EG/OG/UG pruefen;
   danach mit Zustimmung lokales `tmpdir` konfigurieren und genau einen
   unkritischen LXC-Backup-/Restore-Test planen. UG hatte rund 46 GiB lokal
   frei; benoetigter Platz ist vorab anhand des konkreten Containers zu
   berechnen.
3. Nextcloud-Ziel-I/O/NFS/NAS-Fehler untersuchen, keine pauschale
   zstd-Aenderung.
4. Erst dann produktive Backup-Auswahl, Retention und NAS-Kapazitaet abstimmen;
   keine alten Sicherungen oder Tempverzeichnisse ungeprueft loeschen.
5. DT-Upgrade erst nach brauchbarer Sicherung und vereinbartem Wartungsfenster.
