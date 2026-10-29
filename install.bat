@echo off
rem ============================================================
rem  pojia-workbuddy-win - one-click installer
rem  Just double-click.  It detects where WorkBuddy is installed,
rem  remembers the path, closes a running WorkBuddy, previews the
rem  changes and writes them.  No prompts, no env vars.
rem
rem  Optional args:  install.bat --dry-run     (check only)
rem                  install.bat --force       (rebuild seal)
rem ============================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title pojia - install

call "%~dp0_find_py.bat"
if not defined PY goto :no_python

echo.
%PY% "%~dp0pojia.py" setup --yes --close %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" goto :done
if "%RC%"=="2" echo [!] Environment check failed - run doctor.bat and send the output.
if "%RC%"=="3" echo [!] Already patched here but seal.json is missing - see README "exit code 3".
if "%RC%"=="4" echo [!] Permission or Python version problem - see the lines above.
if "%RC%"=="5" echo [!] WorkBuddy is still running - quit it completely, then run install.bat again.
echo.
echo Installer stopped with code %RC%.
pause
exit /b %RC%

:done
echo.
echo Next: 1^) start WorkBuddy   2^) open any chat and send a message   3^) run check.bat
pause
exit /b 0

:no_python
echo.
echo [!] Python 3.9+ not found.
echo     Install it, then close this window and run install.bat again:
echo       winget install -e --id Python.Python.3.12
echo       or https://www.python.org/downloads/windows/  ^(tick "Add python.exe to PATH"^)
echo.
pause
exit /b 4
