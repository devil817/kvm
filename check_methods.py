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

def check_methods():
    print("Checking Monitor methods...")
    
    try:
        monitors = get_monitors()
        for i, m in enumerate(monitors):
            print(f"\nMonitor {i}:")
            try:
                with m:
                    # Test get_input_source
                    try:
                        inp = m.get_input_source()
                        print(f"  get_input_source() -> {inp} (Type: {type(inp)})")
                        if hasattr(inp, 'value'):
                             print(f"  get_input_source().value -> {inp.value}")
                    except Exception as e:
                        print(f"  get_input_source failed: {e}")

                    # Test internal/raw access if needed
                    # Warning: _get_vcp_feature is protected
                    try:
                        raw = m._get_vcp_feature(0x60)
                        print(f"  _get_vcp_feature(0x60) -> {raw}")
                    except Exception as e:
                        print(f"  _get_vcp_feature failed: {e}")

            except Exception as e:
                print(f"  Error opening monitor: {e}")

    except Exception as e:
        print(f"Enumeration failed: {e}")

if __name__ == "__main__":
    check_methods()
