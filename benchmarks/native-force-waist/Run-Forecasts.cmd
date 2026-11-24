@echo off
cd /d "%~dp0" || exit /b 1
where py >nul 2>nul
if not errorlevel 1 (
    py -3 run_forecast.py %*
) else (
    python run_forecast.py %*
)
exit /b %ERRORLEVEL%
