# Network Topology Manager - Quick Start Guide

## 🚀 Bắt Đầu Nhanh (5 phút)

### **Cách 1: Docker Compose (Dễ nhất)**

```bash
# 1. Clone hoặc download project
mkdir network-topology-manager
cd network-topology-manager

# 2. Copy files đã tạo vào folder này
# docker-compose.yml, Dockerfile.backend, Dockerfile.frontend, 
# websocket-server.py, network-collector.py, init-db.sql, etc.

# 3. Tạo .env file
cat > .env << 'EOF'
DATABASE_URL=postgresql://topology_user:topology_pass@postgres:5432/network_topology
REDIS_URL=redis://redis:6379/0
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
COLLECTOR_INTERVAL=300
EOF

# 4. Start services
docker-compose up -d

# 5. Wait 30 seconds for services to start
sleep 30

# 6. Check services status
docker-compose ps

# 7. Access ứng dụng
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Grafana: http://localhost:3001
# Prometheus: http://localhost:9090
```

### **Cách 2: Local Development**

```bash
# 1. Install Python & Node.js
python --version  # >= 3.9
node --version    # >= 16

# 2. Setup Backend
pip install -r requirements.txt
python websocket_server.py

# 3. Setup Frontend (new terminal)
npm install
npm start

# 4. Setup Database (new terminal)
# Tạo PostgreSQL database
createdb network_topology -U postgres

# Run database migrations
psql network_topology -f init-db.sql

# 5. Run Data Collector (new terminal)
python network_collector.py
```

---

## 📊 Application UI Overview

### **Dashboard Utama**
```
┌─────────────────────────────────────────────────────────┐
│  Left Sidebar          │      Main Canvas        │  Right Panel │
│  (Device List)         │   (Topology Graph)      │ (Device Info)│
│                        │                         │              │
│ Search bar             │     [Devices & Links]   │ Selected Dev │
│ Filter (All/Up/Down)   │   [Interactive Canvas]  │   - Details  │
│ Device list            │                         │   - Metrics  │
│ - Status indicator     │ [Drag devices to move]  │   - Actions  │
│ - Click to select      │ [Click to connect]      │              │
└─────────────────────────────────────────────────────────┘
```

### **Fitur Utama**
- ✅ **Interactive Topology Graph** - Drag & drop devices
- ✅ **Real-time Metrics** - CPU, Memory, Traffic updates
- ✅ **Device Status** - UP/DOWN indicators
- ✅ **Connection Types** - Wired, Tunnel, Wireless
- ✅ **Link Bandwidth** - Show bandwidth per link
- ✅ **Device Details** - Info & metrics on click
- ✅ **Search & Filter** - Find devices quickly
- ✅ **Export** - Download topology as JSON

---

## 🔧 Configuration

### **Tambah Device Baru**

Edit file `config/devices.yml`:

```yaml
devices:
  - id: my-router-1
    name: "My Router"
    type: router
    vendor: mikrotik              # or cisco, fortinet, sophos
    ip: 192.168.1.100
    credentials:
      username: admin
      password: "your_password"
      port: 22
    monitoring:
      enabled: true
      interval: 300
```

### **Konfigurasi Metrics**

Dalam `websocket_server.py`, section `simulate_metrics_update()`:

```python
# Edit metrics yang ingin dipantau
devices = [
    {
        "id": "core-1",
        "cpu_usage": random.randint(30, 60),
        "memory_usage": random.randint(50, 70),
        "interface_1_rx": random.randint(10, 100),
    }
]
```

---

## 🌐 API Examples

### **Get Topology**
```bash
curl http://localhost:8000/api/topology
```

### **Get Devices**
```bash
curl http://localhost:8000/api/devices
curl http://localhost:8000/api/devices/core-1
```

### **WebSocket Connection**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/topology');

ws.onopen = () => {
  console.log('Connected!');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};

ws.send(JSON.stringify({
  type: 'request_update'
}));
```

---

## 📋 Project Structure

```
network-topology-manager/
├── docker-compose.yml          # Docker configuration
├── requirements.txt            # Python dependencies
├── init-db.sql                 # Database schema
│
├── # Backend
├── websocket_server.py         # FastAPI server
├── network_collector.py        # Device data collector
├── Dockerfile.backend          # Backend container
│
├── # Frontend
├── network-topology-app.jsx    # React component
├── Dockerfile.frontend         # Frontend container
├── nginx.conf                  # Nginx reverse proxy
│
├── # Configuration
├── config/
│   ├── devices.yml            # Device list
│   └── credentials.yml        # Credentials (gitignored)
│
├── # Documentation
├── SETUP_GUIDE.md             # Detailed setup guide
└── QUICK_START.md             # This file
```

---

## 🆘 Troubleshooting

### **Problem: Cannot access http://localhost:3000**
```bash
# Check if frontend is running
docker-compose ps

