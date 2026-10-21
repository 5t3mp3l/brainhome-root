# Nextcloud-Backup: NFS-Timeout am 21.10.2026

## Gesicherter Befund

Lesende Pruefung ueber die Proxmox-Cluster-API auf `proxmox-ug`.
Keine Mounts, Job-Parameter, Dienste, Paketstaende oder SSH-Hostschluessel geaendert.
Auf DT lief zum Zeitpunkt der Pruefung kein Backup-Task.

Untersuchter Task:

```text
UPID:proxmox-dt:0014A5A9:01C32920:6AD7F279:vzdump::root@pam:
```

Zeitangaben im DT-Journal sind Ortszeit:

- 01:00:09: Backup-Job startet; VM107 wird erfolgreich gesichert.
- VM121 liest im weiteren Verlauf die gesamte virtuelle Platte, 99,5 GiB.
- 01:49:42: DT-Kernel meldet mehrfach
  `nfs: server 192.168.188.42 not responding, timed out`.
- 01:53:02: Beim Schliessen der Backup-Ausgabe tritt `Input/output error` auf.
- 01:53:11: VM121-Backup endet fehlerhaft, `zstd --threads=1` liefert Exitstatus 1.
- Zahlreiche `pvestatd: got timeout`-Meldungen begleiten das Zeitfenster.

Das ist kein Nachweis eines zstd-Defekts: Die Ausgabe auf den NFS-Backup-Speicher
scheitert zeitlich zusammen mit belegten NFS-Timeouts. Die Ursache hinter der
fehlenden NAS-Antwort bleibt offen: NAS-/Datentraegerlast, Netzwerk, NFS-Dienst
oder andere Ressourcen muessen getrennt untersucht werden.

## Storage und letzte Sicherung

`backup-daily` zeigt auf NAS `.42`, Export
`/mnt/HD/HD_a2/brainhome/proxmox/backup/daily`.
Konfiguriert sind `vers=3,proto=tcp,soft,timeo=600,retrans=5`.
Bei der Folgepruefung waren rund 391,7 GB / 364,8 GiB frei; kein belegter
Speicher-voll-Fehler. Freier Platz heute beweist nicht die gesamte historische
NAS-Gesundheit. NFS-`soft` kann nach ausgeschöpften Wiederholungen I/O-Fehler
zurueckgeben; die Option ist hier ein Risikofaktor, kein alleiniger Ursachenbeweis.

Die vorherige taegliche VM121-Sicherung vom 19.10.2026 23:08 UTC wurde in der
Bestandspruefung gefunden; weder Integritaet noch Restore wurden getestet.
Der zeitgleich auf anderen Nodes auftretende LXC-NFS-Tempfehler ist inzwischen
durch lokale Tempverzeichnisse adressiert. Ob dies auch die NAS-Last ausreichend
senkt, muss ein kuenftiger Lauf zeigen, nicht die Konfigurationsaenderung allein.

## Zugriffsgrenze

Beide Server-Fingerprints wurden unabhaengig ueber ihre Konsolen bestaetigt
und gegen die vom jeweiligen Server angebotenen Schluessel verglichen:

| Host | Fingerprint | Ergebnis |
|---|---|---|
| DT `.133` | `SHA256:mrxOuIBAWJgSYq0Z8jUtSAIyi5zMmyCPa55OWXbvgAk` (ED25519) | Exakt bestaetigt; lesender SSH-Zugriff von UG ueber temporaere Known-Hosts-Datei funktioniert. |
| NAS `.42` | `SHA256:uprifeGyj+dKH8XRKzcEP+kzy1EXqhuweH/bV+e6Ly0` (RSA 4096) | Exakt bestaetigt; SSH-Hostidentitaet ist sicher, Login mit dokumentiertem Benutzer `sshd` und Workstation-Key wird dennoch abgelehnt. |

Keine permanente Known-Hosts-Aenderung. Fuer NAS wurden weder Passwort-Login
versucht noch Accounts/`authorized_keys` angepasst. Der zum Versuch angebotene
Workstation-Key hatte Fingerprint
`SHA256:GNURaebLVquSSr7CdnWdz6fNciggwaVC7JyXDeTjl0k` (ED25519); der Server
akzeptierte diesen Schluessel fuer `sshd` nicht.

## Folgepruefung am 21.10.2026, 11:49 CEST

- Von DT waren TCP-Ports 111 (rpcbind) und 2049 (NFS) erreichbar.
- 20 ICMP-Pings DT -> NAS: 0 % Verlust, Mittelwert 0,404 ms, Maximum 0,804 ms.
- `zpool status -x`: alle Pools healthy.
- `nfsstat -c` meldete 692853 Calls und 0 RPC-Retransmits; die NFSv3-Statistik
   zeigte 516515 Writes. Das ist ein kumulierter Clientstand.
- `mountstats` fuer den NFS-Transport zeigte separat 1122 Retransmits bei
   691549 RPC-Transaktionen. Zaehler koennen seit Mountbeginn/NFS-Monitoring
   laufen; ohne Baseline sind daraus weder Zeitpunkt noch alleiniger Schuldiger
   ableitbar.
- DT-Interfacezaehler waren kumulativ: physische NIC 11109 RX-Drops, Bridge
   335698 RX-Drops. Kein aktueller Linkfehler/Pingverlust; Zaehlerreset und
   Verlauf wurden nicht ermittelt. Das rechtfertigt einen getrennten Switch-/
   Bridge-/Treiberverlaufstest, aber keinen Beweis fuer die Ursache des NFS-Ausfalls.
- NAS-Web-/Konsolenzugang ist damit weiterhin noetig fuer RAID/SMART, NFS-
   Serverlogs und die tatsaechliche Plattenlatenz im Backup-Zeitfenster.

## Naechste Schritte

1. NAS- und DT-Zugaenge anhand bestehender vertrauenswuerdiger Konsole oder
   Verwaltungsoberflaeche verifizieren; SSH-Fingerprints unabhaengig abgleichen.
   Fingerprints sind nun verifiziert; NAS-Loginberechtigung ueber einen
   autorisierten Administrationsweg klaeren. Keine Passwoerter oder privaten
   Schluessel im Chat uebermitteln.
2. Danach lesend NAS-RAID/SMART, NFS-Dienst, Systemprotokolle und DT-NFS-Client-
   Statistiken sowie Netzwerkfehler untersuchen.
3. `soft` nicht blind auf `hard` umstellen: Dies kann Fehler in unbegrenzt
   wartende I/O verwandeln; ausserdem dient dasselbe NAS auch produktiven
   Gastplatten. Jede Mount-Aenderung braucht einen separaten Betriebsplan.
4. Kein erneuter grosser Backup-/Schreibtest ohne Freigabe. Nach der Diagnose
   einen begrenzten, gestaffelten VM121-Lauf ohne Pruning und danach eine
   Integritaets-/isolierte Restore-Pruefung planen.