#!/usr/bin/env python3
"""
pihole-sync.py — BrainHome Pi-hole Sync
Master:   pihole-1  (192.168.188.251, CT100 auf proxmox-ug)
Replicas: pihole-og (192.168.188.249, CT111 auf proxmox-og)
          pihole-eg (192.168.188.245, CT114 auf proxmox-eg)

Aufruf:
  python3 pihole-sync.py           # Nur DNS hosts
  python3 pihole-sync.py --gravity # Zusätzlich Gravity DB
  python3 pihole-sync.py --cron    # Cron-Modus

Cron (alle 5 Min DNS):
  */5 * * * * /usr/bin/python3 /usr/local/bin/pihole-sync.py --cron >> /var/log/pihole-sync.log 2>&1
Cron (tägl. 03:00 Gravity):
  0 3 * * * /usr/bin/python3 /usr/local/bin/pihole-sync.py --gravity --cron >> /var/log/pihole-sync.log 2>&1
"""

import subprocess, sys, re, hashlib, logging, os, tempfile
from datetime import datetime

MASTER_IP = "192.168.188.251"
REPLICAS  = [
    ("pihole-og", "192.168.188.249"),
    ("pihole-eg", "192.168.188.245"),
]
SSH_KEY   = "/home/brain/.ssh/pihole_key"
TOML_PATH  = "/etc/pihole/pihole.toml"
GRAVITY_DB = "/etc/pihole/gravity.db"
LOG_FILE   = "/var/log/pihole-sync.log"

args      = sys.argv[1:]
CRON_MODE = "--cron"    in args
SYNC_GRV  = "--gravity" in args

logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("pihole-sync")

def out(msg):
    log.info(msg)
    if not CRON_MODE:
        print(msg)

def ssh(ip, cmd, input_data=None, timeout=30):
    r = subprocess.run(
        ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
         f"root@{ip}", cmd],
        capture_output=True, text=True, input=input_data, timeout=timeout
    )
    if r.returncode != 0:
        raise RuntimeError(f"SSH {ip}: {r.stderr.strip()[:200]}")
    return r.stdout

def ssh_bytes(ip, cmd, timeout=120):
    r = subprocess.run(
        ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
         f"root@{ip}", cmd],
        capture_output=True, timeout=timeout
    )
    if r.returncode != 0:
        raise RuntimeError(f"SSH {ip}: {r.stderr.decode()[:200]}")
    return r.stdout

def extract_hosts(toml):
    m = re.search(r'(  hosts = \[.*?\])(?:\s*### CHANGED, default = \[\])?', toml, re.DOTALL)
    return m.group(1) if m else "  hosts = []"

def inject_hosts(toml, hosts_block):
    result = re.sub(
        r'  hosts = \[.*?\]\s*(?:### CHANGED, default = \[\])?',
        hosts_block + " ### CHANGED, default = []",
        toml, count=1, flags=re.DOTALL
    )
    if result == toml:
        result = toml.replace("  hosts = []",
                              hosts_block + " ### CHANGED, default = []", 1)
    return result

def md5(s):
    return hashlib.md5(s.encode() if isinstance(s, str) else s).hexdigest()[:8]

