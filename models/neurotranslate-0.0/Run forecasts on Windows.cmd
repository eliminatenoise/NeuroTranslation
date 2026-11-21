@echo off
setlocal
where python >nul 2>nul
if errorlevel 1 (
    set "python_command=py -3"
) else (
    set "python_command=python"
)
if not "%~1"=="" goto custom
echo first_use_body
%python_command% "%~dp0predict.py" "%~dp0first_use_body\example.json"
if errorlevel 1 goto failed
echo next_neuron_prediction
%python_command% "%~dp0predict.py" "%~dp0next_neuron_prediction\example.json"
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo Python 3 and NumPy are required. See README.md for instructions.
pause
exit /b 1
:custom
%python_command% "%~dp0predict.py" %*
exit /b %errorlevel%
