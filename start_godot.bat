@echo off
setlocal EnableExtensions
title Campus Shield Godot Launcher

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

where godot >nul 2>&1
if not errorlevel 1 (
    echo Launching Campus Shield Godot rebuild...
    godot --path "%SCRIPT_DIR%godot" %*
    exit /b %errorlevel%
)

where Godot_v4.6.2-stable_win64.exe >nul 2>&1
if not errorlevel 1 (
    echo Launching Campus Shield Godot rebuild...
    Godot_v4.6.2-stable_win64.exe --path "%SCRIPT_DIR%godot" %*
    exit /b %errorlevel%
)

echo Godot was not found on PATH.
echo Install Godot 4.6.2, then either add it to PATH or launch the godot folder from the Godot editor.
pause
exit /b 1
