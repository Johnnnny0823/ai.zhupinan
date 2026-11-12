@echo off
echo ==========================================
echo   竹聘安 AI DEMO 啟動中...
echo   啟動後請用瀏覽器開啟 http://localhost:8765
echo   要關閉請按 Ctrl+C
echo ==========================================
echo.
start "" http://localhost:8765
python -m uvicorn app:app --app-dir "%~dp0demo\server" --host 127.0.0.1 --port 8765
pause
