# PlNetwork Auto Manager v3.0 — Hướng dẫn chạy

## Cấu trúc thư mục
```
PlnetWork_Automation\
├── backend\
│   ├── main.py          ← FastAPI backend
│   ├── start.bat        ← Chạy backend
│   ├── requirements.txt
│   └── devices.json     ← Tự tạo khi chạy lần đầu
├── netauto-ui\
│   └── src\
│       └── App.jsx      ← React frontend
├── fix_main.py          ← Fix f-string nếu cần
└── START_GUIDE.md
```

## Bước 1 — Cài Node.js & npm (nếu chưa có)
https://nodejs.org → Download LTS

## Bước 2 — Setup Frontend (chỉ làm 1 lần)
```cmd
cd D:\PlnetWork_Automation\PlnetWork_Automation\netauto-ui
npm install
```

## Bước 3 — Chạy Backend (Terminal 1)
```cmd
cd D:\PlnetWork_Automation\PlnetWork_Automation\backend
start.bat
```

## Bước 4 — Chạy Frontend (Terminal 2)
```cmd
cd D:\PlnetWork_Automation\PlnetWork_Automation\netauto-ui
npm run dev
```

## Mở trình duyệt
http://localhost:5173

---

## Update file sau khi tải về
```cmd
copy /Y "%USERPROFILE%\Downloads\App.jsx" "D:\PlnetWork_Automation\PlnetWork_Automation\netauto-ui\src\App.jsx"
copy /Y "%USERPROFILE%\Downloads\main.py" "D:\PlnetWork_Automation\PlnetWork_Automation\backend\main.py"
taskkill /F /IM python.exe
netstat -ano | findstr :8000
:: Kill any remaining PID, then:
cd D:\PlnetWork_Automation\PlnetWork_Automation\backend
start.bat
```

## Thông tin thiết bị thực
- MikroTik CTHO: IP 14.176.141.36, API port 3543
- Console Cisco: COM6, 9600 baud

## Features
- Dashboard — tổng quan thiết bị
- Devices — quản lý thiết bị MikroTik/Cisco/Fortinet/Sophos  
- Terminal — SSH/Telnet terminal
- Net Tools — Ping, Traceroute
- Config Push — đẩy config hàng loạt
- Backup & Rollback — backup config
- Config Scanner — quét config
- Services — bật/tắt services MikroTik
- Console RS232 — serial console USB
- Telegram Bot — bot quản lý qua Telegram
- Settings — cài đặt

