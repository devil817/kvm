import json
import os
import logging
from pynput import keyboard
from typing import Callable, Dict
from monitor_utils import INPUT_SOURCES

# Reverse mapping for user config
INPUT_NAME_TO_VAL = {v: k for k, v in INPUT_SOURCES.items()}
# Add common aliases if needed
INPUT_NAME_TO_VAL.update({
    "HDMI1": 0x11, "HDMI2": 0x12, "DP": 0x0F, "DisplayPort": 0x0F, "USBC": 0x1B
})

class HotkeyManager:
    CONFIG_FILE = "hotkeys.json"
    
    def __init__(self, switch_callback: Callable[[int, int], None]):
        """
        switch_callback: function(monitor_idx, source_value)
        """
        self.switch_callback = switch_callback
        self.listener = None
        self.config = {}
        self.config_path = os.path.join(os.getcwd(), self.CONFIG_FILE)
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            self.create_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logging.info(f"Loaded hotkeys from {self.config_path}")
        except Exception as e:
            logging.error(f"Failed to load hotkeys: {e}")
            self.config = {}

    def reload(self):
        self.stop()
        self.load_config()
        self.start()

    def create_default_config(self):
        # Default mapping using human readable strings
        defaults = {
            "<ctrl>+<alt>+1": {"monitor_idx": 0, "source": "HDMI-1"},
            "<ctrl>+<alt>+2": {"monitor_idx": 0, "source": "DisplayPort"}
        }
        try:
            with open(self.config_path, 'w') as f:
                json.dump(defaults, f, indent=4)
            logging.info("Created default hotkeys.json")
        except Exception as e:
            logging.error(f"Failed to create default config: {e}")

    def start(self):
        if self.listener:
            self.listener.stop()
        
        # Build mapping for pynput
        hotkey_map = {}
        
        for keys, action in self.config.items():
            # Check validity
            if "monitor_idx" in action and "source" in action:
                mon_idx = int(action["monitor_idx"])
                raw_source = action["source"]
                
                # Resolve source
                src_val = None
                if isinstance(raw_source, int):
                    src_val = raw_source
                elif isinstance(raw_source, str):
                    # Try exact match or alias
                    src_val = INPUT_NAME_TO_VAL.get(raw_source)
                    # Try case-insensitive lookup if failed
                    if src_val is None:
                        for name, val in INPUT_NAME_TO_VAL.items():
                            if name.lower() == raw_source.lower():
                                src_val = val
                                break
                
                if src_val is None:
                    logging.warning(f"Invalid source '{raw_source}' for hotkey '{keys}'")
                    continue

                # capture closure
                def action_func(m=mon_idx, s=src_val):
                    logging.info(f"Hotkey triggered! Switch Mon {m} -> {s:02X}")
                    self.switch_callback(m, s)
                
                try:
                    hotkey_map[keys] = action_func
                except Exception as e:
                    logging.error(f"Failed to bind '{keys}': {e}")
        
        if not hotkey_map:
            logging.warning("No valid hotkeys to bind.")
            return

        try:
            self.listener = keyboard.GlobalHotKeys(hotkey_map)
            self.listener.start()
            logging.info("GlobalHotKeys listener started.")
        except Exception as e:
            logging.error(f"Failed to start hotkey listener: {e}")

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None
