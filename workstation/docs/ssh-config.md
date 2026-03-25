# SSH Config — proxmox-master (`/root/.ssh/config`) + brainhome-workstation (`~/.ssh/config`)

> Stand: 25. März 2026  
> `proxmox-root.conf` liegt auf dem proxmox-master unter `/root/.ssh/config`.  
> `workstation.conf` liegt auf der brainhome-workstation VM unter `/home/brain/.ssh/config`.  
> **Keys** sind NICHT versioniert (nur die Config-Struktur).

---

## brainhome-workstation `~/.ssh/config`

> Ermöglicht `devctl.sh` direkt von VS Code aus (SSH → Proxmox-Node → pct exec CT112/CT116).

```ssh-config
# Proxmox-Dev (Master)
Host proxmox proxmox-dev 192.168.188.254
  HostName 192.168.188.254
  User root
  IdentityFile ~/.ssh/brainhome_ws
  ControlMaster auto
  ControlPersist 10m
  ControlPath ~/.ssh/cm/%r@%h:%p
  ServerAliveInterval 30
  ServerAliveCountMax 3
  TCPKeepAlive yes
  ConnectTimeout 10

# Proxmox Workstation (CT112 brainhome-dev)
Host proxmox-workstation proxmox-ws 192.168.188.247
  HostName 192.168.188.247
  User root
  IdentityFile ~/.ssh/brainhome_ws
  ControlMaster auto
  ControlPersist 10m
  ControlPath ~/.ssh/cm/%r@%h:%p
  ServerAliveInterval 30
  ServerAliveCountMax 3
  TCPKeepAlive yes
  ConnectTimeout 10

# Proxmox UG (CT116 brainhome-prod)
Host proxmox-ug 192.168.188.248
  HostName 192.168.188.248
  User root
  IdentityFile ~/.ssh/brainhome_ws
  ControlMaster auto
  ControlPersist 10m
  ControlPath ~/.ssh/cm/%r@%h:%p
  ServerAliveInterval 30
  ServerAliveCountMax 3
  TCPKeepAlive yes
  ConnectTimeout 10
```

**Key**: `~/.ssh/brainhome_ws` (ed25519) — generiert auf brainhome-workstation  
**Pubkey**: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIK1PXQ2VV/mpxOqu0XBurzXcnyzfU87RIx1kiQQTZ9hh brain@brainhome-workstation`

Deploy (einmalig mit Passwort):
```bash
ssh-copy-id -i ~/.ssh/brainhome_ws.pub root@192.168.188.247   # proxmox-workstation
ssh-copy-id -i ~/.ssh/brainhome_ws.pub root@192.168.188.248   # proxmox-ug
```

---

## proxmox-master `/root/.ssh/config`

```ssh-config
# GitHub SSH Keys für verschiedene Repositories

Host github-haos
    HostName github.com
    User git
    IdentityFile /home/haos-configs/.ssh/haos_github
    IdentitiesOnly yes

Host github-haos-eg
    HostName github.com
    User git
    IdentityFile /home/haos-configs/.ssh/haos-eg_github
    IdentitiesOnly yes

Host github-haos-og
    HostName github.com
    User git
    IdentityFile /home/haos-configs/.ssh/haos-og_github
    IdentitiesOnly yes

Host github-haos-ug
    HostName github.com
    User git
    IdentityFile /home/haos-configs/.ssh/haos-ug_github
    IdentitiesOnly yes

Host github-haos-ga
    HostName github.com
    User git
    IdentityFile /home/haos-configs/.ssh/haos-ga_github
    IdentitiesOnly yes

Host github-homeassistant
    HostName github.com
    User git
    IdentityFile /home/haos-configs/.ssh/homeassistant_github
    IdentitiesOnly yes

# Proxmox Nodes
Host proxmox-dev
    HostName 192.168.188.254
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host proxmox-workstation proxmox-ws
    HostName 192.168.188.247
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host proxmox-ug
    HostName 192.168.188.248
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host proxmox-eg
    HostName 192.168.188.253
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host proxmox-og
    HostName 192.168.188.252
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

