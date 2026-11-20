@echo off
setlocal
set "request=%~f1"
if not defined request set "request=%~dp0example.json"
where py >nul 2>nul
if errorlevel 1 goto python
py -3 "%~dp0forward.py" "%request%"
goto done
:python
python "%~dp0forward.py" "%request%"
:done
set "forecast_result=%errorlevel%"
pause
exit /b %forecast_result%
