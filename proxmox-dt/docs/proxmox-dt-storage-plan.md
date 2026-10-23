# proxmox-dt Storage and Backup Plan

## Objective

Move Proxmox guest backups from the degraded BrainCloud NAS to a PBS datastore
on `proxmox-dt` local storage. Keep the NAS archives and NFS job definitions
until the replacement path has passed backup verification and restore tests.

## Current layout

- DT-local ZFS pool: `tank`, three-device RAIDZ1, reported `ONLINE` with no
  known data errors at last check.
- PBS: VM118 `pbs-dt`, PBS 4.2.0, 6 GiB RAM, OS disk on `local-lvm`.
- PBS datastore: `pbs-dt`, ext4 on `/dev/sdb1`, mounted at
  `/mnt/datastore/pbs-dt`; 512 GiB virtual disk on `tank-zfs`.
- Proxmox storage ID: `pbs-dt`, reachable from EG, OG, UG, and WS.
- PBS identity: `pve-backup@pbs!pve-cluster`; only `DatastoreBackup` on
  `/datastore/pbs-dt`. The secret is not stored in this repository.

The PBS destination is local to DT and independent of BrainCloud. However,
HA-OG/EG/UG guest disks still reside on the BrainCloud-backed NFS storage
`shared-storage`; a backup read can therefore still be affected by NAS I/O
failures until those source disks are migrated or the NAS is repaired.

## Backup jobs

The enabled PBS job `haos-pbs-dt` targets only VMs 102, 103, and 106. It runs
daily at 12:00 local time in snapshot mode, uses Zstandard, is limited to
4096 KiB/s, and retains the last seven snapshots per VM.

The previous `backup-daily` and `backup-monthly` jobs target BrainCloud and
include non-HA guests. Both were disabled temporarily on 2026-10-22 after
NAS/RAID and NFS errors. This also pauses automatic Proxmox backups for the
other guests in those jobs. Preserve their archives and definitions until
coverage for those guests has been decided and tested.

## Rollout status

- **PBS provisioned:** VM118 starts from its system disk; datastore is mounted
  and registered.
- **HA-OG pilot, VM103:** PVE backup completed `OK`; PBS Verify completed with
  `TASK OK`, zero errors. A restore to VM190 on DT-local ZFS completed `OK`.
  VM190 has a unique MAC, `onboot=0`, and remains stopped. Do not attach it to
  the production network without isolating its IP and identity first.
- **HA-EG seed, VM102:** PVE task completed `OK`; snapshot
  `pbs-dt:backup/vm/102/2026-10-22T19:34:09Z` is present on PBS. A separate PBS
  Verify task for this snapshot remains to be run.
- **HA-UG seed, VM106:** started after EG completed; PVE task completed `OK`
  at 2026-10-23 02:08 CEST; snapshot
  `pbs-dt:backup/vm/106/2026-10-22T21:51:46Z` is present on PBS. A separate PBS
  Verify task for this snapshot remains to be run.
- **Automatic job:** enabled for the three HA VMs; first scheduled run is
  2026-10-23 at 12:00 CEST.
- **NAS jobs:** disabled, not deleted; re-enable only after NAS health is
  established or replacement coverage exists for their remaining guests.

## Safe operating sequence

1. Seed HA-OG, HA-EG, and HA-UG serially with a conservative bandwidth limit.
2. For every VM, require a successful PVE task and a PBS Verify result with
   zero errors.
3. Keep restores isolated, stopped, and on a local DT storage target; never
   boot a production clone on the live network.
4. Review the first scheduled PBS run and retention result.
5. Inventory non-HA guests still covered by the disabled NAS jobs and add PBS
   coverage in a separate, staged change.
6. Revisit the NAS jobs only after a tested alternate backup exists for every
   included guest. Do not prune or delete BrainCloud archives during migration.
7. Plan a second independent/off-site copy. DT-local PBS protects against
   BrainCloud NAS failure but not DT host/ZFS failure.

See [PBS Backup Plan and Runbook](pbs-backup-plan.md) for the detailed live
configuration and validation steps.