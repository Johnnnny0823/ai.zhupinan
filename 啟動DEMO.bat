@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo 請先依 demo\DEVELOPMENT.md 建立 Python 3.12 虛擬環境。
  pause
  exit /b 1
)
if not exist "demo\.env" (
  echo 請先複製 demo\.env.example 為 demo\.env 並設定登入碼。
  pause
  exit /b 1
)
echo 竹聘安合成示範： http://127.0.0.1:8765
.venv\Scripts\python.exe -m demo.run serve
pause
