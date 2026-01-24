# KDE Neon Migration Checklist for NEXUS AI Operating System

## Overview
Migration from current system to KDE Neon while preserving all NEXUS services, data, and configurations.

## Phase 1: Pre-Migration Preparation (Current System)

### 1.1 System Analysis
- [ ] **Inventory running services**: `docker ps --filter "name=nexus-" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"`
- [ ] **Check container health**: `docker ps --filter "name=nexus-" --filter "health=unhealthy"`
- [ ] **Verify data directories exist**:
  - PostgreSQL: `/home/philip/nexus/data/postgres`
  - Redis: `/home/philip/nexus/data/redis`
  - n8n: `/home/philip/nexus/data/n8n`
  - Syncthing: `/home/philip/nexus/data/syncthing`
  - Vaultwarden: `/home/philip/nexus/data/vaultwarden`
  - ChromaDB: `/home/philip/nexus/data/chromadb` (may not exist)
- [ ] **Check service dependencies**:
  - FastAPI systemd service: `systemctl status nexus-api`
  - Tailscale: `tailscale status`
  - Docker: `systemctl status docker`

### 1.2 Complete System Backup
```bash
cd /home/philip/nexus
./scripts/backup_nexus_enhanced.sh --verify --cleanup --max-backups 3
```

**Backup verifies**:
- [ ] PostgreSQL dump created and valid
- [ ] Redis RDB file created
- [ ] n8n data backed up (SQLite + workflows)
- [ ] Configuration files (.env, docker-compose.yml, etc.)
- [ ] Home Assistant configuration
- [ ] ChromaDB data (if exists)

### 1.3 Critical Configuration Collection

#### Environment Variables
- [ ] **Copy .env file**: `cp /home/philip/nexus/.env ~/nexus_env_backup.txt`
- [ ] **Document missing variables** (check docker-compose.yml for all `${VARIABLE}` references):
  - `POSTGRES_PASSWORD`
  - `REDIS_PASSWORD`
  - `CHROMA_TOKEN`
  - `N8N_PASSWORD`
  - `VAULTWARDEN_ADMIN_TOKEN`
  - `GROQ_API_KEY`, `GOOGLE_AI_API_KEY`, `OPENROUTER_API_KEY`
  - `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY` (if used)
  - Email credentials: `GMAIL_APP_PASSWORD`, `ICLOUD_APP_PASSWORD`
  - NTFY topic: `NTFY_TOPIC`

#### System Configuration
- [ ] **Tailscale configuration**:
  ```bash
  tailscale status --json > ~/tailscale_status.json
  sudo cat /etc/tailscale/tailscaled.state 2>/dev/null | tail -100 > ~/tailscale_state.txt
  ```
- [ ] **Systemd service files**:
  ```bash
  cp /home/philip/nexus/nexus-api.service ~/
  cp /etc/systemd/system/nexus-api.service ~/ 2>/dev/null || true
  ```
- [ ] **Cron jobs**: `crontab -l > ~/crontab_backup.txt`
- [ ] **Firewall rules**: `sudo iptables-save > ~/iptables_backup.txt`

#### Docker Configuration
- [ ] **Docker images list**: `docker images --filter "reference=*nexus*" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}"`
- [ ] **Docker networks**: `docker network ls --filter "name=nexus" --format "table {{.Name}}\t{{.Driver}}\t{{.Scope}}"`
- [ ] **Volume inspection**: `docker volume ls --filter "name=nexus" --format "table {{.Name}}\t{{.Driver}}\t{{.Mountpoint}}"`

## Phase 2: New System Setup (KDE Neon)

### 2.1 Base System Installation
- [ ] **Install KDE Neon** (fresh installation)
- [ ] **Update system**: `sudo apt update && sudo apt upgrade -y`
- [ ] **Install essential packages**:
  ```bash
  sudo apt install -y git curl wget vim htop net-tools docker.io docker-compose python3-pip python3-venv
  ```
- [ ] **Configure Docker**:
  ```bash
  sudo systemctl enable docker
  sudo systemctl start docker
  sudo usermod -aG docker $USER
  # Log out and back in for group changes
  ```

### 2.2 Tailscale Setup
- [ ] **Install Tailscale**: `sudo apt install -y tailscale`
- [ ] **Start Tailscale**: `sudo tailscale up`
- [ ] **Authenticate**: Use same account as previous system
- [ ] **Verify IP assignment**: `tailscale status`
- [ ] **Note new IP address** (will be different from 100.68.201.55)

### 2.3 NEXUS Repository Setup
- [ ] **Clone repository**:
  ```bash
  cd /home/philip
  git clone https://github.com/YOUR_USERNAME/nexus.git  # Or copy from backup
  # OR restore from backup:
  cd /home/philip
  tar -xzf /path/to/nexus_code_backup.tar.gz
  ```
- [ ] **Restore .env file**:
  ```bash
  cp ~/nexus_env_backup.txt /home/philip/nexus/.env
  # Update any IP addresses if changed (WEBHOOK_URL in docker-compose.yml)
  ```
