@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    python predict.py %*
) else (
    py -3 predict.py %*
)
set "forecast_status=%errorlevel%"
pause
exit /b %forecast_status%
