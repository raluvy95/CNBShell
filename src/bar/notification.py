import datetime
import threading 
import subprocess
import atexit
import psutil
import socket
from PIL import Image

from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.utils import exec_shell_command
from gi.repository import GLib, GdkPixbuf # type: ignore

from src.bar.dashboard import SystemDashboard

# --- CONFIG ---
MAX_IMAGE_BYTES = 5 * 1024 * 1024  
MAX_TEXT_LEN = 1000                
SAFE_ICON_SIZE = 48                

# --- HELPER: SAFE STRING PARSING ---
def safe_extract_string(line):
    start = line.find('"')
    if start == -1: return None
    end = line.rfind('"')
    if end <= start: return None
    raw = line[start+1:end]
    return raw.replace('\\"', '"').replace('\\\\', '\\')

# --- HELPER: DND CHECK ---
def get_dnd_status():
    try:
        result = exec_shell_command("makoctl mode")
        return "do-not-disturb" in result # type: ignore
    except: return False

def toggle_dnd_mode():
    try:
        if get_dnd_status(): exec_shell_command("makoctl mode -r do-not-disturb")
        else: exec_shell_command("makoctl mode -a do-not-disturb")
        return get_dnd_status()
    except: return False

# --- HELPER: NETWORK CHECK ---
def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=1)
        return True
    except OSError: return False

