@echo off
py -3 "%~dp0transfer_predict.py" %*
exit /b %ERRORLEVEL%
