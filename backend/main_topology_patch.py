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
