@echo off
cd /d "%~dp0"
start "" http://127.0.0.1:8000
"D:\工作区\软件\Python312\python.exe" -m src.web.app
pause
