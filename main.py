import sys
import os

# Add src directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

from kvm_tray import KVMApp

if __name__ == "__main__":
    import sys
    import logging
    import ctypes
    
    # Configure logging
    logging.basicConfig(
        filename='kvm.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Check for arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--settings':
        try:
            from src.settings_ui import SettingsUI
            import tkinter as tk
            
            root = tk.Tk()
            app = SettingsUI(root)
            root.mainloop()
        except Exception as e:
            logging.error(f"Failed to launch settings: {e}")
    else:
        try:
           print("Starting KVM Switcher...")
           from src.kvm_tray import KVMApp
           app = KVMApp()
           app.run()
        except Exception as e:
            logging.error(f"Fatal error: {e}", exc_info=True)
            print(f"Application crashed. See above for errors.")
            input("Press Enter to close...")
            ctypes.windll.user32.MessageBoxW(0, f"Error starting KVM Switcher: {e}", "KVM Switcher Error", 0x10)
    
    print("Exiting main.")
