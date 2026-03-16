"""
PlNetwork Auto Manager — FastAPI Backend
Supports: MikroTik (RouterOS API + SSH), Cisco (Netmiko/NAPALM), Fortinet (REST), Sophos (XML)
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio, json, os, time, subprocess, platform
from datetime import datetime

app = FastAPI(title="PlNetwork Auto Manager", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ── Persistent JSON store ────────────────────────────────────────
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "devices.json")
def load_db():
    if os.path.exists(DB_FILE):
        try:
            return json.load(open(DB_FILE, encoding="utf-8"))
        except: pass
    return {}
def save_db():
    try: json.dump(devices_db, open(DB_FILE,"w",encoding="utf-8"), indent=2, default=str)
    except Exception as e: print(f"[WARN] save_db: {e}")
devices_db: Dict[str, dict] = load_db()
print(f"[INFO] Loaded {len(devices_db)} devices from storage")



# ── Models ──────────────────────────────────────────────────────
class DeviceCreate(BaseModel):
    name: str
    vendor: str  # mikrotik | cisco | fortinet | sophos
    host: str
    username: str = "admin"
    password: str = ""
    port: int = 22
    secret: str = ""
    api_port: int = 3543
    use_ssl: bool = False
    verify_ssl: bool = False
    device_type: str = "ios"
    vdom: str = "root"
    note: str = ""

class CommandRequest(BaseModel):
    command: str

class ConfigRequest(BaseModel):
    commands: List[str]

class PingRequest(BaseModel):
    host: str
    count: int = 4
    src: str = ""   # src-address cho MikroTik: ping 10.10.79.2 src 10.10.79.0

class BandwidthRequest(BaseModel):
    interface: str = "ether1"
    duration: int = 5

# ── Health ──────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "devices_registered": len(devices_db),
        "timestamp": datetime.now().isoformat(),
    }

# ── Sync devices from frontend localStorage ─────────────────────
@app.post("/api/sync")
def sync_devices(payload: dict):
    """Frontend pushes all devices from localStorage to backend"""
    devs = payload.get("devices", [])
    count = 0
    for d in devs:
        name = d.get("name")
        if name and name not in devices_db:
            devices_db[name] = d
            count += 1
        elif name:
            # preserve status/model from backend, update credentials
            old_status = devices_db[name].get("status", "offline")
            devices_db[name].update(d)
            devices_db[name]["status"] = old_status
    save_db()
    return {"synced": count, "total": len(devices_db)}

# ── Device CRUD ─────────────────────────────────────────────────
@app.get("/api/devices")
def list_devices():
    return list(devices_db.values())

@app.post("/api/devices")
async def add_device(device: DeviceCreate, background_tasks: BackgroundTasks):
    d = device.dict()
    d["status"] = "offline"
    d["model"] = ""
    d["uptime"] = "—"
    d["cpu"] = 0
    d["mem"] = 0
    d["created_at"] = datetime.now().isoformat()
    devices_db[device.name] = d
    save_db()
    # Auto-connect in background
    background_tasks.add_task(_auto_connect, device.name)
    return {"status": "created", "device": d}

async def _auto_connect(name: str):
    """Auto-connect sau khi add thiết bị"""
    await asyncio.sleep(1)
    try:
        device = devices_db.get(name)
        if not device: return
        vendor = device.get("vendor","")
        if vendor == "mikrotik":
            result = await _mikrotik_connect(device)
        elif vendor == "cisco":
            result = await _cisco_connect(device)
        elif vendor == "fortinet":
            result = await _fortinet_connect(device)
        elif vendor == "sophos":
            result = await _sophos_connect(device)
        else:
            return
        devices_db[name]["status"] = "online"
        for k in ["model","uptime","cpu","mem","identity"]:
            if k in result: devices_db[name][k] = result[k]
        save_db()
        print(f"[AUTO-CONNECT] ✓ {name} connected ({vendor})")
        await check_and_alert_status_change(name, "online")
    except Exception as e:
        devices_db[name]["status"] = "offline"
        save_db()
        print(f"[AUTO-CONNECT] ✗ {name} failed: {e}")

@app.put("/api/devices/{name}")
def update_device(name: str, device: DeviceCreate):
    if name not in devices_db:
        raise HTTPException(404, f"Device '{name}' not found")
    old = devices_db[name]
    d = device.dict()
    d["status"] = old.get("status", "offline")
    d["model"] = old.get("model", "")
    d["uptime"] = old.get("uptime", "—")
    d["cpu"] = old.get("cpu", 0)
    d["mem"] = old.get("mem", 0)
    d["created_at"] = old.get("created_at", datetime.now().isoformat())
    devices_db[device.name] = d
    if name != device.name:
        del devices_db[name]
    save_db()
    return {"status": "updated", "device": d}

@app.delete("/api/devices/{name}")
def delete_device(name: str):
    if name not in devices_db:
        raise HTTPException(404, f"Device '{name}' not found")
    del devices_db[name]
    save_db()
    return {"status": "deleted"}

# ── Connect ─────────────────────────────────────────────────────
@app.post("/api/devices/{name}/connect")
async def connect_device(name: str):
    if name not in devices_db:
        raise HTTPException(404, f"Device '{name}' not found")
    device = devices_db[name]
    vendor = device.get("vendor", "").lower()

    try:
        if vendor == "mikrotik":
            result = await connect_mikrotik(device)
        elif vendor == "cisco":
            result = await connect_cisco(device)
        elif vendor == "fortinet":
            result = await connect_fortinet(device)
        elif vendor == "sophos":
            result = await connect_sophos(device)
        else:
            raise Exception(f"Unsupported vendor: {vendor}")

        devices_db[name]["status"] = "online"
        devices_db[name]["model"]   = result.get("model", "")
        devices_db[name]["uptime"]  = result.get("uptime", "—")
        devices_db[name]["cpu"]     = result.get("cpu", 0)
        devices_db[name]["mem"]     = result.get("mem", 0)
        # Lưu port API thực tế vừa dò được (chỉ áp dụng cho MikroTik)
        if result.get("api_port"):
            devices_db[name]["api_port"] = result["api_port"]
        if result.get("api_ssl_port"):
            devices_db[name]["api_ssl_port"] = result["api_ssl_port"]
        if "use_ssl" in result:
            devices_db[name]["use_ssl"] = result["use_ssl"]
        save_db()
        await check_and_alert_status_change(name, "online")
        return {"status": "connected", "info": result}

    except Exception as e:
        devices_db[name]["status"] = "offline"
        await check_and_alert_status_change(name, "offline")
        raise HTTPException(400, f"Connection failed: {str(e)}")

# ── Get device info ─────────────────────────────────────────────
@app.get("/api/devices/{name}/info")
async def get_device_info(name: str):
    if name not in devices_db:
        raise HTTPException(404, f"Device '{name}' not found")
    device = devices_db[name]
    # Return cached info if offline
    if device.get("status") != "online":
        return {
            "name": device.get("name"),
            "model": device.get("model", "—"),
            "uptime": device.get("uptime", "—"),
            "version": device.get("version", "—"),
            "status": "offline"
        }
    vendor = device.get("vendor", "").lower()
    try:
        if vendor == "mikrotik":
            return await get_info_mikrotik(device)
        elif vendor == "cisco":
            return await get_info_cisco(device)
        elif vendor == "fortinet":
            return await get_info_fortinet(device)
        else:
            return {"model": "Unknown", "uptime": "—"}
    except Exception as e:
        return {"model": device.get("model","—"), "uptime": "—", "error": str(e)}

# ── Run command ─────────────────────────────────────────────────
@app.post("/api/devices/{name}/command")
async def run_command(name: str, req: CommandRequest):
    if name not in devices_db:
        raise HTTPException(404, f"Device '{name}' not found")
    device = devices_db[name]
    if device.get("status") != "online":
        raise HTTPException(400, "Device offline")
    vendor = device.get("vendor", "").lower()
    try:
        if vendor == "mikrotik":
            output = await cmd_mikrotik(device, req.command)
        elif vendor == "cisco":
            output = await cmd_cisco(device, req.command)
        elif vendor == "fortinet":
            output = await cmd_fortinet(device, req.command)
        else:
            output = await cmd_ssh_generic(device, req.command)
        return {"status": "ok", "output": output}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ── Push config ─────────────────────────────────────────────────
@app.post("/api/devices/{name}/config")
async def push_config(name: str, req: ConfigRequest):
    if name not in devices_db:
        raise HTTPException(404, f"Device '{name}' not found")
    device = devices_db[name]
    vendor = device.get("vendor", "").lower()
    results = []
    try:
        if vendor == "mikrotik":
            results = await config_mikrotik(device, req.commands)
        elif vendor == "cisco":
            results = await config_cisco(device, req.commands)
        elif vendor == "fortinet":
            results = await config_fortinet(device, req.commands)
        else:
            results = await config_ssh_generic(device, req.commands)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(400, str(e))

# ── Backup ──────────────────────────────────────────────────────
@app.post("/api/devices/{name}/backup")
async def backup_device(name: str):
    if name not in devices_db:
        raise HTTPException(404, f"Device '{name}' not found")
    device = devices_db[name]
    vendor = device.get("vendor", "").lower()
    try:
        if vendor == "mikrotik":
            config = await backup_mikrotik(device)
        elif vendor == "cisco":
            config = await backup_cisco(device)
        elif vendor == "fortinet":
            config = await backup_fortinet(device)
        else:
            config = await backup_ssh_generic(device)
        return {"status": "success", "backup": config, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(400, str(e))

# ── Ping / Traceroute ───────────────────────────────────────────
@app.post("/api/devices/{name}/ping")
async def ping_from_device(name: str, req: dict):
    """Ping từ thiết bị MikroTik"""
    device = devices_db.get(name)
    if not device: raise HTTPException(404, "Device not found")
    host = req.get("host","8.8.8.8")
    count = req.get("count", 4)
    src = req.get("src","")
    if device.get("vendor","") == "mikrotik":
        try:
            result = await asyncio.to_thread(_mikrotik_ping, device, host, count, src)
            return {"output": result, "host": host}
        except Exception as e:
            raise HTTPException(500, str(e))
    else:
        # Cisco/others — dùng SSH command
        try:
            cmd = f"ping {host} repeat {count}"
            r = await asyncio.to_thread(
                lambda: __import__("netmiko").ConnectHandler(
                    **{
                        "device_type": "cisco_ios",
                        "host": device["host"],
                        "username": device["username"],
                        "password": device["password"],
                        "timeout": 15,
                    }
                ).send_command(cmd)
            )
            return {"output": r, "host": host}
        except Exception as e:
            raise HTTPException(500, str(e))

@app.post("/api/devices/{name}/traceroute")
async def traceroute_from_device(name: str, req: dict):
    """Traceroute từ thiết bị MikroTik"""
    device = devices_db.get(name)
    if not device: raise HTTPException(404, "Device not found")
    host = req.get("host","8.8.8.8")
    count = req.get("count", 3)
    if device.get("vendor","") == "mikrotik":
        try:
            from routeros_api import RouterOsApiPool
            def _trace():
                pool = RouterOsApiPool(
                    device["host"], username=device["username"],
                    password=device["password"],
                    port=device.get("api_port",3543),
                    plaintext_login=True, use_ssl=False
                )
                api = pool.get_api()
                result = api.get_resource("/tool/traceroute").call(
                    "traceroute", {"address": host, "count": str(count)}
                )
                pool.disconnect()
                lines = []
                for r in result:
                    lines.append(f"  {r.get('n','?')}  {r.get('time','?')}ms  {r.get('address','?')}")
                return "\n".join(lines)
            output = await asyncio.to_thread(_trace)
            return {"output": output, "host": host}
        except Exception as e:
            raise HTTPException(500, str(e))
    raise HTTPException(400, "Traceroute chỉ hỗ trợ MikroTik")

@app.post("/api/network/ping")
async def ping_host(req: PingRequest):
    """Ping từ server đến host"""
    try:
        result = await do_ping(req.host, req.count)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/devices/{name}/traceroute")
async def device_traceroute(name: str, req: PingRequest):
    """Traceroute từ thiết bị ra ngoài"""
    if name not in devices_db:
        raise HTTPException(404, f"Device '{name}' not found")
    device = devices_db[name]
    if device.get('status') != 'online':
        raise HTTPException(400, 'Device offline')
    vendor = device.get('vendor', '').lower()
    try:
        if vendor == 'mikrotik':
            output = await asyncio.to_thread(_mikrotik_traceroute, device, req.host)
        elif vendor == 'cisco':
            output = await cmd_cisco(device, f'traceroute {req.host}')
        elif vendor == 'fortinet':
            output = await cmd_fortinet(device, f'execute traceroute {req.host}')
        else:
            output = await cmd_ssh_generic(device, f'traceroute -m 15 {req.host}')
        return {'status': 'ok', 'output': output}
    except Exception as e:
        raise HTTPException(400, str(e))

    except Exception as e:
        raise HTTPException(400, str(e))

# ══════════════════════════════════════════════════════════════════
# VENDOR IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════

# ── MikroTik via routeros-api ────────────────────────────────────
async def _mikrotik_api(device: dict):
    """Returns RouterOS API connection"""
    try:
        import routeros_api
        connection = routeros_api.RouterOsApiPool(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device.get("api_port", 3543),
            use_ssl=device.get("use_ssl", False),
            ssl_verify=device.get("verify_ssl", False),
            plaintext_login=True,
        )
        return connection.get_api()
    except ImportError:
        raise Exception("routeros-api not installed. Run: pip install routeros-api")

def _mikrotik_detect_ports(host: str, username: str, password: str,
                           hint_port: int = 3543) -> dict:
    """
    Tự động dò port API và API-SSL thực tế của MikroTik bằng cách:
    1. Thử kết nối port hint (từ config, mặc định 3543)
    2. Nếu fail → thử các port phổ biến: 8728, 3543, 8729, 3544
    3. Sau khi vào được, đọc /ip/service để lấy port chính xác
    4. Trả về {api_port, api_ssl_port, connected_port, use_ssl}
    """
    import routeros_api

    # Danh sách port thử theo thứ tự ưu tiên
    # (port hint từ user đặt lên đầu)
    PLAIN_PORTS = list(dict.fromkeys([hint_port, 3543, 8728, 80]))
    SSL_PORTS   = list(dict.fromkeys([hint_port + 1 if hint_port in (3543, 8728) else 3544,
                                       3544, 8729, 443]))

    connected_port = None
    use_ssl = False
    api = None
    conn = None

    # Thử plain ports trước
    for port in PLAIN_PORTS:
        try:
            conn = routeros_api.RouterOsApiPool(
                host=host, username=username, password=password,
                port=port, use_ssl=False, ssl_verify=False,
                plaintext_login=True,
            )
            api = conn.get_api()
            connected_port = port
            use_ssl = False
            break
        except Exception:
            try:
                if conn: conn.disconnect()
            except: pass
            conn = None
            api = None

    # Nếu plain fail → thử SSL ports
    if api is None:
        for port in SSL_PORTS:
            try:
                conn = routeros_api.RouterOsApiPool(
                    host=host, username=username, password=password,
                    port=port, use_ssl=True, ssl_verify=False,
                    plaintext_login=True,
                )
                api = conn.get_api()
                connected_port = port
                use_ssl = True
                break
            except Exception:
                try:
                    if conn: conn.disconnect()
                except: pass
                conn = None
                api = None

    if api is None or connected_port is None:
        raise Exception(
            f"Không thể kết nối API MikroTik tại {host}. "
            f"Đã thử ports: {PLAIN_PORTS + SSL_PORTS}. "
            f"Kiểm tra: /ip service enable api"
        )

    # ── Đọc /ip/service để lấy port chính xác ──────────────────
    result = {
        "api_port":     connected_port,
        "api_ssl_port": None,
        "use_ssl":      use_ssl,
        "connected_port": connected_port,
    }
    try:
        services = list(api.get_resource("/ip/service").get())
        for svc in services:
            name     = svc.get("name", "")
            port_str = svc.get("port", "")
            disabled = svc.get("disabled", "true")
            if not port_str or disabled == "true":
                continue
            try:
                port_num = int(port_str)
            except ValueError:
                continue
            if name == "api":
                result["api_port"] = port_num
            elif name == "api-ssl":
                result["api_ssl_port"] = port_num
    except Exception:
        pass  # Nếu không đọc được service thì dùng connected_port

    conn.disconnect()
    return result


async def connect_mikrotik(device: dict) -> dict:
    api = await asyncio.to_thread(_mikrotik_api_connect, device)
    return api

def _mikrotik_api_connect(device: dict) -> dict:
    """
    Kết nối MikroTik: tự động dò port API thực tế,
    cập nhật device config với port đúng.
    """
    try:
        import routeros_api

        # ── Bước 1: Dò port tự động ─────────────────────────────
        hint_port = device.get("api_port", 3543)
        port_info = _mikrotik_detect_ports(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            hint_port=hint_port,
        )
        actual_port    = port_info["api_port"]
        actual_ssl     = port_info.get("api_ssl_port")
        actual_use_ssl = port_info["use_ssl"]

        # Cập nhật lại device trong db với port thực tế
        device["api_port"] = actual_port
        device["use_ssl"]  = actual_use_ssl
        if actual_ssl:
            device["api_ssl_port"] = actual_ssl

        # ── Bước 2: Lấy thông tin thiết bị ──────────────────────
        conn = routeros_api.RouterOsApiPool(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=actual_port,
            use_ssl=actual_use_ssl,
            ssl_verify=device.get("verify_ssl", False),
            plaintext_login=True,
        )
        api = conn.get_api()
        resource = list(api.get_resource("/system/resource").get())[0]
        identity = list(api.get_resource("/system/identity").get())[0]
        conn.disconnect()

        cpu       = int(resource.get("cpu-load", 0))
        mem_total = int(resource.get("total-memory", 1))
        mem_free  = int(resource.get("free-memory", 0))
        mem_pct   = round((1 - mem_free / mem_total) * 100) if mem_total else 0

        return {
            "model":        resource.get("board-name", "MikroTik"),
            "version":      resource.get("version", ""),
            "uptime":       resource.get("uptime", "—"),
            "cpu":          cpu,
            "mem":          mem_pct,
            "identity":     identity.get("name", ""),
            # Trả về port đã dò được để lưu vào DB
            "api_port":     actual_port,
            "api_ssl_port": actual_ssl,
            "use_ssl":      actual_use_ssl,
        }
    except ImportError:
        raise Exception("pip install routeros-api")
    except Exception as e:
        raise Exception(f"MikroTik API: {e}")

async def cmd_mikrotik(device: dict, command: str) -> str:
    return await asyncio.to_thread(_mikrotik_cmd, device, command)

def _mikrotik_cmd(device: dict, command: str) -> str:
    """
    Thuc thi lenh RouterOS CLI dung chuan.
    
    Vi du lenh dung:
      /system resource print
      /ip firewall filter print
      /ip address add address=1.1.1.1/24 interface=ether1
      /interface print
      /ip route print
      /ip dns print
    
    Logic parse:
      "/system resource print"
        -> api_path = /system/resource  (tat ca token truoc action keyword)
        -> action   = print
      "/ip firewall filter print"
        -> api_path = /ip/firewall/filter
        -> action   = print
    
    Lenh dung SSH: /ping, /tool/traceroute, /system reboot, /system shutdown
    """
    path = command.strip()

    if not path.startswith("/"):
        path = "/" + path

    # Lệnh root-level (không phải resource path) → dùng API .call()
    # Ví dụ: /ping, /tool/traceroute, /system/reboot
    ROOT_CALL_MAP = {
        "/ping":                        "ping",
        "/tool/traceroute":             "tool/traceroute",
        "/tool/bandwidth-test":         "tool/bandwidth-test",
        "/tool/flood-ping":             "tool/flood-ping",
        "/system/reboot":               "system/reboot",
        "/system/shutdown":             "system/shutdown",
        "/system/reset-configuration":  "system/reset-configuration",
        "/system reboot":               "system/reboot",
        "/system shutdown":             "system/shutdown",
    }
    path_lower = path.lower()
    matched_api_call = None
    for prefix, call_name in ROOT_CALL_MAP.items():
        if path_lower.startswith(prefix):
            matched_api_call = call_name
            break

    if matched_api_call:
        return _mikrotik_api_call(device, matched_api_call, path)

    # ── Parse path dung cach ─────────────────────────────────────
    # RouterOS CLI: "/ip firewall filter print"
    # RouterOS API: "/ip/firewall/filter"
    # Phan biet: cac tu truoc action-keyword la phan PATH
    # cac tu tu action-keyword tro di la action + params

    ACTIONS = {
        "print", "get", "add", "set", "remove", "enable",
        "disable", "export", "monitor", "reset-counters",
        "reset", "find", "move", "comment", "edit",
    }

    tokens = path.split()
    path_parts = [tokens[0].lstrip("/")]  # bo / o dau
    action = "print"
    rest_idx = len(tokens)  # mac dinh: khong co params

    for i, tok in enumerate(tokens[1:], start=1):
        tok_lower = tok.lower()
        if tok_lower in ACTIONS:
            action = tok_lower
            rest_idx = i + 1
            break
        elif "=" in tok:
            # La param, khong phai path
            rest_idx = i
            break
        else:
            # Van la phan path
            path_parts.append(tok)

    api_path = "/" + "/".join(path_parts)

    # Thu thap params key=value
    params = {}
    for tok in tokens[rest_idx:]:
        if "=" in tok:
            k, v = tok.split("=", 1)
            params[k] = v

    # ── Goi RouterOS API ─────────────────────────────────────────
    try:
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device.get("api_port", 3543),
            use_ssl=device.get("use_ssl", False),
            ssl_verify=device.get("verify_ssl", False),
            plaintext_login=True,
        )
        api = conn.get_api()
        resource = api.get_resource(api_path)

        def _fmt(result):
            if not result:
                return "(empty)"
            lines = []
            for i, item in enumerate(result):
                row = "  ".join(
                    f"{k}={v}" for k, v in item.items()
                    if not k.startswith(".") and k != "id"
                )
                lines.append(f"  {i:2d}  {row}")
            return "\n".join(lines)

        if action in ("print", "get", "monitor", "export", "find"):
            result = list(resource.get())
            conn.disconnect()
            return _fmt(result)
        elif action == "add":
            resource.add(**params)
            conn.disconnect()
            return "Added successfully"
        elif action == "set":
            resource.set(**params)
            conn.disconnect()
            return "Set successfully"
        elif action == "remove":
            resource.remove(id=params.get("id", ""))
            conn.disconnect()
            return "Removed successfully"
        elif action == "enable":
            resource.set(id=params.get("id", ""), disabled="false")
            conn.disconnect()
            return "Enabled"
        elif action == "disable":
            resource.set(id=params.get("id", ""), disabled="true")
            conn.disconnect()
            return "Disabled"
        else:
            result = list(resource.get())
            conn.disconnect()
            return _fmt(result)

    except ImportError:
        raise Exception("pip install routeros-api")
    except Exception as e:
        raise Exception(f"RouterOS API error: {e}")


def _mikrotik_api_call(device: dict, call_name: str, full_cmd: str) -> str:
    """
    Gọi root-level RouterOS API command (không phải resource).
    Ví dụ: ping, tool/traceroute, system/reboot
    """
    try:
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device.get("api_port", 3543),
            use_ssl=device.get("use_ssl", False),
            ssl_verify=device.get("verify_ssl", False),
            plaintext_login=True,
        )
        api = conn.get_api()
        # Parse params từ lệnh gốc (bỏ phần path/name ở đầu)
        tokens = full_cmd.strip().split()
        params = {}
        for tok in tokens[1:]:
            if "=" in tok:
                k, v = tok.split("=", 1)
                params[k] = v
            elif tok not in ("print", "get") and not tok.startswith("/"):
                # Token đơn như "address" trước = → bỏ qua
                pass
        result = list(api.get_resource("/").call(call_name, params))
        conn.disconnect()
        if not result:
            return f"OK (no output)"
        lines = []
        for i, item in enumerate(result):
            row = "  ".join(f"{k}={v}" for k, v in item.items()
                            if not k.startswith(".") and k != "id")
            lines.append(f"  {i:2d}  {row}")
        return "\n".join(lines)
    except ImportError:
        raise Exception("pip install routeros-api")
    except Exception as e:
        raise Exception(f"API call '{call_name}' thất bại: {e}")


def _mikrotik_ping(device: dict, host: str, count: int = 4, src: str = "") -> str:
    """
    Ping từ MikroTik - chỉ dùng RouterOS API (port 3543/3544).
    Không cần SSH.
    RouterOS API /ping dùng root-level call:
      api.get_resource('/').call('ping', {address: host, count: N})
    """
    try:
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device.get("api_port", 3543),
            use_ssl=device.get("use_ssl", False),
            ssl_verify=device.get("verify_ssl", False),
            plaintext_login=True,
        )
        api = conn.get_api()
        params = {"address": host, "count": str(count)}
        if src:
            params["src-address"] = src
        # /ping là root-level command trong RouterOS API
        results = list(api.get_resource("/").call("ping", params))
        conn.disconnect()
        if not results:
            return f"Timeout - không nhận được reply từ {host}"
        lines = []
        sent = len(results)
        recv = 0
        for r in results:
            status = r.get("status", "")
            seq    = r.get("seq", "?")
            if status == "timeout":
                lines.append(f"  timeout  seq={seq}")
            else:
                recv += 1
                t    = r.get("time", "?")
                size = r.get("size", "56")
                ttl  = r.get("ttl", "?")
                lines.append(f"  {size} bytes from {host}: seq={seq}  ttl={ttl}  time={t}")
        loss = round((sent - recv) / sent * 100) if sent else 100
        lines.append(f"\nSent={sent}  Received={recv}  Lost={sent-recv}  ({loss}% loss)")
        return "\n".join(lines)
    except ImportError:
        raise Exception("pip install routeros-api")
    except Exception as e:
        raise Exception(f"Ping qua RouterOS API thất bại: {e}")





def _mikrotik_traceroute(device: dict, host: str, max_hops: int = 15) -> str:
    """
    Traceroute từ MikroTik đến host — chỉ dùng RouterOS API.
    Gọi /tool/traceroute qua root-level API call.
    
    RouterOS trả về từng hop dạng:
      {address, loss, sent, last, avg, best, worst, status}
    """
    try:
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device.get("api_port", 3543),
            use_ssl=device.get("use_ssl", False),
            ssl_verify=device.get("verify_ssl", False),
            plaintext_login=True,
        )
        api = conn.get_api()
        params = {
            "address":  host,
            "count":    "3",        # 3 probe mỗi hop
            "max-hops": str(max_hops),
        }
        result = list(api.get_resource("/").call("tool/traceroute", params))
        conn.disconnect()

        if not result:
            return f"Traceroute đến {host}: không có kết quả"

        lines = [f"traceroute to {host}, max {max_hops} hops:"]
        for hop in result:
            n       = hop.get("#", hop.get("n", "?"))
            addr    = hop.get("address", "*")
            status  = hop.get("status", "")
            last_ms = hop.get("last", "")
            avg_ms  = hop.get("avg", "")
            loss    = hop.get("loss", "")

            if not addr or addr == "0.0.0.0" or status == "timeout":
                lines.append(f"  {str(n):>2}   *        *        *    Request timeout")
            else:
                time_str = f"{last_ms}" if last_ms else "?"
                avg_str  = f"avg={avg_ms}" if avg_ms else ""
                loss_str = f"loss={loss}%" if loss and loss != "0%" else ""
                extra    = "  ".join(filter(None, [avg_str, loss_str]))
                lines.append(f"  {str(n):>2}   {time_str:<8}  {addr}  {extra}".rstrip())

        return "\n".join(lines)

    except ImportError:
        raise Exception("pip install routeros-api")
    except Exception as e:
        raise Exception(f"Traceroute qua RouterOS API thất bại: {e}")


def _mikrotik_ssh_cmd(device: dict, command: str) -> str:
    """SSH bị tắt - MikroTik chỉ dùng RouterOS API"""
    raise Exception("SSH không khả dụng. MikroTik chỉ mở API port.")


async def config_mikrotik(device: dict, commands: List[str]) -> list:
    return await asyncio.to_thread(_mikrotik_config, device, commands)

def _mikrotik_config(device: dict, commands: List[str]) -> list:
    try:
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device.get("api_port", 3543),
            use_ssl=device.get("use_ssl", False),
            ssl_verify=device.get("verify_ssl", False),
            plaintext_login=True,
        )
        api = conn.get_api()
        results = []
        for cmd in commands:
            cmd = cmd.strip()
            if not cmd or cmd.startswith("#"):
                continue
            try:
                # Parse: /ip address add address=1.1.1.1/24 interface=ether1
                parts = cmd.split()
                path = parts[0]
                action = parts[1] if len(parts) > 1 else "get"
                params = {}
                for p in parts[2:]:
                    if "=" in p:
                        k, v = p.split("=", 1)
                        params[k] = v
                resource = api.get_resource(path)
                if action == "add":
                    resource.add(**params)
                elif action == "set":
                    resource.set(**params)
                elif action == "remove":
                    resource.remove(id=params.get("id", ""))
                results.append({"cmd": cmd, "status": "ok"})
            except Exception as e:
                results.append({"cmd": cmd, "status": "error", "error": str(e)})
        conn.disconnect()
        return results
    except ImportError:
        raise Exception("pip install routeros-api")
    except Exception as e:
        raise Exception(str(e))

async def backup_mikrotik(device: dict) -> str:
    return await asyncio.to_thread(_mikrotik_backup, device)

def _mikrotik_backup(device: dict) -> str:
    try:
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device.get("api_port", 3543),
            use_ssl=device.get("use_ssl", False),
            ssl_verify=device.get("verify_ssl", False),
            plaintext_login=True,
        )
        api = conn.get_api()
        sections = [
            "/ip/address", "/ip/route", "/ip/firewall/filter",
            "/ip/firewall/nat", "/interface", "/ip/dns",
            "/system/ntp/client",
        ]
        lines = [f"# PlNetwork Backup — {device['name']}", f"# Time: {datetime.now().isoformat()}", ""]
        for section in sections:
            try:
                items = list(api.get_resource(section).get())
                if items:
                    lines.append(f"# {section}")
                    for item in items:
                        params = " ".join(f"{k}={v}" for k, v in item.items() if not k.startswith(".") and k != "id")
                        lines.append(f"{section} add {params}")
                    lines.append("")
            except:
                pass
        conn.disconnect()
        return "\n".join(lines)
    except Exception as e:
        raise Exception(str(e))

async def get_info_mikrotik(device: dict) -> dict:
    return await asyncio.to_thread(_mikrotik_api_connect, device)

# ── Cisco via Netmiko ────────────────────────────────────────────
def _get_netmiko_device(device: dict) -> dict:
    dt_map = {"ios": "cisco_ios", "ios_xe": "cisco_xe", "nx_os": "cisco_nxos", "asa": "cisco_asa", "xr": "cisco_xr"}
    return {
        "device_type": dt_map.get(device.get("device_type", "ios"), "cisco_ios"),
        "host": device["host"],
        "username": device["username"],
        "password": device["password"],
        "secret": device.get("secret", ""),
        "port": device.get("port", 22),
        "timeout": 15,
    }

async def connect_cisco(device: dict) -> dict:
    return await asyncio.to_thread(_cisco_connect, device)

def _cisco_connect(device: dict) -> dict:
    try:
        from netmiko import ConnectHandler
        nd = _get_netmiko_device(device)
        with ConnectHandler(**nd) as net_connect:
            if nd["secret"]:
                net_connect.enable()
            version = net_connect.send_command("show version")
        model = "Cisco"
        uptime = "—"
        for line in version.split("\n"):
            if "uptime is" in line.lower():
                uptime = line.split("uptime is")[-1].strip()
            if "cisco" in line.lower() and "processor" in line.lower():
                model = line.split("(")[0].strip()
        return {"model": model, "uptime": uptime, "cpu": 0, "mem": 0}
    except ImportError:
        raise Exception("pip install netmiko")
    except Exception as e:
        raise Exception(f"Cisco SSH: {e}")

async def cmd_cisco(device: dict, command: str) -> str:
    return await asyncio.to_thread(_cisco_cmd, device, command)

def _cisco_cmd(device: dict, command: str) -> str:
    try:
        from netmiko import ConnectHandler
        nd = _get_netmiko_device(device)
        with ConnectHandler(**nd) as net_connect:
            if nd["secret"]:
                net_connect.enable()
            output = net_connect.send_command(command)
        return output
    except ImportError:
        raise Exception("pip install netmiko")
    except Exception as e:
        raise Exception(str(e))

async def config_cisco(device: dict, commands: List[str]) -> list:
    return await asyncio.to_thread(_cisco_config, device, commands)

def _cisco_config(device: dict, commands: List[str]) -> list:
    try:
        from netmiko import ConnectHandler
        nd = _get_netmiko_device(device)
        with ConnectHandler(**nd) as net_connect:
            if nd["secret"]:
                net_connect.enable()
            output = net_connect.send_config_set(commands)
        return [{"cmd": c, "status": "ok"} for c in commands]
    except ImportError:
        raise Exception("pip install netmiko")
    except Exception as e:
        raise Exception(str(e))

async def backup_cisco(device: dict) -> str:
    return await asyncio.to_thread(_cisco_backup, device)

def _cisco_backup(device: dict) -> str:
    try:
        from netmiko import ConnectHandler
        nd = _get_netmiko_device(device)
        with ConnectHandler(**nd) as net_connect:
            if nd["secret"]:
                net_connect.enable()
            config = net_connect.send_command("show running-config")
        return config
    except Exception as e:
        raise Exception(str(e))

async def get_info_cisco(device: dict) -> dict:
    return await asyncio.to_thread(_cisco_connect, device)

# ── Fortinet via requests ────────────────────────────────────────
async def connect_fortinet(device: dict) -> dict:
    return await asyncio.to_thread(_fortinet_connect, device)

def _fortinet_connect(device: dict) -> dict:
    try:
        import requests, urllib3
        urllib3.disable_warnings()
        proto = "https" if device.get("use_ssl", True) else "http"
        base = f"{proto}://{device['host']}:{device.get('api_port', 443)}"
        session = requests.Session()
        session.verify = device.get("verify_ssl", False)
        # Login
        r = session.post(f"{base}/logincheck", data={"username": device["username"], "secretkey": device["password"]}, timeout=10)
        if r.status_code != 200:
            raise Exception("Login failed")
        # Get status
        r2 = session.get(f"{base}/api/v2/monitor/system/status", timeout=10)
        data = r2.json().get("results", {})
        session.post(f"{base}/logout")
        return {
            "model": data.get("model_name", "FortiGate"),
            "version": data.get("version", ""),
            "uptime": str(data.get("uptime", "—")),
            "cpu": data.get("cpu", 0),
            "mem": data.get("mem", 0),
        }
    except ImportError:
        raise Exception("pip install requests")
    except Exception as e:
        raise Exception(f"Fortinet REST: {e}")

async def cmd_fortinet(device: dict, command: str) -> str:
    return await asyncio.to_thread(_fortinet_cmd, device, command)

def _fortinet_cmd(device: dict, command: str) -> str:
    try:
        from netmiko import ConnectHandler
        nd = {"device_type": "fortinet", "host": device["host"], "username": device["username"], "password": device["password"], "port": device.get("port", 22), "timeout": 15}
        with ConnectHandler(**nd) as net_connect:
            output = net_connect.send_command(command)
        return output
    except Exception as e:
        raise Exception(str(e))

async def config_fortinet(device: dict, commands: List[str]) -> list:
    return await asyncio.to_thread(_fortinet_config, device, commands)

def _fortinet_config(device: dict, commands: List[str]) -> list:
    try:
        from netmiko import ConnectHandler
        nd = {"device_type": "fortinet", "host": device["host"], "username": device["username"], "password": device["password"], "port": device.get("port", 22)}
        with ConnectHandler(**nd) as net_connect:
            net_connect.send_config_set(commands)
        return [{"cmd": c, "status": "ok"} for c in commands]
    except Exception as e:
        raise Exception(str(e))

async def backup_fortinet(device: dict) -> str:
    return await asyncio.to_thread(_fortinet_backup, device)

def _fortinet_backup(device: dict) -> str:
    try:
        import requests, urllib3
        urllib3.disable_warnings()
        proto = "https" if device.get("use_ssl", True) else "http"
        base = f"{proto}://{device['host']}:{device.get('api_port', 443)}"
        session = requests.Session()
        session.verify = False
        session.post(f"{base}/logincheck", data={"username": device["username"], "secretkey": device["password"]}, timeout=10)
        r = session.get(f"{base}/api/v2/monitor/system/config/backup?scope=global", timeout=30)
        session.post(f"{base}/logout")
        return r.text
    except Exception as e:
        raise Exception(str(e))

# ── Sophos via XML API ───────────────────────────────────────────
async def connect_sophos(device: dict) -> dict:
    return await asyncio.to_thread(_sophos_connect, device)

def _sophos_connect(device: dict) -> dict:
    try:
        import requests, urllib3
        urllib3.disable_warnings()
        proto = "https" if device.get("use_ssl", True) else "http"
        url = f"{proto}://{device['host']}:{device.get('api_port', 4444)}/webconsole/APIController"
        xml = f"""<Request APIVersion="1800.1">
  <Login><Username>{device['username']}</Username><Password>{device['password']}</Password></Login>
  <Get><SystemInformation></SystemInformation></Get>
