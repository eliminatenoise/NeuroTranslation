@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3 is needed. Install it or run paired_plates.py with your Python interpreter. 1>&2
exit /b 1

:use_py
py -3 -B paired_plates.py %*
exit /b %errorlevel%

:use_python
python -B paired_plates.py %*
exit /b %errorlevel%
