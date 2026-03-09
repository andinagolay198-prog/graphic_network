"""
Network Topology Data Collector
Hỗ trợ: Mikrotik, Cisco, Fortinet, Sophos
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import paramiko
import requests
from pysnmp.hlapi import (
    SnmpEngine, CommunityData, UdpTransportTarget,
    ObjectIdentity, ObjectType, getCmd, bulkCmd
)


class DeviceType(Enum):
    ROUTER = "router"
    FIREWALL = "firewall"
    SWITCH = "switch"
    AP = "ap"
    MODEM = "modem"


class Vendor(Enum):
    MIKROTIK = "mikrotik"
    CISCO = "cisco"
    FORTINET = "fortinet"
    SOPHOS = "sophos"
    GENERIC = "generic"


@dataclass
class Device:
    id: str
    name: str
    type: DeviceType
    ip: str
    vendor: Vendor
    status: str = "down"
    uptime: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    temperature: float = 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'ip': self.ip,
            'vendor': self.vendor.value,
            'status': self.status,
            'uptime': self.uptime,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'temperature': self.temperature,
        }


@dataclass
class Link:
    from_device: str
    to_device: str
    link_type: str  # "wired", "tunnel", "wireless"
    bandwidth: str
    status: str
    rx_bytes: int = 0
    tx_bytes: int = 0

    def to_dict(self):
        return {
            'from': self.from_device,
            'to': self.to_device,
            'type': self.link_type,
            'bandwidth': self.bandwidth,
            'status': self.status,
            'rx_bytes': self.rx_bytes,
            'tx_bytes': self.tx_bytes,
        }


class BaseCollector:
    """Base class cho tất cả collectors"""
    
    def __init__(self, ip: str, device_id: str, device_name: str):
        self.ip = ip
        self.device_id = device_id
        self.device_name = device_name

    async def collect(self) -> Optional[Device]:
        raise NotImplementedError

    async def get_links(self) -> List[Link]:
        raise NotImplementedError


class SNMPCollector(BaseCollector):
    """SNMP Collector - dùng cho Cisco, generic devices"""
    
    def __init__(self, ip: str, device_id: str, device_name: str, community: str = "public"):
        super().__init__(ip, device_id, device_name)
        self.community = community
        self.engine = SnmpEngine()
        
    def _get_snmp_value(self, oid: str):
        """Lấy giá trị từ SNMP OID"""
        try:
            iterator = getCmd(
                self.engine,
                CommunityData(self.community, mpModel=0),
                UdpTransportTarget((self.ip, 161), timeout=2, retries=0),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                return None
            
            if varBinds:
                return str(varBinds[0][1])
            return None
        except Exception as e:
            print(f"SNMP Error on {self.ip}: {e}")
            return None

    async def collect(self) -> Optional[Device]:
        """Collect device metrics via SNMP"""
        
        # Common SNMP OIDs
        oids = {
            'sysUpTime': '1.3.6.1.2.1.1.3.0',
            'sysDescr': '1.3.6.1.2.1.1.1.0',
            'cpuUsage': '1.3.6.1.4.1.9.9.109.1.1.1.1.5.1',  # Cisco CPU %
            'memUsage': '1.3.6.1.4.1.9.9.109.1.1.1.1.12.1',  # Cisco Memory %
            'ifName': '1.3.6.1.2.1.31.1.1.1.1',
            'ifInOctets': '1.3.6.1.2.1.2.2.1.10',
            'ifOutOctets': '1.3.6.1.2.1.2.2.1.16',
        }

        uptime_raw = self._get_snmp_value(oids['sysUpTime'])
        uptime = int(uptime_raw.split('(')[0]) if uptime_raw else 0

        cpu = float(self._get_snmp_value(oids['cpuUsage']) or 0)
        memory = float(self._get_snmp_value(oids['memUsage']) or 0)

        device = Device(
            id=self.device_id,
            name=self.device_name,
            type=DeviceType.ROUTER,
            ip=self.ip,
            vendor=Vendor.CISCO,
            status="up" if uptime > 0 else "down",
            uptime=uptime,
            cpu_usage=cpu,
            memory_usage=memory,
        )
        
        return device

    async def get_links(self) -> List[Link]:
        """Lấy thông tin link từ SNMP"""
        links = []
        # Implementation phức tạp, cần parse interface data
        return links


class SSHCollector(BaseCollector):
    """SSH Collector - dùng cho Mikrotik, Cisco, Fortinet"""
    
    def __init__(self, ip: str, device_id: str, device_name: str, 
                 username: str, password: str, port: int = 22):
        super().__init__(ip, device_id, device_name)
        self.username = username
        self.password = password
        self.port = port

    async def _ssh_command(self, command: str) -> str:
        """Execute SSH command"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, port=self.port, username=self.username, password=self.password, timeout=5)
            
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode('utf-8')
            ssh.close()
            return output
        except Exception as e:
            print(f"SSH Error on {self.ip}: {e}")
            return ""

    async def collect(self) -> Optional[Device]:
        # Implementation sẽ khác nhau tùy từng vendor
        raise NotImplementedError


