import subprocess
import json
import re
from monitorcontrol import get_monitors

def get_wmi_ids():
    print("--- WMI Data ---")
    cmd = """
    $Monitors = Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorID
    
    $Result = $Monitors | ForEach-Object {
        $curr = $_
        
        $Manuf = [System.Text.Encoding]::ASCII.GetString($curr.ManufacturerName).Trim([char]0)
        $Product = [System.Text.Encoding]::ASCII.GetString($curr.ProductCodeID).Trim([char]0)
        $Serial = [System.Text.Encoding]::ASCII.GetString($curr.SerialNumberID).Trim([char]0)
        $Friendly = [System.Text.Encoding]::ASCII.GetString($curr.UserFriendlyName).Trim([char]0)
        
        [PSCustomObject]@{
            Manufacturer = $Manuf
            ProductCode = $Product
            SerialNumber = $Serial
            FriendlyName = $Friendly
            InstanceName = $curr.InstanceName
        }
    }
    
    if ($Result) { 
        if ($Result -is [PSCustomObject]) { $Result = @($Result) }
    } else {
         $Result = @() 
    }
    $Result | ConvertTo-Json -Compress
    """
    
    try:
        result = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            text=True,
            creationflags=0x08000000
        ).strip()
        
        match = re.search(r'(\[.*\]|\{.*\})', result, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            if isinstance(data, dict): data = [data]
            for item in data:
                print(item)
            return data
    except Exception as e:
        print(f"WMI Error: {e}")
    return []

def get_mc_monitors():
    print("\n--- MonitorControl Data ---")
    monitors = get_monitors()
    for i, m in enumerate(monitors):
        print(f"Monitor {i}: {m}")
        try:
            with m:
                caps = m.get_vcp_capabilities()
                print(f"  Caps Model: {caps.get('model')}")
                print(f"  Caps Type: {caps.get('type')}")
                # Inspect internal vcp object if possible for clues
                if hasattr(m, 'vcp'):
                    print(f"  VCP Description: {m.vcp.description}")
        except Exception as e:
            print(f"  Error accessing: {e}")

if __name__ == "__main__":
    get_wmi_ids()
    get_mc_monitors()
