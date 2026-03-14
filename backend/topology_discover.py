"""
topology_discover.py
────────────────────
SSH/Netmiko discovery module for Network Topology Manager.

Supports:
  - MikroTik RouterOS  (device_type: "mikrotik_routeros")
  - Cisco IOS / IOS-XE (device_type: "cisco_ios")

Collects per-device:
  - Interface list + status + speed
  - IP neighbors (ARP table)
  - LLDP neighbors (→ builds links between devices)
  - Bandwidth utilization (tx/rx rates per interface)

Exposes:
  discover_all(devices)  →  { links: [...], interfaces: { device_id: [...] } }
  discover_device(dev)   →  { interfaces: [...], neighbors: [...], arp: [...] }
"""

import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────

def _clean(s):
    return s.strip() if s else ""


def _speed_to_str(speed_bps):
    """Convert bps integer to human string: 1000000000 → '1G'"""
    try:
        s = int(speed_bps)
    except (TypeError, ValueError):
        return str(speed_bps) if speed_bps else None
    if s >= 1_000_000_000:
        return f"{s // 1_000_000_000}G"
    if s >= 1_000_000:
        return f"{s // 1_000_000}M"
    if s >= 1_000:
        return f"{s // 1_000}K"
    return f"{s}"


def _guess_link_type(iface_name):
    """Guess link type from interface name."""
    if not iface_name:
        return "ethernet"
    s = iface_name.lower()
    if re.match(r"^(tun|ovpn|pptp|l2tp|ipsec|gre|wireguard)", s):
        return "tunnel"
    if re.match(r"^(bond|lag|ae|po\d|trunk)", s):
        return "lag"
    if re.match(r"^(wlan|wifi|ath|wl|wireless)", s):
        return "wireless"
    if re.match(r"^vlan|\.(\d+)$", s):
        return "vlan"
    if re.match(r"^(sfp|qsfp|fo|fiber|opt)", s):
        return "fiber"
    return "ethernet"


# ── MikroTik RouterOS ──────────────────────────────────────────────────────

def _mikrotik_interfaces(conn):
    """
    Returns list of dicts:
      { name, status, speed, tx_rate, rx_rate, mac, type, comment }
    """
    interfaces = []

    # Get interface list with running status
    raw = conn.send_command("/interface print detail without-paging")
    # Each interface block starts with a number like "0  name=..."
    blocks = re.split(r'\n(?=\s*\d+\s+)', raw)
    for block in blocks:
        iface = {}
        name_m = re.search(r'name="?([^\s"]+)"?', block)
        if not name_m:
            continue
        iface["name"]    = name_m.group(1)
        iface["status"]  = "up" if "running" in block and "R" in block.split("\n")[0][:20] else "down"
        iface["mac"]     = _clean(re.search(r'mac-address=([\w:]+)', block).group(1)) if re.search(r'mac-address=([\w:]+)', block) else None
        iface["comment"] = _clean(re.search(r'comment="?([^"\n]+)"?', block).group(1)) if re.search(r'comment="?([^"\n]+)"?', block) else ""
        iface["type"]    = _clean(re.search(r'type=(\S+)', block).group(1)) if re.search(r'type=(\S+)', block) else "ether"
        interfaces.append(iface)

    # Get tx/rx rates and speed from monitor (only running interfaces)
    try:
        running = [i["name"] for i in interfaces if i["status"] == "up"]
        for name in running[:16]:  # limit to avoid timeout
            mon = conn.send_command(
                f'/interface monitor-traffic {name} once',
                expect_string=r'[\$#>]', read_timeout=8
            )
            tx_m = re.search(r'tx-bits-per-second:\s*(\d+)', mon)
            rx_m = re.search(r'rx-bits-per-second:\s*(\d+)', mon)
            for ifc in interfaces:
                if ifc["name"] == name:
                    ifc["tx_rate"] = int(tx_m.group(1)) if tx_m else 0
                    ifc["rx_rate"] = int(rx_m.group(1)) if rx_m else 0
                    # utilization % based on presumed link speed
                    total = ifc["tx_rate"] + ifc["rx_rate"]
                    ifc["utilization"] = min(100, round(total / 1_000_000_000 * 100, 1))
    except Exception as e:
        logger.warning(f"MikroTik monitor-traffic error: {e}")

    # Get speeds from ethernet settings
    try:
        eth_raw = conn.send_command("/interface ethernet print detail without-paging")
        for block in re.split(r'\n(?=\s*\d+\s+)', eth_raw):
            name_m = re.search(r'name="?([^\s"]+)"?', block)
            if not name_m:
                continue
            speed_m = re.search(r'(?:speed|actual-mtu).*?(\d+[GMK])', block)
            rate_m  = re.search(r'(?:rate)="?(\d+[GMK]bps)"?', block)
            spd     = rate_m.group(1) if rate_m else (speed_m.group(1) if speed_m else None)
            for ifc in interfaces:
                if ifc["name"] == name_m.group(1):
                    ifc["speed"] = spd
    except Exception as e:
        logger.warning(f"MikroTik ethernet speed error: {e}")

    return interfaces