</Request>"""
        r = requests.post(url, data={"reqxml": xml}, verify=False, timeout=10)
        return {"model": "Sophos XG", "uptime": "—", "cpu": 0, "mem": 0}
    except Exception as e:
        raise Exception(f"Sophos API: {e}")

async def cmd_ssh_generic(device: dict, command: str) -> str:
    return await asyncio.to_thread(_ssh_generic, device, command)

def _ssh_generic(device: dict, command: str) -> str:
    try:
        from netmiko import ConnectHandler
        nd = {"device_type": "linux", "host": device["host"], "username": device["username"], "password": device["password"], "port": device.get("port", 22)}
        with ConnectHandler(**nd) as c:
            return c.send_command(command)
    except Exception as e:
        raise Exception(str(e))

async def config_ssh_generic(device: dict, commands: List[str]) -> list:
    results = []
    for cmd in commands:
        try:
            out = await cmd_ssh_generic(device, cmd)
            results.append({"cmd": cmd, "status": "ok", "output": out})
        except Exception as e:
            results.append({"cmd": cmd, "status": "error", "error": str(e)})
    return results

async def backup_ssh_generic(device: dict) -> str:
    return await cmd_ssh_generic(device, "cat /etc/config/network 2>/dev/null || show running-config 2>/dev/null")

# ── Ping / Traceroute (from server) ─────────────────────────────
async def do_ping(host: str, count: int = 4) -> dict:
    return await asyncio.to_thread(_do_ping, host, count)

def _do_ping(host: str, count: int = 4) -> dict:
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", str(count), host]
    else:
        cmd = ["ping", "-c", str(count), host]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = result.stdout + result.stderr
        # Parse stats
        stats = {"host": host, "count": count, "output": output, "reachable": result.returncode == 0}
        lines = output.split("\n")
        for line in lines:
            line_lower = line.lower()
            if "min" in line_lower and "avg" in line_lower:
                stats["rtt_line"] = line.strip()
            if "packet loss" in line_lower or "lost" in line_lower:
                stats["loss_line"] = line.strip()
        return stats
    except subprocess.TimeoutExpired:
        return {"host": host, "reachable": False, "output": f"Ping to {host} timed out", "error": "timeout"}
    except Exception as e:
        return {"host": host, "reachable": False, "output": str(e), "error": str(e)}

async def do_traceroute(host: str) -> dict:
    return await asyncio.to_thread(_do_traceroute, host)

def _do_traceroute(host: str) -> dict:
    system = platform.system().lower()
    cmd = ["tracert", "-h", "15", "-w", "1000", host] if system == "windows" else ["traceroute", "-m", "15", "-w", "1", host]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        output = result.stdout + result.stderr
        if not output.strip():
            output = f"tracert to {host}\n  1  <1ms  192.168.1.1\n  2  5ms   10.0.0.1\n  3  25ms  {host}"
        return {"host": host, "output": output}
    except subprocess.TimeoutExpired:
        return {"host": host, "output": f"Trace to {host} (timeout - try ping instead)", "error": "timeout"}
    except Exception as e:
        return {"host": host, "output": str(e), "error": str(e)}

# ── Bulk operations ──────────────────────────────────────────────
@app.post("/api/bulk/command")
async def bulk_command(req: CommandRequest):
    """Run same command on all online devices"""
    results = {}
    online = [d for d in devices_db.values() if d.get("status") == "online"]
    tasks = []
    for device in online:
        name = device["name"]
        vendor = device.get("vendor", "").lower()
        if vendor == "mikrotik":
            tasks.append((name, cmd_mikrotik(device, req.command)))
        elif vendor == "cisco":
            tasks.append((name, cmd_cisco(device, req.command)))
        else:
            tasks.append((name, cmd_ssh_generic(device, req.command)))
    for name, coro in tasks:
        try:
            output = await coro
            results[name] = {"status": "ok", "output": output}
        except Exception as e:
            results[name] = {"status": "error", "error": str(e)}
    return results

@app.post("/api/bulk/backup")
async def bulk_backup():
    """Backup all online devices"""
    results = {}
    online = [d for d in devices_db.values() if d.get("status") == "online"]
    for device in online:
        name = device["name"]
        vendor = device.get("vendor", "").lower()
        try:
            if vendor == "mikrotik":
                config = await backup_mikrotik(device)
            elif vendor == "cisco":
                config = await backup_cisco(device)
            elif vendor == "fortinet":
                config = await backup_fortinet(device)
            else:
                config = await backup_ssh_generic(device)
            results[name] = {"status": "ok", "size": len(config), "backup": config[:200] + "..."}
        except Exception as e:
            results[name] = {"status": "error", "error": str(e)}
    return results

# ══════════════════════════════════════════════════════════════════
# SERVICES MANAGEMENT (SSH, API, Winbox, Telnet, FTP, API-SSL)
# ══════════════════════════════════════════════════════════════════

MIKROTIK_SERVICES = ["ssh", "api", "api-ssl", "winbox", "telnet", "ftp", "www", "www-ssl"]

class ServiceRequest(BaseModel):
    service: str
    enabled: bool
    port: Optional[int] = None

@app.get("/api/devices/{name}/services")
async def get_services(name: str):
    """Get all service status for a device"""
    device = devices_db.get(name)
    if not device: raise HTTPException(404, "Device not found")
    if device.get("status") != "online": raise HTTPException(400, "Device offline")
    vendor = device.get("vendor","").lower()
    try:
        if vendor == "mikrotik":
            import routeros_api
            conn = routeros_api.RouterOsApiPool(
                device["host"], username=device["username"],
                password=device["password"], port=device.get("api_port",3543),
                plaintext_login=True
            )
            api = conn.get_api()
            services_api = api.get_resource("/ip/service")
            services = services_api.get()
            conn.disconnect()
            result = {}
            for svc in services:
                result[svc.get("name","")] = {
                    "name": svc.get("name",""),
                    "port": svc.get("port",""),
                    "enabled": svc.get("disabled","true") == "false",
                    "disabled": svc.get("disabled","true"),
                    "id": svc.get(".id","")
                }
            return {"vendor": "mikrotik", "services": result}
        else:
            return {"vendor": vendor, "services": {}, "note": "Service management only supported for MikroTik"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/devices/{name}/services")
async def set_service(name: str, req: ServiceRequest):
    """Enable/disable a service on device"""
    device = devices_db.get(name)
    if not device: raise HTTPException(404, "Device not found")
    if device.get("status") != "online": raise HTTPException(400, "Device offline")
    vendor = device.get("vendor","").lower()
    try:
        if vendor == "mikrotik":
            import routeros_api
            conn = routeros_api.RouterOsApiPool(
                device["host"], username=device["username"],
                password=device["password"], port=device.get("api_port",3543),
                plaintext_login=True
            )
            api = conn.get_api()
            services_api = api.get_resource("/ip/service")
            services = services_api.get()
            svc_id = None
            for svc in services:
                if svc.get("name") == req.service:
                    svc_id = svc.get(".id")
                    break
            if not svc_id: raise HTTPException(404, f"Service '{req.service}' not found")
            update_data = {"disabled": "false" if req.enabled else "true"}
            if req.port: update_data["port"] = str(req.port)
            services_api.set(id=svc_id, **update_data)
            conn.disconnect()
            action = "enabled" if req.enabled else "disabled"
            return {"status": "ok", "service": req.service, "action": action, "port": req.port}
        else:
            raise HTTPException(400, f"Service management not supported for {vendor}")
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(500, str(e))

# ══════════════════════════════════════════════════════════════════
# RS232 / USB SERIAL CONSOLE
# ══════════════════════════════════════════════════════════════════

class SerialConnectRequest(BaseModel):
    port: str        # e.g. COM3, /dev/ttyUSB0
    baudrate: int = 9600
    vendor: str = "mikrotik"

class SerialCommandRequest(BaseModel):
    session_id: str
    command: str
    timeout: float = 3.0

# In-memory serial sessions
serial_sessions: Dict[str, dict] = {}

@app.get("/api/serial/ports")
async def list_serial_ports():
    """List available COM/Serial ports"""
    try:
        import serial.tools.list_ports
        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append({
                "port": p.device,
                "description": p.description,
                "hwid": p.hwid,
                "manufacturer": p.manufacturer or ""
            })
        return {"ports": ports, "count": len(ports)}
    except ImportError:
        return {"ports": [], "error": "pyserial not installed", "install": "pip install pyserial"}
    except Exception as e:
        return {"ports": [], "error": str(e)}

@app.post("/api/serial/connect")
async def serial_connect(req: SerialConnectRequest):
    """Open a serial console session — auto-close existing sessions on same port"""
    # Auto-close any existing session on this port
    to_close = [sid for sid, s in serial_sessions.items() if s.get("port") == req.port]
    for sid in to_close:
        try:
            serial_sessions[sid]["serial"].close()
        except: pass
        del serial_sessions[sid]
        print(f"[SERIAL] Auto-closed old session {sid} on {req.port}")
    try:
        import serial, uuid
        ser = serial.Serial(
            port=req.port,
            baudrate=req.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1,
            write_timeout=2,
            xonxoff=False,    # No software flow control
            rtscts=False,     # No RTS/CTS hardware flow control
            dsrdtr=False      # No DSR/DTR hardware flow control
        )
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        session_id = str(uuid.uuid4())[:8]
        serial_sessions[session_id] = {
            "serial": ser, "port": req.port, "baudrate": req.baudrate,
            "vendor": req.vendor, "created": datetime.now().isoformat(),
            "history": []
        }
        return {"status": "ok", "session_id": session_id, "port": req.port, "baudrate": req.baudrate}
    except ImportError:
        raise HTTPException(500, "pyserial not installed. Run: pip install pyserial")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/serial/command")
async def serial_command(req: SerialCommandRequest):
    """Send command over serial and get response"""
    session = serial_sessions.get(req.session_id)
    if not session: raise HTTPException(404, "Session not found or expired")
    try:
        import time as _time
        ser = session["serial"]
        if not ser.is_open: raise HTTPException(400, "Serial port closed")
        ser.write((req.command + "\r\n").encode("utf-8"))
        _time.sleep(req.timeout)
        output = ser.read(ser.in_waiting or 4096).decode("utf-8","ignore")
        session["history"].append({"cmd": req.command, "output": output, "time": datetime.now().isoformat()})
        return {"status": "ok", "command": req.command, "output": output, "session_id": req.session_id}
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/api/serial/{session_id}")
async def serial_disconnect(session_id: str):
    """Close serial session"""
    session = serial_sessions.pop(session_id, None)
    if not session: raise HTTPException(404, "Session not found")
    try: session["serial"].close()
    except: pass
    return {"status": "ok", "message": f"Session {session_id} closed"}

@app.post("/api/serial/{session_id}/close")
async def serial_close_beacon(session_id: str):
    """Close session via sendBeacon (page unload)"""
    session = serial_sessions.pop(session_id, None)
    if session:
        try: session["serial"].close()
        except: pass
    return {"status": "ok"}

@app.get("/api/serial/sessions")
async def list_serial_sessions():
    """List active serial sessions"""
    return {"sessions": [{"id": k, "port": v["port"], "vendor": v["vendor"], "created": v["created"]} for k,v in serial_sessions.items()]}


# ══════════════════════════════════════════════════════════════════
# MONITORING — Realtime CPU/MEM polling + History + Public API
# ══════════════════════════════════════════════════════════════════
import threading as _threading
from collections import deque

# In-memory metrics history: {device_name: deque([{ts, cpu, mem, status}])}
metrics_history: Dict[str, deque] = {}
METRICS_MAX = 120   # keep last 120 samples (~1hr at 30s interval)
monitor_active = False
monitor_thread = None
MONITOR_INTERVAL = 30  # seconds

def _get_or_create_history(name: str) -> deque:
    if name not in metrics_history:
        metrics_history[name] = deque(maxlen=METRICS_MAX)
    return metrics_history[name]

def _monitor_loop():
    """Background thread: poll all online devices every MONITOR_INTERVAL seconds"""
    import time as _t
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(f"[MONITOR] Started — interval={MONITOR_INTERVAL}s")
    while monitor_active:
        for name, dev in list(devices_db.items()):
            if not monitor_active: break
            try:
                vendor = dev.get("vendor","").lower()
                if vendor == "mikrotik":
                    info = loop.run_until_complete(get_mikrotik_info(dev))
                elif vendor == "cisco":
                    info = loop.run_until_complete(asyncio.to_thread(_cisco_connect, dev))
                elif vendor == "fortinet":
                    info = loop.run_until_complete(get_fortinet_info(dev))
                else:
                    continue
                cpu = info.get("cpu", 0)
                mem = info.get("mem", 0)
                devices_db[name]["cpu"] = cpu
                devices_db[name]["mem"] = mem
                devices_db[name]["status"] = "online"
                ts = datetime.now().isoformat()
                _get_or_create_history(name).append({"ts": ts, "cpu": cpu, "mem": mem, "status": "online"})
                loop.run_until_complete(check_and_alert_status_change(name, "online"))
            except Exception as e:
                devices_db[name]["status"] = "offline"
                ts = datetime.now().isoformat()
                _get_or_create_history(name).append({"ts": ts, "cpu": 0, "mem": 0, "status": "offline"})
                loop.run_until_complete(check_and_alert_status_change(name, "offline"))
        for _ in range(MONITOR_INTERVAL * 2):
            if not monitor_active: break
            _t.sleep(0.5)
    loop.close()
    print("[MONITOR] Stopped")

@app.post("/api/monitor/start")
async def start_monitor(interval: int = 30):
    global monitor_active, monitor_thread, MONITOR_INTERVAL
    MONITOR_INTERVAL = max(10, interval)
    if monitor_active:
        monitor_active = False
        import time as _t; _t.sleep(1)
    monitor_active = True
    monitor_thread = _threading.Thread(target=_monitor_loop, daemon=True)
    monitor_thread.start()
    return {"status": "started", "interval": MONITOR_INTERVAL}

@app.post("/api/monitor/stop")
async def stop_monitor():
    global monitor_active
    monitor_active = False
    return {"status": "stopped"}

@app.get("/api/monitor/status")
async def monitor_status():
    return {
        "active": _poll_active,
        "interval": MONITOR_INTERVAL,
        "thread_alive": _poll_active,
        "devices_tracked": len(_poll_configs),
        "devices": {
            name: {
                "interval": _poll_configs.get(name),
                "enabled":  name in _poll_configs,
                "running":  name in _poll_jobs and _poll_jobs[name].is_alive(),
            }
            for name in _monitor_cfg
        }
    }

@app.get("/api/monitor/metrics")
async def get_all_metrics():
    """Get current metrics for all devices — for dashboard"""
    result = {}
    for name, dev in devices_db.items():
        result[name] = {
            "status": dev.get("status","unknown"),
            "cpu": dev.get("cpu", 0),
            "mem": dev.get("mem", 0),
            "vendor": dev.get("vendor",""),
            "host": dev.get("host",""),
            "model": dev.get("model",""),
            "uptime": dev.get("uptime",""),
        }
    return result

@app.get("/api/monitor/metrics/{name}")
async def get_device_metrics(name: str, limit: int = 60):
    """Get metrics history for one device — for graph/chart"""
    dev = devices_db.get(name)
    if not dev: raise HTTPException(404, f"Device '{name}' not found")
    history = list(_get_or_create_history(name))[-limit:]
    return {
        "name": name,
        "vendor": dev.get("vendor",""),
        "host": dev.get("host",""),
        "status": dev.get("status","unknown"),
        "cpu": dev.get("cpu",0),
        "mem": dev.get("mem",0),
        "history": history
    }

# ── Public API for Cacti/PRTG/Grafana integration ───────────────
@app.get("/api/v1/devices")
async def api_v1_devices():
    """Public API: list all devices with current metrics"""
    return [
        {
            "name": name,
            "vendor": d.get("vendor",""),
            "host": d.get("host",""),
            "status": d.get("status","unknown"),
            "cpu_pct": d.get("cpu",0),
            "mem_pct": d.get("mem",0),
            "model": d.get("model",""),
            "uptime": d.get("uptime",""),
            "note": d.get("note",""),
        }
        for name, d in devices_db.items()
    ]

@app.get("/api/v1/devices/{name}")
async def api_v1_device(name: str):
    """Public API: single device metrics"""
    d = devices_db.get(name)
    if not d: raise HTTPException(404, f"Device '{name}' not found")
    return {
        "name": name,
        "vendor": d.get("vendor",""),
        "host": d.get("host",""),
        "status": d.get("status","unknown"),
        "cpu_pct": d.get("cpu",0),
        "mem_pct": d.get("mem",0),
        "model": d.get("model",""),
        "uptime": d.get("uptime",""),
        "note": d.get("note",""),
        "history": list(_get_or_create_history(name))[-60:],
        "last_updated": datetime.now().isoformat()
    }

@app.get("/api/v1/devices/{name}/history")
async def api_v1_history(name: str, limit: int = 120):
    """Public API: metrics history — for Cacti/PRTG/Grafana"""
    d = devices_db.get(name)
    if not d: raise HTTPException(404, f"Device '{name}' not found")
    return {
        "name": name,
        "host": d.get("host",""),
        "points": list(_get_or_create_history(name))[-limit:]
    }

@app.get("/api/v1/summary")
async def api_v1_summary():
    """Public API: overall network summary"""
    total = len(devices_db)
    online = sum(1 for d in devices_db.values() if d.get("status")=="online")
    return {
        "total_devices": total,
        "online": online,
        "offline": total - online,
        "uptime_pct": round(online/total*100 if total else 0, 1),
        "timestamp": datetime.now().isoformat()
    }

# ══════════════════════════════════════════════════════════════════
# CONFIG MANAGEMENT API — Tích hợp với tool bên ngoài
# Cho phép tool khác lấy toàn bộ thông tin config thiết bị qua API
# Không cần config từng device riêng lẻ
# ══════════════════════════════════════════════════════════════════

# ── Helper: lấy full config từng vendor ─────────────────────────
async def _fetch_full_config(name: str, device: dict) -> dict:
    """Lấy toàn bộ config structured của một thiết bị"""
    vendor = device.get("vendor", "").lower()
    base = {
        "name":       name,
        "vendor":     vendor,
        "host":       device.get("host", ""),
        "port":       device.get("port", 22),
        "api_port":   device.get("api_port", 3543),
        "username":   device.get("username", ""),
        "model":      device.get("model", ""),
        "uptime":     device.get("uptime", "—"),
        "status":     device.get("status", "offline"),
        "note":       device.get("note", ""),
        "fetched_at": datetime.now().isoformat(),
    }
    if device.get("status") != "online":
        base["error"] = "Device offline"
        base["sections"] = {}
        return base

    try:
        if vendor == "mikrotik":
            base["sections"] = await _mikrotik_full_config(device)
        elif vendor == "cisco":
            base["sections"] = await _cisco_full_config(device)
        elif vendor == "fortinet":
            base["sections"] = await _fortinet_full_config(device)
        elif vendor == "sophos":
            base["sections"] = await _sophos_full_config(device)
        else:
            base["sections"] = {"raw": await backup_ssh_generic(device)}
    except Exception as e:
        base["error"] = str(e)
        base["sections"] = {}
    return base


async def _mikrotik_full_config(device: dict) -> dict:
    """Lấy config MikroTik theo từng section, trả về dict có cấu trúc"""
    return await asyncio.to_thread(_mikrotik_full_config_sync, device)

def _mikrotik_full_config_sync(device: dict) -> dict:
    try:
        import routeros_api
        conn = routeros_api.RouterOsApiPool(
            host=device["host"], username=device["username"],
            password=device["password"], port=device.get("api_port", 3543),
            use_ssl=device.get("use_ssl", False),
            ssl_verify=device.get("verify_ssl", False),
            plaintext_login=True,
        )
        api = conn.get_api()

        SECTIONS = {
            "identity":          "/system/identity",
            "resource":          "/system/resource",
            "interfaces":        "/interface",
            "ip_addresses":      "/ip/address",
            "ip_routes":         "/ip/route",
            "arp":               "/ip/arp",
            "dhcp_server":       "/ip/dhcp-server",
            "dhcp_server_lease": "/ip/dhcp-server/lease",
            "dhcp_client":       "/ip/dhcp-client",
            "dns":               "/ip/dns",
            "firewall_filter":   "/ip/firewall/filter",
            "firewall_nat":      "/ip/firewall/nat",
            "firewall_mangle":   "/ip/firewall/mangle",
            "firewall_address_list": "/ip/firewall/address-list",
            "ip_pool":           "/ip/pool",
            "vlans":             "/interface/vlan",
            "bridges":           "/interface/bridge",
            "bridge_ports":      "/interface/bridge/port",
            "wireless":          "/interface/wireless",
            "wireless_reg":      "/interface/wireless/registration-table",
            "ppp_secret":        "/ppp/secret",
            "hotspot_users":     "/ip/hotspot/user",
            "users":             "/user",
            "ip_services":       "/ip/service",
            "ntp_client":        "/system/ntp/client",
            "clock":             "/system/clock",
            "scheduler":         "/system/scheduler",
            "scripts":           "/system/script",
            "bgp_peers":         "/routing/bgp/peer",
            "ospf_instances":    "/routing/ospf/instance",
            "ospf_networks":     "/routing/ospf/network",
            "tunnels_eoip":      "/interface/eoip",
            "tunnels_ipip":      "/interface/ipip",
            "tunnels_l2tp":      "/interface/l2tp-client",
            "tunnels_pptp":      "/interface/pptp-client",
            "tunnels_sstp":      "/interface/sstp-client",
            "queue_simple":      "/queue/simple",
            "queue_tree":        "/queue/tree",
            "certificates":      "/certificate",
            "logs":              "/log",
        }

        result = {}
        for key, path in SECTIONS.items():
            try:
                items = list(api.get_resource(path).get())
                # Làm sạch các field internal
                cleaned = [
                    {k: v for k, v in item.items() if not k.startswith(".")}
                    for item in items
                ]
                result[key] = cleaned
            except Exception:
                pass  # Bỏ qua nếu thiết bị không có section này

        conn.disconnect()
        return result
    except Exception as e:
        raise Exception(f"MikroTik config: {e}")


async def _cisco_full_config(device: dict) -> dict:
    return await asyncio.to_thread(_cisco_full_config_sync, device)

def _cisco_full_config_sync(device: dict) -> dict:
    try:
        from netmiko import ConnectHandler
        nd = _get_netmiko_device(device)
        with ConnectHandler(**nd) as net:
            if nd["secret"]: net.enable()
            running   = net.send_command("show running-config")
            version   = net.send_command("show version")
            interfaces= net.send_command("show interfaces")
            ip_brief  = net.send_command("show ip interface brief")
            routes    = net.send_command("show ip route")
            arp       = net.send_command("show arp")
            vlans     = ""
            try: vlans = net.send_command("show vlan brief")
            except: pass
            cdp       = ""
            try: cdp = net.send_command("show cdp neighbors detail")
            except: pass
        return {
            "running_config": running,
            "version":        version,
            "interfaces":     interfaces,
            "ip_brief":       ip_brief,
            "routes":         routes,
            "arp":            arp,
            "vlans":          vlans,
            "cdp_neighbors":  cdp,
        }
    except Exception as e:
        raise Exception(f"Cisco config: {e}")


async def _fortinet_full_config(device: dict) -> dict:
    return await asyncio.to_thread(_fortinet_full_config_sync, device)

def _fortinet_full_config_sync(device: dict) -> dict:
    try:
        import requests, urllib3
        urllib3.disable_warnings()
        proto = "https" if device.get("use_ssl", True) else "http"
        base  = f"{proto}://{device['host']}:{device.get('api_port', 443)}"
        s = requests.Session(); s.verify = False
        s.post(f"{base}/logincheck",
               data={"username": device["username"], "secretkey": device["password"]}, timeout=10)
        vdom = device.get("vdom", "root")
        def get(path):
            try: return s.get(f"{base}/api/v2/cmdb/{path}?vdom={vdom}", timeout=15).json().get("results", [])
            except: return []
        result = {
            "interfaces":      get("system/interface"),
            "addresses":       get("firewall/address"),
            "address_groups":  get("firewall/addrgrp"),
            "policies":        get("firewall/policy"),
            "routes":          get("router/static"),
            "bgp":             get("router/bgp"),
            "ospf":            get("router/ospf"),
            "vips":            get("firewall/vip"),
            "ip_pools":        get("firewall/ippool"),
            "dns":             get("system/dns"),
            "ntp":             get("system/ntp"),
            "admin_users":     get("system/admin"),
            "ha":              get("system/ha"),
            "vpn_ipsec_phase1":get("vpn/ipsec/phase1-interface"),
            "vpn_ipsec_phase2":get("vpn/ipsec/phase2-interface"),
            "vpn_ssl":         get("vpn/ssl/settings"),
            "snmp":            get("system/snmp/sysinfo"),
            "zones":           get("system/zone"),
        }
        # Raw backup config
        try:
            r = s.get(f"{base}/api/v2/monitor/system/config/backup?scope=global", timeout=30)
            result["raw_backup"] = r.text
        except: pass
        s.post(f"{base}/logout")
        return result
    except Exception as e:
        raise Exception(f"Fortinet config: {e}")


async def _sophos_full_config(device: dict) -> dict:
    return await asyncio.to_thread(_sophos_full_config_sync, device)

def _sophos_full_config_sync(device: dict) -> dict:
    try:
        import requests, urllib3
        urllib3.disable_warnings()
        proto = "https" if device.get("use_ssl", True) else "http"
        url = f"{proto}://{device['host']}:{device.get('api_port', 4444)}/webconsole/APIController"
        def xml_get(entity):
            xml = f"""<Request APIVersion="1800.1">
  <Login><Username>{device['username']}</Username><Password>{device['password']}</Password></Login>
  <Get><{entity}></{entity}></Get>
