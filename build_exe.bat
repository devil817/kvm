@echo off
echo Installing PyInstaller...
python -m pip install pyinstaller

echo Cleaning up previous builds...
rmdir /s /q build
rmdir /s /q dist
del *.spec

echo Building KVM Switcher...
python -m PyInstaller --noconfirm --log-level=WARN --onefile --windowed --name "KVM Switcher" ^
    --add-data "src;src" ^
    --hidden-import "pynput.keyboard._win32" ^
    --hidden-import "pynput.mouse._win32" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "monitorcontrol" ^
    main.py

echo Build complete!
echo The executable is located in the 'dist' folder.

