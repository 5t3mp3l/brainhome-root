#!/bin/bash
set -euo pipefail

node="$(hostname)"
case "$node" in
    proxmox-eg|proxmox-og|proxmox-ug) ;;
    *) printf 'Unsupported node: %s\n' "$node" >&2; exit 1 ;;
esac

config=/etc/vzdump.conf
target=/var/tmp/brainhome-vzdump
active="$(pvesh get "/nodes/$node/tasks" --source active --typefilter vzdump --output-format json)"
printf '%s' "$active" | perl -MJSON::PP -e 'local $/; exit(@{decode_json(<STDIN>)} ? 1 : 0)' || {
    printf 'Active backup on %s; no changes made\n' "$node" >&2
    exit 1
}

filesystem="$(findmnt -n -o FSTYPE -T /var/tmp)"
case "$filesystem" in
    ext4|xfs|zfs|btrfs) ;;
    *) printf 'Unexpected temporary filesystem: %s\n' "$filesystem" >&2; exit 1 ;;
esac
available="$(df -B1 --output=avail /var/tmp | tail -1 | tr -d ' ')"
(( available >= 21474836480 )) || {
    printf 'Less than 20 GiB free; no changes made\n' >&2
    exit 1
}

if grep -Eq '^[[:space:]]*tmpdir:' "$config"; then
    grep -Eq '^tmpdir: /var/tmp/brainhome-vzdump$' "$config" || {
        printf 'Existing tmpdir differs; manual decision required\n' >&2
        exit 1
    }
    test -d "$target"
    test ! -L "$target"
    chmod 0711 "$target"
    printf 'Already configured: %s\n' "$target"
    exit 0
fi
test ! -L "$target"
test ! -e "$target" || {
    printf 'Unmanaged target already exists; no changes made\n' >&2
    exit 1
}
grep -qx '#tmpdir: DIR' "$config"
backup="$(mktemp /etc/vzdump.conf.before-local-tmp.XXXXXXXX)"
cp -p "$config" "$backup"
staged="$(mktemp /etc/vzdump.conf.staged.XXXXXXXX)"
trap 'rm -f "$staged"' EXIT
cp -p "$config" "$staged"
perl -pi -e 's!^#tmpdir: DIR$!tmpdir: /var/tmp/brainhome-vzdump!' "$staged"
grep -qx 'tmpdir: /var/tmp/brainhome-vzdump' "$staged"
install -d -m 0711 -o root -g root "$target"
mv "$staged" "$config"
printf 'Configured %s; rollback copy: %s\n' "$node" "$backup"
grep '^tmpdir:' "$config"
stat -c '%U:%G %a %n' "$target"
findmnt -n -o SOURCE,FSTYPE -T "$target"