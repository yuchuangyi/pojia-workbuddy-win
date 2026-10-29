@echo off
rem ============================================================
rem  Locate a Python 3.9+ interpreter and export it as %PY%.
rem  Called by the other .bat files:  call "%~dp0_find_py.bat"
rem  Order: py launcher -> PATH -> portable .\python -> per-user installs
rem  NOTE: no setlocal here on purpose - %PY% must leak to caller.
rem ============================================================
set "PY="
call :trypy py -3
if not defined PY call :trypy python
if not defined PY call :trypy python3
if not defined PY call :trylocal "%~dp0python\python.exe"
if not defined PY for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :trylocal "%%~D\python.exe"
exit /b 0

:trypy
%* -c "import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=%*"
exit /b 0

:trylocal
if exist %1 call :trypy %1
exit /b 0
