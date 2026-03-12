@echo off
echo.
echo  ========================================
echo   PlNetwork Auto Manager — Backend
echo  ========================================
echo.

cd /d %~dp0

echo [1/3] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://python.org
    pause & exit /b 1
)

echo.
echo [2/3] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: pip install failed
    pause & exit /b 1
)

echo.
echo [3/3] Starting FastAPI server...
echo.
echo  API:      http://localhost:8000
echo  Docs:     http://localhost:8000/docs
echo  Health:   http://localhost:8000/health
echo.
echo  Press Ctrl+C to stop
echo.

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