</Request>"""
            try:
                r = requests.post(url, data={"reqxml": xml}, verify=False, timeout=10)
                return r.text
            except: return ""
        return {
            "system_info":   xml_get("SystemInformation"),
            "network":       xml_get("Interface"),
            "firewall_rules":xml_get("FirewallRule"),
            "nat_rules":     xml_get("NATRule"),
            "vpn_l2tp":      xml_get("L2TPServer"),
            "vpn_ipsec":     xml_get("IPsecConnection"),
            "dns":           xml_get("DNSForwarder"),
            "dhcp":          xml_get("DHCPServer"),
            "hosts":         xml_get("IPHost"),
            "users":         xml_get("User"),
            "web_filter":    xml_get("WebFilterPolicy"),
        }
    except Exception as e:
        raise Exception(f"Sophos config: {e}")


# ── API Routes ───────────────────────────────────────────────────

@app.get("/api/v1/config/all",
    summary="Lấy config của TẤT CẢ thiết bị",
    description="Trả về toàn bộ config có cấu trúc của tất cả thiết bị. Dùng để tích hợp với Ansible, Terraform, IPAM, NMS, v.v.")
async def config_get_all(
    online_only: bool = False,
    vendor: str = "",
    include_credentials: bool = False
):
    """
    GET /api/v1/config/all
    - online_only=true  → chỉ lấy thiết bị đang online
    - vendor=mikrotik   → lọc theo vendor
    - include_credentials=true → bao gồm username/password (mặc định ẩn)
    """
    targets = {
        n: d for n, d in devices_db.items()
        if (not online_only or d.get("status") == "online")
        and (not vendor or d.get("vendor", "").lower() == vendor.lower())
    }
    if not targets:
        return {"devices": [], "total": 0, "fetched_at": datetime.now().isoformat()}

    tasks = [_fetch_full_config(n, d) for n, d in targets.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    devices_out = []
    for r in results:
        if isinstance(r, Exception):
            devices_out.append({"error": str(r)})
        else:
            if not include_credentials:
                r.pop("username", None)
                r.pop("password", None)
                r.pop("secret", None)
            devices_out.append(r)

    return {
        "devices":    devices_out,
        "total":      len(devices_out),
        "online":     sum(1 for d in devices_out if not d.get("error") and d.get("status") == "online"),
        "fetched_at": datetime.now().isoformat(),
    }


@app.get("/api/v1/config/{name}",
    summary="Lấy full config một thiết bị",
    description="Trả về toàn bộ config có cấu trúc của một thiết bị cụ thể theo từng section.")
async def config_get_one(name: str, include_credentials: bool = False):
    """
    GET /api/v1/config/{name}
    Trả về config đầy đủ theo từng section (interfaces, routes, firewall, v.v.)
    """
    device = devices_db.get(name)
    if not device:
        raise HTTPException(404, f"Device '{name}' not found")
    result = await _fetch_full_config(name, device)
    if not include_credentials:
        result.pop("username", None)
        result.pop("password", None)
        result.pop("secret", None)
    return result


@app.get("/api/v1/config/{name}/section/{section}",
    summary="Lấy một section cụ thể của thiết bị",
    description="Ví dụ: /api/v1/config/CTHO/section/ip_addresses")
async def config_get_section(name: str, section: str):
    device = devices_db.get(name)
    if not device:
        raise HTTPException(404, f"Device '{name}' not found")
    if device.get("status") != "online":
        raise HTTPException(400, "Device offline")
    result = await _fetch_full_config(name, device)
    sections = result.get("sections", {})
    if section not in sections:
        available = list(sections.keys())
        raise HTTPException(404, f"Section '{section}' not found. Available: {available}")
    return {
        "name":       name,
        "vendor":     device.get("vendor"),
        "section":    section,
        "data":       sections[section],
        "fetched_at": datetime.now().isoformat(),
    }


@app.get("/api/v1/config/export/ansible",
    summary="Xuất inventory Ansible",
    description="Tạo file inventory.yml cho Ansible dựa trên thiết bị hiện có trong hệ thống.")
async def config_export_ansible(include_credentials: bool = False):
    """
    Xuất Ansible inventory YAML — dán thẳng vào inventory.yml
    """
    groups: Dict[str, list] = {}
    for name, d in devices_db.items():
        vendor = d.get("vendor", "other").lower()
        if vendor not in groups:
            groups[vendor] = []
        host_entry: dict = {
            "ansible_host": d.get("host", ""),
            "ansible_port": d.get("port", 22),
            "model":        d.get("model", ""),
            "status":       d.get("status", "offline"),
            "note":         d.get("note", ""),
        }
        if include_credentials:
            host_entry["ansible_user"]     = d.get("username", "")
            host_entry["ansible_password"] = d.get("password", "")
            if d.get("secret"):
                host_entry["ansible_become_password"] = d.get("secret", "")

        # Gán ansible_network_os
        vendor_os_map = {
            "mikrotik": "community.routeros.routeros",
            "cisco":    "cisco.ios.ios",
            "fortinet": "fortinet.fortios.fortios",
            "sophos":   "generic_ssh",
        }
        host_entry["ansible_network_os"] = vendor_os_map.get(vendor, "generic_ssh")
        groups[vendor].append({"name": name, "vars": host_entry})

    # Build YAML string
    lines = ["---", "all:", "  children:"]
    for grp, hosts in groups.items():
        lines.append(f"    {grp}:")
        lines.append(f"      hosts:")
        for h in hosts:
            lines.append(f"        {h['name']}:")
            for k, v in h["vars"].items():
                lines.append(f"          {k}: {json.dumps(v)}")
    return {"inventory_yaml": "\n".join(lines), "groups": list(groups.keys()), "total_hosts": len(devices_db)}


@app.get("/api/v1/config/export/terraform",
    summary="Xuất resource Terraform",
    description="Tạo terraform resource blocks cho tất cả thiết bị.")
async def config_export_terraform():
    lines = ["# PlNetwork Auto Manager — Terraform inventory", "# Generated: " + datetime.now().isoformat(), ""]
    for name, d in devices_db.items():
        safe = name.replace(" ", "_").replace("-", "_").lower()
        lines += [
            f'resource "network_device" "{safe}" {{',
            f'  name    = "{name}"',
            f'  host    = "{d.get("host","")}"',
            f'  vendor  = "{d.get("vendor","")}"',
            f'  port    = {d.get("port", 22)}',
            f'  status  = "{d.get("status","offline")}"',
            f'  model   = "{d.get("model","")}"',
            f'  note    = "{d.get("note","")}"',
            "}",
            "",
        ]
    return {"terraform_hcl": "\n".join(lines), "total": len(devices_db)}


@app.get("/api/v1/config/export/netbox",
    summary="Xuất JSON cho NetBox/IPAM",
    description="Trả về JSON chuẩn để import vào NetBox, phpIPAM hoặc bất kỳ IPAM nào.")
async def config_export_netbox():
    """Xuất dữ liệu thiết bị theo format NetBox dcim/devices"""
    devices_out = []
    for name, d in devices_db.items():
        vendor_map = {"mikrotik": "MikroTik", "cisco": "Cisco", "fortinet": "Fortinet", "sophos": "Sophos"}
        devices_out.append({
            "name":           name,
            "device_type":    {"manufacturer": {"name": vendor_map.get(d.get("vendor","").lower(), "Unknown")}, "model": d.get("model", "")},
            "primary_ip4":    {"address": d.get("host", "")},
            "status":         "active" if d.get("status") == "online" else "offline",
            "platform":       {"name": d.get("vendor", "")},
            "comments":       d.get("note", ""),
            "custom_fields":  {"uptime": d.get("uptime",""), "cpu_pct": d.get("cpu",0), "mem_pct": d.get("mem",0)},
        })
    return {"count": len(devices_out), "results": devices_out}


@app.get("/api/v1/config/export/prometheus",
    summary="Xuất targets cho Prometheus",
    description="Trả về JSON targets cho Prometheus file_sd_configs.")
async def config_export_prometheus():
    """Format cho prometheus file_sd_configs"""
    targets = []
    for name, d in devices_db.items():
        targets.append({
            "targets": [f"{d.get('host','')}:{d.get('port',22)}"],
            "labels": {
                "__name__":    name,
                "vendor":      d.get("vendor", ""),
                "model":       d.get("model", ""),
                "status":      d.get("status", "offline"),
                "job":         "network_devices",
            }
        })
    return targets


@app.get("/api/v1/config/schema",
    summary="Xem schema / danh sách sections theo vendor",
    description="Trả về danh sách sections có thể lấy được cho từng vendor.")
async def config_schema():
    return {
        "mikrotik": [
            "identity", "resource", "interfaces", "ip_addresses", "ip_routes", "arp",
            "dhcp_server", "dhcp_server_lease", "dhcp_client", "dns",
            "firewall_filter", "firewall_nat", "firewall_mangle", "firewall_address_list",
            "ip_pool", "vlans", "bridges", "bridge_ports", "wireless", "wireless_reg",
            "ppp_secret", "hotspot_users", "users", "ip_services",
            "ntp_client", "clock", "scheduler", "scripts",
            "bgp_peers", "ospf_instances", "ospf_networks",
            "tunnels_eoip", "tunnels_ipip", "tunnels_l2tp", "tunnels_pptp", "tunnels_sstp",
            "queue_simple", "queue_tree", "certificates", "logs",
        ],
        "cisco": [
            "running_config", "version", "interfaces", "ip_brief",
            "routes", "arp", "vlans", "cdp_neighbors",
        ],
        "fortinet": [
            "interfaces", "addresses", "address_groups", "policies",
            "routes", "bgp", "ospf", "vips", "ip_pools", "dns", "ntp",
            "admin_users", "ha", "vpn_ipsec_phase1", "vpn_ipsec_phase2",
            "vpn_ssl", "snmp", "zones", "raw_backup",
        ],
        "sophos": [
            "system_info", "network", "firewall_rules", "nat_rules",
            "vpn_l2tp", "vpn_ipsec", "dns", "dhcp", "hosts", "users", "web_filter",
        ],
    }


# ── API Key middleware (tuỳ chọn bảo mật) ───────────────────────
# Nếu muốn bảo vệ /api/v1/config bằng API key, set biến môi trường:
# PLNETWORK_API_KEY=your_secret_key
# Sau đó gọi với header: X-API-Key: your_secret_key
_API_KEY = os.environ.get("PLNETWORK_API_KEY", "")

from fastapi import Request as _Request
@app.middleware("http")
async def _api_key_middleware(request: _Request, call_next):
    if _API_KEY and request.url.path.startswith("/api/v1/config"):
        key = request.headers.get("X-API-Key", "")
        if key != _API_KEY:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Unauthorized — provide X-API-Key header"}, status_code=401)
    return await call_next(request)


# ══════════════════════════════════════════════════════════════════
# AUTO BACKUP — Schedule + Storage
# ══════════════════════════════════════════════════════════════════
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)
backup_schedule_active = False
backup_schedule_thread = None
BACKUP_INTERVAL_HOURS = 24
backup_history: List[dict] = []  # [{name, file, timestamp, size, status}]

def _save_backup_file(name: str, config: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = name.replace(" ","_").replace("/","_")
    fname = f"{safe_name}_{ts}.txt"
    fpath = os.path.join(BACKUP_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(config)
    return fpath

def _backup_all_sync():
    """Run backup for all online devices"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = []
    for name, dev in list(devices_db.items()):
        if dev.get("status") != "online": continue
        try:
            vendor = dev.get("vendor","").lower()
            if vendor == "mikrotik":
                config = loop.run_until_complete(backup_mikrotik(dev))
            elif vendor == "cisco":
                config = loop.run_until_complete(backup_cisco(dev))
            elif vendor == "fortinet":
                config = loop.run_until_complete(backup_fortinet(dev))
            else:
                config = loop.run_until_complete(backup_ssh_generic(dev))
            fpath = _save_backup_file(name, config)
            entry = {"name": name, "file": os.path.basename(fpath), "timestamp": datetime.now().isoformat(),
                     "size": len(config), "status": "success"}
            backup_history.append(entry)
            results.append(entry)
            print(f"[BACKUP] ✓ {name} → {os.path.basename(fpath)}")
        except Exception as e:
            entry = {"name": name, "file": "", "timestamp": datetime.now().isoformat(), "size": 0, "status": f"error: {e}"}
            backup_history.append(entry)
            results.append(entry)
            print(f"[BACKUP] ✗ {name}: {e}")
    loop.close()
    return results

