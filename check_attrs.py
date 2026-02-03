import sys
import os

# Ensure we can find our src
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from monitorcontrol import get_monitors
except ImportError:
    sys.exit(1)

def inspect_monitor():
    try:
        monitors = get_monitors()
        for i, m in enumerate(monitors):
            print(f"Monitor {i}:")
            with m:
                print(f"  Attributes: {dir(m)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_monitor()
