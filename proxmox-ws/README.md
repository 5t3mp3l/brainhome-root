# proxmox-ws

Node-Arbeitsbereich für `proxmox-ws` (`192.168.188.247`).

## Live-Objekte

- `vms/ha-master/` - VM101, `192.168.188.142` -> `HomeAssistant/haos`
- `vms/brainhome-workstation/` - VM113, `192.168.188.193` -> `workstation`
- `vms/windows-stefan/` - VM220
- `ct/brainhome-dev/` - CT112, `192.168.188.112` -> `../webserver`

Die primären Node-Objekte enthalten die kanonischen Modulquellen unter `source/`.
Die Workstation- und HA-Master-Quellen werden auf dieser Node gepflegt; der
Webserver bleibt als unabhängiger externer Checkout referenziert.
