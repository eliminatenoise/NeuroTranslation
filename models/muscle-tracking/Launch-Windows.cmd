@echo off
setlocal
set "request=%~f1"
if not defined request set "request=%~dp0example.json"
where py >nul 2>nul
if errorlevel 1 goto python
py -3 -B "%~dp0forecast.py" "%request%"
goto done
:python
python -B "%~dp0forecast.py" "%request%"
:done
set "forecast_status=%errorlevel%"
if not defined CI pause
exit /b %forecast_status%
