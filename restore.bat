@echo off
rem ============================================================
rem  pojia-workbuddy-win - restore factory prompt files
rem  Restores every target from backup/ recorded in seal.json.
rem  Then quit and restart WorkBuddy.
rem  Add --force to overwrite files that changed after patching.
rem ============================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title pojia - restore

call "%~dp0_find_py.bat"
if not defined PY goto :no_python

echo.
%PY% "%~dp0pojia.py" restore %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" echo Remember: quit WorkBuddy completely and start it again.
pause
exit /b %RC%

:no_python
echo.
echo [!] Python 3.9+ not found.
echo       winget install -e --id Python.Python.3.12
echo.
pause
exit /b 4
