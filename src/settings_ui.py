import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import threading
from pynput import keyboard

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from monitor_utils import MonitorManager, INPUT_SOURCES
from hotkey_manager import HotkeyManager

class SettingsUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KVM Hotkey Settings")
        self.root.geometry("700x450")
        
        self.hotkeys = {}
        self.monitors = []
        self.row_frames = []
        self.listening = False
        self.current_recording_entry = None
        self.current_pressed = set()
        self.listener = None
        
        # UI Elements
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        ttk.Label(self.main_frame, text="Configure Hotkeys", font=("Arial", 14, "bold")).pack(pady=5)
        ttk.Label(self.main_frame, text="Click 'Record' and press your key combination.").pack(pady=(0, 10))
        
        # Scrollable Area for Rows
        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bottom Buttons
        self.btn_frame = ttk.Frame(root, padding="10")
        self.btn_frame.pack(fill=tk.X)
        
        ttk.Button(self.btn_frame, text="Add New Hotkey", command=self.add_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.btn_frame, text="Save & Close", command=self.save_and_close).pack(side=tk.RIGHT, padx=5)
        
        # Load Data
        self.scan_monitors()
        self.load_hotkeys()
        
    def scan_monitors(self):
        # We need a list of monitor indices and names
        # Since scanning takes time, we might show a splash or just block briefly
        # For UI simple: just call synchronously.
        try:
            detected = MonitorManager.get_connected_monitors()
            self.monitors = [f"Monitor {m['id']} ({m['name']})" for m in detected]
        except Exception:
            self.monitors = ["Monitor 0 (Generic)", "Monitor 1 (Generic)"]
            
        if not self.monitors:
             self.monitors = ["Monitor 0", "Monitor 1", "Monitor 2"]

    def load_hotkeys(self):
        config_path = os.path.join(os.getcwd(), "hotkeys.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.hotkeys = json.load(f)
        else:
            self.hotkeys = {}
            
        for key, action in self.hotkeys.items():
            self.add_row(key, action.get("monitor_idx", 0), action.get("source", "HDMI-1"))

    def start_recording(self, entry, btn):
        if self.listening: return
        
        self.listening = True
        self.current_recording_entry = entry
        self.current_pressed = set()
        
        entry.delete(0, tk.END)
        entry.insert(0, "Press keys...")
        btn.config(text="Listening...", state="disabled")
        
        # Start listener
        self.listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.listener.start()

    def on_key_press(self, key):
        if not self.listening: return
        
        # Store key
        self.current_pressed.add(key)
        
        # Convert to string to show dynamic update
        # But finalized on release usually
        
    def on_key_release(self, key):
        if not self.listening: return
        
        # If it's a modifier key release, we ignore it unless it was the only thing pressed?
        # Usually we want to capture the combo when a non-modifier is pressed OR released.
        # Simple strategy: capture the combo present at the moment of this release, 
        # then stop.
        
        keys_list = []
        # Sort keys to have modifiers first
        # We need a robust way to map pynput keys to strings
        
        # Check modifiers
        modifiers = {
            keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
            keyboard.Key.alt_l, keyboard.Key.alt_r,
            keyboard.Key.shift_l, keyboard.Key.shift_r,
            keyboard.Key.cmd_l, keyboard.Key.cmd_r
        }
        
        # If only modifiers are pressed, keep listening
        is_only_modifiers = all(k in modifiers for k in self.current_pressed)
        
        if is_only_modifiers:
            # If the released key was a modifier, and nothing else was pressed,
            # we might have just finished a modifier-only click?
            # But usually we wait for a non-modifier.
            # If user wants to bind just 'Ctrl', pynput doesn't support that easily as hotkey.
            # Let's assume we wait for a non-modifier key OR user releases all keys.
            
            if not self.current_pressed: # All released
                # Finish recording
                pass
            else:
                return # Still holding some modifiers
                
        # Generate string
        combo_str = self.format_combo(self.current_pressed | {key}) # Ensure the released key is included
        
        # Update UI in main thread
        self.root.after(0, lambda: self.finish_recording(combo_str))
        return False # Stop listener

    def format_combo(self, keys):
        parts = []
        
        # Order: Cmd, Ctrl, Alt, Shift, Others
        
        def is_key(k, target): return k == target
        
        has_ctrl = any(k in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r] for k in keys)
        has_alt = any(k in [keyboard.Key.alt_l, keyboard.Key.alt_r] for k in keys)
        has_shift = any(k in [keyboard.Key.shift_l, keyboard.Key.shift_r] for k in keys)
        has_cmd = any(k in [keyboard.Key.cmd_l, keyboard.Key.cmd_r] for k in keys)
        
        if has_cmd: parts.append("<cmd>")
        if has_ctrl: parts.append("<ctrl>")
        if has_alt: parts.append("<alt>")
        if has_shift: parts.append("<shift>")
        
        for k in keys:
            if isinstance(k, keyboard.Key):
                if k in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.alt_l, keyboard.Key.alt_r,
                         keyboard.Key.shift_l, keyboard.Key.shift_r, keyboard.Key.cmd_l, keyboard.Key.cmd_r]:
                    continue
                # Special key format <f12>
                parts.append(f"<{k.name}>")
            elif isinstance(k, keyboard.KeyCode):
                # Char
                if k.char:
                    parts.append(k.char.lower())
                else:
                    parts.append(f"<{k.vk}>") # Fallback
                    
        return "+".join(parts)

    def finish_recording(self, combo_str):
        if self.listening:
            self.listening = False
            self.current_recording_entry.delete(0, tk.END)
            self.current_recording_entry.insert(0, combo_str)
            # Find the button to reset state? 
            # We don't have ref to button easily unless stored.
            # Iterating rows to find which one?
            for row in self.row_frames:
                if row['key'] == self.current_recording_entry:
                     row['btn'].config(text="Record", state="normal")
            
            self.current_pressed = set()
            self.current_recording_entry = None

    def add_row(self, key="", mon_idx=0, source="HDMI-1"):
        row_frame = ttk.Frame(self.scrollable_frame)
        row_frame.pack(fill=tk.X, pady=2)
        
        # Key Entry
        ent_key = ttk.Entry(row_frame, width=20)
        ent_key.insert(0, key)
        ent_key.pack(side=tk.LEFT, padx=2)
        
        # Record Button
        btn_rec = ttk.Button(row_frame, text="Record", width=8)
        btn_rec.configure(command=lambda e=ent_key, b=btn_rec: self.start_recording(e, b))
        btn_rec.pack(side=tk.LEFT, padx=2)
        
        # Monitor Combo
        cb_mon = ttk.Combobox(row_frame, values=self.monitors, state="readonly", width=20)
        # Set selection
        try:
            if mon_idx < len(self.monitors):
                cb_mon.current(mon_idx)
            else:
                cb_mon.current(0)
        except:
             cb_mon.current(0)
             
        cb_mon.pack(side=tk.LEFT, padx=2)
        
        # Input Source Combo
        # Get list of friendly names
        input_names = sorted([k for k, v in INPUT_SOURCES.items() if isinstance(k, str)])
        # Also include common ones if missing
        common = ["HDMI-1", "HDMI-2", "DisplayPort", "USB-C"]
        for c in common:
            if c not in input_names: input_names.append(c)
            
        cb_src = ttk.Combobox(row_frame, values=input_names, width=15)
        cb_src.set(source)
        cb_src.pack(side=tk.LEFT, padx=2)
        
        # Delete Button
        btn_del = ttk.Button(row_frame, text="X", width=3, command=lambda: self.delete_row(row_frame))
        btn_del.pack(side=tk.LEFT, padx=5)
        
        self.row_frames.append({
            "frame": row_frame,
            "key": ent_key,
            "btn": btn_rec,
            "mon": cb_mon,
            "src": cb_src
        })

    def delete_row(self, frame):
        frame.destroy()
        self.row_frames = [r for r in self.row_frames if r["frame"] != frame]

    def save_and_close(self):
        new_config = {}
        
        for row in self.row_frames:
            key = row["key"].get().strip()
            if not key: continue
            
            mon_str = row["mon"].get() # "Monitor 0 (Name)"
            # Extract index
            try:
                mon_idx = int(mon_str.split()[1])
            except:
                mon_idx = 0
            
            src = row["src"].get()
            
            new_config[key] = {
                "monitor_idx": mon_idx,
                "source": src
            }
            
        # Write
        try:
            with open("hotkeys.json", "w") as f:
                json.dump(new_config, f, indent=4)
            messagebox.showinfo("Saved", "Configuration saved!\n\nPlease select 'Reload Hotkeys' in the System Tray to apply changes.")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SettingsUI(root)
    root.mainloop()
