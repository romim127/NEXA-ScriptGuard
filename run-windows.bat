@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0" || exit /b 1

set "NEXA_PYTHON=%CD%\.venv\Scripts\python.exe"
if exist "%NEXA_PYTHON%" goto launch
if not defined VIRTUAL_ENV goto missing_venv
set "NEXA_PYTHON=%VIRTUAL_ENV%\Scripts\python.exe"
if not exist "%NEXA_PYTHON%" goto missing_venv

:launch
"%NEXA_PYTHON%" -m nexa_scriptguard.gui %*
set "NEXA_EXIT=%ERRORLEVEL%"
popd
exit /b %NEXA_EXIT%

:missing_venv
>&2 echo NEXA ScriptGuard: create .venv or activate a Windows virtual environment.
>&2 echo From the project root: python -m venv .venv
>&2 echo Then run: .venv\Scripts\python.exe -m pip install .
popd
exit /b 1