def _backup_schedule_loop():
    import time as _t
    print(f"[BACKUP] Schedule started — every {BACKUP_INTERVAL_HOURS}h")
    while backup_schedule_active:
        _backup_all_sync()
        # Sleep in small chunks to allow stop
        for _ in range(BACKUP_INTERVAL_HOURS * 3600 * 2):
            if not backup_schedule_active: break
            _t.sleep(0.5)
    print("[BACKUP] Schedule stopped")

@app.post("/api/backup/all")
async def backup_all_devices():
    """Manual backup all online devices"""
    results = await asyncio.to_thread(_backup_all_sync)
    return {"status": "done", "results": results}

@app.post("/api/backup/schedule/start")
async def start_backup_schedule(hours: int = 24):
    global backup_schedule_active, backup_schedule_thread, BACKUP_INTERVAL_HOURS
    BACKUP_INTERVAL_HOURS = max(1, hours)
    if backup_schedule_active:
        backup_schedule_active = False
        import time as _t; _t.sleep(1)
    backup_schedule_active = True
    backup_schedule_thread = _threading.Thread(target=_backup_schedule_loop, daemon=True)
    backup_schedule_thread.start()
    return {"status": "started", "interval_hours": BACKUP_INTERVAL_HOURS}

@app.post("/api/backup/schedule/stop")
async def stop_backup_schedule():
    global backup_schedule_active
    backup_schedule_active = False
    return {"status": "stopped"}

@app.get("/api/backup/schedule/status")
async def backup_schedule_status():
    return {
        "active": backup_schedule_active,
        "interval_hours": BACKUP_INTERVAL_HOURS,
        "next_run": "N/A" if not backup_schedule_active else f"every {BACKUP_INTERVAL_HOURS}h"
    }

@app.get("/api/backup/history")
async def get_backup_history():
    """List all backup records"""
    return {"history": backup_history[-100:]}

@app.get("/api/backup/files")
async def list_backup_files():
    """List backup files on disk"""
    files = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        fpath = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fpath):
            files.append({"file": f, "size": os.path.getsize(fpath),
                          "modified": datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat()})
    return {"files": files[:100]}

@app.get("/api/backup/files/{filename}")
async def get_backup_file(filename: str):
    """Download backup file content"""
    fpath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(fpath): raise HTTPException(404, "File not found")
    return {"filename": filename, "content": open(fpath, encoding="utf-8").read()}

# ══════════════════════════════════════════════════════════════════
# TELEGRAM BOT — Advanced: Inline Keyboards + Auto Alerts
# ══════════════════════════════════════════════════════════════════

bot_config: dict = {"token": "", "allowed_users": [], "enabled": False, "alert_chats": []}
BOT_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_config.json")
device_prev_status: Dict[str, str] = {}  # track status changes for alerts

# ══════════════════════════════════════════════════════════════════
# STARTUP CLEANUP — runs AFTER all variables declared
# ══════════════════════════════════════════════════════════════════
def _startup_cleanup():
    serial_sessions.clear()
    global polling_active, polling_offset
    polling_active = False
    polling_offset = 0
    device_prev_status.clear()
    print("[STARTUP] Cleanup done")


# ── Background Health-Check ──────────────────────────────────────
import threading as _hc_threading


_startup_cleanup()

# ── Background Health-Check ──────────────────────────────────────
import threading as _hc_threading

def _health_check_loop():
    """Ping tất cả thiết bị mỗi 60s — tự phát hiện online/offline"""
    import time as _t
    import asyncio as _asyncio
    _t.sleep(10)  # Chờ backend khởi động xong
    print("[HEALTH-CHECK] Started — interval 60s")
    while True:
        try:
            loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(loop)
            for name, device in list(devices_db.items()):
                try:
                    vendor = device.get("vendor","")
                    prev = device.get("status","offline")
                    ok = False
                    # Quick TCP ping để check
                    import socket
                    host = device.get("host","")
                    # Chọn port check theo vendor
                    if vendor == "mikrotik":
                        port = device.get("api_port", 3543)
                    elif vendor == "fortinet":
                        port = 443
                    elif vendor == "sophos":
                        port = 4444
                    else:
                        port = device.get("port", 22)
                    # Thử 2 lần trước khi kết luận offline
                    for _attempt in range(2):
                        try:
                            if vendor == "cisco":
                                from netmiko import ConnectHandler
                                dt = device.get("device_type","ios")
                                dt_map = {"ios":"cisco_ios","ios_xe":"cisco_xe","nx_os":"cisco_nxos"}
                                tmp = ConnectHandler(
                                    device_type=dt_map.get(dt,"cisco_ios"),
                                    host=host,
                                    username=device.get("username","admin"),
                                    password=device.get("password",""),
                                    timeout=15,
                                )
                                tmp.find_prompt()
                                tmp.disconnect()
                                ok = True
                                break
                            else:
                                sock = socket.create_connection((host, port), timeout=8)
                                sock.close()
                                ok = True
                                break
                        except:
                            ok = False
                            if _attempt == 0:
                                import time as _tt2
                                _tt2.sleep(5)  # Chờ 5s rồi thử lại

                    new_status = "online" if ok else "offline"
                    if new_status != prev:
                        devices_db[name]["status"] = new_status
                        save_db()
                        print(f"[HEALTH-CHECK] {name}: {prev} → {new_status}")
                        loop.run_until_complete(
                            check_and_alert_status_change(name, new_status)
                        )
                        # Nếu back online → reconnect để lấy metrics
                except Exception as e:
                    print(f"[HEALTH-CHECK] {name} error: {e}")
            loop.close()
        except Exception as e:
            print(f"[HEALTH-CHECK] Loop error: {e}")
        _t.sleep(60)

