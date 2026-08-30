@echo off
setlocal
cd /d "D:/工作区/新闻智能体"

"D:/工作区/软件/Python312/python.exe" -m src.scheduler.run > "D:/工作区/新闻智能体/logs/run_daily.log" 2>&1
exit /b %ERRORLEVEL%