def _mikrotik_lldp_neighbors(conn):
    """
    Returns list of dicts:
      { local_iface, neighbor_mac, neighbor_name, neighbor_iface, neighbor_ip }
    Uses /ip neighbor print for MikroTik (CDP/LLDP/MNDP).
    """
    neighbors = []
    raw = conn.send_command("/ip neighbor print detail without-paging")
    blocks = re.split(r'\n(?=\s*\d+\s+)', raw)
    for block in blocks:
        if not block.strip():
            continue
        nb = {}
        iface_m  = re.search(r'interface=(\S+)', block)
        mac_m    = re.search(r'mac-address=([\w:]+)', block)
        name_m   = re.search(r'identity="?([^"\n]+)"?', block)
        ip_m     = re.search(r'address=([\d\.]+)', block)
        port_m   = re.search(r'(?:port-id|interface-name)="?([^"\n]+)"?', block)

        if not iface_m:
            continue
        nb["local_iface"]    = _clean(iface_m.group(1))
        nb["neighbor_mac"]   = _clean(mac_m.group(1))  if mac_m  else None
        nb["neighbor_name"]  = _clean(name_m.group(1)) if name_m else None
        nb["neighbor_ip"]    = _clean(ip_m.group(1))   if ip_m   else None
        nb["neighbor_iface"] = _clean(port_m.group(1)) if port_m else None
        neighbors.append(nb)
    return neighbors


def _mikrotik_arp(conn):
    """Returns ARP table as list of { ip, mac, interface }"""
    arp = []
    raw = conn.send_command("/ip arp print without-paging")
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            ip_m  = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
            mac_m = re.search(r'([\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2})', line)
            if ip_m and mac_m:
                iface_m = re.search(r'(ether\d+|sfp\S*|bridge\S*|vlan\S*)', line)
                arp.append({
                    "ip":        ip_m.group(1),
                    "mac":       mac_m.group(1).lower(),
                    "interface": iface_m.group(1) if iface_m else None,
                })
    return arp


def discover_mikrotik(conn, dev_id):
    logger.info(f"[{dev_id}] MikroTik: collecting interfaces...")
    interfaces = _mikrotik_interfaces(conn)
    logger.info(f"[{dev_id}] MikroTik: collecting LLDP/MNDP neighbors...")
    neighbors  = _mikrotik_lldp_neighbors(conn)
    logger.info(f"[{dev_id}] MikroTik: collecting ARP table...")
    arp        = _mikrotik_arp(conn)
    return {"interfaces": interfaces, "neighbors": neighbors, "arp": arp}


# ── Cisco IOS / IOS-XE ────────────────────────────────────────────────────