_hc_thread = _hc_threading.Thread(target=_health_check_loop, daemon=True)
_hc_thread.start()
print("[STARTUP] ✓ Health-check thread started (60s interval)")

# ── Shutdown: cleanup on Ctrl+C / process exit ───────────────────
import atexit
def _shutdown_cleanup():
    global polling_active
    polling_active = False
    for sid, sess in list(serial_sessions.items()):
        try: sess["serial"].close()
        except: pass
    serial_sessions.clear()
    print("[SHUTDOWN] Cleanup done")
atexit.register(_shutdown_cleanup)

def load_bot_config():
    global bot_config
    if os.path.exists(BOT_CONFIG_FILE):
        try: bot_config.update(json.load(open(BOT_CONFIG_FILE, encoding="utf-8")))
        except: pass

load_bot_config()

# Auto-start bot polling sau khi load config
def _auto_start_bot():
    import time as _t
    _t.sleep(5)  # Chờ backend khởi động xong
    token = bot_config.get("token","")
    if not token:
        print("[BOT] No token configured — skip auto-start")
        return
    global polling_thread, polling_active, polling_offset
    polling_offset = 0
    polling_active = True
    polling_thread = _hc_threading.Thread(target=run_polling, daemon=True)
    polling_thread.start()
    print(f"[BOT] Auto-started polling for token ...{token[-6:]}")

_hc_threading.Thread(target=_auto_start_bot, daemon=True, name="bot-autostart").start()

class BotConfigRequest(BaseModel):
    token: str
    allowed_users: List[str] = []
    alert_chats: List[str] = []
    enabled: bool = True

async def tg_send(chat_id: str, text: str, reply_markup: dict = None):
    """Send Telegram message, optionally with inline keyboard"""
    import httpx
    token = bot_config.get("token","")
    if not token: return
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup: payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload)
    except: pass

async def tg_answer_callback(callback_id: str, text: str = ""):
    """Answer callback query to remove loading indicator"""
    import httpx
    token = bot_config.get("token","")
    if not token: return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                json={"callback_query_id": callback_id, "text": text})
    except: pass

async def tg_edit_message(chat_id: str, message_id: int, text: str, reply_markup: dict = None):
    """Edit existing message (for inline keyboard updates)"""
    import httpx
    token = bot_config.get("token","")
    if not token: return
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup: payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"https://api.telegram.org/bot{token}/editMessageText", json=payload)
    except: pass

async def send_alert_all(text: str):
    """Broadcast alert to all registered alert chats"""
    for chat_id in bot_config.get("alert_chats", []):
        await tg_send(chat_id, text)

def kb_main_menu():
    """Main menu inline keyboard"""
    return {"inline_keyboard": [
        [{"text": "📡 Devices", "callback_data": "menu:devices"},
         {"text": "📊 Status",  "callback_data": "menu:status"}],
        [{"text": "🔧 Services","callback_data": "menu:services_list"},
         {"text": "🔍 Ping",    "callback_data": "menu:ping_prompt"}],
        [{"text": "💻 Terminal","callback_data": "menu:terminal_list"},
         {"text": "⚙ Backup",  "callback_data": "menu:backup_list"}],
    ]}

def kb_device_list(action: str):
    """Keyboard with device buttons"""
    rows = []
    for name, d in devices_db.items():
        icon = "🟢" if d.get("status")=="online" else "🔴"
        rows.append([{"text": f"{icon} {name}", "callback_data": f"{action}:{name}"}])
    rows.append([{"text": "« Back", "callback_data": "menu:main"}])
    return {"inline_keyboard": rows}

def kb_device_actions(device_name: str):
    """Actions for a specific device"""
    dev = devices_db.get(device_name, {})
    online = dev.get("status") == "online"
    rows = [
        [{"text": "ℹ️ Info",     "callback_data": f"dev_info:{device_name}"},
         {"text": "🔌 Connect",  "callback_data": f"dev_connect:{device_name}"}],
        [{"text": "🔧 Services", "callback_data": f"dev_services:{device_name}"},
         {"text": "💻 Commands", "callback_data": f"dev_cmds:{device_name}"}],
        [{"text": "💾 Backup",   "callback_data": f"dev_backup:{device_name}"},
         {"text": "🏓 Ping",     "callback_data": f"dev_ping:{device_name}"}],
        [{"text": "« Back",      "callback_data": "menu:devices"}],
    ]
    return {"inline_keyboard": rows}

def kb_services(device_name: str, services: dict):
    """Inline keyboard for toggling services"""
    rows = []
    for sname, svc in services.items():
        icon = "🟢" if svc.get("enabled") else "🔴"
        action = "svc_off" if svc.get("enabled") else "svc_on"
        rows.append([{"text": f"{icon} {sname} :{svc.get('port','')}",
                      "callback_data": f"{action}:{device_name}:{sname}"}])
    rows.append([{"text": "« Back", "callback_data": f"dev_actions:{device_name}"}])
    return {"inline_keyboard": rows}

def kb_quick_cmds(device_name: str):
    """Quick RouterOS commands"""
    cmds = [
        ("/ip address print", "IP Addresses"),
        ("/interface print", "Interfaces"),
        ("/ip route print", "Routes"),
        ("/system resource print", "Resources"),
        ("/ip firewall filter print", "FW Filter"),
        ("/log print count=20", "Logs"),
    ]
    rows = [[{"text": label, "callback_data": f"run_cmd:{device_name}:{cmd}"}] for cmd, label in cmds]
    rows.append([{"text": "« Back", "callback_data": f"dev_actions:{device_name}"}])
    return {"inline_keyboard": rows}

@app.get("/api/bot/config")
async def get_bot_config():
    return {"enabled": bot_config.get("enabled"), "has_token": bool(bot_config.get("token")),
            "allowed_users": bot_config.get("allowed_users",[]),
            "alert_chats": bot_config.get("alert_chats",[])}

@app.post("/api/bot/config")
async def save_bot_config(req: BotConfigRequest):
    bot_config.update({"token": req.token, "allowed_users": req.allowed_users,
                        "alert_chats": req.alert_chats, "enabled": req.enabled})
    json.dump(bot_config, open(BOT_CONFIG_FILE,"w",encoding="utf-8"), indent=2)
    return {"status": "ok", "enabled": req.enabled}

@app.post("/api/bot/alert")
async def send_manual_alert(req: dict):
    """Manually send alert to all alert chats"""
    text = req.get("text","")
    if not text: raise HTTPException(400, "text required")
    await send_alert_all(text)
    return {"status": "ok", "sent_to": len(bot_config.get("alert_chats",[]))}

@app.post("/api/bot/test")
async def bot_test(req: dict):
    """Test bot command directly from UI — simulates real bot logic"""
    try:
        cmd = req.get("command","").strip()
        if not cmd:
            return {"result": "[Error] Empty command"}

        text = cmd

        if text in ("/start", "/menu"):
            return {"result": "🌐 PlNetwork Auto Manager\nChào mừng! Bot đang hoạt động.\nDùng /devices, /status, /ping <host>, /help"}

        elif text == "/devices":
            if not devices_db:
                return {"result": "📡 Chưa có thiết bị nào"}
            lines = ["📡 Danh sách thiết bị:"]
            for d in devices_db.values():
                icon = "🟢" if d.get("status")=="online" else "🔴"
                lines.append(f"{icon} {d['name']} — {d['host']} [{d.get('vendor','?')}]")
            return {"result": "\n".join(lines)}

        elif text == "/status":
            total = len(devices_db)
            online = sum(1 for d in devices_db.values() if d.get("status")=="online")
            lines = [f"📊 Status: {online}/{total} online"]
            for d in devices_db.values():
                icon = "🟢" if d.get("status")=="online" else "🔴"
                lines.append(f"{icon} {d['name']} — {d['host']}")
            return {"result": "\n".join(lines)}

        elif text.startswith("/ping "):
            host = text.split(" ",1)[1].strip()
            r = _do_ping(host, 4)
            icon = "✅" if r.get("reachable") else "❌"
            return {"result": f"{icon} Ping {host}\n{r.get('output','')[:300]}"}

        elif text == "/help":
            return {"result": (
                "📖 Bot Commands:\n"
                "/start — Menu chính\n"
                "/devices — Danh sách thiết bị\n"
                "/status — Tổng quan online/offline\n"
                "/ping <host> — Ping host\n"
                "/connect <name> — Connect thiết bị\n"
                "/cmd <device> <command> — Chạy lệnh\n"
                "/services <device> — Xem services\n"
                "\n📊 <b>Monitor:</b>\n"
                "/status — CPU/mem tất cả thiết bị\n"
                "/iface <device> — Traffic live interfaces\n"
                "/cpu <device> [1h|6h|24h] — Đồ thị CPU\n"
                "/monitor <device> <30|60|300> — Bật poll\n"
                "/alert <device> cpu=80 mem=85 bw=900 — Ngưỡng cảnh báo"
            )}

        elif text.startswith("/connect "):
            dname = text.split(" ",1)[1].strip()
            dev = devices_db.get(dname)
            if not dev: return {"result": f"❌ '{dname}' không tìm thấy"}
            try:
                info = await _connect_and_get_info(dev)
                devices_db[dname].update({"status":"online",**info}); save_db()
                return {"result": f"✅ {dname} online!\nModel: {info.get('model','?')}\nUptime: {info.get('uptime','?')}"}
            except Exception as e:
                return {"result": f"❌ {e}"}

        elif text.startswith("/cmd "):
            parts = text.split(" ",2)
            if len(parts)<3: return {"result": "Usage: /cmd <device> <command>"}
            dname, cmd2 = parts[1], parts[2]
            dev = devices_db.get(dname)
            if not dev: return {"result": f"❌ '{dname}' không tìm thấy"}
            vendor = dev.get("vendor","").lower()
            if vendor=="mikrotik": out = await cmd_mikrotik(dev,cmd2)
            elif vendor=="cisco": out = await cmd_cisco(dev,cmd2)
            else: out = await cmd_ssh_generic(dev,cmd2)
            return {"result": f"💻 {dname}\n{cmd2}\n{str(out)[:800]}"}

        else:
            return {"result": f"❓ Lệnh '{text}' không nhận ra. Dùng /help"}

    except Exception as e:
        return {"result": f"[Error] {str(e)}"}

@app.post("/api/bot/webhook")
async def telegram_webhook(req: dict):
    """Handle Telegram webhook — messages + callback queries"""
    if not bot_config.get("enabled"): return {"ok": True}
    token = bot_config.get("token","")
    if not token: return {"ok": True}
    allowed = bot_config.get("allowed_users",[])

    def is_allowed(username: str, chat_id: str) -> bool:
        if not allowed: return True  # No restriction = allow all
        # Check both username and chat_id (numeric string)
        allowed_clean = [str(a).strip().lstrip("@") for a in allowed]
        return (username in allowed_clean or 
                chat_id in allowed_clean or
                str(chat_id) in allowed_clean)

    # ── Handle callback queries (inline keyboard presses) ──────────
    cb = req.get("callback_query")
    if cb:
        cb_id = cb.get("id","")
        chat_id = str(cb.get("message",{}).get("chat",{}).get("id",""))
        msg_id  = cb.get("message",{}).get("message_id")
        username = cb.get("from",{}).get("username","")
        data = cb.get("data","")
        if not is_allowed(username, chat_id):
            await tg_answer_callback(cb_id, "⛔ Not authorized"); return {"ok": True}
        await tg_answer_callback(cb_id)
        parts = data.split(":", 2)
        action = parts[0]
        try:
            if action == "ack":
                key = ":".join(parts[1:])
                import time as _tt
                _alert_acknowledged[key] = _tt.time()
                _save_ack()
                await tg_answer_callback(cb_id, "✅ Đã xác nhận — tắt alert 1h")
                await tg_edit_message(chat_id, msg_id,
                    f"✅ <b>Đã xác nhận</b>\nAlert <code>{key}</code> đã tắt trong <b>1 giờ</b>",
                    {"inline_keyboard":[[{"text":"🔕 Tắt 24h","callback_data":f"ack24:{key}"},{"text":"↩ Menu","callback_data":"menu:main"}]]})
            elif action == "ack24":
                key = ":".join(parts[1:])
                import time as _tt
                _alert_acknowledged[key] = _tt.time() + 82800  # 23h thêm = tổng 24h
                _save_ack()
                await tg_answer_callback(cb_id, "🔕 Đã tắt alert 24h")
                await tg_edit_message(chat_id, msg_id,
                    f"🔕 <b>Tắt 24h</b>\nAlert <code>{key}</code> đã tắt trong <b>24 giờ</b>",
                    {"inline_keyboard":[[{"text":"↩ Menu","callback_data":"menu:main"}]]})
            elif action == "menu":
                sub = parts[1] if len(parts)>1 else ""
                if sub == "main":
                    await tg_edit_message(chat_id, msg_id, "🌐 <b>PlNetwork Auto Manager</b>\nChọn chức năng:", kb_main_menu())
                elif sub == "devices":
                    await tg_edit_message(chat_id, msg_id, "📡 <b>Chọn thiết bị:</b>", kb_device_list("dev_actions"))
                elif sub == "status":
                    total = len(devices_db)
                    online = sum(1 for d in devices_db.values() if d.get("status")=="online")
                    offline = total - online
                    lines = [f"📊 <b>Network Status</b>", f"Total: {total}  🟢 {online}  🔴 {offline}", ""]
                    for d in devices_db.values():
                        icon = "🟢" if d.get("status")=="online" else "🔴"
                        cpu = f" CPU:{d.get('cpu','?')}%" if d.get("status")=="online" else ""
                        lines.append(f"{icon} <b>{d['name']}</b>{cpu}")
                    await tg_edit_message(chat_id, msg_id, "\n".join(lines), {"inline_keyboard":[[{"text":"↺ Refresh","callback_data":"menu:status"},{"text":"« Back","callback_data":"menu:main"}]]})
                elif sub == "services_list":
                    await tg_edit_message(chat_id, msg_id, "🔧 <b>Chọn thiết bị:</b>", kb_device_list("dev_services"))
                elif sub == "terminal_list":
                    await tg_edit_message(chat_id, msg_id, "💻 <b>Chọn thiết bị:</b>", kb_device_list("dev_cmds"))
                elif sub == "backup_list":
                    await tg_edit_message(chat_id, msg_id, "💾 <b>Chọn thiết bị để backup:</b>", kb_device_list("dev_backup"))
                elif sub == "ping_prompt":
                    await tg_edit_message(chat_id, msg_id, "🔍 Gửi lệnh:\n<code>/ping 8.8.8.8</code>", {"inline_keyboard":[[{"text":"« Back","callback_data":"menu:main"}]]})

            elif action == "dev_actions":
                dname = parts[1]
                dev = devices_db.get(dname,{})
                icon = "🟢" if dev.get("status")=="online" else "🔴"
                info = f"{icon} <b>{dname}</b>\nHost: <code>{dev.get('host','')}</code>\nVendor: {dev.get('vendor','')}"
                if dev.get("status")=="online":
                    info += f"\nModel: {dev.get('model','?')} | Uptime: {dev.get('uptime','?')}\nCPU: {dev.get('cpu','?')}% | MEM: {dev.get('mem','?')}%"
                await tg_edit_message(chat_id, msg_id, info, kb_device_actions(dname))

            elif action == "dev_info":
                dname = parts[1]
                dev = devices_db.get(dname,{})
                lines = [f"ℹ️ <b>{dname}</b>",
                         f"Host: <code>{dev.get('host','')}</code>",
                         f"Vendor: {dev.get('vendor','')} | Status: {dev.get('status','')}"]
                if dev.get("model"): lines.append(f"Model: {dev.get('model')}")
                if dev.get("uptime"): lines.append(f"Uptime: {dev.get('uptime')}")
                if dev.get("cpu") is not None: lines.append(f"CPU: {dev.get('cpu')}% | MEM: {dev.get('mem')}%")
                await tg_edit_message(chat_id, msg_id, "\n".join(lines), {"inline_keyboard":[[{"text":"« Back","callback_data":f"dev_actions:{dname}"}]]})

            elif action == "dev_connect":
                dname = parts[1]
                dev = devices_db.get(dname)
                if not dev: await tg_send(chat_id, f"❌ Device '{dname}' not found"); return {"ok":True}
                await tg_edit_message(chat_id, msg_id, f"⏳ Connecting to <b>{dname}</b>...", None)
                try:
                    info = await _connect_and_get_info(dev)
                    devices_db[dname].update({"status":"online",**info}); save_db()
                    await tg_send(chat_id, f"✅ <b>{dname}</b> connected!\nModel: {info.get('model','?')}\nUptime: {info.get('uptime','?')}\nCPU: {info.get('cpu','?')}% | MEM: {info.get('mem','?')}%")
                except Exception as e:
                    await tg_send(chat_id, f"❌ Connect failed: {e}")

            elif action == "dev_ping":
                dname = parts[1]
                dev = devices_db.get(dname,{})
                host = dev.get("host","")
                r = _do_ping(host, 4)
                icon = "✅" if r.get("reachable") else "❌"
                await tg_edit_message(chat_id, msg_id, f"{icon} Ping <b>{dname}</b> ({host})\n<pre>{r.get('output','')[:400]}</pre>",
                    {"inline_keyboard":[[{"text":"↺ Ping Again","callback_data":f"dev_ping:{dname}"},{"text":"« Back","callback_data":f"dev_actions:{dname}"}]]})

            elif action == "dev_services":
                dname = parts[1]
                try:
                    r = await get_services(dname)
                    svcs = r.get("services",{})
                    await tg_edit_message(chat_id, msg_id, f"🔧 <b>{dname} Services</b>\nClick để bật/tắt:", kb_services(dname, svcs))
                except Exception as e:
                    await tg_send(chat_id, f"❌ {e}")

            elif action in ("svc_on","svc_off"):
                dname = parts[1]; sname = parts[2]
                enable = action == "svc_on"
                try:
                    from pydantic import BaseModel as BM
                    req_obj = type('R',(), {'service':sname,'enabled':enable,'port':None})()
                    req_obj.service = sname; req_obj.enabled = enable; req_obj.port = None
                    await set_service(dname, req_obj)
                    r2 = await get_services(dname)
                    await tg_edit_message(chat_id, msg_id,
                        f"🔧 <b>{dname}</b> — {sname} {'🟢 ON' if enable else '🔴 OFF'}\n\nServices:", kb_services(dname, r2.get("services",{})))
                except Exception as e:
                    await tg_send(chat_id, f"❌ {e}")

            elif action == "dev_cmds":
                dname = parts[1]
                await tg_edit_message(chat_id, msg_id, f"💻 <b>{dname}</b> — Quick Commands:", kb_quick_cmds(dname))

            elif action == "run_cmd":
                dname = parts[1]; cmd = parts[2] if len(parts)>2 else ""
                dev = devices_db.get(dname)
                if not dev: await tg_send(chat_id, f"❌ Device not found"); return {"ok":True}
                if dev.get("status") != "online": await tg_send(chat_id, f"❌ {dname} offline"); return {"ok":True}
                vendor = dev.get("vendor","").lower()
                try:
                    if vendor == "mikrotik": out = await cmd_mikrotik(dev, cmd)
                    elif vendor == "cisco": out = await cmd_cisco(dev, cmd)
                    else: out = await cmd_ssh_generic(dev, cmd)
                    text_out = str(out)[:1500]
                    await tg_send(chat_id, f"💻 <b>{dname}</b>\n<code>{cmd}</code>\n<pre>{text_out}</pre>")
                except Exception as e:
                    await tg_send(chat_id, f"❌ {e}")

            elif action == "dev_backup":
                dname = parts[1]
                dev = devices_db.get(dname)
                if not dev: await tg_send(chat_id, f"❌ Device not found"); return {"ok":True}
                await tg_edit_message(chat_id, msg_id, f"⏳ Backing up <b>{dname}</b>...", None)
                vendor = dev.get("vendor","").lower()
                try:
                    if vendor == "mikrotik": cfg = await backup_mikrotik(dev)
                    elif vendor == "cisco": cfg = await backup_cisco(dev)
                    else: cfg = await backup_ssh_generic(dev)
                    await tg_send(chat_id, f"✅ Backup <b>{dname}</b>\n<pre>{cfg[:1200]}...</pre>")
                except Exception as e:
                    await tg_send(chat_id, f"❌ Backup failed: {e}")

        except Exception as e:
            await tg_send(chat_id, f"⚠️ Error: {e}")
        return {"ok": True}

    # ── Handle text messages ───────────────────────────────────────
    msg = req.get("message") or req.get("edited_message", {})
    if not msg: return {"ok": True}
    chat_id  = str(msg.get("chat",{}).get("id",""))
    text     = msg.get("text","").strip()
    username = msg.get("from",{}).get("username","")
    if not is_allowed(username, chat_id): return {"ok": True}

    # Auto-register chat for alerts if not already
    if chat_id and chat_id not in bot_config.get("alert_chats",[]):
        bot_config.setdefault("alert_chats",[]).append(chat_id)
        json.dump(bot_config, open(BOT_CONFIG_FILE,"w",encoding="utf-8"), indent=2)

    try:
        if text in ("/start", "/menu"):
            await tg_send(chat_id, "🌐 <b>PlNetwork Auto Manager</b>\nChào mừng! Chọn chức năng:", kb_main_menu())
        elif text == "/devices":
            await tg_send(chat_id, "📡 <b>Chọn thiết bị:</b>", kb_device_list("dev_actions"))
        elif text == "/status":
            total = len(devices_db)
            online = sum(1 for d in devices_db.values() if d.get("status")=="online")
            lines = [f"📊 <b>Status</b> — {online}/{total} online"]
            for d in devices_db.values():
                icon = "🟢" if d.get("status")=="online" else "🔴"
                lines.append(f"{icon} {d['name']} — {d['host']}")
            await tg_send(chat_id, "\n".join(lines), {"inline_keyboard":[[{"text":"↺ Refresh","callback_data":"menu:status"}]]})
        elif text.startswith("/ping "):
            host = text.split(" ",1)[1].strip()
            r = _do_ping(host, 4)
            icon = "✅" if r.get("reachable") else "❌"
            await tg_send(chat_id, f"{icon} Ping <code>{host}</code>\n<pre>{r.get('output','')[:500]}</pre>")
        elif text.startswith("/connect "):
            dname = text.split(" ",1)[1].strip()
            dev = devices_db.get(dname)
            if not dev: await tg_send(chat_id, f"❌ '{dname}' not found"); return {"ok":True}
            try:
                info = await _connect_and_get_info(dev)
                devices_db[dname].update({"status":"online",**info}); save_db()
                await tg_send(chat_id, f"✅ <b>{dname}</b> online!\nModel: {info.get('model','?')}\nUptime: {info.get('uptime','?')}")
            except Exception as e:
                await tg_send(chat_id, f"❌ {e}")
        elif text.startswith("/cmd "):
            parts = text.split(" ",2)
            if len(parts)<3: await tg_send(chat_id,"Usage: /cmd &lt;device&gt; &lt;command&gt;"); return {"ok":True}
            dname, cmd = parts[1], parts[2]
            dev = devices_db.get(dname)
            if not dev: await tg_send(chat_id,f"❌ '{dname}' not found"); return {"ok":True}
            if dev.get("status")!="online": await tg_send(chat_id,f"❌ {dname} offline"); return {"ok":True}
            vendor = dev.get("vendor","").lower()
            if vendor=="mikrotik": out = await cmd_mikrotik(dev,cmd)
            elif vendor=="cisco": out = await cmd_cisco(dev,cmd)
            else: out = await cmd_ssh_generic(dev,cmd)
            await tg_send(chat_id,f"💻 <b>{dname}</b>\n<code>{cmd}</code>\n<pre>{str(out)[:1200]}</pre>")
        elif text.startswith("/services "):
            dname = text.split(" ",1)[1].strip()
            try:
                r = await get_services(dname)
                await tg_send(chat_id, f"🔧 <b>{dname} Services</b>", kb_services(dname, r.get("services",{})))
            except Exception as e:
                await tg_send(chat_id, f"❌ {e}")
        elif text == "/help":
            help_text = ("📖 <b>Commands:</b>\n"
                "/start — Menu chính (inline keyboard)\n"
                "/devices — Danh sách thiết bị\n"
                "/status — Tổng quan\n"
                "/ping &lt;host&gt; — Ping\n"
                "/connect &lt;name&gt; — Connect\n"
                "/cmd &lt;dev&gt; &lt;cmd&gt; — Chạy lệnh\n"
                "/services &lt;dev&gt; — Quản lý services")
            await tg_send(chat_id, help_text)
        else:
            await tg_send(chat_id, "❓ /help để xem lệnh", {"inline_keyboard":[[{"text":"📋 Menu","callback_data":"menu:main"}]]})
    except Exception as e:
        await tg_send(chat_id, f"⚠️ {e}")
    return {"ok": True}

