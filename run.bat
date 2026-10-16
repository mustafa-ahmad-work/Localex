@echo off
chcp 65001 >nul
title Offline Windows Translator Runner

set "PYTHON_EXE=C:\Users\mosta\AppData\Local\Programs\Python\Python311\python.exe"

if not exist "%PYTHON_EXE%" (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_EXE=python"
    ) else (
        echo [ERROR] Python not found. Please install Python 3.11.
        pause
        exit /b 1
    )
)

set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
cd /d "%~dp0"

echo ========================================================
echo  Launching Offline Windows Translator...
echo ========================================================

"%PYTHON_EXE%" -m Localex %*

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%.
    pause
)