# Check frontend logs
docker-compose logs frontend

# Restart frontend
docker-compose restart frontend
```

### **Problem: Backend API not responding**
```bash
# Check backend logs
docker-compose logs backend

# Test API
curl http://localhost:8000/api/health

# Restart backend
docker-compose restart backend
```

### **Problem: Database connection error**
```bash
# Check PostgreSQL
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
docker-compose exec postgres psql -U topology_user -f /init-db.sql
```

### **Problem: WebSocket not connecting**
```bash
# Test WebSocket connection
wscat -c ws://localhost:8000/ws/topology

# Check browser console for errors
# Clear browser cache (Ctrl+Shift+Delete)
```

---

## 📱 Sample Devices

App sudah include sample devices. Untuk menambah device sendiri:

### **Mikrotik Router**
```yaml
- id: mikrotik-1
  name: "Mikrotik Router"
  ip: 192.168.1.1
  vendor: mikrotik
  credentials:
    username: admin
    password: "your_password"
```

### **Cisco Switch**
```yaml
- id: cisco-1
  name: "Cisco Switch"
  ip: 192.168.2.1
  vendor: cisco
  credentials:
    snmp_community: "public"
```

### **Fortinet Firewall**
```yaml
- id: fortinet-1
  name: "FortiGate Firewall"
  ip: 192.168.1.3
  vendor: fortinet
  credentials:
    api_key: "your_api_key"
```

### **Sophos Firewall**
```yaml
- id: sophos-1
  name: "Sophos Firewall"
  ip: 192.168.1.4
  vendor: sophos
  credentials:
    api_key: "your_api_key"
    api_token: "your_token"
```

---

## 🔐 Security Tips

1. **Change Default Passwords**
   ```bash
   docker-compose exec postgres psql -U postgres
   ALTER USER topology_user WITH PASSWORD 'strong_password';
   ```

2. **Use HTTPS in Production**
   - Add Nginx reverse proxy with SSL
   - Use Let's Encrypt for certificates

3. **Secure Credentials**
   - Use environment variables
   - Never commit `credentials.yml` to git
   - Use `.gitignore`:
     ```
     credentials.yml
     .env
     *.key
     *.pem
     ```

4. **Network Access Control**
   ```bash
   # Only allow local network
   ufw allow from 192.168.0.0/16 to any port 8000
   ```

---

## 📈 Performance Tips

1. **Reduce Collector Interval** (if server has good resources)
   ```env
   COLLECTOR_INTERVAL=60  # Collect every 60 seconds instead of 300
   ```

2. **Archive Old Data**
   ```bash
   docker-compose exec postgres psql -U topology_user -d network_topology
   DELETE FROM device_metrics WHERE measured_at < NOW() - INTERVAL '30 days';
   ```

3. **Enable Caching**
   - Already using Redis in docker-compose.yml
   - Data cached for 5 minutes

---

## 🎯 Next Steps

1. **Deploy to Production**
   - Follow SETUP_GUIDE.md for detailed setup
   - Configure SSL/HTTPS
   - Setup backups

2. **Customize Dashboard**
   - Modify colors in `network-topology-app.jsx`
   - Add more metrics in `websocket_server.py`
   - Create custom views

3. **Add More Devices**
   - Edit `config/devices.yml`
   - Support for Ubiquiti, Netgate, etc. coming

4. **Setup Monitoring Alerts**
   - Configure alert thresholds
   - Send notifications (email, Slack, etc.)

---

## 📚 Documentation Files

- **SETUP_GUIDE.md** - Detailed installation & configuration
- **network-collector.py** - Device data collection logic
- **websocket_server.py** - API & WebSocket server
- **network-topology-app.jsx** - React frontend component

---

## 💡 Support

- Check logs: `docker-compose logs -f`
- Read SETUP_GUIDE.md for detailed troubleshooting
- Modify files in `config/` folder for custom settings
- Edit `network-topology-app.jsx` to customize UI

---

## ⚡ Quick Commands

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Rebuild images
docker-compose up -d --build

# Execute command in container
docker-compose exec backend bash

# Database backup
docker-compose exec postgres pg_dump -U topology_user network_topology > backup.sql

# Database restore
docker-compose exec postgres psql -U topology_user network_topology < backup.sql
```

---

**Happy Networking! 🌐**

Enjoy your Network Topology Manager!
