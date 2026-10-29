@echo off
rem ============================================================
rem  pojia-workbuddy-win - environment self-check
rem  Run this first when install.bat fails; send the output when
rem  asking for help.
rem ============================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title pojia - doctor

call "%~dp0_find_py.bat"
if not defined PY goto :no_python

echo.
%PY% "%~dp0pojia.py" doctor %*
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%

:no_python
echo.
echo [!] Python 3.9+ not found.
echo       winget install -e --id Python.Python.3.12
echo.
pause
exit /b 4