class MikrotikCollector(SSHCollector):
    """Mikrotik-specific collector"""
    
    async def collect(self) -> Optional[Device]:
        """Collect từ Mikrotik"""
        
        # Kiểm tra kết nối
        output = await self._ssh_command("system identity print")
        if not output:
            return Device(
                id=self.device_id,
                name=self.device_name,
                type=DeviceType.ROUTER,
                ip=self.ip,
                vendor=Vendor.MIKROTIK,
                status="down"
            )

        # Lấy system info
        uptime_output = await self._ssh_command("system uptime print")
        cpu_output = await self._ssh_command("system resource print")
        
        # Parse CPU/Memory từ output
        cpu = 45.0  # Sample
        memory = 62.0

        device = Device(
            id=self.device_id,
            name=self.device_name,
            type=DeviceType.ROUTER,
            ip=self.ip,
            vendor=Vendor.MIKROTIK,
            status="up",
            cpu_usage=cpu,
            memory_usage=memory,
        )
        
        return device

    async def get_links(self) -> List[Link]:
        """Lấy interface info từ Mikrotik"""
        links = []
        
        # /ip/address print
        output = await self._ssh_command("/ip/address/print")
        # Parse output
        
        # /interface/ethernet/print
        interface_output = await self._ssh_command("/interface/ethernet/print")
        
        return links


class FortnetCollector(BaseCollector):
    """Fortinet FortiGate REST API collector"""
    
    def __init__(self, ip: str, device_id: str, device_name: str, 
                 api_key: str, port: int = 443):
        super().__init__(ip, device_id, device_name)
        self.api_key = api_key
        self.port = port
        self.base_url = f"https://{ip}:{port}"
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {api_key}'})
        self.session.verify = False  # Disable SSL verification (dev only!)

    async def collect(self) -> Optional[Device]:
        """Collect từ FortiGate API"""
        try:
            # System info endpoint
            response = self.session.get(f"{self.base_url}/api/v2/monitor/system/interface")
            
            if response.status_code != 200:
                return Device(
                    id=self.device_id,
                    name=self.device_name,
                    type=DeviceType.FIREWALL,
                    ip=self.ip,
                    vendor=Vendor.FORTINET,
                    status="down"
                )

            # Get performance stats
            perf_response = self.session.get(f"{self.base_url}/api/v2/monitor/system/performance")
            perf_data = perf_response.json().get('results', {})[0] if perf_response.status_code == 200 else {}

            device = Device(
                id=self.device_id,
                name=self.device_name,
                type=DeviceType.FIREWALL,
                ip=self.ip,
                vendor=Vendor.FORTINET,
                status="up",
                cpu_usage=float(perf_data.get('cpu', 0)),
                memory_usage=float(perf_data.get('memory', 0)),
            )
            
            return device
        except Exception as e:
            print(f"Fortinet Error on {self.ip}: {e}")
            return None

    async def get_links(self) -> List[Link]:
        """Lấy interface links dari FortiGate"""
        links = []
        try:
            response = self.session.get(f"{self.base_url}/api/v2/monitor/system/interface")
            interfaces = response.json().get('results', [])
            
            for iface in interfaces:
                # Process interface data
                pass
            
        except Exception as e:
            print(f"Error getting Fortinet links: {e}")
        
        return links


