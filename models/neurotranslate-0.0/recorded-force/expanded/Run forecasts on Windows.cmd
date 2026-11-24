@echo off
setlocal
set "package_python=%~dp0.venv\Scripts\python.exe"
if exist "%package_python%" goto local
where python >nul 2>nul
if not errorlevel 1 goto system_python
where py >nul 2>nul
if not errorlevel 1 goto system_py
echo Install Python 3 and set up the local environment. See README.md.
exit /b 1
:local
"%package_python%" "%~dp0predict.py" %*
goto report
:system_python
python "%~dp0predict.py" %*
goto report
:system_py
py -3 "%~dp0predict.py" %*
:report
set "status=%errorlevel%"
if not "%~1"=="" exit /b %status%
if not "%status%"=="0" echo Check the Python and NumPy setup in README.md.
pause
exit /b %status%
