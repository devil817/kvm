import sys
import os

# Ensure we can find our src
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from monitorcontrol import get_monitors
    from monitor_utils import MonitorManager
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def check_ddc():
    print("Checking DDC/CI capabilities...")
    
    # 1. Test MonitorManager logic
    print("\n--- MonitorManager Detection ---")
    try:
        monitors = MonitorManager.get_connected_monitors()
        print(f"Detected {len(monitors)} monitors via MonitorManager.")
        for mon in monitors:
            print(f"  ID: {mon['id']}")
            print(f"  Name: {mon['name']}")
            print(f"  Supported Inputs: {mon['inputs']}")
            print(f"  Current Input: {mon['current_input']}")
    except Exception as e:
        print(f"MonitorManager Failed: {e}")

if __name__ == "__main__":
    check_ddc()
