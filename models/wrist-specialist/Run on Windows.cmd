@echo off
setlocal
pushd "%~dp0" || exit /b 1
where py >nul 2>nul
if errorlevel 1 (
  python specialist.py invented-window.json
) else (
  py -3 specialist.py invented-window.json
)
set "result=%errorlevel%"
popd
pause
exit /b %result%
