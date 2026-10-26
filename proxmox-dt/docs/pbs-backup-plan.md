# Proxmox Backup Server Plan and Runbook

Status: 2026-10-26. Live values in this document are observations from the
deployment date, not immutable configuration defaults. No passwords or token
secrets belong here.

## Goal and scope

Use Proxmox Backup Server (PBS) on `proxmox-dt` to move Proxmox VM/CT backups
off the degraded BrainCloud NAS. PBS's datastore is on the DT-local ZFS pool,
not on BrainCloud. This removes the NAS from the backup destination path, but
does not remove the NAS dependency of guests whose source disks still live on
`shared-storage`.

The rollout is staged: retain existing archives and job definitions, seed the
PBS-covered HA VMs, verify the archives, and test restore before deciding
whether to restore the NAS schedules or migrate their remaining guests to PBS.

As of 2026-10-26, five Home Assistant VMs (101, 102, 103, 106, 115) are
registered with Proxmox HA. The current PBS job covers only 102, 103, and 106;
Proxmox HA registration does not provide backup coverage for 101 or 115.

## PBS deployment

| Item | Current value |
| --- | --- |
| Proxmox node / VM | `proxmox-dt` / VM 118 `pbs-dt` |
| PBS version | 4.2.0 |
| PBS address | `192.168.188.37` (currently obtained by DHCP; reserve this address before relying on long-term schedules) |
| VM resources | 4 vCPU, 6 GiB RAM, ballooning disabled; `onboot=1`, startup order 99 |
| OS disk | 32 GiB on DT `local-lvm` |
| Datastore disk | 1 TiB virtual disk on DT `tank-zfs`, grown online from 512 GiB on 2026-10-26; excluded from backup of PBS VM itself |
| Filesystem / mount | ext4 on PBS `/dev/sdb1`, mounted at `/mnt/datastore/pbs-dt`; partition and filesystem grown online |
| PBS datastore | `pbs-dt`; about 1 TiB total, about 931 GiB free after expansion |
| PBS TLS fingerprint | `95:29:F0:21:CE:82:E2:BC:63:8A:16:D8:C8:02:88:7A:95:43:62:96:E5:70:8D:7B:CF:1B:6A:15:77:89:9E:38` |
| PBS auth identity | `pve-backup@pbs!pve-cluster`; user and token have `DatastorePowerUser` only on `/datastore/pbs-dt` for backup plus prune; no `Datastore.Modify` |
| PVE storage ID | `pbs-dt`; PBS API verified reachable from EG, OG, UG and WS nodes |
| Guest agent | `qemu-guest-agent` 1:10.0.13+ds-0+deb13u1 active; PVE agent API verified; SysV boot links present for runlevels 2-5; no VM restart performed |

The `tank` ZFS pool was `ONLINE` with no known data errors when checked. It was
a three-device RAIDZ1. PBS is a VM on the same DT host, so this datastore is
separate from BrainCloud but is not a second physical host or an off-site
copy. A future independent/off-site copy and restore plan are still required.

## Backup destinations and jobs

### PBS Home Assistant job

| Setting | Value |
| --- | --- |
| Job ID | `haos-pbs-dt` |
| Schedule | Daily, `12:00` local time |
| Guests | VM 101 `haos`, VM 102 `haos-eg`, VM 103 `haos-og`, VM 106 `haos-ug`, VM 115 `haos-ga` |
| Destination | `pbs-dt` |
| Mode / compression | Snapshot / Zstandard |
| Bandwidth limit | 4096 KiB/s (4 MiB/s) |
| Retention | Keep last 7; pruning enabled |

The job was enabled on 2026-10-22 and expanded on 2026-10-26 to include all five
PVE-HA-managed Home Assistant VMs. Initial PBS seeds and Verify results are
complete for 102, 103, and 106. VM101 and VM115 still need their first PBS
snapshots; all five source disks remain on the NAS-backed NFS `shared-storage`.
The first scheduled run on 2026-10-23 created snapshots for all three VMs, but
PVE reported `job errors` because retention pruning was denied: the token lacked
`Datastore.Prune`. Since the token uses privilege separation, adding the role
only to the token was insufficient; the matching base-user ACL was also added.
Both user and token now have `DatastorePowerUser` only on `/datastore/pbs-dt`.
A single-VM UG test then completed with PVE task `OK`, `keep-last=7`, and
`pruned 0 backup(s)`. PVE task:
`UPID:proxmox-ug:0036CC9A:030813FB:6ADB341D:vzdump:106:root@pam:`. Snapshot:
`pbs-dt:backup/vm/106/2026-10-23T10:17:01Z`.

### Other active VM/CT job

| Setting | Value |
| --- | --- |
| Job ID | `active-pve-pbs-dt` |
| Schedule | Daily, `01:00` local time |
| Guests | 100, 107, 108, 109, 110, 111, 113, 114, 117, 118, 119, 120, 121, 130, 219 |
| Destination | `pbs-dt` |
| Mode / compression | Snapshot / Zstandard |
| Bandwidth limit | 2048 KiB/s (2 MiB/s) |
| Retention | Keep last 7; pruning enabled |
| Notes | `{{guestname}} - PBS DT` |

