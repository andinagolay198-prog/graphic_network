# Upload GitHub & Pull về Ubuntu Docker

## **PHẦN 1: Setup GitHub Repository**

### **1.1 Tạo Repository (nếu chưa có)**

**Trên GitHub.com:**
1. Đăng nhập GitHub
2. Click "+" → "New repository"
3. Repository name: `graphic_network`
4. Description: "Network Topology Manager with Topology Visualization"
5. Private hoặc Public (tùy bạn)
6. **Initialize with:**
   - [ ] Add a README file
   - [ ] Add .gitignore (Python)
   - [ ] Choose a license (MIT)
7. Click "Create repository"

**Repository URL:** `https://github.com/andinagolay198-prog/graphic_network`

---

## **PHẦN 2: Upload Files từ Windows lên GitHub**

### **2.1 Cách 1: Dùng Git (Recommended)**

**Prerequisite: Cài Git**
- Download từ: https://git-scm.com/download/win
- Install với settings mặc định

**Sau cài xong, mở Command Prompt/PowerShell:**

```powershell
# Navigate tới folder project
cd D:\GRAPHIC NETWORK

# Initialize Git repository (nếu chưa có)
git init

# Add GitHub repository as remote
git remote add origin https://github.com/andinagolay198-prog/graphic_network.git

# Verify remote
git remote -v
# Output:
# origin  https://github.com/andinagolay198-prog/graphic_network.git (fetch)
# origin  https://github.com/andinagolay198-prog/graphic_network.git (push)

# Configure Git (first time only)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### **2.2 Tạo .gitignore**

**Tạo file `.gitignore` trong `D:\GRAPHIC NETWORK`:**

```powershell
# PowerShell - tạo .gitignore
@"
# Environment
.env
.env.local
*.pem
*.key
credentials.yml

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/

# Node
node_modules/
npm-debug.log
yarn-error.log
.next/
.out/

# Docker
.docker/
.dockerignore

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Database
*.db
*.sqlite
*.sqlite3
*.sql

# Logs
*.log
logs/

# Docker volumes
postgres_data/
redis_data/
influxdb_data/
grafana_data/
prometheus_data/
"@ | Out-File -Encoding UTF8 .gitignore
```

### **2.3 Add & Commit Files**

```powershell
# Verify files
git status
# Sẽ show tất cả files (trong red) sẵn để add

# Add tất cả files
git add .

# Verify added files
git status
# Sẽ show tất cả files (trong green)

# Create first commit
git commit -m "Initial commit: Network Topology Manager with visualization"

# Verify commit
git log --oneline
```

### **2.4 Push lên GitHub**

```powershell
# First time push - set upstream
git push -u origin main

# Nếu branch là master:
git push -u origin master

# Subsequent pushes
git push origin main
```

**Nếu nhờ nhập password:**

```powershell
# GitHub có yêu cầu Personal Access Token (không dùng password trực tiếp)

# 1. Tạo Personal Access Token:
#    GitHub → Settings → Developer settings → Personal access tokens → Generate new token
#    - Name: "git-windows"
#    - Expiration: 30 days
#    - Scopes: repo, workflow
#    - Copy token

# 2. Khi GitHub yêu cầu password, paste token này

# 3. Save credentials (optional)
git config --global credential.helper wincred
# Hoặc dùng GitHub CLI:
gh auth login
```

### **2.5 Verify Upload**

**Kiểm tra trên GitHub.com:**
- Truy cập: https://github.com/andinagolay198-prog/graphic_network
- Sẽ thấy tất cả files đã upload
- Xem commit history

---

## **PHẦN 3: Pull về Ubuntu Docker**

### **3.1 Mở Ubuntu Terminal (WSL2)**

**Cách 1: Từ Windows Terminal**
- Mở Windows Terminal
- Click dropdown → Ubuntu-22.04
- Hoặc press `Ctrl+Shift+3`

**Cách 2: Từ PowerShell**
```powershell
wsl
# Hoặc
wsl --distribution Ubuntu-22.04
```

**Cách 3: Direct (Desktop)**
- Search "Ubuntu" → Open

### **3.2 Clone Repository**

```bash
# Navigate tới home directory
cd ~

