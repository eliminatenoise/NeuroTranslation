@echo off
setlocal
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3.9 or later is needed to run aligned_walk.py. 1>&2
exit /b 1

:use_py
py -3 -B "%~dp0aligned_walk.py" %*
exit /b %errorlevel%

:use_python
python -B "%~dp0aligned_walk.py" %*
exit /b %errorlevel%
