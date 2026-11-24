@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
    py -3 -B predict.py common-six
    pause
) else (
    py -3 -B predict.py %*
)
