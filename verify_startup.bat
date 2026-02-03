@echo off
echo Killing existing KVM Switcher instances...
taskkill /F /IM "KVM Switcher.exe" 2>nul
taskkill /F /IM "python.exe" 2>nul

echo Starting KVM Switcher from dist folder...
start "" "dist\KVM Switcher.exe"

echo Waiting for app to launch...
timeout /t 5

echo Checking Registry for Run at Startup key...
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "KVMInputSwitcher"

echo.
echo If you see the key above pointing to "dist\KVM Switcher.exe", it works!
echo Please right-click the Tray Icon -> 'Run at Startup' to toggle and re-verify if needed.
pause