def _cisco_interfaces(conn):
    """
    Returns list of interface dicts.
    Uses 'show interfaces' for status+speed+rate and 'show ip interface brief'.
    """
    interfaces = []

    # --- show interfaces (full detail) ---
    raw = conn.send_command("show interfaces", use_textfsm=True)

    if isinstance(raw, list):
        # TextFSM parsed
        for r in raw:
            ifc = {
                "name":        r.get("interface",    ""),
                "status":      "up" if r.get("link_status", "").lower() == "up"
                               and r.get("protocol_status", "").lower() == "up"
                               else "down",
                "speed":       r.get("bandwidth",    None),
                "tx_rate":     _parse_rate(r.get("output_rate", "0")),
                "rx_rate":     _parse_rate(r.get("input_rate",  "0")),
                "mac":         r.get("address",      None),
                "description": r.get("description",  ""),
                "type":        "ethernet",
            }
            if ifc["tx_rate"] is not None and ifc["rx_rate"] is not None:
                total = ifc["tx_rate"] + ifc["rx_rate"]
                speed_bps = _rate_str_to_bps(str(ifc.get("speed", "")))
                ifc["utilization"] = min(100, round(total / speed_bps * 100, 1)) if speed_bps else 0
            interfaces.append(ifc)
    else:
        # Fallback: regex parse
        blocks = re.split(r'\n(?=\S)', raw)
        for block in blocks:
            name_m = re.match(r'^(\S+)\s+is\s+(\w+(?:\s+\w+)?),\s+line protocol is\s+(\w+)', block)
            if not name_m:
                continue
            ifc = {
                "name":    name_m.group(1),
                "status":  "up" if name_m.group(2).lower() == "up"
                           and name_m.group(3).lower() == "up" else "down",
                "speed":   None, "tx_rate": 0, "rx_rate": 0, "mac": None,
                "description": "", "type": "ethernet",
            }
            bw_m  = re.search(r'BW\s+(\d+)\s+Kbit', block)
            mac_m = re.search(r'Hardware.*?address is\s+([\w\.]+)', block)
            desc_m = re.search(r'Description:\s*(.+)', block)
            tx_m  = re.search(r'(\d+)\s+(?:bits/sec|kbits/sec)\s+output rate', block)
            rx_m  = re.search(r'(\d+)\s+(?:bits/sec|kbits/sec)\s+input rate', block)
            if bw_m:
                bw_kbps = int(bw_m.group(1))
                ifc["speed"] = _speed_to_str(bw_kbps * 1000)
            if mac_m:
                ifc["mac"] = mac_m.group(1)
            if desc_m:
                ifc["description"] = _clean(desc_m.group(1))
            if tx_m:
                ifc["tx_rate"] = int(tx_m.group(1))
            if rx_m:
                ifc["rx_rate"] = int(rx_m.group(1))
            interfaces.append(ifc)

    return interfaces


def _parse_rate(s):
    """Parse '1000 kbits/sec' or '1000000 bits/sec' → bps int"""
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        pass
    m = re.search(r'(\d+)\s*(kbit|mbit|gbit|bit)', str(s).lower())
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        return n * (1000 if unit == 'kbit' else 1_000_000 if unit == 'mbit' else 1_000_000_000 if unit == 'gbit' else 1)
    return 0


def _rate_str_to_bps(s):
    """'1G' / '1000M' / '100M' → bps int"""
    if not s:
        return 0
    s = str(s).upper().strip()
    m = re.match(r'^(\d+(?:\.\d+)?)\s*([GMKT]?)(?:BIT|B)?', s)
    if not m:
        return 0
    n = float(m.group(1))
    u = m.group(2)
    mul = {'G': 1_000_000_000, 'M': 1_000_000, 'K': 1_000, 'T': 1_000_000_000_000}.get(u, 1)
    return int(n * mul)


