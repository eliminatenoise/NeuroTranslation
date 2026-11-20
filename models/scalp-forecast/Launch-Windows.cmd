@echo off
setlocal
set "request=%~f1"
pushd "%~dp0" || exit /b 1
if not defined request set "request=example.json"
where node >nul 2>nul
if errorlevel 1 goto :pystart
node run-example.cjs "%request%"
goto :done
:pystart
where py >nul 2>nul
if errorlevel 1 goto :python
py -3 predict.py "%request%"
goto :done
:python
python predict.py "%request%"
:done
set "exit_code=%errorlevel%"
pause
popd
exit /b %exit_code%