class NotificationIndicator(Button):
    def __init__(self, **kwargs):
        super().__init__(
            style_classes="notification-indicator",
            visible=True,
            **kwargs
        )
        self.set_no_show_all(True)

        # --- INSTANTIATE DASHBOARD ---
        self.dashboard = SystemDashboard(
            dnd_callback=self.handle_dnd_toggle,
            count_callback=self.update_count_display # Pass the callback!
        )

        self.connect("clicked", self.toggle_dashboard)
        
        self.layout_box = Box(orientation="h", spacing=15)
        self.net_label = Label(label="󰤯", style_classes="txt-icon")
        self.layout_box.add(self.net_label)
        self.vol_label = Label(label="󰕾", style_classes="txt-icon")
        self.layout_box.add(self.vol_label)
        self.icon_label = Label(label="󰂚", style_classes="txt-icon") 
        self.layout_box.add(self.icon_label)
        self.count_label = Label(label="0", style_classes="txt-count", visible=False)
        self.layout_box.add(self.count_label)
        self.add(self.layout_box)
        self.unread_count = 0
        
        # --- START PROCESSES ---
        # 1. DBus Monitor (Background Thread)
        self._monitor_thread = threading.Thread(target=self.monitor_dbus_subprocess, daemon=True)
        self._monitor_thread.start()
        
        # 2. Initial State Checks
        self.update_dnd_state()
        self.update_status_indicators()
        GLib.timeout_add_seconds(3, self.update_status_indicators)

    def update_count_display(self, count):
        self.unread_count = count
        self.count_label.set_label(str(count))
        
        if count > 0:
            self.count_label.set_visible(True)
            self.icon_label.set_label("󱅫") # Unread Bell
        else:
            self.count_label.set_visible(False)
            self.update_dnd_state() # Reset to standard/DND icon
            
    def toggle_dashboard(self, *args):
        if self.dashboard.get_visible():
            self.dashboard.hide()
            self.unread_count = 0
            self.count_label.set_visible(False)
            self.icon_label.set_label("󰂚")
            # Refresh status one last time when closing
            self.update_status_indicators()
        else:
            self.dashboard.show_all()
            self.dashboard.check_empty()
            # Force refresh dashboard sliders when opening
            self.dashboard.quick_settings.refresh()
    
    def handle_dnd_toggle(self):
        toggle_dnd_mode()
        self.update_dnd_state()

    def update_dnd_state(self):
        is_dnd = get_dnd_status()
        self.dashboard.update_dnd_icon(is_dnd)
        # Update the bell icon based on DND, preserving read/unread logic if needed
        # For now, DND overrides the bell shape
        if is_dnd: self.icon_label.set_label("󰂛") # Moon/Silent
        else: self.icon_label.set_label("󰂚")     # Bell

    def update_status_indicators(self):
        """Updates Volume and Network icons in the bar."""
        # --- VOLUME ---
        try:
            vol = int(exec_shell_command("pamixer --get-volume").strip()) # type: ignore
            is_muted = exec_shell_command("pamixer --get-mute").strip() == "true" # type: ignore
            
            icons = ["󰝟", "󰖁", "󰕿", "󰖀", "󰕾"]
            if is_muted:
                self.vol_label.set_label(icons[0])
            else:
                idx = 1
                if vol > 0: idx = 2
                if vol > 33: idx = 3
                if vol > 66: idx = 4
                self.vol_label.set_label(icons[idx])
        except: 
            self.vol_label.set_label("󰕾") # Fallback

        # --- NETWORK ---
        try:
            stats = psutil.net_if_stats()
            active_iface = False
            for iface, stat in stats.items():
                if stat.isup and iface != "lo":
                    active_iface = True
                    break
            
            if active_iface:
                # Only check internet if link is up (saves resources)
                if check_internet(): self.net_label.set_label("󰤨") # Connected
                else: self.net_label.set_label("󰤢") # No Internet
            else:
                self.net_label.set_label("󰤯") # Disconnected
        except:
            self.net_label.set_label("󰤯")

        return True # Keep GLib timer running

    # --- DBUS MONITOR (Existing Logic) ---
    def monitor_dbus_subprocess(self):
        cmd = ["dbus-monitor", "interface='org.freedesktop.Notifications',member='Notify'"]
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1, shell=False)
        except FileNotFoundError:
            print("Error: dbus-monitor not installed.")
            return

        atexit.register(lambda: process.terminate() if process.poll() is None else None)

        current_msg = self.new_msg_template()
        arg_index = -1 
        in_hints = False
        in_image_struct = False
        current_hint_key = None
        image_ints = []
        hex_buffer = []
        total_image_bytes = 0

        for line in process.stdout: # type: ignore
            line = line.strip()
            
            if "member=Notify" in line or "member='Notify'" in line:
                if current_msg["app_name"] or current_msg["summary"]:
                    self.finalize_message(current_msg)
                current_msg = self.new_msg_template()
                arg_index = -1; in_hints = False; in_image_struct = False; total_image_bytes = 0
                continue

            if not in_image_struct and not in_hints:
                is_type_decl = line.startswith("string ") or line.startswith("uint32 ") or line.startswith("int32 ") or line.startswith("array [")
                if is_type_decl and not line.startswith("variant"):
                    arg_index += 1

            if arg_index == 1 and line.startswith("uint32 "):
                try: current_msg["replaces_id"] = int(line.split()[1])
                except: pass

            if line.startswith('string "') and not in_image_struct:
                content = safe_extract_string(line)
                if content is not None:
                    if arg_index == 0: current_msg["app_name"] = content
                    elif arg_index == 2: current_msg["icon"] = content
                    elif arg_index == 3: current_msg["summary"] = content
                    elif arg_index == 4: current_msg["body"] = content
                    if in_hints:
                        if current_hint_key is None: current_hint_key = content
                        else:
                            current_msg["hints"][current_hint_key] = content
                            current_hint_key = None

            if arg_index == 6:
                if line.startswith("array ["): in_hints = True
                if line == "]": in_hints = False
            
            if in_hints and "dict entry(" in line: current_hint_key = None

            if '"image-data"' in line or '"image_data"' in line or '"icon_data"' in line:
                in_image_struct = True; image_ints = []; hex_buffer = []
                continue

            if in_image_struct:
                if line.startswith("int32 ") or line.startswith("boolean "):
                    parts = line.split()
                    if len(parts) >= 2:
                        val = parts[1]
                        image_ints.append(1 if val == "true" else 0 if val == "false" else int(val))
                elif total_image_bytes < MAX_IMAGE_BYTES and all(c in "0123456789abcdefABCDEF " for c in line) and len(line) > 5:
                    hex_buffer.append(line)
                    total_image_bytes += len(line) // 2
                if line == "}" or (line == "]" and len(hex_buffer) > 0):
                    if len(image_ints) >= 5 and hex_buffer:
                        try:
                            # 1. Reconstruct raw bytes
                            full_hex = "".join(hex_buffer).replace(" ", "")
                            raw_data = bytes.fromhex(full_hex)
                            
                            width = image_ints[0]
                            height = image_ints[1]
                            rowstride = image_ints[2]
                            has_alpha = bool(image_ints[3])
                            bits_per_sample = image_ints[4]
                            
                            # 2. Load into Pillow
                            mode = 'RGBA' if has_alpha else 'RGB'
                            img = Image.frombytes(mode, (width, height), raw_data, 'raw', mode, rowstride, 1)

                            img.thumbnail((42, 42), Image.Resampling.LANCZOS)
                            
                            # 4. Save back to the message structure
                            new_width, new_height = img.size
                            new_rowstride = new_width * (4 if has_alpha else 3)
                            
                            current_msg["img_struct"] = [
                                new_width, 
                                new_height, 
                                new_rowstride, 
                                has_alpha, 
                                bits_per_sample, 
                                img.tobytes()
                            ]
                        except Exception as e:
                            print(f"Image resize failed: {e}")
                            pass
                    in_image_struct = False

    def new_msg_template(self):
        return { "app_name": "", "replaces_id": 0, "icon": "", "summary": "", "body": "", "hints": {}, "img_struct": [] }

    def finalize_message(self, msg):
        app_name = msg["app_name"]
        ignored = ["audio-feedback", "dunst", "mako", "volume", "brightness"]
        if app_name.lower() in ignored: return
        
        if not app_name.strip() or app_name.startswith(":"): app_name = "System"

        image_pixbuf = None
        if msg["img_struct"]:
            try:
                w, h, stride, alpha, bits, data = msg["img_struct"]
                glib_bytes = GLib.Bytes.new(data)
                image_pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(glib_bytes, GdkPixbuf.Colorspace.RGB, alpha, bits, w, h, stride)
            except: pass

        sync_tag = msg["hints"].get("x-canonical-private-synchronous")

        GLib.idle_add(
            self.dashboard.add_or_update_notification,
            app_name, msg["summary"], msg["body"],
            datetime.datetime.now().strftime("%H:%M"),
            image_pixbuf, msg["icon"], msg["replaces_id"], sync_tag
        )