def _cisco_cdp_neighbors(conn):
    """
    Returns LLDP/CDP neighbor list:
      { local_iface, neighbor_name, neighbor_iface, neighbor_ip, platform }
    """
    neighbors = []

    # Try CDP first
    try:
        raw = conn.send_command("show cdp neighbors detail", use_textfsm=True)
        if isinstance(raw, list):
            for r in raw:
                neighbors.append({
                    "local_iface":    r.get("local_port",       ""),
                    "neighbor_name":  r.get("destination_host", ""),
                    "neighbor_iface": r.get("remote_port",      ""),
                    "neighbor_ip":    r.get("management_ip",    ""),
                    "platform":       r.get("platform",         ""),
                    "protocol":       "CDP",
                })
        else:
            # Regex fallback
            blocks = re.split(r'-{5,}', raw)
            for block in blocks:
                name_m  = re.search(r'Device ID:\s*(\S+)', block)
                lip_m   = re.search(r'Interface:\s*(\S+?),', block)
                rport_m = re.search(r'Port ID.*?:\s*(\S+)', block)
                ip_m    = re.search(r'IP address:\s*([\d\.]+)', block)
                plat_m  = re.search(r'Platform:\s*([^,\n]+)', block)
                if name_m and lip_m:
                    neighbors.append({
                        "local_iface":    _clean(lip_m.group(1)),
                        "neighbor_name":  _clean(name_m.group(1)),
                        "neighbor_iface": _clean(rport_m.group(1)) if rport_m else None,
                        "neighbor_ip":    _clean(ip_m.group(1))    if ip_m    else None,
                        "platform":       _clean(plat_m.group(1))  if plat_m  else None,
                        "protocol":       "CDP",
                    })
    except Exception as e:
        logger.warning(f"CDP failed: {e}")

    # Try LLDP if CDP gave nothing
    if not neighbors:
        try:
            raw = conn.send_command("show lldp neighbors detail", use_textfsm=True)
            if isinstance(raw, list):
                for r in raw:
                    neighbors.append({
                        "local_iface":    r.get("local_interface",   ""),
                        "neighbor_name":  r.get("neighbor",          ""),
                        "neighbor_iface": r.get("neighbor_interface",""),
                        "neighbor_ip":    r.get("management_address",""),
                        "platform":       r.get("system_description",""),
                        "protocol":       "LLDP",
                    })
            else:
                # Regex fallback
                blocks = re.split(r'-{5,}', raw)
                for block in blocks:
                    sys_m   = re.search(r'System Name:\s*(\S+)', block)
                    lip_m   = re.search(r'Local Intf:\s*(\S+)', block)
                    rport_m = re.search(r'Port id:\s*(\S+)', block)
                    ip_m    = re.search(r'Management Addresses.*?([\d\.]+)', block, re.S)
                    if sys_m and lip_m:
                        neighbors.append({
                            "local_iface":    _clean(lip_m.group(1)),
                            "neighbor_name":  _clean(sys_m.group(1)),
                            "neighbor_iface": _clean(rport_m.group(1)) if rport_m else None,
                            "neighbor_ip":    _clean(ip_m.group(1))    if ip_m    else None,
                            "platform":       None,
                            "protocol":       "LLDP",
                        })
        except Exception as e:
            logger.warning(f"LLDP failed: {e}")

    return neighbors


def _cisco_arp(conn):
    """Returns ARP table: [{ ip, mac, interface }]"""
    arp = []
    try:
        raw = conn.send_command("show ip arp", use_textfsm=True)
        if isinstance(raw, list):
            for r in raw:
                arp.append({
                    "ip":        r.get("address",   ""),
                    "mac":       r.get("mac",        ""),
                    "interface": r.get("interface",  ""),
                })
        else:
            for line in raw.splitlines():
                ip_m  = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                mac_m = re.search(r'([\da-fA-F]{4}\.[\da-fA-F]{4}\.[\da-fA-F]{4})', line)
                if ip_m and mac_m:
                    iface_m = re.search(r'(\S+)$', line)
                    arp.append({
                        "ip":        ip_m.group(1),
                        "mac":       mac_m.group(1),
                        "interface": iface_m.group(1) if iface_m else None,
                    })
    except Exception as e:
        logger.warning(f"ARP table error: {e}")
    return arp


