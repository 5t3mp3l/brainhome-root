# proxmox-ug

Node-Arbeitsbereich für `proxmox-ug` (`192.168.188.248`).

## Live-Objekte

- `vms/haos-ug/` - VM106, `192.168.188.152` -> `HomeAssistant/haos-ug`
- `vms/haos-ga/` - VM115, `192.168.188.191` -> `HomeAssistant/haos-ga`
- `vms/openwrt-ug/` - VM119, `192.168.188.150` -> `openwrt-repeater-setup`
- `vms/grafana/` - VM219, `192.168.188.108` -> `grafana`
- `ct/pihole/` - CT100, `192.168.188.251` -> `pihole`
- `ct/caddy/` - CT110, `192.168.188.202` -> `caddy`
- `ct/brainhome-prod/` - CT116, `192.168.188.116` -> `../webserver`
- `ct/pxe-stack/` - CT130, `192.168.188.250` -> `pxe-boot`

Die primären Node-Objekte enthalten die kanonischen Modulquellen unter `source/`.
Caddy, Pi-hole, OpenWrt, Grafana und PXE werden auf dieser Node kanonisch
gepflegt; Replikate auf EG und OG folgen über `brainhome node-mirrors --apply`.
