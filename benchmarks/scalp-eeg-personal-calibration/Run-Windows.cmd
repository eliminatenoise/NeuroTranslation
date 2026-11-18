@echo off
setlocal
if defined PYTHON (
    if "%~1"=="" (
        "%PYTHON%" "%~dp0run.py" --help
    ) else (
        "%PYTHON%" "%~dp0run.py" %*
    )
) else (
    if "%~1"=="" (
        python "%~dp0run.py" --help
    ) else (
        python "%~dp0run.py" %*
    )
)
exit /b %ERRORLEVEL%
