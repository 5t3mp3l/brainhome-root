#!/usr/bin/env python3
"""
ha-addon-update-sync.py
=======================
Synct Addon-Versionen von ha-master auf ha-ug/ha-eg/ha-og.

Strategie:
  1. Addon-Liste von ha-master via SSH holen
  2. Addon-Liste von jedem Remote holen
  3. Wenn Remote ein Addon hat das auch auf Master läuft UND
     Remote-Version != Master-Version → Update auf Remote

Voraussetzung: SSH-Key /root/.ssh/pihole_key muss auf alle HA-Instanzen passen.

Usage:
  python3 ha-addon-update-sync.py [--dry-run]
"""

import subprocess
import sys
import re
from datetime import datetime

# ── Konfiguration ──────────────────────────────────────────────────────────────
SSH_KEY    = "/home/brain/.ssh/pihole_key"
SSH_OPTS   = ["-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
LOG_FILE   = "/var/log/ha-addon-sync.log"
DRY_RUN    = "--dry-run" in sys.argv

MASTER = {"name": "ha-master", "host": "root@192.168.188.142"}
REMOTES = [
    {"name": "ha-ug",  "host": "root@192.168.188.152"},
    {"name": "ha-eg",  "host": "root@192.168.188.148"},
    {"name": "ha-og",  "host": "root@192.168.188.143"},
]

# ── Hilfsfunktionen ────────────────────────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def ssh_run(host, cmd, timeout=30):
    """Führt einen Befehl via SSH aus. Gibt (returncode, stdout, stderr) zurück."""
    result = subprocess.run(
        ["ssh"] + SSH_OPTS + [host, cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr

def parse_addons_yaml(yaml_text):
    """
    Parst die Ausgabe von 'ha apps list --no-progress' (YAML-Format).
    Gibt Dict {slug: {"name": ..., "version": ..., "state": ..., "update_available": ...}} zurück.
    """
    addons = {}
    current = {}
    for line in yaml_text.splitlines():
        # Neues Addon startet mit '- ' (Listenelement)
        if re.match(r'^- ', line):
            if current.get('slug'):
                addons[current['slug']] = current
            current = {}
            # Erste Zeile kann auch ein Feld enthalten: '- slug: ...'
            line = line[2:]  # '- ' entfernen
        
        # Key: Value Felder parsen
        m = re.match(r'^\s+?(\w+):\s*(.*)', line)
        if not m:
            m = re.match(r'^(\w+):\s*(.*)', line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if key == 'update_available':
                current[key] = val.lower() == 'true'
            else:
                current[key] = val
    
    # Letztes Addon nicht vergessen
    if current.get('slug'):
        addons[current['slug']] = current
    
    return addons

def get_addons(instance):
    """Gibt Dict {slug: addon_info} für eine HA-Instanz zurück oder None bei Fehler."""
    rc, stdout, stderr = ssh_run(instance['host'], "ha apps list --no-progress 2>/dev/null")
    if rc != 0:
        log(f"  ✗ SSH-Fehler bei {instance['name']}: {stderr.strip()[:100]}")
        return None
    
    addons = parse_addons_yaml(stdout)
    return addons

def update_addon(instance, slug, dry_run=False):
    """Führt ha apps update <slug> auf einer Remote-Instanz aus."""
    if dry_run:
        log(f"  [DRY-RUN] ha apps update {slug} auf {instance['name']}")
        return True
    
    log(f"  → Update {slug} auf {instance['name']} …")
    rc, stdout, stderr = ssh_run(instance['host'], f"ha apps update {slug} --no-progress 2>&1", timeout=120)
    if rc == 0:
        log(f"  ✓ {slug} erfolgreich upgedated")
        return True
    else:
        log(f"  ✗ Update von {slug} fehlgeschlagen: {(stdout + stderr).strip()[:200]}")
        return False

# ── Hauptprogramm ──────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log(f"HA Addon Sync gestartet {'(DRY-RUN)' if DRY_RUN else ''}")
    
    # 1. Addon-Liste von ha-master holen
    log(f"Lade Addons von {MASTER['name']} …")
    master_addons = get_addons(MASTER)
    if master_addons is None:
        log(f"✗ Kann {MASTER['name']} nicht erreichen — Abbruch")
        sys.exit(1)
    
    installed_on_master = {slug for slug, info in master_addons.items() if info.get('state') not in ('', None)}
    log(f"  Master hat {len(master_addons)} Addons")
    
    # 2. Für jede Remote-Instanz sync durchführen
    total_updates = 0
    total_errors = 0
    
    for remote in REMOTES:
        log(f"\nVerarbeite {remote['name']} …")
        remote_addons = get_addons(remote)
        if remote_addons is None:
            log(f"  ✗ Übersprungen")
            total_errors += 1
            continue
        
        log(f"  {len(remote_addons)} Addons installiert")
        
        updates_needed = []
        for slug, rinfo in remote_addons.items():
            if slug not in master_addons:
                continue  # Addon nicht auf Master → überspringen
            
            minfo = master_addons[slug]
            r_ver = rinfo.get('version', '')
            m_ver = minfo.get('version', '')
            
            if r_ver and m_ver and r_ver != m_ver:
                updates_needed.append((slug, rinfo.get('name', slug), r_ver, m_ver))
        
        if not updates_needed:
            log(f"  ✓ Alles aktuell")
            continue
        
        log(f"  {len(updates_needed)} Update(s) nötig:")
        for slug, name, r_ver, m_ver in updates_needed:
            log(f"    {name} ({slug}): {r_ver} → {m_ver}")
            success = update_addon(remote, slug, dry_run=DRY_RUN)
            if success:
                total_updates += 1
            else:
                total_errors += 1
    
    log(f"\nFertig: {total_updates} Updates, {total_errors} Fehler")
    log("=" * 60)

if __name__ == "__main__":
    main()
