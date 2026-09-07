# proxmox-eg

Node-Arbeitsbereich für `proxmox-eg` (`192.168.188.253`).

## Live-Objekte

- `vms/haos-eg/` - VM102, `192.168.188.194` -> `HomeAssistant/haos-eg`
- `vms/openwrt-eg/` - VM108, `192.168.188.149` -> `openwrt-repeater-setup`
- `ct/pihole-eg/` - CT114, `192.168.188.245` -> `pihole`
- `ct/caddy-eg/` - CT117, `192.168.188.203` -> `caddy`

Die primären Node-Objekte enthalten die kanonischen Modulquellen unter `source/`.
Diese Node ist für Caddy EG und Pi-hole EG ein Replikat; die Manifeste verweisen
auf die kanonischen Quellen auf `proxmox-ug`.