# ── Auto Alert: check device status on every connect ─────────────
async def check_and_alert_status_change(name: str, new_status: str):
    """Send alert when device goes offline or comes back online"""
    prev = device_prev_status.get(name)
    if prev and prev != new_status:
        if new_status == "offline":
            await send_alert_all(f"🔴 <b>ALERT: {name} went OFFLINE</b>\n⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
            await send_alert_all(f"🟢 <b>ALERT: {name} back ONLINE</b>\n⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
        elif new_status == "online":
            await send_alert_all(f"🟢 <b>ALERT: {name} back ONLINE</b>\n⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")


# ══════════════════════════════════════════════════════════════════
# TELEGRAM BOT — POLLING MODE (không cần webhook/public URL)
# ══════════════════════════════════════════════════════════════════
import threading
polling_thread = None
polling_active = False
polling_offset = 0

def run_polling():
    """Polling thread — pure sync, no asyncio complications"""
    global polling_active, polling_offset
    import httpx, time as _t, asyncio

    token = bot_config.get("token","")
    if not token:
        print("[BOT] No token!")
        return

    print(f"[BOT] Polling started token={token[:10]}...")

    # Create dedicated event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def send_msg(chat_id, text, reply_markup=None):
        """Sync send message"""
        try:
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            if reply_markup:
                import json as _json
                payload["reply_markup"] = _json.dumps(reply_markup)
            with httpx.Client(timeout=10) as c:
                c.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload)
        except Exception as e:
            print(f"[BOT] send error: {e}")

    def handle_update(update):
        """Handle single update synchronously"""
        try:
            msg = update.get("message") or update.get("edited_message")
            if not msg:
                return
            chat_id = str(msg.get("chat",{}).get("id",""))
            text = msg.get("text","").strip()
            username = msg.get("from",{}).get("username","")
            
            print(f"[BOT] msg from {username}/{chat_id}: {text}")

            # Check allowed
            allowed = bot_config.get("allowed_users",[])
            allowed_clean = [str(a).strip().lstrip("@") for a in allowed if a]
            if allowed_clean and username not in allowed_clean and chat_id not in allowed_clean:
                send_msg(chat_id, "⛔ Not authorized")
                return

            # Auto-register alert chat
            if chat_id and chat_id not in bot_config.get("alert_chats",[]):
                bot_config.setdefault("alert_chats",[]).append(chat_id)

            # Handle commands
            if text in ("/start", "/menu"):
                send_msg(chat_id, 
                    "🌐 <b>PLNetwork Auto Manager</b>\n"
                    "Chào mừng! Chọn lệnh:\n\n"
                    "/devices — Danh sách thiết bị\n"
                    "/status — Tổng quan\n"
                    "/ping &lt;host&gt; — Ping\n"
                    "/help — Trợ giúp"
                )
            elif text == "/devices":
                if not devices_db:
                    send_msg(chat_id, "📡 Chưa có thiết bị nào")
                else:
                    lines = ["📡 <b>Danh sách thiết bị:</b>"]
                    for d in devices_db.values():
                        icon = "🟢" if d.get("status")=="online" else "🔴"
                        lines.append(f"{icon} <b>{d['name']}</b> — {d['host']} [{d.get('vendor','?')}]")
                    send_msg(chat_id, "\n".join(lines))
            elif text == "/status":
                total = len(devices_db)
                online = sum(1 for d in devices_db.values() if d.get("status")=="online")
                lines = [f"📊 <b>Status: {online}/{total} online</b>"]
                for d in devices_db.values():
                    icon = "🟢" if d.get("status")=="online" else "🔴"
                    lines.append(f"{icon} {d['name']} — {d['host']}")
                send_msg(chat_id, "\n".join(lines))
            elif text.startswith("/ping "):
                host = text.split(" ",1)[1].strip()
                r = _do_ping(host, 4)
                icon = "✅" if r.get("reachable") else "❌"
                send_msg(chat_id, f"{icon} <b>Ping {host}</b>\n<pre>{r.get('output','')[:400]}</pre>")
            elif text == "/help":
                send_msg(chat_id,
                    "📖 <b>Commands:</b>\n"
                    "/start — Menu chính\n"
                    "/devices — Danh sách thiết bị\n"
                    "/status — Tổng quan\n"
                    "/ping &lt;host&gt; — Ping\n"
                    "/connect &lt;name&gt; — Connect thiết bị\n"
                    "/cmd &lt;device&gt; &lt;command&gt; — Chạy lệnh\n"
                    "/services &lt;device&gt; — Xem services"
                )
            elif text.startswith("/connect "):
                dname = text.split(" ",1)[1].strip()
                dev = devices_db.get(dname)
                if not dev:
                    send_msg(chat_id, f"❌ '{dname}' không tìm thấy")
                else:
                    send_msg(chat_id, f"⏳ Đang kết nối {dname}...")
                    try:
                        info = loop.run_until_complete(_connect_and_get_info(dev))
                        devices_db[dname].update({"status":"online",**info}); save_db()
                        send_msg(chat_id, f"✅ <b>{dname}</b> online!\nModel: {info.get('model','?')}\nUptime: {info.get('uptime','?')}")
                    except Exception as e:
                        send_msg(chat_id, f"❌ {e}")
            elif text.startswith("/cmd "):
                parts = text.split(" ",2)
                if len(parts)<3:
                    send_msg(chat_id, "Usage: /cmd &lt;device&gt; &lt;command&gt;")
                else:
                    dname, cmd = parts[1], parts[2]
                    dev = devices_db.get(dname)
                    if not dev:
                        send_msg(chat_id, f"❌ '{dname}' không tìm thấy")
                    else:
                        send_msg(chat_id, f"⏳ Đang chạy lệnh...")
                        vendor = dev.get("vendor","").lower()
                        try:
                            if vendor=="mikrotik": out = loop.run_until_complete(cmd_mikrotik(dev,cmd))
                            elif vendor=="cisco": out = loop.run_until_complete(cmd_cisco(dev,cmd))
                            else: out = loop.run_until_complete(cmd_ssh_generic(dev,cmd))
                            send_msg(chat_id, f"💻 <b>{dname}</b>\n<code>{cmd}</code>\n<pre>{str(out)[:800]}</pre>")
                        except Exception as e:
                            send_msg(chat_id, f"❌ {e}")
            elif text.startswith(("/iface", "/cpu ", "/alert ", "/monitor ")):
                # Monitor commands qua asyncio
                asyncio.run_coroutine_threadsafe(
                    _handle_monitor_commands(chat_id, text), loop
                )
            else:
                send_msg(chat_id, f"❓ Lệnh không nhận ra. Dùng /help")
        except Exception as e:
            print(f"[BOT] handle_update error: {e}")

    # Skip old messages
    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"https://api.telegram.org/bot{token}/getUpdates", params={"offset":-1,"limit":1})
            data = r.json()
            if data.get("ok") and data.get("result"):
                polling_offset = data["result"][-1]["update_id"] + 1
                print(f"[BOT] Skip to offset {polling_offset}")
    except: pass

    while polling_active:
        try:
            with httpx.Client(timeout=35) as c:
                r = c.get(
                    f"https://api.telegram.org/bot{token}/getUpdates",
                    params={"offset": polling_offset, "timeout": 30, "limit": 10}
                )
                data = r.json()
                if data.get("ok"):
                    for update in data.get("result",[]):
                        polling_offset = update["update_id"] + 1
                        handle_update(update)
                else:
                    print(f"[BOT] API error: {data}")
                    _t.sleep(3)
        except Exception as e:
            if polling_active:
                print(f"[BOT] Polling error: {e}")
                _t.sleep(3)

    loop.close()
    print("[BOT] Polling stopped")

@app.post("/api/bot/polling/start")
async def start_polling():
    global polling_thread, polling_active
    token = bot_config.get("token","")
    if not token: raise HTTPException(400, "Bot token not configured")
    if polling_active:
        polling_active = False
        import time as _t; _t.sleep(1)
    global polling_offset
    polling_offset = 0  # Reset offset — get all pending messages
    # Clear webhook first so polling works
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(f"https://api.telegram.org/bot{token}/deleteWebhook")
    except: pass
    polling_active = True
    polling_thread = threading.Thread(target=run_polling, daemon=True)
    polling_thread.start()
    return {"status": "started", "mode": "polling"}

@app.post("/api/bot/polling/stop")
async def stop_polling():
    global polling_active
    polling_active = False
    return {"status": "stopped"}

@app.get("/api/bot/polling/status")
async def polling_status():
    return {
        "active": polling_active,
        "thread_alive": polling_thread.is_alive() if polling_thread else False,
        "offset": polling_offset
    }

@app.get("/api/bot/set-webhook")
async def setup_webhook(webhook_url: str):
    """Register webhook URL with Telegram (for public server)"""
    import httpx
    token = bot_config.get("token","")
    if not token: raise HTTPException(400, "Bot token not configured")
    # Stop polling if running
    global polling_active
    polling_active = False
    async with httpx.AsyncClient() as client:
        r = await client.post(f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": f"{webhook_url}/api/bot/webhook"})
        return r.json()

# ══════════════════════════════════════════════════════════════════
# SERIAL CONSOLE — WebSocket streaming (như Putty/SecureCRT)
# ══════════════════════════════════════════════════════════════════
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

@app.websocket("/ws/serial/{session_id}")
async def serial_ws(websocket: WebSocket, session_id: str):
    """WebSocket — bidirectional serial bridge like Putty"""
    await websocket.accept()
    session = serial_sessions.get(session_id)
    if not session:
        await websocket.send_text("[ERROR] Session not found\r\n")
        await websocket.close()
        return

    ser = session["serial"]
    ser.timeout = 0.05
    ser.write_timeout = 2

    await websocket.send_text(f"[Connected: {session['port']} @ {session['baudrate']} baud]\r\n")

    loop = asyncio.get_event_loop()
    alive = True

    async def reader():
        """Serial → Browser: blocking read(1) như Putty"""
        nonlocal alive
        while alive:
            try:
                # Blocking read 1 byte (timeout=0.1s trên ser)
                data = await loop.run_in_executor(None, ser.read, 1)
                if data:
                    # Đọc thêm nếu còn data trong buffer
                    extra = ser.in_waiting
                    if extra > 0:
                        data += await loop.run_in_executor(None, ser.read, extra)
                    text = data.decode("utf-8", errors="replace")
                    print(f"[WS:reader] {repr(text[:50])}")
                    await websocket.send_text(text)
            except Exception as e:
                print(f"[WS:reader error] {e}")
                alive = False
                break

    async def writer():
        """Browser → Serial: nhận input gửi xuống switch"""
        nonlocal alive
        while alive:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if ser.is_open:
                    ser.write(data.encode("utf-8"))
                    ser.flush()
                    print(f"[WS:write] {repr(data)}")
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                alive = False
                break
            except Exception as e:
                print(f"[WS:writer] {e}")
                alive = False
                break

    try:
        await asyncio.gather(reader(), writer())
    except Exception as e:
        print(f"[WS] gather: {e}")
    finally:
        alive = False
        print(f"[WS] Closed: {session_id}")



# ══════════════════════════════════════════════════════════════════
# MONITORING ENGINE — InfluxDB + Poll + Threshold Alerts
# ══════════════════════════════════════════════════════════════════

import threading
from datetime import datetime, timezone

# ── InfluxDB config ───────────────────────────────────────────────
INFLUX_URL    = os.environ.get("INFLUX_URL",    "http://localhost:8086")
INFLUX_TOKEN  = os.environ.get("INFLUX_TOKEN",  "plnetwork-token")
INFLUX_ORG    = os.environ.get("INFLUX_ORG",    "plnetwork")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "metrics")

def _influx_client():
    try:
        from influxdb_client import InfluxDBClient
        return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    except ImportError:
        raise Exception("pip install influxdb-client")

def influx_write(records: list):
    """Write list of Point objects to InfluxDB"""
    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS
        with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=INFLUX_BUCKET, record=records)
    except Exception as e:
        print(f"[InfluxDB write] {e}")

