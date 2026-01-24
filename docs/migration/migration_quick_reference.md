# NEXUS Migration Quick Reference

## BEFORE YOU START (Current System)
1. **Run enhanced backup**: `./scripts/backup_nexus_enhanced.sh --verify`
2. **Copy .env file**: `cp .env ~/nexus_env_backup.txt`
3. **Check Tailscale status**: `tailscale status`
4. **Verify containers running**: `docker-compose ps`

## MIGRATION STEPS (KDE Neon)

### Step 1: Base System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose python3-pip python3-venv tailscale git
sudo systemctl enable docker
sudo tailscale up
```

### Step 2: Clone & Configure
```bash
cd /home/philip
git clone YOUR_REPO_URL nexus  # Or copy from backup
cd nexus
cp ~/nexus_env_backup.txt .env
# Update WEBHOOK_URL in docker-compose.yml with new Tailscale IP
```

### Step 3: Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Start Database (Restore First)
```bash
docker-compose up -d postgres
sleep 10
docker exec -i nexus-postgres pg_restore -Fc -U nexus -d nexus_db < backups/daily/latest/postgres_backup.dump
```

### Step 5: Restore Other Data
```bash
# Redis
sudo cp backups/daily/latest/redis_dump.rdb data/redis/dump.rdb
sudo chown 100:101 data/redis/dump.rdb

# n8n
cp backups/daily/latest/n8n/database.sqlite data/n8n/
cp -r backups/daily/latest/n8n/workflows automation/

# Start all containers
docker-compose up -d
```

### Step 6: FastAPI Service
```bash
sudo cp nexus-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nexus-api
sudo systemctl start nexus-api
```

### Step 7: Verify
```bash
curl http://localhost:8080/health
curl http://localhost:5678/  # n8n
```

## TROUBLESHOOTING

### PostgreSQL Restore Fails
```bash
# Drop database and recreate
docker exec nexus-postgres dropdb -U nexus nexus_db
docker exec nexus-postgres createdb -U nexus nexus_db
# Try restore again
```

### Redis Permission Denied
```bash
sudo chown -R 100:101 data/redis  # dnsmasq:docker
```

### n8n Webhook URL
**Critical**: Update `WEBHOOK_URL` in docker-compose.yml with new Tailscale IP.

### Tailscale Issues
```bash
sudo tailscale down
sudo tailscale up --reset
# Re-authenticate
```

### Python Import Errors
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## POST-MIGRATION

### Fix 116 Failing Tests
After migration, run the parallel agent swarm:
1. Master agent categorizes failures
2. 4 specialized agents fix tests simultaneously
3. Git isolation prevents conflicts
4. ~20 minute estimated fix time

### Test All Endpoints
```bash
python scripts/test_api.py --all
```

## EMERGENCY CONTACTS
- **Backup location**: `backups/daily/latest/`
- **Logs**: `logs/` directory
- **Documentation**: `CLAUDE.md`
- **Original .env**: `~/nexus_env_backup.txt`

## TIME ESTIMATE
- **Preparation**: 30 min
- **Migration**: 2-3 hours
- **Testing**: 1 hour
- **Total**: 4-5 hours

> **Note**: ChromaDB directory may be empty - this is normal if not heavily used. The vector database will regenerate as needed.
