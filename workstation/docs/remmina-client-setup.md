# CT113 Workstation — Client Setup (Remmina RDP)

## Übersicht

CT113 (`brainhome-workstation`, `192.168.188.193`) ist die primäre VS Code / Arbeits-Umgebung (Ubuntu 24.04 GNOME, XRDP Port 3389).

**Login:** `brain` / `0248Brain8579`

---

## Clients einrichten

### eg-stefan-lp (192.168.188.58) — Stefan's Laptop

```bash
# Auf eg-stefan-lp als stefan user ausführen:
curl -sO http://192.168.188.193/remmina-setup-ct113.sh 2>/dev/null \
  || scp root@192.168.188.254:/home/workstation/scripts/remmina-setup-ct113.sh /tmp/
bash /tmp/remmina-setup-ct113.sh
```

Oder manuell (Script liegt auf proxmox-master):
```bash
scp root@192.168.188.254:/home/workstation/scripts/remmina-setup-ct113.sh /tmp/remmina-setup-ct113.sh
bash /tmp/remmina-setup-ct113.sh
```

### ug-buero-tc (192.168.188.148) — Thin Client UG/Büro

Gleicher Vorgang wenn der TC online ist:
```bash
scp root@192.168.188.254:/home/workstation/scripts/remmina-setup-ct113.sh /tmp/remmina-setup-ct113.sh
bash /tmp/remmina-setup-ct113.sh
```

---

## Manuelle Remmina Profile Installation

Falls kein SCP-Zugang, Profil manuell anlegen:

```bash
mkdir -p ~/.local/share/remmina
cat > ~/.local/share/remmina/brainhome-ct113-rdp.remmina << 'EOF'
[remmina]
name=CT113 BrainHome Workstation
group=BrainHome
server=192.168.188.193
protocol=RDP
username=brain
domain=
password=
colordepth=32
quality=2
resolution_mode=2
resolution_width=1920
resolution_height=1080
scale=2
keyboard_grab=0
viewmode=1
fullscreen=0
keymap=de
ignore_certificate=1
enableautoreconnect=1
reconnect_maxattempts=5
sound=off
EOF
```

Dann Remmina starten → **BrainHome → CT113 BrainHome Workstation**

---

## CT113 XRDP Status prüfen

```bash
ssh brainhome-workstation 'systemctl is-active xrdp xrdp-sesman'
```

## RDP Verbindung testen (von proxmox-master)

```bash
xfreerdp /v:192.168.188.193 /u:brain /p:0248Brain8579 /w:1920 /h:1080 2>/dev/null | head -5
```

---

## Netzwerk-Topologie

```
ug-buero-tc (192.168.188.148) ──┐
                                 ├── RDP :3389 ──► CT113 brainhome-workstation
eg-stefan-lp (192.168.188.58)  ──┘                (192.168.188.193, proxmox-ws)
```

## Bekannte Probleme

| Problem | Lösung |
|---------|--------|
| "Authentication failed" | Login: brain / 0248Brain8579 |
| Schwarzer Bildschirm nach Login | .xsession vorhanden? `ls ~/.xsession` auf CT113 |
| GNOME startet nicht | startwm.sh nutzt GNOME X11 Session |
| Color Manager Dialog | Polkit Regel: `/etc/polkit-1/rules.d/02-allow-color-manager.rules` |
| Wayland statt X11 | GDM3: `WaylandEnable=false` in `/etc/gdm3/custom.conf` |
