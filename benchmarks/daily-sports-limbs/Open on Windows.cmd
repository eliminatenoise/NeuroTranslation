@echo off
cd /d "%~dp0"
python -B serve.py
if errorlevel 1 pause
