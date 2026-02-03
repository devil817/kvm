from monitorcontrol import get_monitors
import time

def check_inputs():
    print("Enumerating monitors...")
    try:
        monitors = get_monitors()
        print(f"Found {len(monitors)} monitors.")
    except Exception as e:
        print(f"Failed to get monitors: {e}")
        return
    
    for i, monitor in enumerate(monitors):
        print(f"\nMonitor {i}:")
        try:
            with monitor:
                try:
                    caps = monitor.get_vcp_capabilities()
                    print(f"  Capabilities: {caps}")
                except Exception as e:
                    print(f"  Failed to get capabilities: {e}")
                    caps = {}

                try:
                    current = monitor.get_input_source()
                    print(f"  Current Input: {current} (type: {type(current)})")
                    
                    # Check inputs from caps
                    if 'inputs' in caps:
                        print("  Supported Inputs per Caps:")
                        for inp in caps['inputs']:
                             # Handle both int and objects (monitorcontrol might return objects)
                             val = getattr(inp, 'value', inp)
                             print(f"    - {inp} (Value: {val}, Type: {type(val)})")
                             
                             if val == current:
                                 print(f"      [MATCH] This input matches current source!")
                             else:
                                 print(f"      [NO MATCH] {val} != {current}")
                except Exception as e:
                    print(f"  Error reading input: {e}")
                    
        except Exception as e:
            print(f"  Error accessing monitor: {e}")

if __name__ == "__main__":
    check_inputs()
