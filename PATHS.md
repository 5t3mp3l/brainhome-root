# BrainHome Path Library

## Goal

The workspace may move without changing production deployment or runtime paths.
All scripts must resolve their repository location from their own location and
must not infer a production path from the workspace location.

## Path Domains

| Domain | Example | Migration behavior |
| --- | --- | --- |
| Workspace | `${BRAINHOME_ROOT}/caddy` | May move |
| Deployment | `/home/caddy` or `/home/brain/grafana` | Changes only through a service deployment |
| Runtime | `/var/lib/caddy`, `/opt/vaultwarden` | Never moved by a workspace migration |

## Manifests

`paths.toml` at the workspace root defines the schema and logical module map.
Every module that owns deployment or runtime paths has its own `paths.toml`.
Nested manifests exist only for independently deployed services, such as the
Vaultwarden and Stalwart VMs under `proxmox-dt/vms`. Do not add copies to passive
folders such as `docs`, `logs`, `data`, or `config`.

The first migrated application and infrastructure modules are:

- `architektur`
- `proxmox-dt`
- `proxmox-dt/vms/vaultwarden`
- `proxmox-dt/vms/stalwart-mail`
- `caddy`
- `grafana`
- `keycloak`
- `nextcloud`
- `workstation`
- `autarkie`
- `brainhome-platform`
- `pxe-boot`
- `appstore-system`
- `openwrt`
- `openwrt-repeater-setup`
- `AI-on-the-edge` with `gasmeter` and `strommeter`
- independent `webserver` checkout at `../webserver`

The Proxmox node inventory workspaces use the same base layout as
`proxmox-dt`:

- `proxmox-eg`
- `proxmox-og`
- `proxmox-ug`
- `proxmox-ws`

Each node has `config`, `data`, `docs`, `logs`, `scripts`, `tools`, `vms`, and
`ct` directories. Every live VM or container has a nested `paths.toml` with
its placement metadata and a `source_module` reference where a canonical
service source exists. The primary node object owns the canonical `source/`
directory; replica objects point to that source through `source_module`.

Every object with a `source_module` also has a complete managed copy under its
`source/` directory. Full canonical moves retain the original module contents,
including hidden files and Git history; replica synchronization excludes virtual
environments, dependency directories, builds, logs, and runtime caches. Check
mirror drift with:

```bash
brainhome-proxmox-node-mirrors --check
```

Run `brainhome-proxmox-node-mirrors --apply` only when the node copies should
be refreshed; it uses `rsync --delete` strictly inside each object `source/`
directory.

The root manifest currently contains 20 internal entries: these 16 application
and infrastructure modules plus the four Proxmox node inventory workspaces.

The Caddy module already uses the resolver in its local `devctl` and
CA-distribution script. Its remote Caddy data and PKI paths remain declared as
runtime paths in `caddy/paths.toml`.

Grafana and Keycloak use the resolver in their local `devctl` entrypoints. Their
older installation runbooks still reference target-host deployment paths and
remain migration candidates until those deployments receive their own rollout.

Home Assistant and Pi-hole follow the same rule for their local `devctl`
entrypoints. Home Assistant's add-on synchronization log path is derived from
the workspace root; its `/config` target and Pi-hole's `/etc/pihole` paths are
runtime paths and remain stable.
`pihole devctl sync` uses the workstation-safe Python synchronizer; the legacy
shell synchronizer is retained only for a direct run on `proxmox-og` against
CT111.

Autarkie's Solarman importer derives its configuration and local data paths
from its module directory. The NAS mount `/mnt/nas-braincloud` remains an
external runtime path.

Grafana's VM provisioner derives its cloud-init source from its own repository
location. Its `/var/lib/vz/snippets` destination remains a Proxmox runtime path.
Its Home Assistant token helper similarly keeps local repository sources separate
from the monitoring VM deployment root `/home/brain/grafana`.

Keycloak's installer resolves the Caddy root certificate through the relative
module relationship `../caddy/config/caddy-root-ca.crt`; the certificate target
on VM 107 remains `/usr/local/share/ca-certificates/caddy-root-ca.crt`.

Vaultwarden and Stalwart provisioning scripts resolve their cloud-init sources
relative to the individual service module. `CLOUD_INIT_SOURCE` remains an
optional explicit override for controlled recovery or alternate source paths.

Nextcloud's VS Code tasks use `${workspaceFolder}` for local deploy commands.
Their remote log command uses the declared VM deployment root
`/home/brain/nextcloud` and is not coupled to the workspace checkout path.

The main workspace's Home Assistant pull/push tasks use named workspace-folder
variables for the HA repository and the versioned `haos-configs` SSH key. The
tasks target HA EG at `192.168.188.194`.

`HomeAssistant/brainhome.env` derives its local repository and `haos-configs`
paths from the environment file itself and uses the same HA EG address.
The compatibility copy under `haos-configs/scripts/brainhome.env` uses the same
values relative to its own submodule location.

Use `paths.local.toml` for user- or host-specific values. It is intentionally
ignored by Git. Start from `paths.local.example.toml`.

## Shell Resolver

Shell tooling sources `tools/lib/paths.sh`:

```bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/paths.sh"
module_dir="$(bh_module_dir caddy)"
```