class SophosCollector(BaseCollector):
    """Sophos REST API collector"""
    
    def __init__(self, ip: str, device_id: str, device_name: str, api_key: str):
        super().__init__(ip, device_id, device_name)
        self.api_key = api_key
        self.base_url = f"https://{ip}"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        self.session.verify = False

    async def collect(self) -> Optional[Device]:
        """Collect từ Sophos API"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/system")
            
            if response.status_code != 200:
                return Device(
                    id=self.device_id,
                    name=self.device_name,
                    type=DeviceType.FIREWALL,
                    ip=self.ip,
                    vendor=Vendor.SOPHOS,
                    status="down"
                )

            data = response.json()
            
            device = Device(
                id=self.device_id,
                name=self.device_name,
                type=DeviceType.FIREWALL,
                ip=self.ip,
                vendor=Vendor.SOPHOS,
                status="up",
                cpu_usage=float(data.get('cpu_usage', 0)),
                memory_usage=float(data.get('memory_usage', 0)),
            )
            
            return device
        except Exception as e:
            print(f"Sophos Error on {self.ip}: {e}")
            return None

    async def get_links(self) -> List[Link]:
        """Lấy link info dari Sophos"""
        links = []
        try:
            response = self.session.get(f"{self.base_url}/api/v1/interfaces")
            interfaces = response.json().get('data', [])
            
            for iface in interfaces:
                # Process interface data
                pass
            
        except Exception as e:
            print(f"Error getting Sophos links: {e}")
        
        return links


class NetworkTopologyCollector:
    """Main collector orchestrator"""
    
    def __init__(self):
        self.devices: List[Device] = []
        self.links: List[Link] = []
        self.collectors: Dict[str, BaseCollector] = {}

    def add_device(self, device_config: Dict):
        """Add device collector"""
        device_id = device_config['id']
        ip = device_config['ip']
        name = device_config['name']
        vendor = device_config['vendor'].lower()
        
        if vendor == 'mikrotik':
            collector = MikrotikCollector(
                ip=ip,
                device_id=device_id,
                device_name=name,
                username=device_config.get('username', 'admin'),
                password=device_config.get('password', ''),
            )
        elif vendor == 'cisco':
            collector = SNMPCollector(
                ip=ip,
                device_id=device_id,
                device_name=name,
                community=device_config.get('snmp_community', 'public'),
            )
        elif vendor == 'fortinet':
            collector = FortnetCollector(
                ip=ip,
                device_id=device_id,
                device_name=name,
                api_key=device_config.get('api_key', ''),
            )
        elif vendor == 'sophos':
            collector = SophosCollector(
                ip=ip,
                device_id=device_id,
                device_name=name,
                api_key=device_config.get('api_key', ''),
            )
        else:
            collector = SNMPCollector(ip, device_id, name)
        
        self.collectors[device_id] = collector

    async def collect_all(self):
        """Collect từ tất cả devices"""
        tasks = [
            collector.collect() 
            for collector in self.collectors.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.devices = [r for r in results if isinstance(r, Device) and r is not None]
        return self.devices

    async def collect_links(self):
        """Collect link info từ tất cả devices"""
        tasks = [
            collector.get_links() 
            for collector in self.collectors.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.links = []
        for result in results:
            if isinstance(result, list):
                self.links.extend(result)
        
        return self.links

    async def collect(self):
        """Collect all data"""
        await self.collect_all()
        await self.collect_links()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'devices': [d.to_dict() for d in self.devices],
            'links': [l.to_dict() for l in self.links],
        }

    def export_json(self, filename: str):
        """Export topology to JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'devices': [d.to_dict() for d in self.devices],
            'links': [l.to_dict() for l in self.links],
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Topology exported to {filename}")


# Example usage
async def main():
    collector = NetworkTopologyCollector()
    
    # Add devices
    collector.add_device({
        'id': 'core-1',
        'name': 'Core-Router-1',
        'ip': '192.168.1.1',
        'vendor': 'mikrotik',
        'username': 'admin',
        'password': 'password123',
    })
    
    collector.add_device({
        'id': 'fw-1',
        'name': 'Firewall-1',
        'ip': '192.168.1.3',
        'vendor': 'fortinet',
        'api_key': 'your-api-key',
    })
    
    collector.add_device({
        'id': 'sw-1',
        'name': 'Switch-1',
        'ip': '192.168.2.1',
        'vendor': 'cisco',
        'snmp_community': 'public',
    })
    
    # Collect data
    data = await collector.collect()
    print(json.dumps(data, indent=2))
    
    # Export
    collector.export_json('network-topology.json')


if __name__ == '__main__':
    asyncio.run(main())