- [ ] **Update WEBHOOK_URL** in docker-compose.yml if Tailscale IP changed:
  ```yaml
  environment:
    - WEBHOOK_URL=http://NEW_TAILSCALE_IP:5678/
  ```

### 2.4 Python Virtual Environment
- [ ] **Create venv**: `cd /home/philip/nexus && python3 -m venv venv`
- [ ] **Install dependencies**:
  ```bash
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  # Additional dependencies from backup if any:
  pip install psutil>=5.9.0 filelock>=3.13.0
  ```

## Phase 3: Data Migration

### 3.1 Restore from Backup
```bash
cd /home/philip/nexus
BACKUP_PATH="/home/philip/nexus/backups/daily/latest"  # Or specific backup
```

#### PostgreSQL Restoration
- [ ] **Start PostgreSQL container first**:
  ```bash
  docker-compose up -d postgres
  sleep 10  # Wait for startup
  ```
- [ ] **Restore database**:
  ```bash
  docker exec -i nexus-postgres pg_restore -Fc -U nexus -d nexus_db < "$BACKUP_PATH/postgres_backup.dump"
  ```
- [ ] **Verify restoration**:
  ```bash
  docker exec nexus-postgres psql -U nexus -d nexus_db -c "SELECT COUNT(*) FROM agents;"
  ```

#### Redis Restoration
- [ ] **Stop Redis if running**: `docker stop nexus-redis`
- [ ] **Copy RDB file**:
  ```bash
  sudo cp "$BACKUP_PATH/redis_dump.rdb" /home/philip/nexus/data/redis/dump.rdb
  sudo chown 100:101 /home/philip/nexus/data/redis/dump.rdb  # dnsmasq:docker
  ```
- [ ] **Start Redis**: `docker-compose up -d redis`

#### n8n Data Restoration
- [ ] **Stop n8n**: `docker stop nexus-n8n`
- [ ] **Restore SQLite database**:
  ```bash
  cp "$BACKUP_PATH/n8n/database.sqlite" /home/philip/nexus/data/n8n/database.sqlite
  ```
- [ ] **Restore workflows**:
  ```bash
  cp -r "$BACKUP_PATH/n8n/workflows" /home/philip/nexus/automation/
  ```
- [ ] **Start n8n**: `docker-compose up -d n8n`

#### ChromaDB Data (if exists)
- [ ] **Copy ChromaDB data**:
  ```bash
  if [ -d "$BACKUP_PATH/chromadb" ]; then
    mkdir -p /home/philip/nexus/data/chromadb
    cp -r "$BACKUP_PATH/chromadb/"* /home/philip/nexus/data/chromadb/
  fi
  ```

#### Home Assistant Configuration
- [ ] **Restore config**:
  ```bash
  cp -r "$BACKUP_PATH/config/homeassistant/"* /home/philip/nexus/config/homeassistant/
  ```

### 3.2 Start All Services
- [ ] **Start all Docker containers**:
  ```bash
  cd /home/philip/nexus
  docker-compose up -d
  ```
- [ ] **Verify all containers running**: `docker-compose ps`
- [ ] **Check container logs for errors**:
  ```bash
  docker-compose logs --tail=50 postgres redis chromadb n8n
  ```

## Phase 4: FastAPI Service Setup

### 4.1 Systemd Service Configuration
- [ ] **Copy service file**:
  ```bash
  sudo cp /home/philip/nexus/nexus-api.service /etc/systemd/system/
  sudo systemctl daemon-reload
  ```
- [ ] **Update service file paths** if home directory changed
- [ ] **Enable and start service**:
  ```bash
  sudo systemctl enable nexus-api
  sudo systemctl start nexus-api
  ```
- [ ] **Check status**: `systemctl status nexus-api`
- [ ] **View logs**: `journalctl -u nexus-api -f`

### 4.2 Verify API Connectivity
- [ ] **Test health endpoint**: `curl http://localhost:8080/health`
- [ ] **Test chat endpoint**: `curl -X POST http://localhost:8080/chat -H "Content-Type: application/json" -d '{"message": "test"}'`
- [ ] **Test agent framework**: `curl http://localhost:8080/agents`

## Phase 5: Integration Testing

### 5.1 Email Service Verification
- [ ] **Test email scanning**: `curl -X POST http://localhost:8080/email/scan -H "Content-Type: application/json" -d '{"account": "gmail"}'`
- [ ] **Check email credentials** in .env are correct

### 5.2 n8n Workflow Testing
- [ ] **Access n8n UI**: `http://localhost:5678`
- [ ] **Test webhooks**:
  - AI router: `curl -X POST http://localhost:5678/webhook/ai-test`
  - Quick capture: `curl -X POST http://localhost:5678/webhook/quick-capture`
- [ ] **Verify workflow executions** in n8n UI

### 5.3 Home Assistant Verification
- [ ] **Access Home Assistant**: `http://localhost:8123`
- [ ] **Check entities and automations**

### 5.4 Syncthing Setup
- [ ] **Access Syncthing UI**: `http://localhost:8384`
- [ ] **Reconfigure sync directories** if paths changed
- [ ] **Re-pair devices** if necessary