def discover_cisco(conn, dev_id):
    logger.info(f"[{dev_id}] Cisco: collecting interfaces...")
    interfaces = _cisco_interfaces(conn)
    logger.info(f"[{dev_id}] Cisco: collecting CDP/LLDP neighbors...")
    neighbors  = _cisco_cdp_neighbors(conn)
    logger.info(f"[{dev_id}] Cisco: collecting ARP table...")
    arp        = _cisco_arp(conn)
    return {"interfaces": interfaces, "neighbors": neighbors, "arp": arp}


# ── Per-device SSH connect + dispatch ─────────────────────────────────────

NETMIKO_DEVICE_TYPES = {
    "mikrotik": "mikrotik_routeros",
    "cisco":    "cisco_ios",
    "fortinet": "fortinet",
    "juniper":  "juniper_junos",
    "hp":       "hp_comware",
    "huawei":   "huawei",
}


def discover_device(dev):
    """
    dev = {
        "id": "CTHO",
        "name": "CTHO",
        "ip": "14.176.141.36",
        "vendor": "Mikrotik",
        "status": "up",
        # credentials from DB:
        "ssh_username": "admin",
        "ssh_password": "secret",
        "ssh_port": 22,           # optional, default 22
        "ssh_key_file": None,     # optional, path to private key
    }
    Returns:
        { "device_id": ..., "interfaces": [...], "neighbors": [...], "arp": [...], "error": None }
    """
    dev_id = dev["id"]
    result = {"device_id": dev_id, "interfaces": [], "neighbors": [], "arp": [], "error": None}

    if dev.get("status") != "up":
        result["error"] = "device_offline"
        return result

    vendor = (dev.get("vendor") or "").lower()
    device_type = NETMIKO_DEVICE_TYPES.get(vendor, "cisco_ios")

    conn_params = {
        "device_type": device_type,
        "host":        dev["ip"],
        "username":    dev.get("ssh_username", ""),
        "password":    dev.get("ssh_password", ""),
        "port":        int(dev.get("ssh_port") or 22),
        "timeout":     20,
        "session_timeout": 60,
        "fast_cli":    False,
    }
    if dev.get("ssh_key_file"):
        conn_params["use_keys"]    = True
        conn_params["key_file"]    = dev["ssh_key_file"]
        conn_params["password"]    = ""

    try:
        logger.info(f"[{dev_id}] Connecting via SSH to {dev['ip']} ({device_type})...")
        with ConnectHandler(**conn_params) as conn:
            conn.enable()  # Enter enable mode if needed (Cisco); no-op on MikroTik
            if vendor in ("mikrotik",):
                data = discover_mikrotik(conn, dev_id)
            else:
                data = discover_cisco(conn, dev_id)
            result.update(data)
            logger.info(f"[{dev_id}] ✓ {len(data['interfaces'])} interfaces, {len(data['neighbors'])} neighbors")
    except NetmikoTimeoutException:
        result["error"] = f"timeout connecting to {dev['ip']}"
        logger.error(f"[{dev_id}] Timeout")
    except NetmikoAuthenticationException:
        result["error"] = f"authentication failed for {dev['ip']}"
        logger.error(f"[{dev_id}] Auth failed")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[{dev_id}] Error: {e}")

    return result


# ── Build topology links from neighbor data ────────────────────────────────

