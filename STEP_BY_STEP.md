# 🚀 STEP-BY-STEP: Upload GitHub & Run Docker (30 phút)

## **📋 BƯỚC 1: Upload lên GitHub (Windows - 10 phút)**

### 1️⃣ Mở Command Prompt/PowerShell

```powershell
# Vào folder project
cd D:\GRAPHIC NETWORK

# Kiểm tra git đã cài chưa
git --version

# Nếu chưa cài, download tại: https://git-scm.com/download/win
```

### 2️⃣ Initialize Git Repository

```powershell
# Tạo git repo local
git init

# Add remote (GitHub)
git remote add origin https://github.com/andinagolay198-prog/graphic_network.git

# Kiểm tra
git remote -v
```

### 3️⃣ Configure Git (First time only)

```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 4️⃣ Add & Commit Files

```powershell
# Show files sẽ upload
git status

# Add tất cả
git add .

# Commit
git commit -m "Initial commit: Network Topology Manager with visualization"

# Check commit
git log --oneline
```

### 5️⃣ Push lên GitHub

```powershell
# Push lần đầu
git push -u origin main

# Nếu có yêu cầu password, paste Personal Access Token
# (tạo tại: GitHub → Settings → Developer settings → Personal access tokens)

# Xác nhận: Mở https://github.com/andinagolay198-prog/graphic_network
# Sẽ thấy tất cả files
```

---

## **🐧 BƯỚC 2: Clone & Setup Ubuntu Docker (20 phút)**

### 1️⃣ Mở Ubuntu Terminal (WSL2)

**Cách 1:** Windows Terminal → Click dropdown → Ubuntu-22.04

**Cách 2:** PowerShell
```powershell
wsl
```

**Cách 3:** Search "Ubuntu" → Open

### 2️⃣ Clone từ GitHub

```bash
# Vào home folder
cd ~

# Tạo projects folder
mkdir -p projects
cd projects

# Clone repo
git clone https://github.com/andinagolay198-prog/graphic_network.git

# Enter folder
cd graphic_network

# Kiểm tra files
ls -la
```

### 3️⃣ Tạo .env file

```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql://topology_user:topology_pass@postgres:5432/network_topology
REDIS_URL=redis://redis:6379/0
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
COLLECTOR_INTERVAL=300
EOF

# Verify
cat .env
```

### 4️⃣ Tạo Config Folders

```bash
# Create folders
mkdir -p config
mkdir -p collectors

# Create sample devices.yml
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
EOF

# Verify
ls -la config/
```

### 5️⃣ Check Docker Installation

```bash
# Verify Docker
docker --version
# Output: Docker version 24.x.x

# Verify Docker Compose
docker-compose --version
# Output: Docker Compose version 2.x.x

# Test
docker run hello-world
```

---

## **🏗️ BƯỚC 3: Build & Run Services (10 phút)**

### 1️⃣ Build Docker Images

```bash
# Ensure in project folder
cd ~/projects/graphic_network

# Build all images
docker-compose build

# Wait 5-10 minutes...
# You'll see: "=> naming to docker.io/library/graphic-network-backend"
```

### 2️⃣ Start All Services

```bash
# Start containers
docker-compose up -d

# Check services are running
docker-compose ps

# Expected output:
# NAME                    STATUS              PORTS
# graphic-network-backend Up 10 seconds        0.0.0.0:8000->8000/tcp
# graphic-network-frontend Up 10 seconds       0.0.0.0:3000->3000/tcp
# topology-postgres       Up 10 seconds        0.0.0.0:5432->5432/tcp
# topology-redis          Up 10 seconds        0.0.0.0:6379->6379/tcp
```

### 3️⃣ Verify Services

```bash
# Test backend
curl http://localhost:8000/api/health
# Output: {"status":"ok",...}

# Test PostgreSQL
docker-compose exec postgres psql -U topology_user -d network_topology -c "SELECT COUNT(*) FROM devices;"
# Output: count = 6

# Test Redis
docker-compose exec redis redis-cli ping
# Output: PONG
```

---

## **🌐 BƯỚC 4: Access Application (Windows Browser)**

### 1️⃣ Open in Browser

Mở Windows browser (Chrome, Firefox, Edge):

```
Frontend:     http://localhost:3000       ← Main UI
Backend API:  http://localhost:8000       ← API
API Docs:     http://localhost:8000/docs  ← Swagger documentation
Grafana:      http://localhost:3001       ← Metrics (optional)
Prometheus:   http://localhost:9090       ← Monitoring (optional)
```

### 2️⃣ Frontend Display

Bạn sẽ thấy:
- **Left sidebar:** Device list (6 sample devices)
- **Main canvas:** Topology graph (devices + connections)
- **Right panel:** Selected device details
- **Status:** Green (UP) / Red (DOWN) indicators

### 3️⃣ Test Interactions

- Click device → Right panel shows details
- Drag device → Move around canvas
- Toggle "Show Labels" → Hide/show names & IPs
- Filter (All/Up/Down) → Filter devices

---

## **📝 BƯỚC 5: Configuration (Optional)**

### 1️⃣ Add Real Devices

Edit `config/devices.yml`:

```bash
# Ubuntu Terminal
cd ~/projects/graphic_network

