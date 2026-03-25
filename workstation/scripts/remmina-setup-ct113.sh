#!/bin/bash
# ============================================================
# Remmina RDP Setup: CT113 BrainHome Workstation
# Einsatz auf: ug-buero-tc (192.168.188.148) und
#              eg-stefan-lp (192.168.188.58)
# CT113 Ziel:  192.168.188.193, User: brain
# ============================================================

set -e

REMMINA_DIR="${HOME}/.local/share/remmina"
PROFILE_UUID="brainhome-ct113-rdp"
PROFILE_FILE="${REMMINA_DIR}/${PROFILE_UUID}.remmina"

echo "🖥️  Remmina RDP Setup für CT113 BrainHome Workstation"
echo "========================================================="
echo "Ziel: brain@192.168.188.193 (Port 3389)"
echo ""

# 1. Remmina installieren falls noch nicht vorhanden
if ! command -v remmina &>/dev/null; then
    echo "📦 Remmina installieren..."
    sudo apt-get update -q
    sudo apt-get install -y remmina remmina-plugin-rdp
    echo "   ✅ Remmina installiert"
else
    echo "   ✅ Remmina bereits installiert: $(remmina --version 2>/dev/null | head -1)"
fi

# Remmina RDP Plugin prüfen
if ! dpkg -l remmina-plugin-rdp &>/dev/null; then
    echo "📦 RDP Plugin installieren..."
    sudo apt-get install -y remmina-plugin-rdp
fi

# 2. Profil-Verzeichnis anlegen
mkdir -p "${REMMINA_DIR}"

# 3. Remmina Profil erstellen
echo ""
echo "📝 Remmina RDP Profil erstellen..."
cat > "${PROFILE_FILE}" << 'REMMINA_PROFILE'
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
keyboard_layout=0
keymap=de
exec=
execpath=
shareprinter=0
sharesmartcard=0
sharedc=
sharecmd=
disablepasswordstoring=0
console=0
ignore_certificate=1
cert_ignore=1
precommand=
postcommand=
sound=off
microphone=off
disableserverbackground=0
disablewin8effect=0
disablecontentscaling=0
disablemenuanimations=0
disablethemes=0
disablecursorshadow=0
disablecursorblinking=0
enableautoreconnect=1
reconnect_maxattempts=5
ssh_tunnel_enabled=0
ssh_tunnel_loopback=0
REMMINA_PROFILE

chmod 600 "${PROFILE_FILE}"
echo "   ✅ Profil erstellt: ${PROFILE_FILE}"

# 4. Verbindung testen (ping)
echo ""
echo "🔍 Verbindungstest zu CT113 (192.168.188.193)..."
if ping -c1 -W2 192.168.188.193 &>/dev/null; then
    echo "   ✅ CT113 erreichbar"
else
    echo "   ⚠️  CT113 nicht erreichbar (Netzwerk prüfen)"
fi

echo ""
echo "============================================================"
echo "✅ Remmina RDP Profil bereit!"
echo ""
echo "🚀 Starten: remmina"
echo "   Dann: BrainHome → CT113 BrainHome Workstation"
echo ""
echo "🔑 Login: brain / 0248Brain8579"
echo "============================================================"
