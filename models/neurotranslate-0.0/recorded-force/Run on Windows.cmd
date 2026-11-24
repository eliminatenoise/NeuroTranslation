@echo off
setlocal
cd /d "%~dp0"
if defined PYTHON (
  "%PYTHON%" -B forecast.py %*
) else (
  py -3 -B forecast.py %*
)
set "RESULT=%errorlevel%"
if "%~1"=="" pause
exit /b %RESULT%