# DNS
Host pihole
    HostName 192.168.188.251
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host pihole-og
    HostName 192.168.188.249
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host pihole-eg
    HostName 192.168.188.245
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

# Reverse Proxy (Caddy HA-Cluster)
Host caddy
    HostName 192.168.188.200      # Keepalived VIP
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host caddy-backup caddy-1
    HostName 192.168.188.202      # CT110 proxmox-ug — HA Master
    User root
    IdentityFile /root/.ssh/pihole_key

Host caddy-og
    HostName 192.168.188.201      # CT120 proxmox-og — HA Backup OG
    User root
    IdentityFile /root/.ssh/pihole_key

Host caddy-eg
    HostName 192.168.188.203      # CT117 proxmox-eg — HA Backup EG
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

# Services
Host keycloak
    HostName 192.168.188.107
    User brain
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host monitoring
    HostName 192.168.188.108
    User root
    IdentityFile /root/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

Host nextcloud
    HostName 192.168.188.121
    User brain
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host pxe-stack
    HostName 192.168.188.250
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host nas
    HostName 192.168.188.42
    User sshd
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

# BrainHome Webserver
Host brainhome-dev
    HostName 192.168.188.112      # CT112 proxmox-workstation — devctl-target
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host brainhome-prod
    HostName 192.168.188.116      # CT116 proxmox-ug
    User root
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

Host brainhome-workstation
    HostName 192.168.188.193      # VM113 proxmox-workstation
    User brain
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

# Sonstiges
Host workstation
    HostName 192.168.188.178
    User brain
    IdentityFile /root/.ssh/pihole_key
    StrictHostKeyChecking no

# Home Assistant Instanzen
Host ha-master
    HostName 192.168.188.142      # VM101 proxmox-workstation
    User root
    IdentityFile /home/haos-configs/.ssh/vscode_rsa
    StrictHostKeyChecking no
    ServerAliveInterval 30

Host ha-ug
    HostName 192.168.188.152      # VM106 proxmox-ug
    User root
    IdentityFile /home/haos-configs/.ssh/vscode_rsa
    StrictHostKeyChecking no
    ServerAliveInterval 30

Host ha-eg
    HostName 192.168.188.194      # VM102 proxmox-eg
    User root
    IdentityFile /home/haos-configs/.ssh/vscode_rsa
    StrictHostKeyChecking no
    ServerAliveInterval 30

Host ha-og
    HostName 192.168.188.143      # VM103 proxmox-og
    User root
    IdentityFile /home/haos-configs/.ssh/vscode_rsa
    StrictHostKeyChecking no
    ServerAliveInterval 30

Host ha-ga
    HostName 192.168.188.191      # VM115 proxmox-ug
    User root
    IdentityFile /home/haos-configs/.ssh/vscode_rsa
    StrictHostKeyChecking no
    ServerAliveInterval 30
```

---

## Benötigte Keys

| Key | Pfad | Typ | Verwendet für |
|-----|------|-----|---------------|
| `pihole_key` | `/root/.ssh/pihole_key` | ed25519 | Alle Infra-Hosts |
| `vscode_rsa` | `/home/haos-configs/.ssh/vscode_rsa` | ed25519 | Home Assistant Instanzen |
| `id_rsa` | `/root/.ssh/id_rsa` | RSA | monitoring VM |
| `haos_github` | `/home/haos-configs/.ssh/haos_github` | ed25519 | GitHub haos-Repo |
| `haos-eg_github` | `/home/haos-configs/.ssh/haos-eg_github` | ed25519 | GitHub haos-eg-Repo |
| `haos-og_github` | `/home/haos-configs/.ssh/haos-og_github` | ed25519 | GitHub haos-og-Repo |
| `haos-ug_github` | `/home/haos-configs/.ssh/haos-ug_github` | ed25519 | GitHub haos-ug-Repo |
| `haos-ga_github` | `/home/haos-configs/.ssh/haos-ga_github` | ed25519 | GitHub haos-ga-Repo |
| `homeassistant_github` | `/home/haos-configs/.ssh/homeassistant_github` | ed25519 | GitHub homeassistant-Repo |
