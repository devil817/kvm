import subprocess
import json

def get_wmi_params():
    # PowerShell command to get Monitor Connection Params
    cmd = """
    Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorConnectionParams | Select-Object InstanceName, VideoOutputTechnology | ConvertTo-Json
    """
    
    try:
        result = subprocess.check_output(["powershell", "-Command", cmd], text=True)
        print(result)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_wmi_params()
