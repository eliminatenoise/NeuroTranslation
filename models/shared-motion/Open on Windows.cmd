@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python shared-motion-model\run_examples.py
) else (
  py -3 shared-motion-model\run_examples.py
)
set result=%errorlevel%
pause
exit /b %result%
