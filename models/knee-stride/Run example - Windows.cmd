@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    python predict.py example.json
) else (
    py -3 predict.py example.json
)
set "result=%ERRORLEVEL%"
pause
exit /b %result%
