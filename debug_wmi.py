import subprocess
import json
import re

def debug_wmi():
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
    
    print(f"Running command...")
    try:
        result = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            text=True,
            creationflags=0x08000000
        ).strip()
        print(f"RAW RESULT:\n{result}\n")
        
        print("Attempting to parse...")
        match = re.search(r'(\[.*\]|\{.*\})', result, re.DOTALL)
        if match:
            json_str = match.group(0)
            print(f"Found JSON: {json_str}")
            data = json.loads(json_str)
            print(f"Parsed Data: {data}")
        else:
            print("No JSON pattern found.")
            
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        print(f"Output: {e.output}")
    except Exception as e:
        print(f"Python error: {e}")

if __name__ == "__main__":
    debug_wmi()
