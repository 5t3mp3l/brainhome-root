# proxmox-og

Node-Arbeitsbereich für `proxmox-og` (`192.168.188.252`).

## Live-Objekte

- `vms/haos-og/` - VM103, `192.168.188.143` -> `HomeAssistant/haos-og`
- `vms/openwrt-og/` - VM109, `192.168.188.144` -> `openwrt-repeater-setup`
- `ct/pihole-og/` - CT111, `192.168.188.249` -> `pihole`
- `ct/caddy-og/` - CT120, `192.168.188.201` -> `caddy`

Die primären Node-Objekte enthalten die kanonischen Modulquellen unter `source/`.
Diese Node ist für Caddy OG und Pi-hole OG ein Replikat; die Manifeste verweisen
auf die kanonischen Quellen auf `proxmox-ug`.
