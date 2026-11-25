@echo off
cd /d "%~dp0"
py -3 -B apply_readouts.py %*
if errorlevel 1 exit /b %errorlevel%
