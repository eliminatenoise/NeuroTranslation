@echo off
node "%~dp0forecast.cjs" %*
if not defined CI if "%~1"=="" pause
