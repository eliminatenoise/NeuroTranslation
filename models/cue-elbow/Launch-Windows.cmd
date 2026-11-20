@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto plain
py -3 -B infer.py %*
goto done
:plain
python -B infer.py %*
:done
set "run_status=%errorlevel%"
if "%~1"=="" pause
exit /b %run_status%