# Tạo folder projects
mkdir -p projects
cd projects

# Clone repository
git clone https://github.com/andinagolay198-prog/graphic_network.git

# Navigate vào project
cd graphic_network

# Verify files
ls -la
```

**Output:**
```
total 120
drwxr-xr-x  5 user user  4096 Mar  9 15:45 .
drwxr-xr-x  3 user user  4096 Mar  9 15:40 ..
-rw-r--r--  1 user user   707 Mar  9 15:45 Dockerfile.backend
-rw-r--r--  1 user user   610 Mar  9 15:45 Dockerfile.frontend
-rw-r--r--  1 user user 11000 Mar  9 15:45 SETUP_GUIDE.md
-rw-r--r--  1 user user  3495 Mar  9 15:45 docker-compose.yml
-rw-r--r--  1 user user  8400 Mar  9 15:45 init-db.sql
-rw-r--r--  1 user user 16044 Mar  9 15:45 network-collector.py
-rw-r--r--  1 user user 19628 Mar  9 15:45 network-topology-app.jsx
-rw-r--r--  1 user user  9555 Mar  9 15:45 QUICK_START.md
-rw-r--r--  1 user user  9120 Mar  9 15:45 websocket-server.py
drwxr-xr-x  8 user user  4096 Mar  9 15:45 .git
```

### **3.3 Tạo .env file**

```bash
# Navigate vào project folder
cd ~/projects/graphic_network

# Tạo .env
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://topology_user:topology_pass@postgres:5432/network_topology
REDIS_URL=redis://redis:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Collector
COLLECTOR_INTERVAL=300
COLLECTOR_TIMEOUT=30

# Logging
LOG_LEVEL=info
EOF

# Verify .env
cat .env
```

### **3.4 Tạo Folder Structures**

```bash
# Tạo config folder
mkdir -p config
mkdir -p collectors

# Tạo sample devices.yml
cat > config/devices.yml << 'EOF'
devices:
  - id: core-1
    name: "Core-Router-1"
    type: router
    vendor: mikrotik
    ip: 192.168.1.1
    credentials:
      username: admin
      password: "your_password"
      port: 22
    monitoring:
      enabled: true
      interval: 300

  - id: fw-1
    name: "Firewall-Primary"
    type: firewall
    vendor: fortinet
    ip: 192.168.1.3
    credentials:
      api_key: "your_api_key"
    monitoring:
      enabled: true
      interval: 300

  - id: sw-1
    name: "Switch-Main"
    type: switch
    vendor: cisco
    ip: 192.168.2.1
    credentials:
      snmp_community: "public"
    monitoring:
      enabled: true
      interval: 300
EOF

# Verify
ls -la config/
cat config/devices.yml
```

### **3.5 Tạo requirements.txt (nếu chưa có)**

```bash
cat > requirements.txt << 'EOF'
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
python-multipart==0.0.6

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
asyncpg==0.29.0

# Cache
redis==5.0.1

# Network
paramiko==3.4.0
pysnmp==4.4.12
requests==2.31.0
pyyaml==6.0.1

# Data Processing
pandas==2.1.3
numpy==1.26.2

# Security
cryptography==41.0.7
pydantic==2.5.2

# Monitoring
prometheus-client==0.19.0

# Utilities
python-dotenv==1.0.0
EOF

# Verify
cat requirements.txt
```

---

## **PHẦN 4: Build & Run Docker**

### **4.1 Verify Docker Installation**

```bash
# Check Docker
docker --version
# Output: Docker version 24.x.x

# Check Docker Compose
docker-compose --version
# Output: Docker Compose version 2.x.x

# Test Docker
docker run hello-world
# Output: "Hello from Docker!"
```

Nếu chưa cài Docker, xem hướng dẫn **Phần 2 - Bước 2** trong file `WSL2_SETUP.md`

### **4.2 Build Images**

```bash
# Navigate vào project folder
cd ~/projects/graphic_network

