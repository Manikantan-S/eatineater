@echo off
echo 🍽️  Starting Semantic Food Recipe Finder...

REM Navigate to the project directory
cd /d "%~dp0"

REM Kill any existing processes on common ports
echo 🧹 Cleaning up any existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8002') do taskkill /f /pid %%a >nul 2>&1

REM Start the application
echo 🚀 Starting the application...
python run.py