def sync_replica(name, replica_ip, master_hosts, master_toml):
    """Sync DNS hosts (and optionally gravity) to a single replica. Returns True if changed."""
    changed = False
    out(f"DNS [{name}]: Lese {replica_ip} ...")
    try:
        replica_toml  = ssh(replica_ip, f"cat {TOML_PATH}")
    except RuntimeError as e:
        out(f"DNS [{name}]: ⚠️  Nicht erreichbar — {e}")
        return False
    replica_hosts = extract_hosts(replica_toml)

    mh, rh = md5(master_hosts), md5(replica_hosts)
    if mh == rh:
        out(f"DNS [{name}]: Kein Unterschied (hash={mh}) — OK")
    else:
        out(f"DNS [{name}]: Unterschied! Master={mh} Replica={rh}")
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        ssh(replica_ip, f"cp {TOML_PATH} {TOML_PATH}.bak.{ts}")
        new_toml = inject_hosts(replica_toml, master_hosts)
        ssh(replica_ip, f"cat > {TOML_PATH}", input_data=new_toml)
        ssh(replica_ip, "pihole reloaddns")
        verify_hosts = extract_hosts(ssh(replica_ip, f"cat {TOML_PATH}"))
        if md5(verify_hosts) == mh:
            out(f"DNS [{name}]: ✓ Sync verifiziert")
            changed = True
        else:
            raise RuntimeError(f"DNS [{name}] Verifikation fehlgeschlagen!")

    if SYNC_GRV:
        out(f"Gravity [{name}]: Prüfe Checksums ...")
        try:
            m_md5 = ssh(MASTER_IP,   f"md5sum {GRAVITY_DB}").split()[0]
            r_md5 = ssh(replica_ip,  f"md5sum {GRAVITY_DB}").split()[0]
        except RuntimeError as e:
            out(f"Gravity [{name}]: ⚠️  Nicht erreichbar — {e}")
            return changed
        if m_md5 == r_md5:
            out(f"Gravity [{name}]: Kein Unterschied (md5={m_md5[:8]}) — OK")
        else:
            out(f"Gravity [{name}]: Unterschied! Master={m_md5[:8]} Replica={r_md5[:8]}")
            db_data = ssh_bytes(MASTER_IP, f"cat {GRAVITY_DB}")
            out(f"Gravity [{name}]: {len(db_data)//1024} KB heruntergeladen")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tf:
                tf.write(db_data)
                tmpfile = tf.name
            try:
                r = subprocess.run(
                    ["scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
                     tmpfile, f"root@{replica_ip}:{GRAVITY_DB}"],
                    capture_output=True, text=True, timeout=120
                )
                if r.returncode != 0:
                    raise RuntimeError(f"scp Fehler: {r.stderr}")
            finally:
                os.unlink(tmpfile)
            ssh(replica_ip, "pihole restartdns")
            out(f"Gravity [{name}]: ✓ DB übertragen")
            changed = True

    return changed


def main():
    out(f"=== Pi-hole Sync Start (Gravity={SYNC_GRV}) ===")
    changed = False

    # ── Fetch master once ─────────────────────────────────────────────────
    out(f"DNS: Lese Master {MASTER_IP} ...")
    master_toml  = ssh(MASTER_IP, f"cat {TOML_PATH}")
    master_hosts = extract_hosts(master_toml)

    # ── Sync to all replicas ──────────────────────────────────────────────
    for name, replica_ip in REPLICAS:
        try:
            if sync_replica(name, replica_ip, master_hosts, master_toml):
                changed = True
        except RuntimeError as e:
            out(f"FEHLER [{name}]: {e}")

    # ── Verify (DNS-Auflösung) ────────────────────────────────────────────
    try:
        import subprocess as sp
        p_master = sp.run(["nslookup", "proxmox.brain", MASTER_IP],
                          capture_output=True, text=True, timeout=5).stdout
        ip_master = re.search(r'Address: ([\d.]+)', p_master)
        for name, replica_ip in REPLICAS:
            p_rep = sp.run(["nslookup", "proxmox.brain", replica_ip],
                           capture_output=True, text=True, timeout=5).stdout
            ip_rep = re.search(r'Address: ([\d.]+)', p_rep)
            if ip_master and ip_rep and ip_master.group(1) == ip_rep.group(1):
                out(f"Verify [{name}]: master={ip_master.group(1)} replica={ip_rep.group(1)} ✓")
            else:
                out(f"Verify [{name}]: WARNUNG master={ip_master} replica={ip_rep}")
    except Exception as e:
        out(f"Verify: Skipped ({e})")

    out(f"=== Sync Ende [{'CHANGED' if changed else 'NO_CHANGE'}] ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(f"FEHLER: {e}")
        if not CRON_MODE:
            print(f"FEHLER: {e}", file=sys.stderr)
        sys.exit(1)
