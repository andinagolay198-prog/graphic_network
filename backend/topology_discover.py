"""
topology_discover.py  v2
────────────────────────
MikroTik  → RouterOS API port 3543  (SSH disabled)
Cisco     → SSH/Netmiko port 22
"""

import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────

def _clean(s):
    return s.strip() if s else ""

def _speed_to_str(speed_bps):
    try:
        s = int(speed_bps)
    except (TypeError, ValueError):
        return str(speed_bps) if speed_bps else None
    if s >= 1_000_000_000: return f"{s // 1_000_000_000}G"
    if s >= 1_000_000:     return f"{s // 1_000_000}M"
    if s >= 1_000:         return f"{s // 1_000}K"
    return f"{s}"

def _guess_link_type(iface_name):
    if not iface_name: return "ethernet"
    s = iface_name.lower()
    if re.match(r"^(tun|ovpn|pptp|l2tp|ipsec|gre|wireguard)", s): return "tunnel"
    if re.match(r"^(bond|lag|ae|po\d|trunk)", s):                  return "lag"
    if re.match(r"^(wlan|wifi|ath|wl|wireless)", s):               return "wireless"
    if re.match(r"^vlan|\.(\d+)$", s):                             return "vlan"
    if re.match(r"^(sfp|qsfp|fo|fiber|opt)", s):                   return "fiber"
    return "ethernet"


# ══════════════════════════════════════════════════════════════════
# MikroTik — RouterOS API (port 3543, không cần SSH)
# ══════════════════════════════════════════════════════════════════

def _mt_api_connect(dev):
    """Kết nối RouterOS API, trả về (api, conn) để dùng với context."""
    import routeros_api
    conn = routeros_api.RouterOsApiPool(
        host=dev["ip"],
        username=dev.get("ssh_username", "admin"),
        password=dev.get("ssh_password", ""),
        port=int(dev.get("api_port") or 3543),
        use_ssl=dev.get("use_ssl", False),
        ssl_verify=dev.get("verify_ssl", False),
        plaintext_login=True,
    )
    api = conn.get_api()
    return api, conn


def _mt_interfaces(api, dev_id):
    """Lấy interface list từ RouterOS API."""
    interfaces = []
    try:
        raw = list(api.get_resource("/interface").get())
    except Exception as e:
        logger.warning(f"[{dev_id}] /interface error: {e}")
        return interfaces

    for item in raw:
        name     = item.get("name", "")
        if not name:
            continue
        running  = item.get("running",  "false") == "true"
        disabled = item.get("disabled", "false") == "true"
        tx_bytes = int(item.get("tx-byte", 0))
        rx_bytes = int(item.get("rx-byte", 0))

        ifc = {
            "name":        name,
            "status":      "up" if running and not disabled else "down",
            "type":        item.get("type", "ether"),
            "mac":         item.get("mac-address"),
            "comment":     item.get("comment", ""),
            "tx_bytes":    tx_bytes,
            "rx_bytes":    rx_bytes,
            "tx_rate":     0,
            "rx_rate":     0,
            "speed":       None,
            "utilization": 0,
            "disabled":    disabled,
        }
        interfaces.append(ifc)

    # Lấy speed từ ethernet settings
    try:
        eth_raw = list(api.get_resource("/interface/ethernet").get())
        eth_map = {e.get("name"): e for e in eth_raw}
        for ifc in interfaces:
            eth = eth_map.get(ifc["name"])
            if eth:
                # actual-mtu không phải speed, dùng rate nếu có
                rate = eth.get("rate") or eth.get("advertise", "")
                if "1000M" in rate or "1G" in rate or "1000" in str(rate):
                    ifc["speed"] = "1G"
                elif "100M" in rate or "100" in str(rate):
                    ifc["speed"] = "100M"
                elif "10G" in rate:
                    ifc["speed"] = "10G"
    except Exception as e:
        logger.debug(f"[{dev_id}] ethernet speed: {e}")

    return interfaces


def _mt_neighbors(api, dev_id):
    """Lấy IP neighbors (LLDP/MNDP/CDP) từ /ip neighbor."""
    neighbors = []
    try:
        raw = list(api.get_resource("/ip/neighbor").get())
    except Exception as e:
        logger.warning(f"[{dev_id}] /ip/neighbor error: {e}")
        return neighbors

    for item in raw:
        iface = item.get("interface", "")
        if not iface:
            continue
        nb = {
            "local_iface":    iface,
            "neighbor_name":  item.get("identity") or item.get("system-caps-enabled", ""),
            "neighbor_ip":    item.get("address", ""),
            "neighbor_mac":   item.get("mac-address", ""),
            "neighbor_iface": item.get("interface-name", ""),
            "platform":       item.get("platform", ""),
            "protocol":       "MNDP/LLDP",
        }
        # Bỏ qua neighbor không có tên và không có IP
        if not nb["neighbor_name"] and not nb["neighbor_ip"]:
            continue
        neighbors.append(nb)
    return neighbors


