@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 predict.py %*
goto finish
:usepython
python predict.py %*
:finish
set result=%ERRORLEVEL%
if "%~1"=="" pause
exit /b %result%
