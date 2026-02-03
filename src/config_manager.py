import winreg
import sys
import os
import logging

class ConfigManager:
    APP_NAME = "KVMInputSwitcher"
    RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @staticmethod
    def is_run_at_startup() -> bool:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, ConfigManager.RUN_KEY_PATH, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, ConfigManager.APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logging.error(f"Error checking startup status: {e}")
            return False

    @staticmethod
    def set_run_at_startup(enabled: bool):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, ConfigManager.RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
            if enabled:
                # Get path to executable
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                else:
                    # If running as script, use pythonw.exe + script path
                    # But for now assuming python.exe
                    exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                
                winreg.SetValueEx(key, ConfigManager.APP_NAME, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, ConfigManager.APP_NAME)
                except FileNotFoundError:
                    pass # Already deleted
            winreg.CloseKey(key)
        except Exception as e:
            logging.error(f"Error changing startup config: {e}")
