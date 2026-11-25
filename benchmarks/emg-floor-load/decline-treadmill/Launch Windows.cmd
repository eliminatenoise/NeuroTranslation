@echo off
py -3 "%~dp0predict.py" %*
exit /b %ERRORLEVEL%
