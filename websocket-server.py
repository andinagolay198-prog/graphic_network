"""
WebSocket Server - Real-time Topology Updates
FastAPI + WebSocket
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import json
from datetime import datetime
from typing import Set
import httpx
import os
import uvicorn


app = FastAPI(title="Network Topology Manager API")

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store connected WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        print(f"Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending message: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "connected_clients": len(manager.active_connections)
    }


PLNETWORK_URL = os.environ.get("PLNETWORK_URL", "http://localhost:8001")

@app.get("/api/topology")
async def get_topology():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{PLNETWORK_URL}/api/devices")
            raw = r.json()
        devices = []
        for dev in raw:
            devices.append({
                "id": dev["name"],
                "name": dev["name"],
                "type": "router" if dev.get("vendor")=="mikrotik" else "firewall" if dev.get("vendor") in ("fortinet","sophos") else "switch",
                "ip": dev.get("host",""),
                "status": "up" if dev.get("status")=="online" else "down",
                "vendor": dev.get("vendor","").capitalize(),
                "cpu_usage": dev.get("cpu",0),
                "memory_usage": dev.get("mem",0),
                "uptime": dev.get("uptime",""),
                "model": dev.get("model",""),
            })
        return {"timestamp": __import__("datetime").datetime.now().isoformat(), "devices": devices, "links": []}
    except Exception as e:
        return {"timestamp": __import__("datetime").datetime.now().isoformat(), "devices": [], "links": [], "error": str(e)}

@app.post("/api/device/{device_id}/alert")
async def trigger_device_alert(device_id: str, alert_data: dict):
    """Trigger an alert for a device"""
    message = {
        "type": "alert",
        "device_id": device_id,
        "timestamp": datetime.now().isoformat(),
        "data": alert_data
    }
    
    await manager.broadcast(message)
    return {"status": "alert_sent"}


@app.post("/api/topology/update")
async def update_topology(topology_data: dict):
    """Manual topology update endpoint"""
    message = {
        "type": "topology_update",
        "timestamp": datetime.now().isoformat(),
        "data": topology_data
    }
    
    await manager.broadcast(message)
    return {"status": "update_sent"}


@app.websocket("/ws/topology")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time topology updates"""
    await manager.connect(websocket)
    
    try:
        # Send initial topology on connect
        initial_data = await get_topology()
        await websocket.send_json({
            "type": "initial",
            "data": initial_data
        })
        
        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            
            elif message.get("type") == "request_update":
                topology = await get_topology()
                await websocket.send_json({
                    "type": "topology_data",
                    "data": topology
                })
            
            elif message.get("type") == "subscribe":
                device_id = message.get("device_id")
                await websocket.send_json({
                    "type": "subscribed",
                    "device_id": device_id,
                    "message": f"Subscribed to {device_id}"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket disconnected")
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/api/devices")
async def get_devices():
    """Get all devices"""
    topology = await get_topology()
    return topology.get("devices", [])


@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    """Get specific device details"""
    topology = await get_topology()
    devices = topology.get("devices", [])
    
    device = next((d for d in devices if d["id"] == device_id), None)
    if not device:
        return {"error": "Device not found"}, 404
    
    return device


@app.get("/api/links")
async def get_links():
    """Get all links"""
    topology = await get_topology()
    return topology.get("links", [])


@app.post("/api/devices/{device_id}/reboot")
async def reboot_device(device_id: str):
    """Trigger device reboot"""
    message = {
        "type": "command",
        "command": "reboot",
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }
    
    await manager.broadcast(message)
    return {"status": "reboot_requested", "device_id": device_id}


@app.post("/api/devices/{device_id}/config")
async def update_device_config(device_id: str, config: dict):
    """Update device configuration"""
    message = {
        "type": "config_update",
        "device_id": device_id,
        "config": config,
        "timestamp": datetime.now().isoformat()
    }
    
    await manager.broadcast(message)
    return {"status": "config_updated", "device_id": device_id}


# Simulated data update task
async def simulate_metrics_update():
    """Simulate periodic metrics updates"""
    import random
    
    while True:
        await asyncio.sleep(5)  # Update setiap 5 detik
        
        # Simulate device metrics changes
        devices = [
            {
                "id": "core-1",
                "cpu_usage": random.randint(30, 60),
                "memory_usage": random.randint(50, 70),
                "interface_1_rx": random.randint(10, 100),
                "interface_1_tx": random.randint(10, 80),
            },
            {
                "id": "fw-1",
                "cpu_usage": random.randint(20, 50),
                "memory_usage": random.randint(40, 60),
                "session_count": random.randint(100, 500),
                "threat_detected": random.randint(0, 5),
            },
        ]
        
        for device in devices:
            message = {
                "type": "metrics_update",
                "device_id": device["id"],
                "timestamp": datetime.now().isoformat(),
                "metrics": device
            }
            
            await manager.broadcast(message)


@app.on_event("startup")
async def startup():
    """Start background tasks"""
    asyncio.create_task(simulate_metrics_update())
    print("Network Topology Manager started")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    print("Network Topology Manager shut down")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

@app.post("/api/topology/discover")
async def topology_discover():
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{PLNETWORK_URL}/api/topology/discover")
            data = r.json()
        await manager.broadcast({"type": "topology_update", "timestamp": datetime.now().isoformat(), "data": data})
        return data
    except httpx.TimeoutException:
        return {"links": [], "interfaces": {}, "errors": {}, "error": "timeout"}
    except Exception as e:
        return {"links": [], "interfaces": {}, "errors": {}, "error": str(e)}

@app.get("/api/devices/{device_id}/interfaces")
async def get_device_interfaces(device_id: str):
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(f"{PLNETWORK_URL}/api/devices/{device_id}/interfaces")
            return r.json()
    except Exception as e:
        return {"device_id": device_id, "interfaces": [], "error": str(e)}
