@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto python
py -3 -c "import numpy" >nul 2>nul
if errorlevel 1 goto python
py -3 predict.py
goto finished
:python
where python >nul 2>nul
if errorlevel 1 goto missing
python -c "import numpy" >nul 2>nul
if errorlevel 1 goto missing
python predict.py
goto finished
:missing
echo This model needs Python 3 with NumPy. See REPRODUCE.md.
pause
exit /b 1
:finished
set "forecast_result=%errorlevel%"
pause
exit /b %forecast_result%
