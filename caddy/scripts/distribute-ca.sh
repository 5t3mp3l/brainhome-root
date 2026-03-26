#!/bin/bash
# distribute-ca.sh — Caddy Root CA auf alle Systeme verteilen
# Wird auch als Cron bei CA-Erneuerung verwendet

set -euo pipefail

CADDY_IP="192.168.188.200"
CA_PATH="/root/.local/share/caddy/pki/authorities/local/root.crt"
LOCAL_CA="/home/brain/brainhome-root/caddy/config/caddy-root-ca.crt"
SSH_KEY="/home/brain/.ssh/pihole_key"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── 1. Aktuelles CA-Cert von Caddy holen ─────────────────────────────────────
log "Hole CA-Cert von Caddy (${CADDY_IP})..."
ssh -i "$SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=no \
    root@${CADDY_IP} "cat ${CA_PATH}" > "${LOCAL_CA}.new"

# Prüfen ob gültiges PEM
if ! grep -q "BEGIN CERTIFICATE" "${LOCAL_CA}.new"; then
    log "FEHLER: Kein gültiges Zertifikat empfangen"
    rm -f "${LOCAL_CA}.new"
    exit 1
fi

# Prüfen ob neu (Fingerprint vergleichen)
OLD_FP=$(openssl x509 -fingerprint -noout -in "$LOCAL_CA" 2>/dev/null || echo "none")
NEW_FP=$(openssl x509 -fingerprint -noout -in "${LOCAL_CA}.new")

if [[ "$OLD_FP" == "$NEW_FP" ]]; then
    log "CA-Cert unverändert — kein Update nötig"
    rm -f "${LOCAL_CA}.new"
    exit 0
fi

log "Neues CA-Cert erkannt — verteile auf alle Systeme..."
mv "${LOCAL_CA}.new" "$LOCAL_CA"

# ── 2. Funktion: CA auf System installieren ───────────────────────────────────
install_ca() {
    local HOST="$1"
    local SSH_CMD="ssh -i $SSH_KEY -o BatchMode=yes -o StrictHostKeyChecking=no root@${HOST}"

    log "  → ${HOST}..."
    $SSH_CMD "cat > /usr/local/share/ca-certificates/caddy-root-ca.crt" < "$LOCAL_CA"
    $SSH_CMD "update-ca-certificates -f" > /dev/null 2>&1
    log "  ✓ ${HOST} aktualisiert"
}

# ── 3. Verteilen ──────────────────────────────────────────────────────────────
install_ca "192.168.188.251"   # pihole-1
install_ca "192.168.188.249"   # pihole-2

# CT110 (Caddy selbst) — file_server Kopie aktualisieren
ssh -i "$SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=no root@${CADDY_IP} \
    "cp ${CA_PATH} /var/www/caddy-ca/ca.crt && chmod 644 /var/www/caddy-ca/ca.crt"
log "  ✓ CT110 /var/www/caddy-ca/ca.crt aktualisiert"

# VM113 (brainhome-workstation, lokal)
sudo cp "$LOCAL_CA" /usr/local/share/ca-certificates/caddy-root-ca.crt
sudo update-ca-certificates -f > /dev/null 2>&1
log "  ✓ brainhome-workstation (lokal) aktualisiert"

# ── 4. Expiry-Info ────────────────────────────────────────────────────────────
EXPIRY=$(openssl x509 -enddate -noout -in "$LOCAL_CA" | cut -d= -f2)
log "CA-Cert gültig bis: ${EXPIRY}"
log "FERTIG — CA auf alle Systeme verteilt"

# ── 5. Cert in /home/caddy/ beschreibbar halten ──────────────────────────────
chmod 644 "$LOCAL_CA"
