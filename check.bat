@echo off
rem ============================================================
rem  pojia-workbuddy-win - post-install verification
rem  Run AFTER fully quitting and restarting WorkBuddy and
rem  sending one message in a chat.
rem  Exit code 0 = payload is really inside the request.
rem ============================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title pojia - check

call "%~dp0_find_py.bat"
if not defined PY goto :no_python

echo.
echo ==== inspect: is the payload in the request? ====
%PY% "%~dp0pojia.py" inspect %*
set "RC=%ERRORLEVEL%"
echo.
echo ==== verify: do the files still match the seal? ====
%PY% "%~dp0pojia.py" verify
echo.
if "%RC%"=="0" echo [OK] Installed and effective.
if "%RC%"=="1" echo [WAIT] No request captured yet - start WorkBuddy and send a message first.
if "%RC%"=="2" echo [MIXED] The trace spans before/after the change - restart WorkBuddy and try again.
if "%RC%"=="3" echo [FAIL] Still the stock policy - read DETAILS.md section 1.3.
pause
exit /b %RC%

:no_python
echo.
echo [!] Python 3.9+ not found.
echo       winget install -e --id Python.Python.3.12
echo.
pause
exit /b 4
