@echo off
setlocal
cd /d "%~dp0"
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
where py >nul 2>nul
if errorlevel 1 (set "interp=python") else (set "interp=py -3")
%interp% -c "import numpy" >nul 2>nul
if errorlevel 1 goto missing
%interp% joint_demo.py %*
if errorlevel 1 goto failed
exit /b 0
:missing
echo This demo needs Python 3.10 or later and NumPy. See README.md for setup.
:failed
pause
exit /b 1
