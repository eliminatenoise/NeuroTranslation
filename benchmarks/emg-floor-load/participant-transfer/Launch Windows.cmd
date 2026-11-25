@echo off
pushd "%~dp0" || exit /b 1
if defined NEUROTRANSLATE_PYTHON (
  "%NEUROTRANSLATE_PYTHON%" -B predict.py EXAMPLE.npz
) else (
  py -3 -B predict.py EXAMPLE.npz
)
set "result=%errorlevel%"
popd
if not "%NEUROTRANSLATE_NO_PAUSE%"=="1" pause
exit /b %result%
