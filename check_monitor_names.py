import ctypes
from ctypes import wintypes

# Define necessary structures and constants
class DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]

def get_monitor_names():
    User32 = ctypes.windll.User32
    
    # iterate over display adapters
    device_idx = 0
    while True:
        device = DISPLAY_DEVICE()
        device.cb = ctypes.sizeof(device)
        
        # Enum display adapters (graphics cards / outputs)
        if not User32.EnumDisplayDevicesW(None, device_idx, ctypes.byref(device), 0):
            break
            
        print(f"\nAdapter {device_idx}: {device.DeviceString} ({device.DeviceName})")
        
        # If attached to desktop
        if device.StateFlags & 1: # DISPLAY_DEVICE_ATTACHED_TO_DESKTOP
            # Enumerate monitors on this adapter
            mon_idx = 0
            while True:
                monitor = DISPLAY_DEVICE()
                monitor.cb = ctypes.sizeof(monitor)
                if not User32.EnumDisplayDevicesW(device.DeviceName, mon_idx, ctypes.byref(monitor), 0):
                    break
                    
                print(f"  - Monitor {mon_idx}: {monitor.DeviceString} (ID: {monitor.DeviceID})")
                mon_idx += 1
                
        device_idx += 1

if __name__ == "__main__":
    try:
        get_monitor_names()
    except Exception as e:
        print(f"Error: {e}")
