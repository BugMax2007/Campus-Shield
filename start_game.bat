@echo off
setlocal EnableExtensions
title Campus Safe Launcher

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo === Campus Safe Windows Launcher ===
echo Project: %SCRIPT_DIR%
echo.

call :find_python
if errorlevel 1 goto :fatal

call :check_python_version
if errorlevel 1 goto :fatal

"%PYTHON_EXE%" %PYTHON_FLAGS% -c "import pygame, pytmx" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    "%PYTHON_EXE%" %PYTHON_FLAGS% -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if errorlevel 1 goto :fatal
)

if defined PYTHONPATH (
    set "PYTHONPATH=%SCRIPT_DIR%src;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%SCRIPT_DIR%src"
)

echo Launching Campus Safe...
"%PYTHON_EXE%" %PYTHON_FLAGS% -m campus_safe_game.main %*
set "EXIT_CODE=%errorlevel%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Game exited with code %EXIT_CODE%.
    echo Run this file from Command Prompt to read the full error message if the window closes too fast.
    pause
)
exit /b %EXIT_CODE%

:find_python
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_FLAGS=-3"
    exit /b 0
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    set "PYTHON_FLAGS="
    exit /b 0
)

echo Python 3 is required. Install Python and try again.
exit /b 1

:check_python_version
"%PYTHON_EXE%" %PYTHON_FLAGS% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo Python 3.10 or newer is required.
    exit /b 1
)
exit /b 0

:fatal
echo.
echo Launcher setup failed.
echo 1. Install Python 3.10 or newer from python.org and enable Add Python to PATH.
echo 2. Open Command Prompt in this folder.
echo 3. Run start_game.bat again.
echo.
pause
exit /b 1
