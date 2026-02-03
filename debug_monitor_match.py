import ctypes
from ctypes import wintypes
import sys

# Constants
DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 0x00000001
CCHDEVICENAME = 32

# Structs
class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * CCHDEVICENAME)
    ]

class DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]

# WinAPI functions
user32 = ctypes.windll.user32
MonitorEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

def get_monitor_device_ids():
    """
    Returns a list of Device IDs (e.g., 'DISPLAY\\MNT2700\\...') in the order of EnumDisplayMonitors.
    This order matches monitorcontrol's get_monitors().
    """
    monitor_ids = []
    
    def callback(hmonitor, hdc, lprect, lparam):
        info = MONITORINFOEX()
        info.cbSize = ctypes.sizeof(MONITORINFOEX)
        
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            adapter_name = info.szDevice
            # print(f"Found Adapter: {adapter_name}")
            
            # Now identify the monitor connected to this adapter
            # We need to EnumDisplayDevices on this adapter name
            
            # 1. Get Adapter Info (to verify/debugging)
            # adapter_dev = DISPLAY_DEVICE()
            # adapter_dev.cb = ctypes.sizeof(DISPLAY_DEVICE)
            # user32.EnumDisplayDevicesW(adapter_name, 0, ctypes.byref(adapter_dev), 0)
            
            # 2. Get Monitor Info attached to this adapter
            # Monitor is usually index 0 on the adapter for the active display?? 
            # Not necessarily, but for EnumDisplayMonitors, hmonitor represents a specific active rect.
            # Usually EnumDisplayDevices(adapter, 0) gives the monitor.
            
            mon_dev = DISPLAY_DEVICE()
            mon_dev.cb = ctypes.sizeof(DISPLAY_DEVICE)
            
            # Note: EnumDisplayDevicesW with adapter name and index 0 usually returns the attached monitor
            if user32.EnumDisplayDevicesW(adapter_name, 0, ctypes.byref(mon_dev), 0):
                 dev_id = mon_dev.DeviceID
                 # print(f"  -> Monitor DeviceID: {dev_id}")
                 monitor_ids.append(dev_id)
            else:
                monitor_ids.append("Unknown")
        else:
            monitor_ids.append("Unknown")
            
        return True

    user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), 0)
    return monitor_ids

if __name__ == "__main__":
    print("EnumDisplayMonitors Order & IDs:")
    ids = get_monitor_device_ids()
    for i, mid in enumerate(ids):
        print(f"Index {i}: {mid}")
