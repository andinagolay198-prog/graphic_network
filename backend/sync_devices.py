import json

# Thêm devices thủ công vào đây
devices = [
    {
        "name": "CTHO",
        "vendor": "mikrotik",
        "host": "14.176.141.36",
        "username": "admin",
        "password": "Digital#002",
        "api_port": 3543,
        "use_ssl": False,
        "port": 22,
        "status": "offline",
        "note": "HOME SERVER"
    },
    {
        "name": "CISCO-SW1",
        "vendor": "cisco",
        "host": "10.10.79.2",
        "username": "admin",
        "password": "Admin@123",
        "port": 22,
        "device_type": "cisco_ios",
        "secret": "",
        "status": "offline",
        "note": "HOME SERVER"
    },
    {
        "name": "CISCO-SW2",
        "vendor": "cisco",
        "host": "10.10.79.3",
        "username": "admin",
        "password": "Admin@123",
        "port": 22,
        "device_type": "cisco_ios",
        "secret": "",
        "status": "offline",
        "note": "HOME SERVER"
    },
]

db = {d["name"]: d for d in devices}
with open("devices.json", "w") as f:
    json.dump(db, f, indent=2)
print(f"OK! Saved {len(db)} devices to devices.json")
