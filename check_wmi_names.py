import subprocess
import re

def get_wmi_names():
    # PowerShell command to get Monitor info
    cmd = """
    Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorID | ForEach-Object {
        $Manuf = [System.Text.Encoding]::ASCII.GetString($_.ManufacturerName).Trim([char]0)
        $Model = [System.Text.Encoding]::ASCII.GetString($_.UserFriendlyName).Trim([char]0)
        $Serial = [System.Text.Encoding]::ASCII.GetString($_.SerialNumberID).Trim([char]0)
        [PSCustomObject]@{
            Manufacturer = $Manuf
            Model = $Model
            Serial = $Serial
            InstanceName = $_.InstanceName
        }
    } | ConvertTo-Json
    """
    
    try:
        result = subprocess.check_output(["powershell", "-Command", cmd], text=True)
        print(result)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_wmi_names()