# Build tất cả images
docker-compose build

# Output:
# [+] Building 45.2s (23/23) FINISHED
# ...
# => naming to docker.io/library/graphic-network-backend
# => naming to docker.io/library/graphic-network-frontend
```

**Lần đầu build sẽ lâu khoảng 5-10 phút.**

### **4.3 Start Services**

```bash
# Start tất cả containers
docker-compose up -d

# Check status
docker-compose ps

# Output:
# NAME                    STATUS                  PORTS
# graphic-network-backend Up 10 seconds           0.0.0.0:8000->8000/tcp
# graphic-network-frontend Up 10 seconds          0.0.0.0:3000->3000/tcp
# topology-postgres       Up 10 seconds           0.0.0.0:5432->5432/tcp
# topology-redis          Up 10 seconds           0.0.0.0:6379->6379/tcp
```

### **4.4 Verify Services**

```bash
# Check backend API
curl http://localhost:8000/api/health
# Output: {"status":"ok","timestamp":"...","connected_clients":0}

# Check frontend
curl http://localhost:3000
# Output: HTML của React app

# Check database
docker-compose exec postgres psql -U topology_user -d network_topology -c "SELECT COUNT(*) FROM devices;"
# Output: count
# -------
#      6
```

---

## **PHẦN 5: Access Application from Windows**

### **5.1 Open in Browser**

**Mở browser trên Windows (Chrome, Firefox, Edge):**

```
Frontend:     http://localhost:3000
Backend API:  http://localhost:8000
API Docs:     http://localhost:8000/docs
Grafana:      http://localhost:3001
Prometheus:   http://localhost:9090
PostgreSQL:   localhost:5432
Redis:        localhost:6379
```

### **5.2 Test Frontend**

Khi mở http://localhost:3000:
- Sẽ thấy "Network Topology Manager"
- Left sidebar: Device list
- Main area: Topology graph
- Right panel: Device details

### **5.3 Test Backend API**

```powershell
# PowerShell - test endpoints
curl http://localhost:8000/api/devices
curl http://localhost:8000/api/links
curl http://localhost:8000/api/topology

# Hoặc access API Docs: http://localhost:8000/docs
```

---

## **PHẦN 6: Daily Workflow**

### **6.1 Update Code từ GitHub**

**Khi code có updates trên GitHub:**

```bash
# Navigate vào project
cd ~/projects/graphic_network

# Pull latest changes
git pull origin main

# Rebuild images nếu requirements.txt thay đổi
docker-compose build

# Restart services
docker-compose up -d
```

### **6.2 Make Local Changes**

**Khi bạn thay đổi code:**

```bash
# Navigate vào project
cd ~/projects/graphic_network

# Check status
git status

# Add changes
git add .

# Commit
git commit -m "Update: Added device X monitoring"

# Push lên GitHub
git push origin main
```

### **6.3 View Logs**

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Last 50 lines
docker-compose logs --tail=50 backend

# Exit logs: Ctrl+C
```

### **6.4 Update Config**

```bash
# Edit devices
nano config/devices.yml

# Reload services
docker-compose restart backend

# Verify in logs
docker-compose logs -f backend
```

---

## **PHẦN 7: Backup & Restore**

### **7.1 Backup Database**

```bash
# Create backup folder
mkdir -p backups

# Backup database
docker-compose exec postgres pg_dump -U topology_user network_topology > backups/backup-$(date +%Y%m%d-%H%M%S).sql

# Verify backup
ls -lah backups/
```

### **7.2 Restore Database**

```bash
# List backups
ls -lah backups/

# Restore từ backup
docker-compose exec postgres psql -U topology_user network_topology < backups/backup-20240309-143020.sql
```

### **7.3 Backup Complete Project**

```bash
# Create tarball
tar -czf graphic_network-backup-$(date +%Y%m%d).tar.gz .

# Move to safe location
mkdir -p ~/backups
mv graphic_network-backup-*.tar.gz ~/backups/

# List backups
ls -lah ~/backups/
```

