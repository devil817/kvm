@echo off
echo Installing dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Error: Python or Pip not found or installation failed.
    echo Please ensure Python 3.8+ is installed and 'python' is in your PATH.
    pause
    exit /b
)

echo.
echo Starting KVM Switcher...
python main.py
if %errorlevel% neq 0 (
    echo.
    echo Application crashed. See above for errors.
    pause
)
