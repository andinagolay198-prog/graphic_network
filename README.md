# Network Topology Manager 🌐

**Interactive Network Topology Visualization & Real-time Monitoring for Mikrotik, Cisco, Fortinet, Sophos**

[![Docker](https://img.shields.io/badge/Docker-Supported-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-green)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18+-blue)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## ✨ Features

### 🎨 **Interactive Topology Visualization**
- Drag & drop network devices
- Real-time device status (UP/DOWN)
- Connection visualization (wired, tunnel, wireless)
- Link bandwidth display
- Auto-layout support

### 📊 **Real-time Monitoring**
- Live CPU & Memory usage
- Interface traffic metrics
- Device uptime tracking
- Session/connection counts
- Temperature monitoring

### 🔌 **Multi-Vendor Support**
- **Mikrotik** - SSH/API
- **Cisco** - SNMP/SSH
- **Fortinet FortiGate** - REST API
- **Sophos** - REST API
- Extensible architecture for more vendors

### 📈 **Advanced Features**
- Historical data with PostgreSQL
- Time-series metrics with InfluxDB (optional)
- Alert system with notifications
- WebSocket real-time updates
- Export topology as JSON
- Device CLI access (SSH terminal)
- Backup & restore database

### 🔒 **Security**
- Role-based access control (Admin, Operator, Viewer)
- Encrypted credentials storage
- HTTPS support with SSL/TLS
- API authentication with tokens
- Audit logging

---

## 🚀 Quick Start

### Prerequisites
- Windows 10/11 with WSL2 enabled
- Docker Desktop installed
- Git installed
- 8GB+ RAM (16GB recommended)

### 5-Minute Setup

```bash
# 1. Clone repository
git clone https://github.com/andinagolay198-prog/graphic_network.git
cd graphic_network

# 2. Create .env file
cat > .env << 'EOF'
DATABASE_URL=postgresql://topology_user:topology_pass@postgres:5432/network_topology
REDIS_URL=redis://redis:6379/0
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
EOF

# 3. Create config folder
mkdir -p config
cat > config/devices.yml << 'EOF'
devices:
  - id: core-1
    name: "Core-Router"
    type: router
    vendor: mikrotik
    ip: 192.168.1.1
    credentials:
      username: admin
      password: "your_password"
EOF

# 4. Start services
docker-compose up -d

# 5. Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

---

## 📖 Documentation

### Setup & Installation
- **[QUICK_START.md](QUICK_START.md)** - 5 minute setup guide
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed installation & configuration
- **[GITHUB_WORKFLOW.md](GITHUB_WORKFLOW.md)** - GitHub & WSL2 Docker workflow

### Configuration
- **[config/devices.yml](config/devices.yml)** - Device configuration
- **[.env.example](.env.example)** - Environment variables

### Architecture
- **Frontend**: React.js with Canvas
- **Backend**: FastAPI + WebSocket
- **Database**: PostgreSQL + InfluxDB (optional)
- **Cache**: Redis
- **Monitoring**: Prometheus + Grafana (optional)

---

## 🔧 Configuration

### Add Network Devices

Edit `config/devices.yml`:

```yaml
devices:
  # Mikrotik Router
  - id: router-1
    name: "Mikrotik Router"
    type: router
    vendor: mikrotik
    ip: 192.168.1.1
    credentials:
      username: admin
      password: "password123"
      port: 22

  # Cisco Switch
  - id: switch-1
    name: "Cisco Switch"
    type: switch
    vendor: cisco
    ip: 192.168.2.1
    credentials:
      snmp_community: "public"
      snmp_port: 161

  # Fortinet Firewall
  - id: firewall-1
    name: "FortiGate"
    type: firewall
    vendor: fortinet
    ip: 192.168.1.3
    credentials:
      api_key: "your_api_key"

  # Sophos Firewall
  - id: firewall-2
    name: "Sophos"
    type: firewall
    vendor: sophos
    ip: 192.168.1.4
    credentials:
      api_key: "your_api_key"
```

Restart services:
```bash
docker-compose restart backend
```

---

## 🌐 API Endpoints

### REST API
```bash
# Get topology
curl http://localhost:8000/api/topology

# Get devices
curl http://localhost:8000/api/devices
curl http://localhost:8000/api/devices/{device_id}

# Get metrics
curl http://localhost:8000/api/devices/{device_id}/metrics

# Get links
curl http://localhost:8000/api/links

# Health check
curl http://localhost:8000/api/health
```

### WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/topology');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📊 Application Screenshots

### Dashboard
- Left Sidebar: Device list with search/filter
- Main Canvas: Interactive topology graph
- Right Panel: Selected device details & metrics

### Features
- Real-time status indicators
- Network traffic visualization
- Drag & drop device positioning
- Click for device details
- Bandwidth per link
- Tunnel/VPN connections

---

## 🐳 Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| frontend | 3000 | React UI |
| backend | 8000 | FastAPI Server |
| postgres | 5432 | Database |
| redis | 6379 | Cache |
| grafana | 3001 | Metrics (optional) |
| prometheus | 9090 | Monitoring (optional) |
| influxdb | 8086 | Time-series (optional) |

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View services
docker-compose ps

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild images
docker-compose up -d --build
```

---

## 📁 Project Structure

```
graphic_network/
├── README.md                      # This file
├── QUICK_START.md                # Quick setup guide
├── SETUP_GUIDE.md                # Detailed setup
├── GITHUB_WORKFLOW.md            # GitHub workflow
│
├── # Core Files
├── docker-compose.yml            # Docker configuration
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
│
├── # Backend
├── websocket_server.py           # FastAPI + WebSocket
├── network_collector.py          # Device data collectors
├── Dockerfile.backend            # Backend container
│
├── # Frontend
├── network-topology-app.jsx      # React component
├── Dockerfile.frontend           # Frontend container
├── nginx.conf                    # Nginx config
│
├── # Configuration
├── config/
│   ├── devices.yml              # Device list
│   └── .gitkeep
│
├── # Database
├── init-db.sql                  # PostgreSQL schema
│
└── # Documentation
    └── backups/                 # Database backups
```

---

## 🔐 Security Considerations

1. **Change Default Passwords**
   ```bash
   # PostgreSQL
   docker-compose exec postgres psql -U postgres
   ALTER USER topology_user WITH PASSWORD 'strong_password';
   ```

2. **Use HTTPS in Production**
   - Configure Nginx reverse proxy with SSL
   - Use Let's Encrypt certificates

3. **Secure Credentials**
   - Store sensitive data in `.env` (add to `.gitignore`)
   - Use environment variables for secrets
   - Rotate API keys regularly

4. **Network Security**
   - Limit access to admin panel
   - Use firewalls for SSH/API access
   - Enable SNMP v3 with authentication

5. **Backup Strategy**
   ```bash
   # Daily backup
   docker-compose exec postgres pg_dump -U topology_user network_topology > backup.sql
   ```

---

## 🆘 Troubleshooting

### Container won't start
```bash
docker-compose logs backend
docker-compose down -v
docker-compose up -d
```

### Cannot connect to database
```bash
docker-compose exec postgres psql -U topology_user network_topology
```

### WebSocket connection failed
```bash
curl http://localhost:8000/api/health
docker-compose logs -f backend
```

### Port already in use
```bash
sudo lsof -i :3000
sudo kill -9 <PID>
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for more troubleshooting.

---

## 🚀 Performance Tips

1. Reduce collector interval for faster updates
2. Archive old metrics data periodically
3. Use Redis caching for frequently accessed data
4. Enable InfluxDB for better time-series performance
5. Monitor resource usage: `docker stats`

---

## 📈 Roadmap

- [ ] Web-based SSH terminal
- [ ] Advanced alert rules
- [ ] Multi-site monitoring
- [ ] Mobile app
- [ ] Packet capture integration
- [ ] Traffic matrix view
- [ ] Ansible integration
- [ ] NetFlow/sFlow support

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add feature'`
4. Push branch: `git push origin feature/my-feature`
5. Submit pull request

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file

---

## 📞 Support

- 📖 Documentation: See `/docs` folder
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions
- 📧 Email: your.email@example.com

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://reactjs.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [Docker](https://www.docker.com/)
- [Redis](https://redis.io/)

---

## 📊 Status

- ✅ Core functionality complete
- ✅ Docker deployment ready
- ✅ Multi-vendor support
- 🟡 Production testing in progress
- 🔄 Continuous improvements

---

**Last Updated:** March 2026

**Made with ❤️ for Network Engineers**