### 5.5 Vaultwarden Verification
- [ ] **Access Vaultwarden**: `http://localhost:8222`
- [ ] **Test login with existing credentials**

## Phase 6: Network & Security

### 6.1 Firewall Configuration
- [ ] **Allow necessary ports**:
  ```bash
  sudo ufw allow 8080/tcp  # FastAPI
  sudo ufw allow 5678/tcp  # n8n
  sudo ufw allow 8123/tcp  # Home Assistant
  sudo ufw allow 8384/tcp  # Syncthing
  sudo ufw allow 8222/tcp  # Vaultwarden
  sudo ufw allow 5432/tcp  # PostgreSQL (optional, local only)
  sudo ufw allow 6379/tcp  # Redis (optional, local only)
  sudo ufw allow 8000/tcp  # ChromaDB (optional, local only)
  ```
- [ ] **Enable firewall**: `sudo ufw enable`

### 6.2 Tailscale Configuration
- [ ] **Verify Tailscale connectivity**: `tailscale ping 100.68.201.55` (old IP)
- [ ] **Update any hardcoded IPs** in configurations
- [ ] **Test external access** via new Tailscale IP

### 6.3 SSL Certificates (Optional)
- [ ] **Consider Let's Encrypt** for public endpoints
- [ ] **Or use Tailscale's HTTPS** for internal access

## Phase 7: Post-Migration Validation

### 7.1 Comprehensive System Test
- [ ] **Run full test suite**:
  ```bash
  cd /home/philip/nexus
  source venv/bin/activate
  python -m pytest tests/ -v
  ```
- [ ] **Fix any test failures** (116 currently failing)

### 7.2 Performance Benchmarking
- [ ] **Test API response times**: `time curl -s http://localhost:8080/health > /dev/null`
- [ ] **Check database connection speed**
- [ ] **Monitor resource usage**: `docker stats --no-stream`

### 7.3 Data Integrity Verification
- [ ] **Compare record counts** with old system
- [ ] **Verify email processing** works
- [ ] **Test financial data** accuracy

## Phase 8: Cleanup & Optimization

### 8.1 Old System Cleanup
- [ ] **Secure wipe** of old system if disposing hardware
- [ ] **Remove sensitive data** from old drives

### 8.2 New System Optimization
- [ ] **Configure Docker log rotation**:
  ```json
  {
    "log-driver": "json-file",
    "log-opts": {
      "max-size": "10m",
      "max-file": "3"
    }
  }
  ```
- [ ] **Set up monitoring**:
  ```bash
  # Install monitoring tools
  sudo apt install -y glances
  ```
- [ ] **Configure automatic backups**:
  ```bash
  # Copy systemd timer files
  sudo cp /home/philip/nexus/scripts/systemd/nexus-backup.* /etc/systemd/system/
  sudo systemctl enable nexus-backup.timer
  sudo systemctl start nexus-backup.timer
  ```

## Emergency Rollback Plan

### If Migration Fails:
1. **Stop all services** on new system
2. **Restore old system** from backup
3. **Update .env** with old Tailscale IP
4. **Start services** on old system

### Critical Success Factors:
- **Database integrity** is paramount
- **.env file** must be preserved exactly
- **Tailscale authentication** must be maintained
- **File permissions** on data directories must be correct

## KDE Neon Specific Notes

### Known Issues:
1. **Docker permissions**: KDE Neon may use different default groups
2. **Python versions**: Default Python may be 3.10 or 3.12 - verify compatibility
3. **Systemd differences**: Some service management differences from previous distro

### Performance Tips:
1. **Disable desktop effects** if system resources limited
2. **Use X11 session** if Wayland causes issues with Docker
3. **Configure swap** if limited RAM: `sudo fallocate -l 4G /swapfile`

## Timeline Estimation

| Phase | Time Estimate | Critical Path |
|-------|---------------|---------------|
| 1. Pre-Migration | 30-60 minutes | Backup completion |
| 2. New System Setup | 60-90 minutes | Tailscale, Docker |
| 3. Data Migration | 30-45 minutes | PostgreSQL restore |
| 4. Service Setup | 15-30 minutes | FastAPI service |
| 5. Integration Testing | 45-60 minutes | All endpoints |
| 6. Network & Security | 15-30 minutes | Firewall, Tailscale |
| 7. Post-Migration | 30-60 minutes | Test suite |
| **Total** | **4-6 hours** | **Backup/Restore** |

## Support Resources

1. **Backup location**: `/home/philip/nexus/backups/daily/`
2. **Logs directory**: `/home/philip/nexus/logs/`
3. **Documentation**: `/home/philip/nexus/CLAUDE.md`
4. **Emergency script**: `/home/philip/nexus/scripts/backup_nexus_enhanced.sh`

---

**Last Updated**: 2026-01-23
**Based on NEXUS State**: 8 Docker containers, 193 PostgreSQL tables, 6 n8n workflows
**Current Issues**: 116 failing tests (to be fixed post-migration)

> **Note**: Test the migration process with a non-critical backup first if possible. The parallel agent swarm for test fixing can run after migration completes.
