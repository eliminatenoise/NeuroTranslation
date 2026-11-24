@echo off
setlocal
cd /d "%~dp0" || exit /b 1
where py >nul 2>&1
if errorlevel 1 goto use_python
py -3 forecast.py %*
set "status=%errorlevel%"
goto done
:use_python
where python >nul 2>&1
if errorlevel 1 goto install_python
python forecast.py %*
set "status=%errorlevel%"
goto done
:install_python
echo Install Python 3 with NumPy, then open this launcher again.
pause
exit /b 1
:done
pause
exit /b %status%