# Edit file
nano config/devices.yml

# Add your actual devices (Mikrotik, Cisco, Fortinet, Sophos)
# Example:
# - id: my-router
#   name: "My Mikrotik Router"
#   type: router
#   vendor: mikrotik
#   ip: 192.168.1.100
#   credentials:
#     username: admin
#     password: "actual_password"

# Save: Ctrl+O, Enter, Ctrl+X
```

### 2️⃣ Reload Services

```bash
# Restart backend to load new config
docker-compose restart backend

# Check logs
docker-compose logs -f backend
```

---

## **🔄 BƯỚC 6: Daily Workflow**

### 1️⃣ Update from GitHub

```bash
cd ~/projects/graphic_network

# Pull latest changes
git pull origin main

# Rebuild if needed
docker-compose build

# Restart
docker-compose up -d
```

### 2️⃣ Make Changes & Push

```bash
cd ~/projects/graphic_network

# Make changes
# nano websocket_server.py
# nano network-topology-app.jsx
# etc.

# Check status
git status

# Add & commit
git add .
git commit -m "Update: description"

# Push to GitHub
git push origin main
```

### 3️⃣ View Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Exit: Ctrl+C
```

### 4️⃣ Stop/Start Services

```bash
# Stop all
docker-compose stop

# Start all
docker-compose start

# Restart specific
docker-compose restart backend

# Stop everything (keep data)
docker-compose down

# Stop everything (delete data)
docker-compose down -v
```

---

## **💾 BƯỚC 7: Backup**

### 1️⃣ Backup Database

```bash
# Create backup folder
mkdir -p backups

# Backup
docker-compose exec postgres pg_dump -U topology_user network_topology > backups/backup-$(date +%Y%m%d-%H%M%S).sql

# Check
ls -lah backups/
```

### 2️⃣ Restore Database

```bash
# List backups
ls backups/

# Restore
docker-compose exec postgres psql -U topology_user network_topology < backups/backup-20240309-143020.sql
```

---

## **🆘 BƯỚC 8: Troubleshooting Quick Fixes**

### ❌ "docker: command not found"
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
```

### ❌ "Cannot connect to localhost:3000"
```bash
docker-compose ps
docker-compose logs frontend
docker-compose restart frontend
```

### ❌ "Database connection error"
```bash
docker-compose logs postgres
docker-compose down -v
docker-compose up -d postgres
sleep 10
```

### ❌ "WebSocket not connecting"
```bash
curl http://localhost:8000/api/health
docker-compose logs -f backend
```

### ❌ "Port already in use"
```bash
# Find & kill process
sudo lsof -i :3000
sudo kill -9 <PID>
```

---

## **✅ QUICK CHECKLIST**

After setup, verify:

```
☑ GitHub repo created: https://github.com/andinagolay198-prog/graphic_network
☑ Files uploaded to GitHub
☑ WSL Ubuntu folder: ~/projects/graphic_network
☑ .env file created
☑ Docker running: docker ps
☑ Services up: docker-compose ps (4 containers)
☑ Frontend: http://localhost:3000 opens ✓
☑ Backend API: curl http://localhost:8000/api/health works
☑ Database: Shows 6 devices
☑ Git configured: git config --list works
☑ Can push: git push origin main works
```

---

## **🎯 NEXT STEPS**

1. **Customize Devices**
   - Edit `config/devices.yml`
   - Add your real network devices
   - Provide credentials (SSH, SNMP, API keys)
   - Restart backend

2. **Monitor in Real-time**
   - Open http://localhost:3000
   - Watch live topology updates
   - Check metrics in right panel
   - View alerts

3. **Deploy to Production** (Optional)
   - Follow SETUP_GUIDE.md
   - Configure HTTPS
   - Setup SSL certificates
   - Enable backups

4. **Extend Features**
   - Modify `network-topology-app.jsx` for UI changes
   - Update `websocket_server.py` for API changes
   - Commit & push to GitHub

---

## **📚 IMPORTANT FILES**

- `README.md` - Project overview
- `QUICK_START.md` - Quick setup (5 min)
- `SETUP_GUIDE.md` - Detailed setup
- `GITHUB_WORKFLOW.md` - GitHub & Docker workflow
- `docker-compose.yml` - Docker configuration
- `config/devices.yml` - Your network devices
- `.env` - Environment variables

---

## **🎉 YOU'RE DONE!**

Network Topology Manager running on WSL2 Ubuntu Docker! 🚀

**Summary:**
- ✅ Files uploaded to GitHub
- ✅ Repository cloned to WSL
- ✅ Docker services running
- ✅ Application accessible at http://localhost:3000
- ✅ Ready for production use

**Enjoy your Network Topology Manager!** 🌐