---

## **PHẦN 8: Troubleshooting**

### **Problem: Docker command not found**

```bash
# Install Docker Desktop nếu chưa cài
# Hoặc cài Docker CLI trong WSL:
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
sudo newgrp docker

# Verify
docker --version
```

### **Problem: Cannot clone from GitHub**

```bash
# If authentication fails, setup SSH keys
ssh-keygen -t ed25519 -C "your.email@example.com"

# Add key to GitHub
cat ~/.ssh/id_ed25519.pub
# Copy output to GitHub → Settings → SSH Keys

# Clone with SSH
git clone git@github.com:andinagolay198-prog/graphic_network.git
```

### **Problem: Containers won't start**

```bash
# Check logs
docker-compose logs postgres

# Reset containers
docker-compose down
docker volume prune -f

# Rebuild
docker-compose up -d

# Check status
docker-compose ps
```

### **Problem: Port already in use**

```bash
# Find process using port 3000
sudo lsof -i :3000

# Kill process
sudo kill -9 <PID>

# Or change port in docker-compose.yml
# ports:
#   - "3001:3000"
```

### **Problem: Out of disk space**

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a --volumes

# Remove unused images
docker image prune -a

# Remove build cache
docker builder prune -a
```

---

## **PHẦN 9: Production Deployment (Bonus)**

### **9.1 Deploy to Server**

**Assumptions: Linux server (Ubuntu 22.04) dengan Docker installed**

```bash
# SSH vào server
ssh user@your-server.com

# Clone repository
git clone https://github.com/andinagolay198-prog/graphic_network.git
cd graphic_network

# Create .env
nano .env
# Edit dengan production values

# Start services
docker-compose up -d

# Setup Nginx reverse proxy
sudo apt-get install -y nginx
sudo nano /etc/nginx/sites-available/topology
# Paste config dengan https

# Start Nginx
sudo systemctl restart nginx

# Check status
docker-compose ps
```

### **9.2 Auto-update Script**

**Tạo file `auto-update.sh`:**

```bash
#!/bin/bash

# Navigate to project
cd ~/projects/graphic_network

# Pull latest
git pull origin main

# Rebuild images
docker-compose build

# Restart services
docker-compose up -d

# Log
echo "✅ Auto-update completed at $(date)" >> update.log

# Send notification (optional)
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Network Topology Manager updated"}'
```

**Setup cron job:**

```bash
# Edit crontab
crontab -e

# Add line (update every day at 2 AM):
0 2 * * * /home/user/projects/graphic_network/auto-update.sh

# Save: Ctrl+O, Enter, Ctrl+X
```

---

## **✅ Checklist**

Setelah setup, verify:

- [ ] Repository di GitHub: https://github.com/andinagolay198-prog/graphic_network
- [ ] Folder di WSL: `~/projects/graphic_network`
- [ ] Files ada: `docker-compose.yml`, `websocket-server.py`, etc.
- [ ] Docker running: `docker ps`
- [ ] Services up: `docker-compose ps`
- [ ] Frontend: http://localhost:3000 ✓
- [ ] Backend: http://localhost:8000/api/health ✓
- [ ] Database: `docker-compose exec postgres psql -U topology_user network_topology`
- [ ] Git configured: `git config --list`
- [ ] Can push to GitHub: `git push -u origin main`

---

## **📚 Quick Reference Commands**

```bash
# GitHub
git clone https://github.com/andinagolay198-prog/graphic_network.git
git add .
git commit -m "message"
git push origin main
git pull origin main
git status
git log --oneline

# Docker
docker-compose up -d              # Start all
docker-compose down               # Stop all
docker-compose ps                 # List containers
docker-compose logs -f            # View logs
docker-compose restart            # Restart all
docker-compose exec [service] bash # Shell

# Verify
curl http://localhost:8000/api/health
curl http://localhost:3000
docker-compose ps
```

---

**Done! 🎉 Setup selesai. Enjoy!**
