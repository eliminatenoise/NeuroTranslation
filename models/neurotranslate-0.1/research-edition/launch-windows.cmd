@echo off
setlocal
if exist "%~dp0.venv\Scripts\python.exe" goto local_python
py -3.13 "%~dp0launch.py" %*
exit /b %ERRORLEVEL%
:local_python
"%~dp0.venv\Scripts\python.exe" "%~dp0launch.py" %*
exit /b %ERRORLEVEL%