def _mt_arp(api, dev_id):
    """Lấy ARP table từ /ip/arp."""
    arp = []
    try:
        raw = list(api.get_resource("/ip/arp").get())
        for item in raw:
            ip  = item.get("address", "")
            mac = item.get("mac-address", "")
            if ip:
                arp.append({
                    "ip":        ip,
                    "mac":       mac,
                    "interface": item.get("interface", ""),
                })
    except Exception as e:
        logger.debug(f"[{dev_id}] ARP error: {e}")
    return arp


def discover_mikrotik(dev):
    """
    Discover MikroTik via RouterOS API (port 3543).
    Không dùng SSH.
    """
    dev_id = dev["id"]
    result = {"device_id": dev_id, "interfaces": [], "neighbors": [], "arp": [], "error": None}
    try:
        logger.info(f"[{dev_id}] Connecting via RouterOS API to {dev['ip']}:{dev.get('api_port',3543)}...")
        api, conn = _mt_api_connect(dev)

        logger.info(f"[{dev_id}] MikroTik: interfaces...")
        result["interfaces"] = _mt_interfaces(api, dev_id)

        logger.info(f"[{dev_id}] MikroTik: neighbors (LLDP/MNDP)...")
        result["neighbors"]  = _mt_neighbors(api, dev_id)

        logger.info(f"[{dev_id}] MikroTik: ARP...")
        result["arp"]        = _mt_arp(api, dev_id)

        conn.disconnect()
        logger.info(f"[{dev_id}] ✓ {len(result['interfaces'])} ifaces, {len(result['neighbors'])} neighbors")
    except ImportError:
        result["error"] = "routeros_api not installed — run: pip install routeros_api"
        logger.error(f"[{dev_id}] {result['error']}")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[{dev_id}] RouterOS API error: {e}")
    return result


# ══════════════════════════════════════════════════════════════════
# Cisco IOS / IOS-XE — SSH/Netmiko
# ══════════════════════════════════════════════════════════════════

def _parse_rate(s):
    if not s: return 0
    try: return int(s)
    except ValueError: pass
    m = re.search(r'(\d+)\s*(kbit|mbit|gbit|bit)', str(s).lower())
    if m:
        n = int(m.group(1))
        u = m.group(2)
        return n * (1000 if u=='kbit' else 1_000_000 if u=='mbit' else 1_000_000_000 if u=='gbit' else 1)
    return 0

def _rate_str_to_bps(s):
    if not s: return 0
    s = str(s).upper().strip()
    m = re.match(r'^(\d+(?:\.\d+)?)\s*([GMKT]?)(?:BIT|B)?', s)
    if not m: return 0
    n = float(m.group(1))
    u = m.group(2)
    mul = {'G':1_000_000_000,'M':1_000_000,'K':1_000,'T':1_000_000_000_000}.get(u,1)
    return int(n * mul)

def _cisco_interfaces(conn):
    interfaces = []
    try:
        raw = conn.send_command("show interfaces", use_textfsm=True)
        if isinstance(raw, list):
            for r in raw:
                speed_bps = _rate_str_to_bps(str(r.get("bandwidth", "")))
                tx = _parse_rate(r.get("output_rate", "0"))
                rx = _parse_rate(r.get("input_rate",  "0"))
                interfaces.append({
                    "name":        r.get("interface", ""),
                    "status":      "up" if r.get("link_status","").lower()=="up" and r.get("protocol_status","").lower()=="up" else "down",
                    "speed":       _speed_to_str(r.get("bandwidth","")) if r.get("bandwidth") else None,
                    "tx_rate":     tx,
                    "rx_rate":     rx,
                    "mac":         r.get("address"),
                    "description": r.get("description",""),
                    "type":        "ethernet",
                    "utilization": round(min(100,(tx+rx)/speed_bps*100),1) if speed_bps else 0,
                })
        else:
            # Regex fallback
            for block in re.split(r'\n(?=\S)', raw):
                m = re.match(r'^(\S+)\s+is\s+(\w+(?:\s+\w+)?),\s+line protocol is\s+(\w+)', block)
                if not m: continue
                bw_m = re.search(r'BW\s+(\d+)\s+Kbit', block)
                tx_m = re.search(r'(\d+)\s+(?:bits?|kbits?)/sec\s+output', block)
                rx_m = re.search(r'(\d+)\s+(?:bits?|kbits?)/sec\s+input',  block)
                desc_m = re.search(r'Description:\s*(.+)', block)
                interfaces.append({
                    "name":        m.group(1),
                    "status":      "up" if m.group(2).lower()=="up" and m.group(3).lower()=="up" else "down",
                    "speed":       f"{int(bw_m.group(1))//1000}M" if bw_m else None,
                    "tx_rate":     int(tx_m.group(1)) if tx_m else 0,
                    "rx_rate":     int(rx_m.group(1)) if rx_m else 0,
                    "mac":         None,
                    "description": _clean(desc_m.group(1)) if desc_m else "",
                    "type":        "ethernet",
                    "utilization": 0,
                })
    except Exception as e:
        logger.warning(f"Cisco interfaces error: {e}")
    return interfaces