`BRAINHOME_ROOT` can override the discovered workspace root for a staged
migration or a test checkout. Scripts must use `bh_path` or `bh_module_dir` for
repository files. Deployment and runtime values stay explicit in manifests.

Python tooling uses the equivalent `tools/lib/paths.py` through
`resolve_tools_root()` and `resolve_workspace_root()`. Module discovery, the
inventory manager and task generators therefore derive their paths from the
checked-out tooling rather than `/home/tools`.

All primary `tools/bin/brainhome-*` wrappers derive `TOOLS_ROOT` from their own
location. A relocated checkout therefore needs no fixed `/home/.../tools`
default for these commands. The `tools/bin/devctl` convenience link is relative
to `brainhome-devctl`, never an absolute `/home/tools/...` symlink.

## Migration Preflight

Run this before renaming or moving any workspace directory:

```bash
brainhome path-preflight
brainhome path-preflight --strict
brainhome path-preflight --include-docs
brainhome path-preflight --summary
brainhome path-preflight --all-modules
```

The preflight is read-only. It reports three classes of references:

- `ROOT_BOUND`: references to the current workspace root that must move with it.
- `LEGACY_WORKSPACE_OR_REMOTE`: `/home/<module>` paths requiring classification
  as an old workspace path or a valid target-host deployment path.
- `WORKSPACE_ESCAPE`: relative workspace-folder entries that point outside the
  workspace root.

Verified internal relationships belong in
`tools/config/path-preflight-allowlist.txt`, one source file per line. Path
manifests are declarative input and are excluded from preflight findings. Do not
allowlist an unresolved remote deployment or runtime path.

`--strict` intentionally returns exit status `1` while candidates remain. A
directory move is allowed only after every candidate has an owner and a tested
replacement or compatibility symlink.

`--summary` prints only the counts for `ROOT_BOUND`,
`LEGACY_WORKSPACE_OR_REMOTE`, and `WORKSPACE_ESCAPE`, so migration work can be
prioritized without printing every individual finding.

`--all-modules` runs a migration matrix over the root workspace, every internal
module declared in `paths.toml`, and every manifest-declared external checkout.
It passes when the root has only its intentional external boundary and all
individual modules are candidate-free.
The normal matrix mode returns `0` for that expected state; adding `--strict`
returns `1` whenever any candidate exists, including the intentional root
external boundary.

For a non-destructive relocation rehearsal, copy the root manifest, module
manifests, and the preflight allowlist into a temporary staged root, place the
declared external checkout at the corresponding sibling path, and run:

```bash
brainhome path-preflight --all-modules --root /tmp/brainhome-relocation/root
```

The staged root may report zero root candidates when editor workspace metadata
is not copied; this is valid as long as every staged module and external
checkout remains candidate-free.

Markdown is excluded from the default strict gate because documentation does not
affect runtime behavior. Use `--include-docs` to produce its separate migration
cleanup list before completing a move.

Generated module and infrastructure inventory caches are also excluded from the
strict gate. They are regenerated by the path-aware discovery and inventory
tools after a workspace move; source scripts and installed automation remain in
scope.

The local override template is also excluded because it intentionally documents
an example former workspace root. It is not loaded unless copied to the ignored
`paths.local.toml` file.

Module manifests are declarative and terminal auto-approval matchers do not
execute deployment commands, so both are excluded from the default strict gate.
Review those matchers separately before any major editor-policy change.

Shell examples in module configuration use paths relative to their module root.
Runtime destinations, such as `/etc/keepalived/keepalived.conf`, remain explicit.

The main VS Code workspace starts integrated terminals through the named
BrainHome root folder variable. Its external `../webserver` folder remains an
explicit workspace escape. It is an independent Git checkout with its own
`.brainhome.yml` and must be migrated independently; its classification is
stored in the root `paths.toml` manifest.

Manifest-declared external checkouts are included in `brainhome discover` when
their Git checkout and `.brainhome.yml` are present. This keeps `webserver`
available to `brainhome devctl` while preserving its separate migration boundary.

The Gasmeter and Strommeter workspace files reference each other through
`../strommeter` and `../gasmeter`. These are declared sibling relationships
inside the same AI-on-the-edge parent, not external workspace dependencies. Move
the parent and both submodules together; do not rewrite those relative paths
during such a move.

Generated VS Code tasks and newly installed inventory cron lines already use
the dynamic tools location. Existing installed cron or systemd jobs deliberately
remain unchanged until their owning module is migrated; update them through their
owner's deployment workflow or keep a temporary compatibility symlink.

The central cron registry stores workspace references as `${BRAINHOME_ROOT}`.
`brainhome-cron deploy` expands the placeholder using the location of its own
checked-out tools directory. A migration therefore updates registry deployments
without editing every job definition; existing installed jobs remain unchanged
until explicitly redeployed.

## Safe Sequence

1. Add or update the responsible module's `paths.toml`.
2. Replace local hardcoded repository paths with the shell resolver.
3. Keep remote deployment and runtime paths unchanged unless their service has a
   separate deployment plan.
4. Run `brainhome path-preflight --strict` and resolve every candidate in scope.
5. Create temporary compatibility symlinks for external callers when needed.
6. Move one low-risk module, run its health checks, then remove its compatibility
   link only after a stable observation period.

No workspace directories were moved while introducing this library.
