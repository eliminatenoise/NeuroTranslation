@echo off
setlocal
set "page=%~dp0index.html"
if not exist "%page%" set "page=%~dp0..\..\docs\neural-and-muscle-composites\index.html"
start "" "%page%"
