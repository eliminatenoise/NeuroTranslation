@echo off
where py >nul 2>&1
if errorlevel 1 goto python
py -3 "%~dp0forecast.py" %*
exit /b %ERRORLEVEL%
:python
python "%~dp0forecast.py" %*
exit /b %ERRORLEVEL%