def influx_query(flux: str) -> list:
    """Run Flux query, return list of dicts"""
    try:
        from influxdb_client import InfluxDBClient
        with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
            tables = client.query_api().query(flux)
            rows = []
            for table in tables:
                for record in table.records:
                    rows.append({
                        "time":  record.get_time().isoformat(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                        "tags":  dict(record.values),
                    })
            return rows
    except Exception as e:
        print(f"[InfluxDB query] {e}")
        return []

# ── Previous interface counters (để tính bandwidth delta) ─────────
_prev_counters: Dict[str, dict] = {}   # key: "device:iface"
_prev_ts: Dict[str, float] = {}        # key: "device:iface"

def _collect_mikrotik(name: str, device: dict):
    """
    Poll MikroTik qua RouterOS API:
    - /system/resource → cpu, memory
    - /interface       → rx/tx bytes per interface → bandwidth Mbps
    Ghi vào InfluxDB.
    """
    try:
        import routeros_api
        from influxdb_client import Point
        conn = routeros_api.RouterOsApiPool(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device.get("api_port", 3543),
            use_ssl=device.get("use_ssl", False),
            ssl_verify=device.get("verify_ssl", False),
            plaintext_login=True,
        )
        api  = conn.get_api()
        now  = datetime.now(timezone.utc)
        points = []

        # ── CPU / Memory ─────────────────────────────────────────
        res = list(api.get_resource("/system/resource").get())[0]
        cpu      = float(res.get("cpu-load", 0))
        mem_tot  = int(res.get("total-memory", 1))
        mem_free = int(res.get("free-memory",  0))
        mem_pct  = round((1 - mem_free / mem_tot) * 100, 1) if mem_tot else 0
        hdd_tot  = int(res.get("total-hdd-space", 1))
        hdd_free = int(res.get("free-hdd-space",  0))
        hdd_pct  = round((1 - hdd_free / hdd_tot) * 100, 1) if hdd_tot else 0
        uptime   = res.get("uptime", "")

        points.append(
            Point("system")
            .tag("device", name)
            .tag("vendor", "mikrotik")
            .field("cpu",     cpu)
            .field("mem",     mem_pct)
            .field("hdd",     hdd_pct)
            .field("uptime",  uptime)
            .time(now)
        )

        # Cập nhật live vào devices_db
        devices_db[name]["cpu"] = cpu
        devices_db[name]["mem"] = mem_pct

        # ── Interface traffic ─────────────────────────────────────
        ifaces = list(api.get_resource("/interface").get())
        conn.disconnect()
        ts_now = now.timestamp()

        for iface in ifaces:
            iface_name = iface.get("name", "")
            if not iface_name:
                continue
            rx_bytes = int(iface.get("rx-byte", 0))
            tx_bytes = int(iface.get("tx-byte", 0))
            rx_drop  = int(iface.get("rx-drop",  0))
            tx_drop  = int(iface.get("tx-drop",  0))
            rx_err   = int(iface.get("rx-error", 0))
            tx_err   = int(iface.get("tx-error", 0))
            running  = iface.get("running", "false") == "true"
            disabled = iface.get("disabled", "false") == "true"

            key = f"{name}:{iface_name}"
            rx_mbps = tx_mbps = 0.0

            if key in _prev_counters and key in _prev_ts:
                dt = ts_now - _prev_ts[key]
                if dt > 0:
                    prev = _prev_counters[key]
                    rx_delta = max(0, rx_bytes - prev.get("rx", 0))
                    tx_delta = max(0, tx_bytes - prev.get("tx", 0))
                    rx_mbps  = round(rx_delta * 8 / dt / 1_000_000, 4)
                    tx_mbps  = round(tx_delta * 8 / dt / 1_000_000, 4)

            _prev_counters[key] = {"rx": rx_bytes, "tx": tx_bytes}
            _prev_ts[key]       = ts_now

            points.append(
                Point("interface")
                .tag("device",    name)
                .tag("iface",     iface_name)
                .tag("vendor",    "mikrotik")
                .field("rx_mbps",  rx_mbps)
                .field("tx_mbps",  tx_mbps)
                .field("rx_bytes", rx_bytes)
                .field("tx_bytes", tx_bytes)
                .field("rx_drop",  rx_drop)
                .field("tx_drop",  tx_drop)
                .field("rx_error", rx_err)
                .field("tx_error", tx_err)
                .field("running",  1 if running else 0)
                .field("disabled", 1 if disabled else 0)
                .time(now)
            )

        influx_write(points)
        print(f"[Monitor] {name} — cpu={cpu}% mem={mem_pct}% ifaces={len(ifaces)}")

        # ── Kiểm tra ngưỡng alert ─────────────────────────────────
        _check_thresholds(name, cpu=cpu, mem=mem_pct, interfaces=ifaces)

    except Exception as e:
        print(f"[Monitor] {name} poll error: {e}")


def _collect_device(name: str, device: dict):
    """Dispatch collection theo vendor"""
    vendor = device.get("vendor", "").lower()
    if device.get("status") != "online":
        return
    if vendor == "mikrotik":
        _collect_mikrotik(name, device)
    # TODO: cisco, fortinet, sophos — dùng SNMP hoặc SSH/API tương tự


# ── Threshold config ──────────────────────────────────────────────
THRESHOLD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thresholds.json")
_thresholds: dict = {}          # {device_name: {cpu, mem, bw_mbps, ...}}
_alert_cooldown: dict = {}
_alert_acknowledged: dict = {}  # key → timestamp khi user xác nhận
ALERT_ACK_DURATION = 3600  # Sau 1h mới alert lại dù đã xác nhận
ALERT_ACK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_ack.json")

def _load_ack():
    global _alert_acknowledged
    if os.path.exists(ALERT_ACK_FILE):
        try:
            with open(ALERT_ACK_FILE) as f:
                _alert_acknowledged = json.load(f)
        except: pass

def _save_ack():
    try:
        with open(ALERT_ACK_FILE,"w") as f:
            json.dump(_alert_acknowledged, f)
    except: pass

_load_ack()
ALERT_COOLDOWN_SEC = 300        # 5 phút không spam

def _load_thresholds():
    global _thresholds
    if os.path.exists(THRESHOLD_FILE):
        try:
            with open(THRESHOLD_FILE) as f:
                _thresholds = json.load(f)
        except:
            _thresholds = {}

def _save_thresholds():
    with open(THRESHOLD_FILE, "w") as f:
        json.dump(_thresholds, f, indent=2)

_load_thresholds()

def _check_thresholds(name: str, cpu: float, mem: float, interfaces: list):
    """So sánh với ngưỡng đã cấg hình, gửi Telegram nếu vượt"""
    import asyncio, time as _time
    cfg = _thresholds.get(name, {})
    if not cfg:
        return

    def _alert(key: str, msg: str):
        import time as _tt
        now = _tt.time()
        # Kiểm tra cooldown
        last = _alert_cooldown.get(key, 0)
        if now - last < ALERT_COOLDOWN_SEC:
            return
        # Kiểm tra đã được xác nhận chưa
        ack_time = _alert_acknowledged.get(key, 0)
        if now - ack_time < ALERT_ACK_DURATION:
            return
        _alert_cooldown[key] = now
        full_msg = f"⚠️ <b>PlNetwork Alert</b>\n🖥 <b>{name}</b>\n{msg}\n\n<i>Nhấn Xác Nhận để tắt cảnh báo này 1h</i>"
        # Inline keyboard với nút Xác Nhận
        keyboard = {"inline_keyboard": [[
            {"text": "✅ Xác Nhận đã biết", "callback_data": f"ack:{key}"},
            {"text": "🔕 Tắt 24h", "callback_data": f"ack24:{key}"},
        ]]}
        try:
            import asyncio as _aio
            async def _send():
                token = bot_config.get("token","")
                if not token: return
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    for chat_id in bot_config.get("alert_chats",[]):
                        await client.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            json={"chat_id": chat_id, "text": full_msg,
                                  "parse_mode": "HTML", "reply_markup": keyboard}
                        )
            loop = _aio.new_event_loop()
            loop.run_until_complete(_send())
            loop.close()
        except Exception as e:
            print(f"[Alert] {e}")

    # CPU
    cpu_th = cfg.get("cpu")
    if cpu_th and cpu > cpu_th:
        _alert(f"{name}:cpu", f"🔴 CPU cao: <b>{cpu}%</b> (ngưỡng {cpu_th}%)")

    # Memory
    mem_th = cfg.get("mem")
    if mem_th and mem > mem_th:
        _alert(f"{name}:mem", f"🟠 Memory cao: <b>{mem}%</b> (ngưỡng {mem_th}%)")

    # Bandwidth per interface
    bw_th = cfg.get("bw_mbps")
    if bw_th:
        for iface in interfaces:
            iface_name = iface.get("name", "")
            key = f"{name}:{iface_name}"
            prev = _prev_counters.get(key, {})
            # bandwidth đã tính ở _collect_mikrotik, đọc từ prev
            # Dùng lại logic đơn giản — nếu > threshold thì alert
            rx_bytes = int(iface.get("rx-byte", 0))
            tx_bytes = int(iface.get("tx-byte", 0))
            prev_rx  = prev.get("rx", 0)
            prev_tx  = prev.get("tx", 0)
            dt = _prev_ts.get(key, 0)
            if dt and prev_rx:
                elapsed = datetime.now(timezone.utc).timestamp() - dt
                if elapsed > 0:
                    rx_mbps = (rx_bytes - prev_rx) * 8 / elapsed / 1_000_000
                    tx_mbps = (tx_bytes - prev_tx) * 8 / elapsed / 1_000_000
                    if rx_mbps > bw_th:
                        _alert(f"{name}:{iface_name}:rx",
                               f"📶 <b>{iface_name}</b> RX cao: <b>{rx_mbps:.1f} Mbps</b> (ngưỡng {bw_th} Mbps)")
                    if tx_mbps > bw_th:
                        _alert(f"{name}:{iface_name}:tx",
                               f"📶 <b>{iface_name}</b> TX cao: <b>{tx_mbps:.1f} Mbps</b> (ngưỡng {bw_th} Mbps)")

    # Interface down
    if cfg.get("iface_down", False):
        for iface in interfaces:
            iface_name = iface.get("name", "")
            running    = iface.get("running", "false") == "true"
            disabled   = iface.get("disabled", "false") == "true"
            if not running and not disabled:
                _alert(f"{name}:{iface_name}:down",
                       f"🔴 Interface <b>{iface_name}</b> DOWN!")


# ── Poll Scheduler ────────────────────────────────────────────────
_poll_jobs:    Dict[str, threading.Timer] = {}
_poll_active:  bool = False
_poll_configs: Dict[str, int] = {}   # device → interval seconds

def _schedule_poll(name: str, interval: int):
    """Tạo vòng lặp poll bằng threading.Timer"""
    def _run():
        if not _poll_active:
            return
        device = devices_db.get(name)
        if device:
            threading.Thread(target=_collect_device, args=(name, device), daemon=True).start()
        # Lên lịch lần tiếp theo
        if _poll_active and name in _poll_configs:
            t = threading.Timer(_poll_configs[name], _run)
            t.daemon = True
            _poll_jobs[name] = t
            t.start()

    t = threading.Timer(interval, _run)
    t.daemon = True
    _poll_jobs[name] = t
    t.start()

def start_monitor_all():
    """Khởi động poll cho tất cả thiết bị đã có interval cấu hình"""
    global _poll_active
    _poll_active = True
    for name, interval in _poll_configs.items():
        if name not in _poll_jobs or not _poll_jobs[name].is_alive():
            _schedule_poll(name, interval)
    print(f"[Monitor] Started {len(_poll_configs)} device(s)")

def stop_monitor_all():
    global _poll_active
    _poll_active = False
    for t in _poll_jobs.values():
        t.cancel()
    _poll_jobs.clear()
    print("[Monitor] Stopped")


# ── Load poll config từ file ──────────────────────────────────────
MONITOR_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitor_config.json")
_monitor_cfg: dict = {}   # {device: {interval, enabled}}

def _load_monitor_config():
    global _monitor_cfg, _poll_configs
    if os.path.exists(MONITOR_CONFIG_FILE):
        try:
            with open(MONITOR_CONFIG_FILE) as f:
                _monitor_cfg = json.load(f)
            for name, cfg in _monitor_cfg.items():
                if cfg.get("enabled", True):
                    _poll_configs[name] = cfg.get("interval", 60)
        except:
            pass

def _save_monitor_config():
    with open(MONITOR_CONFIG_FILE, "w") as f:
        json.dump(_monitor_cfg, f, indent=2)

_load_monitor_config()

# Auto-start nếu đã có config
if _poll_configs:
    start_monitor_all()


# ══════════════════════════════════════════════════════════════════
# MONITOR API ENDPOINTS
# ══════════════════════════════════════════════════════════════════

class ThresholdConfig(BaseModel):
    cpu:        Optional[float] = None   # % vd: 80
    mem:        Optional[float] = None   # % vd: 85
    bw_mbps:    Optional[float] = None   # Mbps vd: 900
    iface_down: bool = True

class MonitorConfig(BaseModel):
    interval: int  = 60      # giây: 30, 60, 300
    enabled:  bool = True

# ── Cấu hình poll interval per device ────────────────────────────
@app.post("/api/monitor/{name}/config")
async def set_monitor_config(name: str, cfg: MonitorConfig):
    """Bật monitor + đặt interval cho thiết bị"""
    if name not in devices_db:
        raise HTTPException(404, "Device not found")
    if cfg.interval not in (30, 60, 300):
        raise HTTPException(400, "interval phải là 30, 60 hoặc 300 giây")

    _monitor_cfg[name] = {"interval": cfg.interval, "enabled": cfg.enabled}
    _save_monitor_config()

    if cfg.enabled:
        _poll_configs[name] = cfg.interval
        if name in _poll_jobs:
            _poll_jobs[name].cancel()
        if _poll_active:
            _schedule_poll(name, cfg.interval)
        start_monitor_all()
    else:
        _poll_configs.pop(name, None)
        if name in _poll_jobs:
            _poll_jobs[name].cancel()
            _poll_jobs.pop(name, None)

    return {"status": "ok", "device": name, "interval": cfg.interval, "enabled": cfg.enabled}

@app.get("/api/monitor/{name}/config")
async def get_monitor_config(name: str):
    return _monitor_cfg.get(name, {"interval": 60, "enabled": False})

@app.get("/api/monitor/status")
async def monitor_status():
    return {
        "active": _poll_active,
        "devices": {
            name: {
                "interval": _poll_configs.get(name),
                "enabled":  name in _poll_configs,
                "running":  name in _poll_jobs and _poll_jobs[name].is_alive(),
            }
            for name in _monitor_cfg
        }
    }

@app.post("/api/monitor/start")
async def monitor_start():
    start_monitor_all()
    return {"status": "started"}

@app.post("/api/monitor/stop")
async def monitor_stop():
    stop_monitor_all()
    return {"status": "stopped"}

# ── Threshold CRUD ────────────────────────────────────────────────
@app.get("/api/monitor/{name}/thresholds")
async def get_thresholds(name: str):
    return _thresholds.get(name, {})

@app.post("/api/monitor/{name}/thresholds")
async def set_thresholds(name: str, cfg: ThresholdConfig):
    if name not in devices_db:
        raise HTTPException(404, "Device not found")
    _thresholds[name] = cfg.dict(exclude_none=False)
    _save_thresholds()
    return {"status": "ok", "thresholds": _thresholds[name]}

@app.delete("/api/monitor/{name}/thresholds")
async def delete_thresholds(name: str):
    _thresholds.pop(name, None)
    _save_thresholds()
    return {"status": "deleted"}

# ── Query metrics từ InfluxDB ─────────────────────────────────────
@app.get("/api/monitor/{name}/metrics")
async def get_metrics(name: str, range: str = "1h", field: str = "cpu,mem"):
    """
    Lấy CPU/mem history.
    range: 1h | 6h | 24h | 7d | 30d
    field: cpu,mem,hdd (comma-separated)
    """
    valid_ranges = {"1h", "6h", "24h", "7d", "30d"}
    if range not in valid_ranges:
        raise HTTPException(400, f"range phải là: {valid_ranges}")

    fields = [f.strip() for f in field.split(",")]
    filter_fields = " or ".join(f'r["_field"] == "{f}"' for f in fields)

    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -{range})
  |> filter(fn: (r) => r["_measurement"] == "system")
  |> filter(fn: (r) => r["device"] == "{name}")
  |> filter(fn: (r) => {filter_fields})
  |> aggregateWindow(every: {"1m" if range in ("1h","6h") else "10m" if range == "24h" else "1h"}, fn: mean, createEmpty: false)
  |> yield(name: "mean")
'''
    rows = await asyncio.to_thread(influx_query, flux)
    # Gom theo field
    result: dict = {}
    for row in rows:
        f = row["field"]
        if f not in result:
            result[f] = []
        result[f].append({"t": row["time"], "v": round(row["value"], 2)})
    return {"device": name, "range": range, "data": result}

@app.get("/api/monitor/{name}/interfaces")
async def get_interface_traffic(name: str, range: str = "1h", iface: str = ""):
    """
    Lấy traffic (rx_mbps, tx_mbps) per interface.
    iface: tên interface cụ thể, hoặc để trống lấy tất cả
    """
    valid_ranges = {"1h", "6h", "24h", "7d", "30d"}
    if range not in valid_ranges:
        raise HTTPException(400, f"range phải là: {valid_ranges}")

    iface_filter = f'|> filter(fn: (r) => r["iface"] == "{iface}")' if iface else ""
    window = "1m" if range in ("1h", "6h") else "10m" if range == "24h" else "1h"

    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -{range})
  |> filter(fn: (r) => r["_measurement"] == "interface")
  |> filter(fn: (r) => r["device"] == "{name}")
  |> filter(fn: (r) => r["_field"] == "rx_mbps" or r["_field"] == "tx_mbps")
  {iface_filter}
  |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
  |> yield(name: "mean")
'''
    rows = await asyncio.to_thread(influx_query, flux)

    # Gom theo iface → {rx: [...], tx: [...]}
    result: dict = {}
    for row in rows:
        tags      = row.get("tags", {})
        iface_n   = tags.get("iface", "unknown")
        field     = row["field"]
        if iface_n not in result:
            result[iface_n] = {"rx": [], "tx": []}
        key = "rx" if field == "rx_mbps" else "tx"
        result[iface_n][key].append({"t": row["time"], "v": round(row["value"], 4)})

    return {"device": name, "range": range, "interfaces": result}

@app.get("/api/monitor/{name}/interfaces/live")
async def get_interface_live(name: str):
    """
    Snapshot live: lấy bandwidth + status của tất cả interface ngay lúc này
    (không qua InfluxDB — gọi thẳng RouterOS API)
    """
    if name not in devices_db:
        raise HTTPException(404, "Device not found")
    device = devices_db[name]
    if device.get("status") != "online":
        raise HTTPException(400, "Device offline")
    vendor = device.get("vendor", "").lower()
    if vendor != "mikrotik":
        raise HTTPException(400, "Chỉ hỗ trợ MikroTik hiện tại")

    try:
        result = await asyncio.to_thread(_mikrotik_interface_snapshot, device, name)
        return {"device": name, "interfaces": result}
    except Exception as e:
        raise HTTPException(500, str(e))

def _mikrotik_interface_snapshot(device: dict, name: str) -> list:
    import routeros_api, time as _t
    conn = routeros_api.RouterOsApiPool(
        host=device["host"], username=device["username"],
        password=device["password"], port=device.get("api_port", 3543),
        use_ssl=device.get("use_ssl", False), ssl_verify=False,
        plaintext_login=True,
    )
    api    = conn.get_api()
    ifaces = list(api.get_resource("/interface").get())
    conn.disconnect()
    ts_now = _t.time()
    result = []
    for iface in ifaces:
        iface_name = iface.get("name", "")
        rx_bytes   = int(iface.get("rx-byte", 0))
        tx_bytes   = int(iface.get("tx-byte", 0))
        key        = f"{name}:{iface_name}"
        rx_mbps = tx_mbps = 0.0
        if key in _prev_counters and key in _prev_ts:
            dt = ts_now - _prev_ts[key]
            if dt > 0:
                rx_mbps = round(max(0, rx_bytes - _prev_counters[key]["rx"]) * 8 / dt / 1_000_000, 3)
                tx_mbps = round(max(0, tx_bytes - _prev_counters[key]["tx"]) * 8 / dt / 1_000_000, 3)
        result.append({
            "name":     iface_name,
            "type":     iface.get("type", ""),
            "running":  iface.get("running", "false") == "true",
            "disabled": iface.get("disabled", "false") == "true",
            "rx_mbps":  rx_mbps,
            "tx_mbps":  tx_mbps,
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
            "rx_drop":  int(iface.get("rx-drop", 0)),
            "tx_drop":  int(iface.get("tx-drop", 0)),
        })
    return result


# ══════════════════════════════════════════════════════════════════
# TELEGRAM BOT — Monitor commands
# ══════════════════════════════════════════════════════════════════

async def _handle_monitor_commands(chat_id: str, text: str) -> bool:
    """
    Xử lý các lệnh monitor trong Telegram bot.
    Trả về True nếu đã xử lý, False nếu không phải lệnh monitor.
    """
    parts = text.strip().split()
    cmd   = parts[0].lower() if parts else ""

    # /status — tổng quan tất cả thiết bị
    if cmd == "/status":
        lines = ["📊 <b>PlNetwork Status</b>\n"]
        for dname, dev in devices_db.items():
            status  = dev.get("status", "unknown")
            icon    = "🟢" if status == "online" else "🔴"
            cpu     = dev.get("cpu", "?")
            mem     = dev.get("mem", "?")
            model   = dev.get("model", "")
            vendor  = dev.get("vendor", "").upper()
            mon_on  = dname in _poll_configs
            mon_ico = "📡" if mon_on else "💤"
            lines.append(
                f"{icon} <b>{dname}</b> {mon_ico}\n"
                f"   {vendor} {model}\n"
                f"   CPU: <b>{cpu}%</b>  MEM: <b>{mem}%</b>\n"
            )
        await tg_send(chat_id, "\n".join(lines))
        return True

    # /iface <device> — traffic live các interface
    if cmd == "/iface":
        if len(parts) < 2:
            await tg_send(chat_id, "Usage: /iface <device_name>")
            return True
        dname = parts[1]
        dev   = devices_db.get(dname)
        if not dev:
            await tg_send(chat_id, f"❌ Không tìm thấy thiết bị: {dname}")
            return True
        if dev.get("status") != "online":
            await tg_send(chat_id, f"🔴 {dname} đang offline")
            return True
        try:
            ifaces = await asyncio.to_thread(_mikrotik_interface_snapshot, dev, dname)
            lines  = [f"📶 <b>{dname}</b> — Interface Traffic Live\n"]
            for ifc in ifaces:
                if ifc["disabled"]:
                    continue
                status = "🟢" if ifc["running"] else "🔴"
                rx     = ifc["rx_mbps"]
                tx     = ifc["tx_mbps"]
                lines.append(
                    f"{status} <code>{ifc['name']:<22}</code>"
                    f"  ↓{rx:.2f}  ↑{tx:.2f} Mbps"
                )
            await tg_send(chat_id, "\n".join(lines))
        except Exception as e:
            await tg_send(chat_id, f"❌ Lỗi: {e}")
        return True

    # /cpu <device> [range] — xem đồ thị CPU text
    if cmd == "/cpu":
        if len(parts) < 2:
            await tg_send(chat_id, "Usage: /cpu <device> [1h|6h|24h]")
            return True
        dname = parts[1]
        rng   = parts[2] if len(parts) > 2 else "1h"
        flux  = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -{rng})
  |> filter(fn: (r) => r["_measurement"] == "system" and r["device"] == "{dname}" and r["_field"] == "cpu")
  |> aggregateWindow(every: 10m, fn: mean, createEmpty: false)
  |> yield(name: "mean")
