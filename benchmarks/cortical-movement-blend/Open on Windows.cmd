@echo off
cd /d "%~dp0"
py -3.12 predict.py %*
exit /b %ERRORLEVEL%