def _cisco_neighbors(conn):
    neighbors = []
    # CDP
    try:
        raw = conn.send_command("show cdp neighbors detail", use_textfsm=True)
        if isinstance(raw, list):
            for r in raw:
                neighbors.append({
                    "local_iface":    r.get("local_port", ""),
                    "neighbor_name":  r.get("destination_host", ""),
                    "neighbor_iface": r.get("remote_port", ""),
                    "neighbor_ip":    r.get("management_ip", ""),
                    "platform":       r.get("platform", ""),
                    "protocol":       "CDP",
                })
        else:
            for block in re.split(r'-{5,}', raw):
                name_m = re.search(r'Device ID:\s*(\S+)', block)
                lip_m  = re.search(r'Interface:\s*(\S+?),', block)
                rpt_m  = re.search(r'Port ID.*?:\s*(\S+)', block)
                ip_m   = re.search(r'IP address:\s*([\d\.]+)', block)
                if name_m and lip_m:
                    neighbors.append({
                        "local_iface":    _clean(lip_m.group(1)),
                        "neighbor_name":  _clean(name_m.group(1)),
                        "neighbor_iface": _clean(rpt_m.group(1)) if rpt_m else None,
                        "neighbor_ip":    _clean(ip_m.group(1))  if ip_m  else None,
                        "platform":       None,
                        "protocol":       "CDP",
                    })
    except Exception as e:
        logger.debug(f"CDP: {e}")

    # LLDP fallback
    if not neighbors:
        try:
            raw = conn.send_command("show lldp neighbors detail", use_textfsm=True)
            if isinstance(raw, list):
                for r in raw:
                    neighbors.append({
                        "local_iface":    r.get("local_interface",    ""),
                        "neighbor_name":  r.get("neighbor",           ""),
                        "neighbor_iface": r.get("neighbor_interface", ""),
                        "neighbor_ip":    r.get("management_address", ""),
                        "platform":       r.get("system_description", ""),
                        "protocol":       "LLDP",
                    })
        except Exception as e:
            logger.debug(f"LLDP: {e}")
    return neighbors


def _cisco_arp(conn):
    arp = []
    try:
        raw = conn.send_command("show ip arp", use_textfsm=True)
        if isinstance(raw, list):
            for r in raw:
                arp.append({"ip": r.get("address",""), "mac": r.get("mac",""), "interface": r.get("interface","")})
        else:
            for line in raw.splitlines():
                ip_m  = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                mac_m = re.search(r'([\da-fA-F]{4}\.[\da-fA-F]{4}\.[\da-fA-F]{4})', line)
                if ip_m and mac_m:
                    arp.append({"ip": ip_m.group(1), "mac": mac_m.group(1), "interface": None})
    except Exception as e:
        logger.debug(f"ARP: {e}")
    return arp


