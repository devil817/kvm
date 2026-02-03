import pystray
from pystray import MenuItem as Item, Menu
from PIL import Image, ImageDraw
import threading
import time
import logging
import os
import sys
import ctypes

# Ensure src is in path if running from parent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from monitor_utils import MonitorManager
from config_manager import ConfigManager
from hotkey_manager import HotkeyManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class KVMApp:
    def __init__(self):
        self.monitors = []
        self.icon = None
        self.scanning = False
        self.should_exit = False
        
        # Start background scanner
        self.scanner_thread = threading.Thread(target=self._monitor_scanner_loop, daemon=True)
        self.scanner_thread.start()
        
        # Start Hotkey Manager
        self.hotkey_mgr = HotkeyManager(self.on_hotkey_switch)
        self.hotkey_mgr.start()

        # Check for Admin Privileges
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                logging.warning("Not running as Admin. Hotkeys might not work in some apps.")
                # Show a toast notification if possible, or just log for now.
                # Pystray notify requires icon to be running, so we can't do it in init easily before icon.run()
                # We'll rely on the log default, but maybe trigger a notification after icon start.
                self.show_admin_warning = True
            else:
                self.show_admin_warning = False
        except Exception:
            logging.warning("Failed to check admin privileges.")
            self.show_admin_warning = False

    def on_hotkey_switch(self, monitor_idx, source_value):
        # We need to find the monitor object by index? 
        # But monitor_idx depends on the order in self.monitors which changes on scan?
        # Ideally, hotkeys should bind to Serial Number or ID.
        # For now, we use the index in the 'monitors' list as a naive approach.
        
        # If monitors haven't been scanned yet, we might miss.
        if not self.monitors:
            logging.warning("Hotkey pressed but no monitors detected yet.")
            return

        target_monitor = None
        # Find by ID match or list index? 
        # MonitorManager assigns 'id' = list index.
        for m in self.monitors:
            if m['id'] == monitor_idx:
                target_monitor = m['monitor_obj']
                break
        
        if target_monitor:
            self.on_switch_input(target_monitor, source_value)
        else:
            logging.warning(f"Hotkey target monitor {monitor_idx} not found.")

    def create_image(self):
        # Create a simple icon (Monitor shape)
        # 64x64
        width = 64
        height = 64
        color1 = (0, 0, 0)
        color2 = (255, 255, 255)
        
        image = Image.new('RGB', (width, height), color2)
        dc = ImageDraw.Draw(image)
        
        # Draw screen
        dc.rectangle([8, 8, 56, 40], fill=color1)
        dc.rectangle([12, 12, 52, 36], fill=color2) # inner screen
        
        # Draw stand
        dc.rectangle([28, 40, 36, 50], fill=color1)
        dc.rectangle([20, 50, 44, 54], fill=color1)
        
        return image

    def _monitor_scanner_loop(self):
        while not self.should_exit:
            if not self.scanning:
                self.scanning = True
                try:
                    self.monitors = MonitorManager.get_connected_monitors()
                except Exception as e:
                    logging.error(f"Scanner error: {e}")
                
                self.scanning = False
                
                # Update menu dynamically by re-assigning it
                if self.icon:
                    self.icon.menu = self.build_menu()
            
            # Sleep 30 seconds
            for _ in range(30): 
                if self.should_exit: break
                time.sleep(1)

    def on_switch_input(self, monitor_obj, source_value):
        def _task():
            # Change icon to indicate activity?
            logging.info(f"Switching input to {source_value}...")
            MonitorManager.set_input_source(monitor_obj, source_value)
            
            # Immediately update internal state so menu reflects this
            # Find the monitor entry
            for m in self.monitors:
                if m['monitor_obj'] == monitor_obj:
                    m['current_input'] = source_value
                    break
                    
            if self.icon: 
                self.icon.menu = self.build_menu()
            
        threading.Thread(target=_task).start()

    def on_toggle_startup(self, icon, item):
        current = ConfigManager.is_run_at_startup()
        ConfigManager.set_run_at_startup(not current)

    def on_refresh(self, icon, item):
        # Force refresh
        def _refresh():
            self.scanning = True
            # Update menu to show "Scanning..."
            if self.icon: self.icon.menu = self.build_menu()
            
            self.monitors = MonitorManager.get_connected_monitors()
            self.scanning = False
            
            if self.icon: self.icon.menu = self.build_menu()
        threading.Thread(target=_refresh).start()

    def on_exit(self, icon, item):
        self.should_exit = True
        if self.hotkey_mgr:
            self.hotkey_mgr.stop()
        icon.stop()

    def on_configure_hotkeys(self, icon, item):
        try:
            # Launch settings UI in new process
            import subprocess
            
            if getattr(sys, 'frozen', False):
                # If packaged exe, run the exe itself with --settings argument
                exe_path = sys.executable
                project_root = os.path.dirname(exe_path) # In onefile, this is usually where exe is
                subprocess.Popen([exe_path, "--settings"], cwd=project_root)
            else:
                python_exe = sys.executable
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings_ui.py")
                # Run from project root so hotkeys.json is found in cwd
                project_root = os.getcwd() 
                # We need to run settings_ui.py directly or via main.py? 
                # If settings_ui.py has valid if __name__ == __main__, we can run it. It does (I wrote it).
                subprocess.Popen([python_exe, script_path], cwd=project_root)
                
        except Exception as e:
            logging.error(f"Failed to open settings: {e}")

    def on_reload_hotkeys(self, icon, item):
        if self.hotkey_mgr:
            self.hotkey_mgr.reload()
            logging.info("Hotkeys reloaded.")

    def build_menu(self):
        # Dynamic menu construction
        items = []
        
        if self.scanning:
            items.append(Item("Scanning monitors...", lambda: None, enabled=False))
        elif not self.monitors:
            items.append(Item("No monitors found", lambda: None, enabled=False))
        else:
            for mon in self.monitors:
                # Submenu for each monitor
                input_items = []
                for name, val in mon['inputs'].items():
                    # Check if this input is the currently active one
                    # If so, skip it as requested by user ("Do not display current source")
                    # if mon.get('current_input') == val:
                    #     logging.info(f"Hiding input {name} ({val}) because it matches current: {mon.get('current_input')}")
                    #     continue
                     
                    
                    def make_callback(m, v):
                        return lambda icon, item: self.on_switch_input(m, v)
                        
                    input_items.append(Item(
                        name,
                        make_callback(mon['monitor_obj'], val)
                    ))
                
                # If no items (e.g. only 1 input and it's active), maybe show "Current: HDMI-1" disabled?
                if not input_items:
                    curr_val = mon.get('current_input')
                    # Find name
                    curr_name = "Unknown"
                    for k,v in mon['inputs'].items(): 
                        if v == curr_val: curr_name = k
                    
                    input_items.append(Item(f"Current: {curr_name}", lambda: None, enabled=False))

                items.append(Item(mon['name'], Menu(*input_items)))
        
        items.append(Menu.SEPARATOR)
        items.append(Item("Configure Hotkeys", self.on_configure_hotkeys))
        items.append(Item("Reload Hotkeys", self.on_reload_hotkeys))
        items.append(Menu.SEPARATOR)
        items.append(Item("Rescan Monitors", self.on_refresh))
        items.append(Item("Run at Startup", self.on_toggle_startup, checked=lambda i: ConfigManager.is_run_at_startup()))
        items.append(Item("Exit", self.on_exit))
        
        return Menu(*items)

    def run(self):
        # Call build_menu() immediately to pass a Menu object, not the method
        logging.info("Building initial menu...")
        menu = self.build_menu()
        logging.info("Creating icon...")
        self.icon = pystray.Icon("KVM Switcher", self.create_image(), "KVM Switcher", menu=menu)
        logging.info("Running icon...")
        logging.info("Running icon...")
        
        # Show specific startup notifications
        def startup_notify():
            time.sleep(2) # Wait for icon availability
            if getattr(self, 'show_admin_warning', False):
                self.icon.notify(
                    "Hotkeys may not work in games or admin apps without Admin privileges.",
                    title="KVM Switcher: Not running as Admin"
                )
        
        threading.Thread(target=startup_notify, daemon=True).start()
        
        self.icon.run()
        logging.info("Icon run loop ended.")

if __name__ == "__main__":
    app = KVMApp()
    app.run()