def build_links_from_neighbors(all_results, all_devices):
    """
    Cross-correlate LLDP/CDP neighbor data from all devices to produce
    a deduplicated list of links.

    all_results: list of discover_device() return values
    all_devices: list of device dicts (from DB / topology API)

    Returns: list of link dicts:
      {
        id, from, to, type,
        iface_from, iface_to,
        status, bandwidth,
        utilization
      }
    """
    # Build lookup: name/ip → device_id
    name_to_id = {}
    ip_to_id   = {}
    for dev in all_devices:
        name_to_id[dev["name"].lower()] = dev["id"]
        name_to_id[dev["id"].lower()]   = dev["id"]
        if dev.get("ip"):
            ip_to_id[dev["ip"]] = dev["id"]

    def resolve(neighbor_name, neighbor_ip):
        """Try to match a neighbor to a known device_id."""
        if neighbor_name:
            # Exact match
            k = neighbor_name.lower()
            if k in name_to_id:
                return name_to_id[k]
            # Partial match (hostname without domain)
            short = k.split(".")[0]
            if short in name_to_id:
                return name_to_id[short]
        if neighbor_ip and neighbor_ip in ip_to_id:
            return ip_to_id[neighbor_ip]
        return None

    # Build iface→speed lookup per device from interfaces
    iface_speed = {}  # { device_id: { iface_name: speed_str } }
    iface_util  = {}  # { device_id: { iface_name: utilization% } }
    for res in all_results:
        did = res["device_id"]
        iface_speed[did] = {}
        iface_util[did]  = {}
        for ifc in res.get("interfaces", []):
            iface_speed[did][ifc["name"]] = ifc.get("speed")
            iface_util[did][ifc["name"]]  = ifc.get("utilization", 0)

    seen   = set()   # frozenset({dev_a, dev_b}) to deduplicate
    links  = []

    for res in all_results:
        from_id = res["device_id"]
        for nb in res.get("neighbors", []):
            to_id = resolve(nb.get("neighbor_name"), nb.get("neighbor_ip"))
            if not to_id or to_id == from_id:
                continue

            pair = frozenset({from_id, to_id})
            if pair in seen:
                continue
            seen.add(pair)

            local_iface = nb.get("local_iface")
            peer_iface  = nb.get("neighbor_iface")

            # Determine link status: up only if both sides are up
            from_dev = next((d for d in all_devices if d["id"] == from_id), {})
            to_dev   = next((d for d in all_devices if d["id"] == to_id),   {})
            status = "up" if from_dev.get("status") == "up" and to_dev.get("status") == "up" else "down"

            # Bandwidth from interface speed
            bandwidth = None
            if local_iface and from_id in iface_speed:
                bandwidth = iface_speed[from_id].get(local_iface)

            # Utilization: average of tx side
            utilization = 0
            if local_iface and from_id in iface_util:
                utilization = iface_util[from_id].get(local_iface, 0) or 0

            link_type = _guess_link_type(local_iface)

            links.append({
                "id":          f"lnk-{from_id}-{to_id}",
                "from":        from_id,
                "to":          to_id,
                "type":        link_type,
                "iface_from":  local_iface,
                "iface_to":    peer_iface,
                "status":      status,
                "bandwidth":   bandwidth,
                "utilization": round(utilization, 1),
                "protocol":    nb.get("protocol", "LLDP"),
            })

    return links


# ── Main entry point ───────────────────────────────────────────────────────

def discover_all(devices, max_workers=5):
    """
    Run discovery on all devices in parallel.

    devices: list of device dicts WITH credentials:
      Each dict must have: id, name, ip, vendor, status,
                           ssh_username, ssh_password,
                           ssh_port (optional), ssh_key_file (optional)

    Returns:
      {
        "links":      [ { id, from, to, type, iface_from, iface_to,
                          status, bandwidth, utilization } ],
        "interfaces": { device_id: [ { name, status, speed, tx_rate,
                                       rx_rate, utilization, mac,
                                       description/comment, type } ] },
        "errors":     { device_id: error_string_or_None },
      }
    """
    results    = []
    errors     = {}
    interfaces = {}

    online = [d for d in devices if d.get("status") == "up"]
    logger.info(f"discover_all: {len(online)} online devices (of {len(devices)} total)")

    with ThreadPoolExecutor(max_workers=min(max_workers, len(online) or 1)) as pool:
        future_map = {pool.submit(discover_device, dev): dev["id"] for dev in online}
        for future in as_completed(future_map):
            dev_id = future_map[future]
            try:
                res = future.result()
                results.append(res)
                interfaces[dev_id] = res["interfaces"]
                errors[dev_id]     = res.get("error")
            except Exception as e:
                errors[dev_id] = str(e)
                logger.error(f"[{dev_id}] Unexpected error: {e}")

    links = build_links_from_neighbors(results, devices)
    logger.info(f"discover_all: built {len(links)} links")

    return {
        "links":      links,
        "interfaces": interfaces,
        "errors":     errors,
    }
