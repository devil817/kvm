import re
import logging
import time
import threading
from typing import List, Dict, Optional, Tuple
from monitorcontrol import get_monitors, Monitor

logger = logging.getLogger(__name__)

# Standard VCP Code 0x60 Input Source Values
# Based on VESA Monitor Control Command Set (MCCS)
INPUT_SOURCES = {
    0x01: "Analog Video (VGA)",
    0x02: "Analog Video (BNC)",
    0x03: "Digital Video (DVI)",
    0x04: "Analog Video (Composite)",
    0x0F: "DisplayPort",
    0x10: "DisplayPort", # Sometimes used
    0x11: "HDMI-1",
    0x12: "HDMI-2",
    0x13: "HDMI-3",  # Reserved/Generic
    0x14: "HDMI-4",
    0x15: "USB-C",   # Often mapped here
    0x16: "USB-C",   # Or here
    0x1B: "USB-C",   # Common for USB-C
}

# Ctypes definitions for monitor matching
import ctypes
from ctypes import wintypes

class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32)
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

user32 = ctypes.windll.user32
MonitorEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

class MonitorManager:
    _LOCK = threading.Lock()

    @staticmethod
    def get_wmi_monitor_info() -> List[Dict]:
        """
        Uses PowerShell/WMI to get friendly monitor names and connection type.
        Returns a list of dicts with 'Manufacturer', 'Model', 'InstanceName', 'IsInternal'.
        """
        import subprocess
        import json
        
        info_list = []
        # We need both ID (for name) and ConnectionParams (for type) joined by InstanceName
        # Simplified PowerShell command
        # Pipeline-based command with array reinforcement
        cmd = """
        $Monitors = Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorID
        $Params = Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorConnectionParams
        
        $Result = $Monitors | ForEach-Object {
            $curr = $_
            $param = $Params | Where-Object { $_.InstanceName -eq $curr.InstanceName }
            
            if ($curr.ManufacturerName) {
                $Manuf = [System.Text.Encoding]::ASCII.GetString($curr.ManufacturerName).Trim([char]0)
            } else { $Manuf = "Unknown" }
            
            if ($curr.UserFriendlyName) {
                $Model = [System.Text.Encoding]::ASCII.GetString($curr.UserFriendlyName).Trim([char]0)
            } else { $Model = "Generic" }
            
            # 2147483648 (Internal), 11 (eDP), 7 (LVDS)
            $IsInternal = ($param.VideoOutputTechnology -eq 2147483648 -or $param.VideoOutputTechnology -eq 11 -or $param.VideoOutputTechnology -eq 7)
            
            [PSCustomObject]@{
                Manufacturer = $Manuf
                Model = $Model
                InstanceName = $curr.InstanceName
                IsInternal = $IsInternal
            }
        }
        
        # Force array output
        if ($Result) { 
            if ($Result -is [PSCustomObject]) { $Result = @($Result) }
        } else {
             $Result = @() 
        }
        $Result | ConvertTo-Json -Compress
        """
        try:
            # First clean up any previous failures
            info_list = []
            
            result = subprocess.check_output(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                text=True,
                creationflags=0x08000000
            ).strip()
            
            if not result:
                return []
                
            # If result is just brackets/braces from simple output, parsing is easy
            try:
                info_list = json.loads(result)
            except json.JSONDecodeError:
                # If simple parse fails, try regex extraction
                match = re.search(r'(\[.*\]|\{.*\})', result, re.DOTALL)
                if match:
                    info_list = json.loads(match.group(0))
                else:
                    logger.warning(f"Could not parse WMI JSON: {result[:50]}...")
                     
            if isinstance(info_list, dict):
                info_list = [info_list]
                
        except Exception as e:
            # Downgrade to warning/debug to avoid scaring user
            logger.debug(f"WMI info retrieval failed (non-critical): {e}")
            
        return info_list
            
        return info_list

    @staticmethod
    def get_monitor_device_ids() -> List[str]:
        """
        Returns a list of Device IDs (e.g., 'MONITOR\\MNT2700\\...') in EnumDisplayMonitors order.
        Matches the order of monitorcontrol.get_monitors().
        """
        monitor_ids = []
        
        def callback(hmonitor, hdc, lprect, lparam):
            info = MONITORINFOEX()
            info.cbSize = ctypes.sizeof(MONITORINFOEX)
            
            # Default to unknown if retrieval fails
            dev_id = "Unknown"
            
            if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                adapter_name = info.szDevice
                mon_dev = DISPLAY_DEVICE()
                mon_dev.cb = ctypes.sizeof(DISPLAY_DEVICE)
                
                if user32.EnumDisplayDevicesW(adapter_name, 0, ctypes.byref(mon_dev), 0):
                     dev_id = mon_dev.DeviceID
            
            monitor_ids.append(dev_id)
            return True

        user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), 0)
        return monitor_ids

    @staticmethod
    def get_connected_monitors() -> List[Dict]:
        """
        Scans for connected monitors and returns a list of dictionaries.
        Tries to match WMI names to monitors.
        """
        results = []
        with MonitorManager._LOCK:
            try:
                monitors = get_monitors()
                wmi_info = MonitorManager.get_wmi_monitor_info()
                
                # Robust Matching Strategy
                # 1. Get Physical IDs (monitorcontrol order)
                phys_ids = MonitorManager.get_monitor_device_ids()
                
                # 2. Reorder WMI info to match Physical IDs
                ordered_wmi = [None] * len(monitors)
                wmi_pool = wmi_info.copy()
                
                for i, pid in enumerate(phys_ids):
                    if i >= len(monitors): break
                    
                    # Extract HW ID (e.g., LGD076D from MONITOR\LGD076D\...)
                    hw_id = None
                    parts = pid.split('\\')
                    if len(parts) > 1:
                        hw_id = parts[1].upper()
                        
                    # Find matching WMI entry
                    match_idx = -1
                    if hw_id:
                        for k, w in enumerate(wmi_pool):
                            # WMI InstanceName: DISPLAY\LGD076D\5&...
                            if w.get('InstanceName') and hw_id in w['InstanceName'].upper():
                                match_idx = k
                                break
                    
                    # Fallback: exact index match if simple mapping (only if no better ID match found so far?)
                    # Actually, if ID match fails, we shouldn't force index match blindly unless counts are equal.
                    
                    if match_idx != -1:
                        ordered_wmi[i] = wmi_pool.pop(match_idx)
                    else:
                        logger.warning(f"Could not find WMI match for physical monitor {i} ({pid})")

                # Use the reordered list
                wmi_info = ordered_wmi
                use_wmi = True # We always try to use the slot-based WMI info now because it's reordered

                
                for i, monitor in enumerate(monitors):
                    
                    # Retry loop for capabilities
                    caps = {}
                    caps_success = False
                    for attempt in range(3):
                        try:
                            with monitor:
                                caps = monitor.get_vcp_capabilities()
                            caps_success = True
                            break
                        except Exception:
                            time.sleep(0.2)
                    
                    # Internal Monitor Filtering Logic
                    model_name = "Generic Monitor"
                    manufacturer = "Unknown"
                    is_internal = False
                    
                    if use_wmi and wmi_info[i]:
                        w = wmi_info[i]
                        manufacturer = w.get('Manufacturer', 'Unknown').upper()
                        model = w.get('Model', 'Unknown')
                        model_name = f"{manufacturer} {model}"
                        is_internal = w.get('IsInternal', False)
                    elif caps_success and isinstance(caps, dict):
                         model_name = caps.get('model', '') or "Generic Monitor"
    
                    # Filter based on technical connection type
                    if is_internal:
                        logger.info(f"Skipping monitor {i} ({model_name}): Identified as Internal Video Output.")
                        continue
    
                    display_name = f"{model_name} #{i+1}"
                    
                    supported_inputs = MonitorManager._parse_supported_sources(caps) if caps_success else {'HDMI-1': 17, 'DisplayPort': 15}
                    
                    # Try to get current source with retry
                    current_source = None
                    for attempt in range(5):
                        try:
                            with monitor:
                                current_source = MonitorManager._get_current_source(monitor)
                            if current_source is not None:
                                break 
                        except Exception:
                            time.sleep(0.5)
                    
                    results.append({
                        'id': i,
                        'name': display_name,
                        'monitor_obj': monitor,
                        'inputs': supported_inputs,
                        'current_input': current_source
                    })
            except Exception as e:
                logger.error(f"Failed to enumerate monitors: {e}")
        
        return results

    @staticmethod
    def _parse_supported_sources(caps) -> Dict[str, int]:
        """
        Parses the VCP capabilities (dict) to find supported input sources.
        Returns a dict mapping { "Display Name": vcp_value }
        """
        supported = {}
        try:
            if isinstance(caps, dict):
                # 1. Use pre-parsed 'inputs' list if available (List[InputSource | int])
                if 'inputs' in caps:
                    for inp in caps['inputs']:
                        val = getattr(inp, 'value', inp)
                        if isinstance(val, int):
                            name = INPUT_SOURCES.get(val, f"Input {val:02X}")
                            supported[name] = val
                
                # 2. Fallback to 'vcp' dict {0x60: {val: {}, ...}}
                if not supported and 'vcp' in caps and 0x60 in caps['vcp']:
                    vcp60 = caps['vcp'][0x60]
                    for val in vcp60:
                         # val might be string key in some parsing versions? usually int
                        if isinstance(val, str): 
                            try: val = int(val, 16)
                            except: continue
                        name = INPUT_SOURCES.get(val, f"Input {val:02X}")
                        
                        # Ensure unique names
                        original_name = name
                        counter = 2
                        while name in supported:
                            name = f"{original_name} {counter}"
                            counter += 1
                            
                        supported[name] = val
                            
            # 3. Fallback default
            if not supported:
                logger.warning(f"No supported inputs found in capabilities. Using defaults. Raw Caps: {caps}")
                supported = {"HDMI-1": 0x11, "DisplayPort": 0x0F}

        except Exception as e:
            logger.warning(f"Error parsing sources: {e}. Raw Caps: {caps}")
            supported = {"HDMI-1": 0x11, "DisplayPort": 0x0F}
            
        return supported

    @staticmethod
    def _get_current_source(monitor: Monitor) -> Optional[int]:
        try:
            # Use the public API which handles VCP code object and masking
            return monitor.get_input_source()
        except Exception as e:
            msg = str(e)
            if "PDO" in msg or "command field" in msg or "명령 필드" in msg or "비동기적으로 삭제" in msg:
                logger.debug(f"Transient DDC error (common during switching): {e}")
            else:
                logger.warning(f"Could not read current source: {e}")
            return None

    @staticmethod
    def set_input_source(monitor, source_value: int):
        """
        Sets the input source for the given monitor.
        Checks if the monitor is already on that source to prevent black screens.
        """
        with MonitorManager._LOCK:
            try:
                # Ensure we have a valid int
                if isinstance(source_value, str):
                    if source_value.startswith("0x"):
                        source_value = int(source_value, 16)
                    else:
                        source_value = int(source_value)
                
                # Check current source first to prevent redundant switches
                # (Switching to same source can cause black screen/reset on some monitors)
                try:
                    current = None
                    with monitor:
                        current = monitor.get_input_source()
                        
                    if current == source_value:
                        logger.info(f"Monitor is already on source 0x{source_value:02X}. Skipping switch.")
                        return
                    logger.info(f"Current source: 0x{current:02X}, Target: 0x{source_value:02X}")
                except Exception as e:
                    logger.warning(f"Could not verify current source before switching: {e}. Proceeding anyway.")

                logger.info(f"Setting input source to {source_value} (0x{source_value:02X})...")
                
                with monitor:
                    monitor.set_input_source(source_value)
                    logger.info(f"Set monitor source to {source_value:02X}")
                    
            except Exception as e:
                msg = str(e)
                if "PDO" in msg or "command field" in msg or "명령 필드" in msg or "비동기적으로 삭제" in msg:
                    # Downgrade to info/warn as this is expected when the monitor switches away
                    logger.info(f"Monitor accepted command but disconnected (expected): {e}")
                else:
                    logger.error(f"Failed to set input source: {e}")
                    raise e