def discover_cisco(dev):
    """Discover Cisco via SSH/Netmiko."""
    from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

    dev_id = dev["id"]
    result = {"device_id": dev_id, "interfaces": [], "neighbors": [], "arp": [], "error": None}

    dt_map = {"ios": "cisco_ios", "ios_xe": "cisco_xe", "nx_os": "cisco_nxos", "asa": "cisco_asa"}
    device_type = dt_map.get(dev.get("device_type", "ios"), "cisco_ios")

    conn_params = {
        "device_type":    device_type,
        "host":           dev["ip"],
        "username":       dev.get("ssh_username", ""),
        "password":       dev.get("ssh_password", ""),
        "secret":         dev.get("secret", ""),
        "port":           int(dev.get("ssh_port") or 22),
        "timeout":        20,
        "session_timeout":60,
        "fast_cli":       False,
    }
    try:
        logger.info(f"[{dev_id}] Connecting via SSH to {dev['ip']}...")
        with ConnectHandler(**conn_params) as conn:
            if conn_params["secret"]:
                conn.enable()
            logger.info(f"[{dev_id}] Cisco: interfaces...")
            result["interfaces"] = _cisco_interfaces(conn)
            logger.info(f"[{dev_id}] Cisco: CDP/LLDP neighbors...")
            result["neighbors"]  = _cisco_neighbors(conn)
            logger.info(f"[{dev_id}] Cisco: ARP...")
            result["arp"]        = _cisco_arp(conn)
            logger.info(f"[{dev_id}] ✓ {len(result['interfaces'])} ifaces, {len(result['neighbors'])} neighbors")
    except NetmikoTimeoutException:
        result["error"] = f"timeout connecting to {dev['ip']}"
    except NetmikoAuthenticationException:
        result["error"] = f"authentication failed for {dev['ip']}"
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[{dev_id}] {e}")
    return result


# ══════════════════════════════════════════════════════════════════
# Dispatch: chọn đúng method theo vendor
# ══════════════════════════════════════════════════════════════════

def discover_device(dev):
    """
    dev phải có:
      id, name, ip, vendor, status,
      ssh_username, ssh_password,
      api_port   (MikroTik, default 3543)
      ssh_port   (Cisco, default 22)
      secret     (Cisco enable password)
    """
    if dev.get("status") != "up":
        return {"device_id": dev["id"], "interfaces": [], "neighbors": [], "arp": [], "error": "device_offline"}

    vendor = (dev.get("vendor") or "").lower()

    if vendor == "mikrotik":
        return discover_mikrotik(dev)
    else:
        # Cisco, Fortinet via SSH, etc.
        return discover_cisco(dev)


# ══════════════════════════════════════════════════════════════════
# Build topology links từ neighbor data
# ══════════════════════════════════════════════════════════════════

def build_links_from_neighbors(all_results, all_devices):
    name_to_id = {}
    ip_to_id   = {}
    for dev in all_devices:
        name_to_id[dev["name"].lower()] = dev["id"]
        name_to_id[dev["id"].lower()]   = dev["id"]
        if dev.get("ip"):
            ip_to_id[dev["ip"]] = dev["id"]

    def resolve(neighbor_name, neighbor_ip):
        if neighbor_name:
            k = (neighbor_name or "").lower()
            if k in name_to_id: return name_to_id[k]
            short = k.split(".")[0]
            if short in name_to_id: return name_to_id[short]
        if neighbor_ip and neighbor_ip in ip_to_id:
            return ip_to_id[neighbor_ip]
        return None

    iface_speed = {}
    iface_util  = {}
    for res in all_results:
        did = res["device_id"]
        iface_speed[did] = {}
        iface_util[did]  = {}
        for ifc in res.get("interfaces", []):
            iface_speed[did][ifc["name"]] = ifc.get("speed")
            iface_util[did][ifc["name"]]  = ifc.get("utilization", 0)

    seen  = set()
    links = []

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

            from_dev = next((d for d in all_devices if d["id"] == from_id), {})
            to_dev   = next((d for d in all_devices if d["id"] == to_id),   {})
            status   = "up" if from_dev.get("status")=="up" and to_dev.get("status")=="up" else "down"

            bandwidth = iface_speed.get(from_id, {}).get(local_iface) if local_iface else None
            util      = iface_util.get(from_id, {}).get(local_iface, 0) or 0

            links.append({
                "id":          f"lnk-{from_id}-{to_id}",
                "from":        from_id,
                "to":          to_id,
                "type":        _guess_link_type(local_iface),
                "iface_from":  local_iface,
                "iface_to":    peer_iface,
                "status":      status,
                "bandwidth":   bandwidth,
                "utilization": round(util, 1),
                "protocol":    nb.get("protocol", "LLDP"),
            })
    return links


# ══════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════

def discover_all(devices, max_workers=5):
    """
    devices: list of dicts với đủ credentials.
    Returns: { links, interfaces, errors }
    """
    results    = []
    errors     = {}
    interfaces = {}

    online = [d for d in devices if d.get("status") == "up"]
    logger.info(f"discover_all: {len(online)} online / {len(devices)} total")

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
                logger.error(f"[{dev_id}] Unexpected: {e}")

    links = build_links_from_neighbors(results, devices)
    logger.info(f"discover_all: {len(links)} links built")
    return {"links": links, "interfaces": interfaces, "errors": errors}
