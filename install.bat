@echo off
chcp 65001 > nul
echo ========================================
echo Installing the required libraries
echo Installing Required Libraries
echo ========================================
echo.

echo Checking Python...
echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ❌ Python is not installed! Please install Python first.
    echo ❌ Python is not installed! Please install Python first
    pause
    exit /b 1
)
echo.

echo Installing libraries...
echo Installing libraries...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ❌ n error occurred during installation
    echo ❌ An error occurred during installation
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ All libraries installed successfully!
echo ✅ All libraries installed successfully!
echo ========================================
echo.
echo Next steps:
echo Next steps:
echo 1. Copy .env.example to .env
echo    Copy .env.example to .env
echo 2. Edit .env with your credentials
echo    Edit .env with your credentials
echo 3. Run the program using run.bat
echo    Run the program using run.bat
echo.
pause
