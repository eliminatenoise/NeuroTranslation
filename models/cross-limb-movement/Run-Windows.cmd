@echo off
if "%~1"=="" (
  start "" "%~dp0forecast.html"
) else (
  node "%~dp0launch.mjs" %*
)
