# KVM Input Source Switcher

This application allows you to switch monitor inputs via the System Tray.

## Prerequisites
1. **Python 3.8+**: Must be installed and added to your PATH.
   - Check by running `python --version` in a terminal.
2. **DDC/CI Enabled**: Ensure DDC/CI is enabled in your monitor's OSD menu.

## How to Run
1. Double-click `run_kvm.bat` in this folder.
   - This will automatically install dependencies (`monitorcontrol`, `pystray`, `pillow`) and start the app.
2. A monitor icon will appear in your system tray.
   - Right-click to see detected monitors and switch inputs.

## Troubleshooting
- If no monitors appear: Ensure your monitor supports DDC/CI and is connected via HDMI/DP/USB-C (not just USB data).
- If "Python not found": Reinstall Python and check "Add to PATH".
