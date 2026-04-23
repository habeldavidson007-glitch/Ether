@echo off
REM ============================================================================
REM activate_ether.bat - Ether AI Assistant One-Click Launcher
REM ============================================================================
REM Prerequisites: Python 3.9+, Ollama installed and in PATH
REM RAM Optimized: Designed for systems with 2GB+ RAM
REM ============================================================================

setlocal EnableDelayedExpansion

REM Colors for output
set "COLOR_RESET="
set "COLOR_GREEN=[OK]"
set "COLOR_YELLOW=[WAIT]"
set "COLOR_RED=[ERROR]"
set "COLOR_BLUE=[INFO]"
set "COLOR_CYAN=[STEP]"

echo.
echo ============================================================================
echo                    ETHER AI ASSISTANT - ACTIVATION
echo ============================================================================
echo.

REM -----------------------------------------------------------------------------
REM Step 1: Check Python Installation
REM -----------------------------------------------------------------------------
echo %COLOR_CYAN% Checking Python installation...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo %COLOR_RED% Python is not installed or not in PATH!
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)
echo %COLOR_GREEN% Python found: 
python --version
echo.

REM -----------------------------------------------------------------------------
REM Step 2: Check Ollama Installation
REM -----------------------------------------------------------------------------
echo %COLOR_CYAN% Checking Ollama installation...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo %COLOR_RED% Ollama is not installed or not in PATH!
    echo Please install Ollama from https://ollama.ai
    pause
    exit /b 1
)
echo %COLOR_GREEN% Ollama found
echo.

REM -----------------------------------------------------------------------------
REM Step 3: Install Dependencies (scikit-learn)
REM -----------------------------------------------------------------------------
echo %COLOR_CYAN% Installing required dependencies...
echo %COLOR_YELLOW% Installing scikit-learn (this may take a moment)...
pip install scikit-learn --user --quiet 2>nul
if %errorlevel% neq 0 (
    echo %COLOR_RED% Failed to install scikit-learn, continuing with fallback mode...
) else (
    echo %COLOR_GREEN% Dependencies installed successfully
)
echo.

REM -----------------------------------------------------------------------------
REM Step 4: Check and Pull Required Model
REM -----------------------------------------------------------------------------
echo %COLOR_CYAN% Checking for required model (qwen2.5-coder:1.5b)...
ollama list | findstr /i "qwen2.5-coder" >nul 2>&1
if %errorlevel% neq 0 (
    echo %COLOR_YELLOW% Model not found. Pulling qwen2.5-coder:1.5b...
    echo This may take several minutes depending on your connection...
    ollama pull qwen2.5-coder:1.5b
    if %errorlevel% neq 0 (
        echo %COLOR_RED% Failed to pull model. The system will run in limited mode.
    ) else (
        echo %COLOR_GREEN% Model downloaded successfully
    )
) else (
    echo %COLOR_GREEN% Model already available
)
echo.

REM -----------------------------------------------------------------------------
REM Step 5: Create Logs Directory
REM -----------------------------------------------------------------------------
echo %COLOR_CYAN% Setting up logging directory...
if not exist "logs" mkdir logs
echo %COLOR_GREEN% Logs directory ready
echo.

REM -----------------------------------------------------------------------------
REM Step 6: Start Background Daemon
REM -----------------------------------------------------------------------------
echo %COLOR_CYAN% Starting Ether background daemon...
start /b python ether/services/daemon_launcher.py
echo %COLOR_GREEN% Daemon started in background
echo.

REM -----------------------------------------------------------------------------
REM Step 7: Wait for Daemon Initialization
REM -----------------------------------------------------------------------------
echo %COLOR_YELLOW% Waiting for daemon to initialize (2 seconds)...
timeout /t 2 /nobreak >nul
echo %COLOR_GREEN% Daemon ready
echo.

REM -----------------------------------------------------------------------------
REM Step 8: Launch CLI Interface
REM -----------------------------------------------------------------------------
echo %COLOR_GREEN% Launching Ether CLI interface...
echo.
echo ============================================================================
echo                    ETHER IS NOW ACTIVE
echo ============================================================================
echo.
echo Commands:
echo   - Type your question or request
echo   - Use 'exit' or 'quit' to close
echo   - Use 'help' for available commands
echo.
echo ============================================================================
echo.

python ether_cli.py

REM Cleanup on exit
echo.
echo %COLOR_YELLOW% Ether CLI closed. Daemon will continue running in background.
echo To stop the daemon completely, close this terminal window.
pause
