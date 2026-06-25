@echo off
echo Checking for Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Installing Python...
    powershell -Command "Start-Process 'https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe' -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait"
)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python installation failed. Please install Python manually and rerun this script.
    pause
    exit /b 1
) else (
    echo Python installation successful.
)

echo Installing required packages...
python -m pip install --upgrade pip
python -m pip install requests keyboard psutil

echo Installation complete.
pause