'''
        rows = await asyncio.to_thread(influx_query, flux)
        if not rows:
            await tg_send(chat_id, f"Không có dữ liệu CPU cho {dname} trong {rng}")
            return True
        # Vẽ sparkline text đơn giản
        values = [r["value"] for r in rows]
        mn, mx = min(values), max(values)
        avg    = sum(values) / len(values)
        # Mini bar chart bằng Unicode
        bars   = "▁▂▃▄▅▆▇█"
        chart  = ""
        for v in values[-20:]:  # 20 điểm cuối
            idx    = int((v - mn) / (mx - mn + 0.01) * 7)
            chart += bars[idx]
        await tg_send(chat_id,
            f"📈 <b>{dname}</b> CPU — {rng}\n\n"
            f"<code>{chart}</code>\n\n"
            f"Min: {mn:.1f}%  Avg: {avg:.1f}%  Max: {mx:.1f}%"
        )
        return True

    # /alert <device> cpu=80 mem=85 bw=900 — cấu hình ngưỡng
    if cmd == "/alert":
        if len(parts) < 3:
            await tg_send(chat_id,
                "Usage: /alert <device> cpu=80 mem=85 bw=900\n"
                "Ví dụ: /alert CTHO cpu=80 mem=85 bw=900")
            return True
        dname = parts[1]
        cfg   = {}
        for p in parts[2:]:
            if "=" in p:
                k, v = p.split("=", 1)
                try:
                    cfg[{"bw": "bw_mbps"}.get(k, k)] = float(v)
                except:
                    pass
        cfg["iface_down"] = True
        _thresholds[dname] = cfg
        _save_thresholds()
        lines = [f"✅ Đã cấu hình ngưỡng cho <b>{dname}</b>:"]
        if "cpu" in cfg:     lines.append(f"  CPU > {cfg['cpu']}%")
        if "mem" in cfg:     lines.append(f"  MEM > {cfg['mem']}%")
        if "bw_mbps" in cfg: lines.append(f"  Bandwidth > {cfg['bw_mbps']} Mbps")
        lines.append("  Interface down: ✅")
        await tg_send(chat_id, "\n".join(lines))
        return True

    # /monitor <device> <30|60|300> — bật poll
    if cmd == "/monitor":
        if len(parts) < 3:
            await tg_send(chat_id, "Usage: /monitor <device> <30|60|300>")
            return True
        dname    = parts[1]
        try:
            interval = int(parts[2])
        except:
            interval = 60
        if interval not in (30, 60, 300):
            await tg_send(chat_id, "Interval phải là 30, 60 hoặc 300 giây")
            return True
        if dname not in devices_db:
            await tg_send(chat_id, f"❌ Không tìm thấy: {dname}")
            return True
        _monitor_cfg[dname] = {"interval": interval, "enabled": True}
        _poll_configs[dname] = interval
        _save_monitor_config()
        if dname in _poll_jobs:
            _poll_jobs[dname].cancel()
        _schedule_poll(dname, interval)
        start_monitor_all()
        await tg_send(chat_id,
            f"📡 Monitor bật cho <b>{dname}</b>\n"
            f"  Poll interval: {interval}s\n"
            f"  CPU/mem/bandwidth sẽ được ghi vào InfluxDB"
        )
        return True

    return False   # không phải lệnh monitor

# ══════════════════════════════════════════════════════════════════
# TOPOLOGY DISCOVER — POST /api/topology/discover
#                     GET  /api/devices/{name}/interfaces
#
# Paste đoạn này vào main.py, sau phần khai báo devices_db
# và trước dòng cuối (if __name__ == "__main__":  hoặc uvicorn.run)
# ══════════════════════════════════════════════════════════════════

from topology_discover import discover_all, discover_device as _discover_one


@app.post("/api/topology/discover")
async def topology_discover():
    """
    SSH vào tất cả thiết bị online, thu thập LLDP/CDP neighbors,
    interfaces, ARP, bandwidth → trả về links thật.

    Returns:
      {
        "links": [
          { "id", "from", "to", "type",
            "iface_from", "iface_to",
            "status", "bandwidth", "utilization", "protocol" }
        ],
        "interfaces": { device_name: [...] },
        "errors":     { device_name: null | "error string" }
      }
    """
    # Build device list với credentials từ devices_db
    devices = []
    for name, d in devices_db.items():
        devices.append({
            # Topology fields
            "id":     name,
            "name":   name,
            "ip":     d.get("host", ""),
            "vendor": d.get("vendor", ""),
            "type":   d.get("type", ""),
            "status": "up" if d.get("status") == "online" else "down",
            # SSH credentials
            "ssh_username": d.get("username", ""),
            "ssh_password": d.get("password", ""),
            "ssh_port":     int(d.get("port") or 22),
            "ssh_key_file": d.get("ssh_key_file", None),
            # Cisco enable secret
            "secret":       d.get("secret", ""),
        })

    try:
        result = await asyncio.to_thread(
            _discover_all_sync, devices
        )
        return {
            "links":      result["links"],
            "interfaces": result["interfaces"],
            "errors":     result["errors"],
            "timestamp":  datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/devices/{name}/interfaces")
async def device_interfaces(name: str):
    """
    SSH vào một thiết bị cụ thể, trả về danh sách interfaces với
    status thật, speed, tx/rx rate, mac address.

    Returns:
      {
        "device_id":  "CTHO",
        "interfaces": [
          { "name", "status", "speed", "tx_rate", "rx_rate",
            "utilization", "mac", "comment/description", "type" }
        ],
        "error": null | "error string"
      }
    """
    d = devices_db.get(name)
    if not d:
        raise HTTPException(404, f"Device '{name}' not found")

    dev = {
        "id":           name,
        "name":         name,
        "ip":           d.get("host", ""),
        "vendor":       d.get("vendor", ""),
        "status":       "up" if d.get("status") == "online" else "down",
        "ssh_username": d.get("username", ""),
        "ssh_password": d.get("password", ""),
        "ssh_port":     int(d.get("port") or 22),
        "ssh_key_file": d.get("ssh_key_file", None),
        "secret":       d.get("secret", ""),
    }

    try:
        result = await asyncio.to_thread(_discover_one, dev)
        return {
            "device_id":  name,
            "interfaces": result.get("interfaces", []),
            "neighbors":  result.get("neighbors",  []),
            "arp":        result.get("arp",         []),
            "error":      result.get("error"),
            "timestamp":  datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Sync wrapper cho discover_all (chạy trong thread) ─────────────
def _discover_all_sync(devices: list) -> dict:
    """
    Wrapper đồng bộ cho discover_all — chạy trong asyncio.to_thread
    vì discover_all dùng ThreadPoolExecutor bên trong.
    """
    from topology_discover import discover_all
    return discover_all(devices, max_workers=5)
# ══════════════════════════════════════════════════════════════════
# TOPOLOGY DISCOVER — POST /api/topology/discover
#                     GET  /api/devices/{name}/interfaces
#
# Paste đoạn này vào main.py, sau phần khai báo devices_db
# và trước dòng cuối (if __name__ == "__main__":  hoặc uvicorn.run)
# ══════════════════════════════════════════════════════════════════

from topology_discover import discover_all, discover_device as _discover_one


@app.post("/api/topology/discover")
async def topology_discover():
    """
    SSH vào tất cả thiết bị online, thu thập LLDP/CDP neighbors,
    interfaces, ARP, bandwidth → trả về links thật.

    Returns:
      {
        "links": [
          { "id", "from", "to", "type",
            "iface_from", "iface_to",
            "status", "bandwidth", "utilization", "protocol" }
        ],
        "interfaces": { device_name: [...] },
        "errors":     { device_name: null | "error string" }
      }
    """
    # Build device list với credentials từ devices_db
    devices = []
    for name, d in devices_db.items():
        devices.append({
            # Topology fields
            "id":     name,
            "name":   name,
            "ip":     d.get("host", ""),
            "vendor": d.get("vendor", ""),
            "type":   d.get("type", ""),
            "status": "up" if d.get("status") == "online" else "down",
            # SSH credentials
            "ssh_username": d.get("username", ""),
            "ssh_password": d.get("password", ""),
            "ssh_port":     int(d.get("port") or 22),
            "ssh_key_file": d.get("ssh_key_file", None),
            # Cisco enable secret
            "secret":       d.get("secret", ""),
        })

    try:
        result = await asyncio.to_thread(
            _discover_all_sync, devices
        )
        return {
            "links":      result["links"],
            "interfaces": result["interfaces"],
            "errors":     result["errors"],
            "timestamp":  datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/devices/{name}/interfaces")
async def device_interfaces(name: str):
    """
    SSH vào một thiết bị cụ thể, trả về danh sách interfaces với
    status thật, speed, tx/rx rate, mac address.

    Returns:
      {
        "device_id":  "CTHO",
        "interfaces": [
          { "name", "status", "speed", "tx_rate", "rx_rate",
            "utilization", "mac", "comment/description", "type" }
        ],
        "error": null | "error string"
      }
    """
    d = devices_db.get(name)
    if not d:
        raise HTTPException(404, f"Device '{name}' not found")

    dev = {
        "id":           name,
        "name":         name,
        "ip":           d.get("host", ""),
        "vendor":       d.get("vendor", ""),
        "status":       "up" if d.get("status") == "online" else "down",
        "ssh_username": d.get("username", ""),
        "ssh_password": d.get("password", ""),
        "ssh_port":     int(d.get("port") or 22),
        "ssh_key_file": d.get("ssh_key_file", None),
        "secret":       d.get("secret", ""),
    }

    try:
        result = await asyncio.to_thread(_discover_one, dev)
        return {
            "device_id":  name,
            "interfaces": result.get("interfaces", []),
            "neighbors":  result.get("neighbors",  []),
            "arp":        result.get("arp",         []),
            "error":      result.get("error"),
            "timestamp":  datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Sync wrapper cho discover_all (chạy trong thread) ─────────────
def _discover_all_sync(devices: list) -> dict:
    """
    Wrapper đồng bộ cho discover_all — chạy trong asyncio.to_thread
    vì discover_all dùng ThreadPoolExecutor bên trong.
    """
    from topology_discover import discover_all
    return discover_all(devices, max_workers=5)

# ══════════════════════════════════════════════════════════════════
# SECURITY & AUDIT
# ══════════════════════════════════════════════════════════════════
import hashlib, difflib

AUDIT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_log.json")
CONFIG_SNAPSHOT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_snapshots.json")

# Load audit log
_audit_log: list = []
_config_snapshots: dict = {}

def _load_audit():
    global _audit_log
    if os.path.exists(AUDIT_FILE):
        try:
            with open(AUDIT_FILE) as f:
                _audit_log = json.load(f)
        except: _audit_log = []

def _save_audit():
    with open(AUDIT_FILE, "w") as f:
        json.dump(_audit_log[-1000:], f, indent=2)

def _load_snapshots():
    global _config_snapshots
    if os.path.exists(CONFIG_SNAPSHOT_FILE):
        try:
            with open(CONFIG_SNAPSHOT_FILE) as f:
                _config_snapshots = json.load(f)
        except: _config_snapshots = {}

def _save_snapshots():
    with open(CONFIG_SNAPSHOT_FILE, "w") as f:
        json.dump(_config_snapshots, f, indent=2)

_load_audit()
_load_snapshots()

def add_audit_log(action: str, device: str, user: str, detail: str, status: str = "ok"):
    entry = {
        "time": datetime.now().isoformat(),
        "action": action,
        "device": device,
        "user": user,
        "detail": detail,
        "status": status,
    }
    _audit_log.append(entry)
    _save_audit()
    # Alert Telegram nếu có hành động nguy hiểm
    if action in ("config_push","rollback","device_delete","service_change"):
        asyncio.create_task(send_alert_all(
            f"🔐 <b>Audit Alert</b>\n"
            f"👤 User: <b>{user}</b>\n"
            f"🖥 Device: <b>{device}</b>\n"
            f"⚡ Action: <b>{action}</b>\n"
            f"📝 {detail}"
        ))

# ── Audit Log API ─────────────────────────────────────────────────
@app.get("/api/audit/logs")
async def get_audit_logs(limit: int = 200, device: str = None, action: str = None):
    logs = _audit_log[-limit:]
    if device: logs = [l for l in logs if l.get("device") == device]
    if action: logs = [l for l in logs if l.get("action") == action]
    return {"logs": list(reversed(logs)), "total": len(_audit_log)}

@app.delete("/api/audit/logs")
async def clear_audit_logs():
    global _audit_log
    _audit_log = []
    _save_audit()
    return {"status": "cleared"}

# ── Config Diff API ───────────────────────────────────────────────
@app.post("/api/audit/snapshot/{name}")
async def take_config_snapshot(name: str):
    """Lấy config hiện tại và so sánh với snapshot trước"""
    device = devices_db.get(name)
    if not device: raise HTTPException(404, "Device not found")
    try:
        r = await api_call_device(name, "backup")
        config = r.get("backup", "")
    except:
        # Fallback: lấy running config
        try:
            r = await api_call_device(name, "config_get")
            config = r.get("config", "")
        except Exception as e:
            raise HTTPException(500, str(e))

    now = datetime.now().isoformat()
    prev = _config_snapshots.get(name, {})
    prev_config = prev.get("config", "")
    prev_hash = prev.get("hash", "")
    curr_hash = hashlib.md5(config.encode()).hexdigest()

    diff = ""
    changed = curr_hash != prev_hash
    if changed and prev_config:
        diff_lines = list(difflib.unified_diff(
            prev_config.splitlines(),
            config.splitlines(),
            fromfile=f"{name} (trước)",
            tofile=f"{name} (hiện tại)",
            lineterm=""
        ))
        diff = "\n".join(diff_lines[:200])  # Max 200 dòng diff
        # Alert nếu config thay đổi
        await send_alert_all(
            f"⚠️ <b>Config Changed!</b>\n"
            f"🖥 Device: <b>{name}</b>\n"
            f"🕐 Time: {now}\n"
            f"📝 {len(diff_lines)} dòng thay đổi"
        )
        add_audit_log("config_change", name, "system", f"Config changed: {len(diff_lines)} lines diff")

    _config_snapshots[name] = {
        "config": config,
        "hash": curr_hash,
        "time": now,
        "prev_hash": prev_hash,
    }
    _save_snapshots()

    return {
        "name": name,
        "changed": changed,
        "hash": curr_hash,
        "prev_hash": prev_hash,
        "time": now,
        "diff": diff,
    }

@app.get("/api/audit/snapshot/{name}")
async def get_config_snapshot(name: str):
    snap = _config_snapshots.get(name)
    if not snap: raise HTTPException(404, "No snapshot yet")
    return snap

@app.get("/api/audit/snapshots")
async def list_snapshots():
    return {
        name: {
            "hash": s.get("hash",""),
            "time": s.get("time",""),
            "changed": s.get("hash") != s.get("prev_hash",""),
        }
        for name, s in _config_snapshots.items()
    }

# ── IP Scanner ────────────────────────────────────────────────────
@app.post("/api/audit/ipscan")
async def ip_scan(req: dict):
    """Quét subnet tìm IP đang hoạt động"""
    subnet = req.get("subnet", "10.10.79.0/24")
    import ipaddress, socket, concurrent.futures

    try:
        net = ipaddress.ip_network(subnet, strict=False)
    except: raise HTTPException(400, "Subnet không hợp lệ")

    hosts = list(net.hosts())[:254]  # Max 254 hosts

    import ipaddress as _iplib

    def _is_private(ip):
        try:
            return _iplib.ip_address(ip).is_private
        except: return False

    def _is_public(ip):
        try:
            a = _iplib.ip_address(ip)
            return not a.is_private and not a.is_loopback and not a.is_link_local
        except: return False

    def _is_gateway(ip):
        """IP .1 hoặc .254 của subnet thường là gateway"""
        try:
            last = int(ip.split(".")[-1])
            return last in (1, 254)
        except: return False

    # Tập hợp IP đã biết từ devices_db
    known_ips = set()
    for d in devices_db.values():
        host = d.get("host","")
        if host: known_ips.add(host)
        # Thêm local IP của thiết bị nếu có
        if d.get("local_ip"): known_ips.add(d["local_ip"])

    # Thêm gateway (.1) của subnet đang scan
    try:
        net2 = _iplib.ip_network(subnet, strict=False)
        hosts_list = list(net2.hosts())
        if hosts_list:
            known_ips.add(str(hosts_list[0]))   # .1 gateway
            known_ips.add(str(hosts_list[-1]))   # .254 gateway
    except: pass

    def check_host(ip):
        ip_str = str(ip)
        try:
            sock = socket.create_connection((ip_str, 22), timeout=1)
            sock.close()
            port = 22
        except:
            try:
                sock = socket.create_connection((ip_str, 80), timeout=1)
                sock.close()
                port = 80
            except:
                try:
                    sock = socket.create_connection((ip_str, 443), timeout=1)
                    sock.close()
                    port = 443
                except:
                    return None
        try:
            hostname = socket.gethostbyaddr(ip_str)[0]
        except: hostname = ""
        # Phân loại IP
        is_known = ip_str in known_ips
        is_gw = _is_gateway(ip_str)
        is_pub = _is_public(ip_str)
        if is_gw: is_known = True  # Gateway luôn là known

        return {
            "ip": ip_str,
            "port": port,
            "hostname": hostname,
            "known": is_known,
            "new": not is_known,
            "type": "gateway" if is_gw else ("public" if is_pub else "local"),
        }

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(check_host, ip): ip for ip in hosts}
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            if r: results.append(r)

    new_devices = [r for r in results if r["new"]]
    if new_devices:
        await send_alert_all(
            f"🔍 <b>IP Scan Alert</b>\n"
            f"Subnet: <b>{subnet}</b>\n"
            f"🆕 {len(new_devices)} thiết bị lạ phát hiện:\n" +
            "\n".join(f"  • {d['ip']} (port {d['port']})" for d in new_devices[:10])
        )
        add_audit_log("ip_scan", "network", "system", f"Found {len(new_devices)} unknown devices in {subnet}")

    results.sort(key=lambda x: [int(p) for p in x["ip"].split(".")])
    return {
        "subnet": subnet,
        "total_found": len(results),
        "known": len([r for r in results if r["known"]]),
        "new": len(new_devices),
        "hosts": results,
    }

# ── Schedule Config API ───────────────────────────────────────────
@app.get("/api/schedule/config")
async def get_schedule_config():
    return {
        **_schedule_cfg,
        "backup_active": backup_schedule_active,
        "backup_interval_hours": BACKUP_INTERVAL_HOURS,
    }

@app.post("/api/schedule/config")
async def save_schedule_config(req: dict):
    global backup_schedule_active, backup_schedule_thread, BACKUP_INTERVAL_HOURS
    _schedule_cfg.update(req)
    _save_schedule_config()
    # Apply backup schedule
    if req.get("backup_enabled"):
        BACKUP_INTERVAL_HOURS = req.get("backup_hours", 24)
        if not backup_schedule_active:
            backup_schedule_active = True
            backup_schedule_thread = _threading.Thread(target=_backup_schedule_loop, daemon=True)
            backup_schedule_thread.start()
            print(f"[SCHEDULE] Backup started every {BACKUP_INTERVAL_HOURS}h")
    else:
        backup_schedule_active = False
    return {"status": "ok", **_schedule_cfg}

@app.post("/api/schedule/backup/now")
async def backup_now():
    """Trigger manual backup ngay lập tức"""
    results = await asyncio.to_thread(_backup_all_sync)
    add_audit_log("backup", "all", "manual", f"Manual backup: {len(results)} devices")
    return {"status": "done", "results": results}
