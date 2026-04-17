@echo off
REM Ether v1.6 - Quick Setup Script for 4GB RAM Systems
REM ====================================================
REM This script pulls the ultra-lightweight qwen2.5:0.5b model
REM and verifies Ollama is running.

echo.
echo ======================================
echo   ETHER v1.6 - Quick Setup
echo   Optimized for 4GB RAM Systems
echo ======================================
echo.

REM Check if Ollama is installed
where ollama >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ollama is not installed!
    echo Please install Ollama from: https://ollama.ai
    echo.
    pause
    exit /b 1
)

echo [OK] Ollama is installed
echo.

REM Check if Ollama service is running
echo Checking if Ollama service is running...
curl -s http://localhost:11434/api/tags >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Ollama service is not running!
    echo Starting Ollama in background...
    start "" ollama serve
    timeout /t 3 /nobreak >nul
    echo Please keep the Ollama window open.
    echo.
) else (
    echo [OK] Ollama service is running
    echo.
)

REM Pull the lightweight model
echo Pulling ultra-lightweight model: qwen2.5:0.5b-instruct-q4_K_M
echo This will download ~500MB and take 2-5 minutes depending on your connection.
echo.

ollama pull qwen2.5:0.5b-instruct-q4_K_M

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to pull model!
    echo Please check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================
echo   Setup Complete!
echo ======================================
echo.
echo Next steps:
echo   1. Make sure Ollama is running: ollama serve
echo   2. Run Ether CLI: python ether_cli.py
echo   3. Load your Godot project: /load C:\path\to\your\game
echo.
echo The model uses only ~500MB RAM, perfect for your 4GB system!
echo.
pause
