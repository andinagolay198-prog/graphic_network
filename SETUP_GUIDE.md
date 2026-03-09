# Network Topology Manager - Setup & Configuration Guide

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Application](#running)
5. [API Reference](#api-reference)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- Docker & Docker Compose (recommended)
- Python 3.9+ (for development)
- Node.js 16+ (for development)
- PostgreSQL 12+ (if not using Docker)
- Redis 6+ (if not using Docker)

### Network Requirements
- SSH access to network devices (for Mikrotik, Cisco)
- SNMP access (default community: public, port 161)
- API access (for Fortinet FortiGate, Sophos)
- HTTP/HTTPS access to web interfaces

---

## Installation

### Option 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/network-topology-manager.git
cd network-topology-manager

# Copy environment file
cp .env.example .env

# Edit configuration (see Configuration section)
nano .env

# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Grafana: http://localhost:3001
# Prometheus: http://localhost:9090
```

### Option 2: Local Development Setup

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start backend
python -m uvicorn websocket_server:app --reload --host 0.0.0.0 --port 8000

# Frontend setup (in new terminal)
cd frontend
npm install
npm start
```

---

## Configuration

### .env File

```env
# Database
DATABASE_URL=postgresql://topology_user:topology_pass@postgres:5432/network_topology
REDIS_URL=redis://redis:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Collector Configuration
COLLECTOR_INTERVAL=300  # Collect data every 5 minutes
COLLECTOR_TIMEOUT=30

# Device Configuration (see devices.yml)
DEVICES_CONFIG_PATH=/app/config/devices.yml
```

### devices.yml - Device Configuration

```yaml
devices:
  # Mikrotik Router
  - id: core-1
    name: "Core-Router-1"
    type: router
    vendor: mikrotik
    ip: 192.168.1.1
    credentials:
      username: admin
      password: "${MIKROTIK_PASS}"
      port: 22
    monitoring:
      enabled: true
      interval: 300  # seconds
      metrics:
        - cpu_usage
        - memory_usage
        - interface_traffic
        - connections
    location: "Data Center"

  # Cisco Switch
  - id: sw-1
    name: "Switch-Main"
    type: switch
    vendor: cisco
    ip: 192.168.2.1
    credentials:
      snmp_version: "3"
      snmp_community: "public"
      snmp_port: 161
    monitoring:
      enabled: true
      interval: 300
      metrics:
        - cpu_usage
        - memory_usage
        - interface_status
        - vlan_info

  # Fortinet FortiGate Firewall
  - id: fw-1
    name: "Firewall-Primary"
    type: firewall
    vendor: fortinet
    ip: 192.168.1.3
    credentials:
      api_key: "${FORTINET_API_KEY}"
      port: 443
    monitoring:
      enabled: true
      interval: 300
      metrics:
        - cpu_usage
        - memory_usage
        - session_count
        - threat_detection
        - vpn_status

  # Sophos XG Firewall
  - id: fw-2
    name: "Firewall-Secondary"
    type: firewall
    vendor: sophos
    ip: 192.168.1.4
    credentials:
      api_key: "${SOPHOS_API_KEY}"
      api_token: "${SOPHOS_API_TOKEN}"
    monitoring:
      enabled: true
      interval: 300
      metrics:
        - cpu_usage
        - memory_usage
        - threat_stats
        - vpn_connections

# Link relationships
links:
  - from: core-1
    to: sw-1
    type: wired
    bandwidth: 1Gbps
  
  - from: core-1
    to: fw-1
    type: wired
    bandwidth: 1Gbps
  
  - from: fw-1
    to: fw-2
    type: tunnel
    tunnel_type: ipsec
    bandwidth: 500Mbps
```

### credentials.yml - Secure Credentials Storage

```yaml
mikrotik:
  admin_pass: "your_mikrotik_password"

cisco:
  snmp_community: "public"
  enable_password: "your_enable_pass"

fortinet:
  api_key: "your_fortinet_api_key"
  api_vdom: "root"

sophos:
  api_key: "your_sophos_api_key"
  api_token: "your_sophos_token"
```

**⚠️ Security Note:** Never commit credentials.yml to version control. Use environment variables instead:

```bash
export MIKROTIK_PASS="password"
export FORTINET_API_KEY="key"
export SOPHOS_API_KEY="key"
```

---

## Running the Application

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down

# Rebuild images
docker-compose up -d --build
```

### Manual Start (Development)

```bash
# Terminal 1: PostgreSQL + Redis
docker run --name topology-postgres -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:15
docker run --name topology-redis -p 6379:6379 redis:7

# Terminal 2: Backend
cd backend
python -m uvicorn websocket_server:app --reload

# Terminal 3: Frontend
cd frontend
npm start

# Terminal 4: Data Collector
cd backend
python network_collector.py
```

### Systemd Service (Production)

Create `/etc/systemd/system/network-topology.service`:

```ini
[Unit]
Description=Network Topology Manager
After=network.target docker.service

[Service]
Type=simple
ExecStart=/usr/bin/docker-compose -f /opt/network-topology-manager/docker-compose.yml up
ExecStop=/usr/bin/docker-compose -f /opt/network-topology-manager/docker-compose.yml down
Restart=always
User=docker

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable network-topology
sudo systemctl start network-topology
sudo systemctl status network-topology
```

---

## API Reference

### REST API Endpoints

#### Get Topology
```bash
GET /api/topology
# Response:
{
  "devices": [...],
  "links": [...],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Get Devices
```bash
GET /api/devices
GET /api/devices/{device_id}
```

#### Get Device Metrics
```bash
GET /api/devices/{device_id}/metrics?period=24h
# Response:
{
  "cpu_usage": [...],
  "memory_usage": [...],
  "timestamp": [...]
}
```

#### Get Links
```bash
GET /api/links
GET /api/links/{link_id}
```

#### Get Link Traffic
```bash
GET /api/links/{link_id}/traffic?period=1h
```

#### Alerts
```bash
GET /api/alerts
GET /api/alerts?severity=critical
POST /api/alerts/{alert_id}/acknowledge
POST /api/alerts/{alert_id}/resolve
```

#### Device Control
```bash
POST /api/devices/{device_id}/reboot
POST /api/devices/{device_id}/config
GET /api/devices/{device_id}/terminal  # SSH access
```

### WebSocket Events

#### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/topology');

ws.onopen = () => {
  console.log('Connected to topology stream');
};
```

#### Subscribe to Device Updates
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  device_id: 'core-1'
}));

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'metrics_update') {
    console.log('Device metrics:', data.metrics);
  } else if (data.type === 'alert') {
    console.log('Alert:', data.data);
  }
};
```

---

## Troubleshooting

### Cannot Connect to Device

```bash
# Check device accessibility
ping 192.168.1.1

# Check SSH access
ssh admin@192.168.1.1

# Check SNMP
snmpwalk -v2c -c public 192.168.1.1 sysUpTime

# Check API access
curl -k -H "Authorization: Bearer API_KEY" https://192.168.1.3/api/v2/monitor/system/interface
```

### Database Connection Error

```bash
# Check PostgreSQL container
docker-compose logs postgres

# Verify database exists
docker-compose exec postgres psql -U topology_user -d network_topology -c "\dt"

# Reset database
docker-compose down -v
docker-compose up -d postgres
docker-compose exec postgres psql -U topology_user -f /init-db.sql
```

### WebSocket Not Connecting

```bash
# Check backend health
curl http://localhost:8000/api/health

# Check WebSocket endpoint
wscat -c ws://localhost:8000/ws/topology

# Check browser console for errors
# Clear browser cache and reload
```

### High CPU/Memory Usage

1. Reduce collector interval in .env
2. Disable unused metrics
3. Archive old data in PostgreSQL
4. Check for runaway processes: `docker-compose top backend`

### Device Showing as DOWN

1. Verify network connectivity
2. Check credentials in devices.yml
3. Verify firewall rules allow access
4. Check device logs: `ssh admin@device_ip`
5. Increase timeout in configuration

---

## Performance Tuning

### PostgreSQL Optimization

```sql
-- Enable query optimizer stats
ANALYZE;

-- Vacuum and analyze
VACUUM ANALYZE;

-- Increase shared buffers (in postgresql.conf)
shared_buffers = 256MB

-- Enable connection pooling with PgBouncer
```

### Redis Caching

```python
# Set cache TTL for metrics
cache.set(f"device:{device_id}:metrics", metrics, ttl=300)
```

### InfluxDB for Time-Series

```bash
# Query recent metrics
influx query 'from(bucket:"network_metrics") 
  |> range(start: -1h) 
  |> filter(fn: (r) => r["device_id"] == "core-1")'
```

---

## Security Considerations

1. **Change Default Passwords**
   ```bash
   # PostgreSQL
   psql -U postgres -d network_topology -c "ALTER USER topology_user WITH PASSWORD 'strong_password';"
   ```

2. **Use HTTPS**
   - Add reverse proxy (Nginx/Caddy)
   - Generate SSL certificates (Let's Encrypt)

3. **API Authentication**
   ```bash
   # Generate API key for external integrations
   curl -X POST http://localhost:8000/api/auth/keys \
     -H "Authorization: Bearer admin_token" \
     -d '{"name": "external_app"}'
   ```

4. **Firewall Rules**
   ```bash
   # Only allow internal network access
   ufw allow from 192.168.0.0/16 to any port 8000
   ```

5. **Backup Database**
   ```bash
   docker-compose exec postgres pg_dump -U topology_user network_topology > backup.sql
   ```

---

## Support & Community

- Documentation: https://docs.example.com
- Issues: https://github.com/yourusername/network-topology-manager/issues
- Discussions: https://github.com/yourusername/network-topology-manager/discussions
- Email: support@example.com

---

## License

MIT License - See LICENSE file for details