The job covers the other 14 active guests plus PBS VM118. VM118's datastore
disk `scsi1` is marked `backup=0`, so only its 32-GiB OS disk is in the archive;
this self-hosted PBS copy is not an independent PBS recovery path.

A test backup for VM108 completed PVE task `OK` on 2026-10-26 using the same
2-MiB/s limit and `keep-last=7`. Snapshot
`pbs-dt:backup/vm/108/2026-10-26T22:06:30Z` has notes `openwrt-eg - PBS DT`;
its PBS Verify state is still `None`.

Proxmox CT130 has host bind mount `mp0=/home/pxe-boot` (about 1.6 GiB). Standard
LXC `vzdump` backs up CT130's rootfs but not this host bind mount; a separate
PBS host-level backup for that path is still required for full CT130 data
coverage.

### BrainCloud/NFS jobs

The pre-existing cluster jobs remain configured but were temporarily disabled
on 2026-10-22 after the BrainCloud RAID member failure and NFS/I/O errors:

| Job ID | Schedule | Destination | State |
| --- | --- | --- | --- |
| `backup-14cfefbd-8b8f` | Monday-Saturday 01:00 | `backup-daily` on BrainCloud | Disabled, retained |
| `backup-4334e708-5eaa` | Sunday 03:00 (weekly despite the storage name) | `backup-monthly` on BrainCloud | Disabled, retained |

These jobs include guests other than HA. Their automatic backups are therefore
also paused. Do not re-enable them until the NAS/NFS path is healthy or a PBS
job covers their guests. Do not remove old NAS archives during recovery.

## Verified pilot

### HA-OG VM 103

- Manual PBS snapshot on 2026-10-22, limited to 4 MiB/s; completed successfully
  in about 2 h 19 min.
- PBS snapshot: `pbs-dt:backup/vm/103/2026-10-22T11:10:46Z`.
- PBS Verify completed with `TASK OK`, 100%, zero errors.
- The PBS UI reported about 1.49 GB of datastore usage for the pilot archive;
  PVE lists the virtual archive size as about 32 GiB. These values describe
  different quantities.
- A restore was performed to VM 190 `haos-og-pbs-restore-test` on local
  `tank-zfs`. Restore task completed `OK`; unique MAC assigned; `onboot=0` and
  VM remains stopped.
- Do not boot VM 190 on the production network: the restored HA configuration
  may retain the production IP and entity state. Delete the test VM only after
  review; it is disposable, but cleanup was intentionally not automatic.

### HA-EG VM 102 and HA-UG VM 106

Both initial seeds completed sequentially, with no overlapping `vzdump` task.
The PVE tasks ended `OK`, and both snapshots were present in datastore
`pbs-dt` at the follow-up check:

| VM | PVE task | Snapshot | Result |
| --- | --- | --- | --- |
| 102 `haos-eg` | `UPID:proxmox-eg:003D223E:02BBD837:6ADA6531:vzdump:102:root@pam:` | `pbs-dt:backup/vm/102/2026-10-22T19:34:09Z` | PVE task `OK`; PBS Verify `TASK OK`, 100%, zero errors |
| 106 `haos-ug` | `UPID:proxmox-ug:00317C38:02C3D96A:6ADA8572:vzdump:106:root@pam:` | `pbs-dt:backup/vm/106/2026-10-22T21:51:46Z` | PVE task `OK` at 2026-10-23 02:08 CEST; PBS Verify `TASK OK`, 100%, zero errors |

The UG task log also reported successful server-side backup validation before
the separate PBS Verify task completed.

## Operator checks

Before a backup:

1. Confirm PBS storage `pbs-dt` is active with `pvesm status --storage pbs-dt`.
2. Confirm the source node's `shared-storage` is active and inspect recent
   kernel logs for NFS timeouts or blocked I/O.
3. Confirm no other `vzdump` task is active. Keep initial HA seeds serial.
4. Start manual seeds with snapshot mode, Zstandard compression, `--remove 0`
   and a conservative bandwidth cap; do not prune during pilot tests.

After each backup:

1. Confirm the PVE task ends `OK` and the expected `vm/<VMID>` snapshot appears
   in the PBS datastore.
2. Run PBS Verify and require `TASK OK` / zero errors.
3. For restore validation, restore to a free VMID on local ZFS, keep it
   stopped, and do not connect it to the production network until its IP,
   identity and network are isolated.

## Remaining work and safety gates

- [ ] Confirm first PBS baselines for VM101 and VM115 and the first
      `active-pve-pbs-dt` run; verify both jobs and seven-snapshot retention.
- [ ] Add a host-level PBS backup for CT130's `/home/pxe-boot` bind mount.
- [ ] Reserve PBS address `192.168.188.37` in DHCP/DNS and verify PVE TLS
      fingerprint after any certificate replacement.
- [ ] Plan a second independent/off-site copy. DT-local PBS protects against
      the NAS failure domain, but not a failure of `proxmox-dt` or its ZFS pool.
- [ ] Only after a tested restore and healthy NAS review, decide whether to
      re-enable the two NFS jobs. Never prune the NAS archives as part of this
      migration without a separate retention review.

Token secrets, PBS root credentials and recovery keys must be kept in the
approved secret store; record only token IDs and ACL scope here.