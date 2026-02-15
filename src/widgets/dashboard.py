import os
from loguru import logger
import psutil
import socket
import pulsectl

from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.scale import Scale
from fabric.utils import exec_shell_command
from gi.repository import GLib, Gtk, Gdk, Pango, GdkPixbuf # type: ignore

# --- HELPERS ---
def get_kbd_backlight_device():
    base = "/sys/class/leds"
    if not os.path.exists(base): return None
    for device in os.listdir(base):
        if "asus::kbd_backlight" in device: return device
        if "kbd_backlight" in device: return device
    return None

def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=1)
        return True
    except OSError: return False

# --- QUICK SETTINGS WIDGETS ---
class QuickSettings(Box):
    def __init__(self):
        super().__init__(orientation="v", spacing=12, style_classes="quick-settings")
        
        self.pulse = None
        self._init_pulse()

        # 1. VOLUME
        self.vol_box = Box(orientation="h", spacing=8)
        self.vol_btn = Button(style_classes="qs-icon-btn", on_clicked=self.toggle_mute)
        self.vol_icon = Label(label="󰕾", style_classes="qs-icon")
        self.vol_btn.add(self.vol_icon)
        self.vol_scale = Scale(min_value=0, max_value=100, orientation="h", h_expand=True)
        self.vol_scale.set_value(50)
        self.vol_scale.connect("value-changed", self.on_vol_change)
        self.vol_scale.connect("button-release-event", self.on_vol_release)
        self.vol_box.add(self.vol_btn); self.vol_box.add(self.vol_scale)
        self.add(self.vol_box)

        # 2. SCREEN BACKLIGHT
        self.bri_box = Box(orientation="h", spacing=8)
        self.bri_icon = Label(label="󰛨", style_classes="qs-icon-label")
        self.bri_scale = Scale(min_value=5, max_value=100, orientation="h", h_expand=True)
        self.bri_scale.set_value(100)
        self.bri_scale.connect("value-changed", self.on_bri_change)
        self.bri_box.add(self.bri_icon); self.bri_box.add(self.bri_scale)
        self.add(self.bri_box)

        # 3. KEYBOARD BACKLIGHT
        self.kbd_device = get_kbd_backlight_device()
        if self.kbd_device:
            self.kbd_max = 3
            try:
                with open(f"/sys/class/leds/{self.kbd_device}/max_brightness", 'r') as f:
                    self.kbd_max = int(f.read().strip())
            except: pass

            self.kbd_box = Box(orientation="h", spacing=8)
            self.kbd_icon = Label(label="󰌌", style_classes="qs-icon-label")
            self.kbd_scale = Scale(min_value=0, max_value=self.kbd_max, orientation="h", h_expand=True)
            self.kbd_scale.set_increments(1, 1)
            self.kbd_scale.set_digits(0)
            self.kbd_scale.set_round_digits(0)
            self.kbd_scale.connect("value-changed", self.on_kbd_change)
            self.kbd_box.add(self.kbd_icon); self.kbd_box.add(self.kbd_scale)
            self.add(self.kbd_box)

        # 4. NETWORK
        self.net_box = Box(orientation="h", spacing=8, style_classes="qs-net-row")
        self.net_icon = Label(label="󰤯", style_classes="qs-net-icon")
        self.net_label = Label(label="Checking...", h_align="start", h_expand=True, style_classes="qs-net-text")
        self.wifi_btn = Button(style_classes="qs-text-btn", label="Manage", on_clicked=self.spawn_nmtui)
        self.net_box.add(self.net_icon); self.net_box.add(self.net_label); self.net_box.add(self.wifi_btn)
        self.add(self.net_box)

    def _init_pulse(self):
        if not self.pulse:
            try: 
                self.pulse = pulsectl.Pulse('cnb-shell') # type: ignore
            except Exception as e: 
                print(f"[Error] Could not connect to PulseAudio: {e}")
                self.pulse = None

    def refresh(self):
        GLib.idle_add(self._update_volume_ui)
        GLib.idle_add(self._update_brightness_ui)
        GLib.idle_add(self._update_network_ui)
        if self.kbd_device: GLib.idle_add(self._update_kbd_ui)

    def on_vol_release(self, widget, event):
        exec_shell_command("pw-play /usr/share/sounds/freedesktop/stereo/audio-volume-change.oga")
        return False

    def _get_vol_data(self):
        # Retry connection if lost
        if self.pulse is None or not self.pulse.connected:
            self._init_pulse()

        if self.pulse:
            try:
                server_info = self.pulse.server_info()
                default_sink = None
                
                # Robust extraction of default sink name
                if isinstance(server_info, dict):
                    default_sink = server_info.get('default_sink_name')
                elif isinstance(server_info, (list, tuple)):
                    if server_info:
                        first = server_info[0]
                        if isinstance(first, dict):
                            default_sink = first.get('default_sink_name')
                        else:
                            default_sink = getattr(first, 'default_sink_name', None)
                else:
                    default_sink = getattr(server_info, 'default_sink_name', None)

                if default_sink:
                    sink = self.pulse.get_sink_by_name(default_sink)
                    return (round(sink.volume.value_flat * 100), sink.mute) # type: ignore
            except Exception as e:
                print(f"[Error] PulseAudio data retrieval failed: {e}")
                self.pulse = None # Force re-init next time
        
        # Default return if Pulse is unreachable (no CLI fallback)
        return (0, False)
    
    
    def get_vol(self):
        icons = ["󰝟", "󰖁", "󰕿", "󰖀", "󰕾"]
        vol, is_muted = self._get_vol_data()
        if is_muted:
            return icons[0], vol
        else:
            idx = 1
            if vol > 0: idx = 2
            if vol > 33: idx = 3
            if vol > 66: idx = 4
            return icons[idx], vol


    def _update_volume_ui(self):
        icon, vol = self.get_vol()
        if abs(self.vol_scale.get_value() - vol) > 1: self.vol_scale.set_value(vol)
        self.vol_icon.set_label(icon)
        self.vol_scale.set_tooltip_text(f"{vol}%")

    def on_vol_change(self, scale):
        val = int(scale.get_value())
        if self.pulse:
            try:
                server_info = self.pulse.server_info()
                # Simplified attribute access assuming standard library behavior now
                sink_name = getattr(server_info, 'default_sink_name', None)
                if not sink_name and isinstance(server_info, dict): 
                     sink_name = server_info.get('default_sink_name')
                
                if sink_name:
                    sink = self.pulse.get_sink_by_name(sink_name) # type: ignore
                    self.pulse.volume_set_all_chans(sink, val / 100.0)
                    if sink.mute and val > 0: self.pulse.mute(sink, False) # type: ignore
                    self._update_volume_ui()
            except Exception as e: 
                print(f"[Error] PulseAudio set volume failed: {e}")

    def toggle_mute(self, btn):
        if self.pulse:
            try:
                server_info = self.pulse.server_info()
                sink_name = getattr(server_info, 'default_sink_name', None)
                if not sink_name and isinstance(server_info, dict): 
                     sink_name = server_info.get('default_sink_name')

                if sink_name:
                    sink = self.pulse.get_sink_by_name(sink_name) # type: ignore
                    self.pulse.mute(sink, not sink.mute) # type: ignore
                    self._update_volume_ui()
            except Exception as e:
                print(f"[Error] PulseAudio toggle mute failed: {e}")

    # --- BRIGHTNESS LOGIC ---
    def _update_brightness_ui(self):
        try:
            out = exec_shell_command("brightnessctl -m").strip().split(',') # type: ignore
            if len(out) >= 4:
                percent = int(out[3].replace('%', ''))
                if abs(self.bri_scale.get_value() - percent) > 1: self.bri_scale.set_value(percent)
                icons = ["󱩎", "󱩐", "󱩓", "󰛨"]
                idx = 0
                if percent > 25: idx = 1
                if percent > 50: idx = 2
                if percent > 75: idx = 3
                self.bri_icon.set_label(icons[idx])
                self.bri_scale.set_tooltip_text(f"{percent}%")
        except: pass

    def on_bri_change(self, scale):
        val = int(scale.get_value())
        if val < 5: val = 5
        exec_shell_command(f"brightnessctl s {val}%")

    # --- KEYBOARD LOGIC ---
    def _update_kbd_ui(self):
        try:
            with open(f"/sys/class/leds/{self.kbd_device}/brightness", 'r') as f:
                val = int(f.read().strip())
                if self.kbd_scale.get_value() != val: self.kbd_scale.set_value(val)
        except: pass

    def on_kbd_change(self, scale):
        val = int(round(scale.get_value()))
        if val > self.kbd_max: val = self.kbd_max
        if val < 0: val = 0
        exec_shell_command(f"brightnessctl -d {self.kbd_device} s {val}")

    # --- NETWORK LOGIC ---
    def _update_network_ui(self):
        try:
            stats = psutil.net_if_stats()
            active_iface = None
            for iface, stat in stats.items():
                if stat.isup and iface != "lo":
                    active_iface = iface
                    if "wlan" in iface or "wi" in iface: break 
            
            has_internet = check_internet()
            if active_iface:
                if has_internet:
                    self.net_icon.set_label("󰤨")
                    self.net_label.set_label(f"Connected ({active_iface})")
                    self.net_label.get_style_context().remove_class("error")
                else:
                    self.net_icon.set_label("󰤢")
                    self.net_label.set_label(f"No Internet ({active_iface})")
                    self.net_label.get_style_context().add_class("error")
            else:
                self.net_icon.set_label("󰤯")
                self.net_label.set_label("Disconnected")
        except: self.net_label.set_label("Net Error")

    def spawn_nmtui(self, btn):
        try: GLib.spawn_command_line_async("kitty -e nmtui")
        except: pass

# --- NOTIFICATION ROW ---
class NotificationRow(Gtk.EventBox):
    def __init__(self, app_name, summary, body, time_str, image_pixbuf, icon_name, on_close_callback):
        super().__init__()
        self.set_visible_window(False)
        self.on_close_callback = on_close_callback
        self.is_pinned = False; self.is_text_interaction = False
        self.has_body = bool(body and body.strip())
        self.offset_x = 0.0; self.velocity_x = 0.0; self.is_animating = False

        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("enter-notify-event", self.on_hover_enter)
        self.connect("leave-notify-event", self.on_hover_leave)
        self.connect("button-press-event", self.on_row_clicked)

        self.drag_gesture = Gtk.GestureDrag.new(self)
        self.drag_gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        self.drag_gesture.connect("drag-begin", self.on_drag_begin)
        self.drag_gesture.connect("drag-update", self.on_drag_update)
        self.drag_gesture.connect("drag-end", self.on_drag_end)

        self.overlay = Overlay(style_classes="notification-row", visible=True)
        self.add(self.overlay)
        self.content_layout = Box(orientation="h", spacing=10)
        self.overlay.add(self.content_layout)

        self.icon_box = Box(v_align="start", style_classes="notif-icon-box")
        pixel_size = 48
        image_widget = Gtk.Image()
        if image_pixbuf:
            w, h = image_pixbuf.get_width(), image_pixbuf.get_height()
            if w > 128 or h > 128: image_pixbuf = image_pixbuf.scale_simple(pixel_size, pixel_size, GdkPixbuf.InterpType.BILINEAR)
            image_widget.set_from_pixbuf(image_pixbuf)
        else:
            clean_icon = icon_name.replace("file://", "") if icon_name else ""
            if clean_icon and os.path.exists(clean_icon):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(clean_icon, pixel_size, pixel_size, True)
                    image_widget.set_from_pixbuf(pixbuf)
                except: image_widget.set_from_icon_name("dialog-information", Gtk.IconSize.DIALOG)
            elif clean_icon:
                image_widget.set_from_icon_name(clean_icon, Gtk.IconSize.DIALOG)
                image_widget.set_pixel_size(pixel_size)
            else:
                image_widget.set_from_icon_name("dialog-information", Gtk.IconSize.DIALOG)
                image_widget.set_pixel_size(pixel_size)
        self.icon_box.add(image_widget)
        self.content_layout.add(self.icon_box)

        self.text_box = Box(orientation="v", spacing=4, h_expand=True)
        header = Box(orientation="h", spacing=10)
        app_label = Label(label=app_name, style_classes="notif-app", h_align="start")
        app_label.set_ellipsize(Pango.EllipsizeMode.END)
        app_label.set_max_width_chars(18)
        header.add(app_label)
        header.add(Label(label=time_str, style_classes="notif-time", h_align="start"))
        self.text_box.add(header)
        
        self.summary_lbl = Label(label=summary, justification="left", style_classes="notif-summary", h_align="start")
        self.summary_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.summary_lbl.set_max_width_chars(26)
        self.summary_lbl.set_selectable(True)
        self.summary_lbl.connect("button-press-event", self.on_text_press)
        self.summary_lbl.connect("button-release-event", self.on_text_release)
        self.text_box.add(self.summary_lbl)
        
        self.body_revealer = Revealer(transition_type="slide-down", transition_duration=250, child_revealed=False)
        self.body_lbl = Label(label=body, justification="left", style_classes="notif-body", h_align="start")
        self.body_lbl.set_line_wrap(True)
        self.body_lbl.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.body_lbl.set_max_width_chars(28) 
        self.body_lbl.set_selectable(True)
        self.body_lbl.connect("button-press-event", self.on_text_press)
        self.body_lbl.connect("button-release-event", self.on_text_release)
        self.body_revealer.add(self.body_lbl)
        self.text_box.add(self.body_revealer)
        if self.has_body: self.body_revealer.set_visible(True)
        else: self.body_revealer.set_visible(False)
        self.content_layout.add(self.text_box)

        self.close_btn = Button(label="✕", style_classes="notif-close-btn", h_align="end", v_align="start", on_clicked=lambda *_: self.start_dismiss_animation())
        self.overlay.add_overlay(self.close_btn)
        self.show_all()
        self.body_revealer.set_reveal_child(False)

    def update_content(self, summary, body, time_str, image_pixbuf, icon_name):
        self.summary_lbl.set_label(summary)
        if body and body.strip():
            self.body_lbl.set_label(body); self.has_body = True; self.body_revealer.set_visible(True)
        else:
            self.has_body = False; self.body_revealer.set_reveal_child(False); self.body_revealer.set_visible(False)
        self.update_visuals(image_pixbuf, icon_name)

    def update_visuals(self, image_pixbuf, icon_name):
        pixel_size = 48
        if image_pixbuf:
            w, h = image_pixbuf.get_width(), image_pixbuf.get_height()
            if w > 128 or h > 128: image_pixbuf = image_pixbuf.scale_simple(pixel_size, pixel_size, GdkPixbuf.InterpType.BILINEAR)
            self.image_widget.set_from_pixbuf(image_pixbuf)
        else:
            clean_icon = icon_name.replace("file://", "") if icon_name else ""
            if clean_icon and os.path.exists(clean_icon):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(clean_icon, pixel_size, pixel_size, True)
                    self.image_widget.set_from_pixbuf(pixbuf)
                except: self.image_widget.set_from_icon_name("dialog-information", Gtk.IconSize.DIALOG)
            elif clean_icon:
                self.image_widget.set_from_icon_name(clean_icon, Gtk.IconSize.DIALOG)
                self.image_widget.set_pixel_size(pixel_size)
            else:
                self.image_widget.set_from_icon_name("dialog-information", Gtk.IconSize.DIALOG)
                self.image_widget.set_pixel_size(pixel_size)

    def on_row_clicked(self, w, e):
        if e.button != 1: return False
        self.is_pinned = not self.is_pinned
        ctx = self.overlay.get_style_context()
        if self.is_pinned: ctx.add_class("pinned"); self.body_revealer.set_reveal_child(True) if self.has_body else None
        else: ctx.remove_class("pinned")
        return False

    def on_text_press(self, w, e): self.is_text_interaction = True; return False 
    def on_text_release(self, w, e): self.is_text_interaction = False; return False
    def on_drag_begin(self, g, x, y): self.is_animating = False; self.velocity_x = 0; g.set_state(Gtk.EventSequenceState.DENIED) if self.is_text_interaction else None
    def on_drag_update(self, g, x, y): 
        if x > 0: self.offset_x = float(x); self.overlay.set_margin_start(int(self.offset_x))
    def on_drag_end(self, g, x, y): 
        self.velocity_x = x * 0.1 
        if x > 100: self.start_dismiss_animation()
        else: self.start_snap_back_animation()

    def start_snap_back_animation(self):
        self.is_animating = True; tension = 0.6; friction = 0.75
        def _step():
            if not self.is_animating: return False
            self.velocity_x += (0 - self.offset_x) * tension; self.velocity_x *= friction
            self.offset_x += self.velocity_x
            if abs(self.offset_x) < 0.5 and abs(self.velocity_x) < 0.5:
                self.offset_x = 0; self.overlay.set_margin_start(0); self.is_animating = False; return False 
            self.overlay.set_margin_start(max(0, int(self.offset_x))); return True
        GLib.timeout_add(16, _step)

    def start_dismiss_animation(self):
        self.is_animating = True
        if self.velocity_x < 5: self.velocity_x = 20
        def _step():
            if not self.is_animating: return False
            self.velocity_x *= 1.15; self.offset_x += self.velocity_x
            if self.offset_x > 500: self.close_notification(); return False
            self.overlay.set_margin_start(max(0, int(self.offset_x))); return True
        GLib.timeout_add(16, _step)

    def on_hover_enter(self, w, e): 
        if self.has_body: self.body_revealer.set_reveal_child(True)
    def on_hover_leave(self, w, e): 
        if e.detail == Gdk.NotifyType.INFERIOR or self.is_pinned: return
        self.body_revealer.set_reveal_child(False)
    def close_notification(self): self.on_close_callback(self); self.destroy()


class SystemDashboard(Window):
    def __init__(self, dnd_callback, count_callback, **kwargs):
        super().__init__(
            title="SystemDashboard",
            anchor="top right", layer="top", margin="5px 10px 0px 0px", exclusivity="none",
            visible=False, all_visible=False, name="SYS_DASH", **kwargs
        )
        self.dnd_callback = dnd_callback
        self.count_callback = count_callback # Callback to update the bar icon
        self.active_rows = {} 

        self.root_box = Box(orientation="v", spacing=0, name="NOTIF_ROOT", style_classes="dashboard-root")
        
        # 1. HEADER
        self.header_box = Box(orientation="h", spacing=10, style_classes="dashboard-header")
        self.title_label = Label(label="Dashboard", style_classes="dashboard-title", h_align="start", v_align="center")
        self.header_box.pack_start(self.title_label, True, True, 0)

        self.dnd_btn = Button(style_classes="dashboard-dnd-btn", h_align="end", v_align="center", on_clicked=self.on_dnd_click)
        self.dnd_label = Label(label="󰂚", style_classes="txt-icon") 
        self.dnd_btn.add(self.dnd_label)
        self.header_box.pack_end(self.dnd_btn, False, False, 0)
        
        self.clear_btn = Button(label="Clear", style_classes="dashboard-clear-btn", on_clicked=self.clear_all_notifications, h_align="end", v_align="center")
        self.header_box.pack_end(self.clear_btn, False, False, 0)
        self.root_box.add(self.header_box)

        # 2. QUICK SETTINGS
        self.quick_settings = QuickSettings()
        self.root_box.add(self.quick_settings)

        # 3. NOTIFICATIONS
        self.notif_header = Label(label="Notifications", style_classes="section-title", h_align="start")
        self.root_box.add(self.notif_header)

        self.scroll = ScrolledWindow(min_content_size=(360, 300), max_content_size=(360, 600), propagate_natural_width=True, propagate_natural_height=True, name="NOTIF_SCROLL")
        self.vbox = Box(orientation="v", spacing=10, style_classes="notification-list")
        self.placeholder = Label(label="No Notifications", style_classes="notif-placeholder", visible=True)
        self.vbox.add(self.placeholder)
        self.scroll.add(self.vbox)
        self.root_box.add(self.scroll)

        self.add(self.root_box)
        self.show_all()
        self.hide()
        
        self.connect("map", lambda *_: self.quick_settings.refresh())

    # --- API ---
    def get_vol(self):
        return self.quick_settings.get_vol()

    def update_dnd_icon(self, is_dnd):
        if is_dnd: self.dnd_label.set_label("󰂛"); self.dnd_label.get_style_context().add_class("dnd-active")
        else: self.dnd_label.set_label("󰂚"); self.dnd_label.get_style_context().remove_class("dnd-active")

    # --- UNIFIED CHECK_EMPTY METHOD (Fixes the Error) ---
    def check_empty(self):
        """
        1. Checks if list is empty -> Toggles placeholder.
        2. Calculates count -> Updates NotificationIndicator via callback.
        """
        children = [c for c in self.vbox.get_children() if isinstance(c, NotificationRow)]
        count = len(children)
        
        # Toggle Placeholder
        if count == 0: self.placeholder.set_visible(True)
        else: self.placeholder.set_visible(False)
        
        # Update Bar Indicator
        if self.count_callback:
            self.count_callback(count)

    def add_or_update_notification(self, app_name, summary, body, time_str, image_pixbuf, icon_name, replaces_id, sync_tag):
        HISTORY_LIMIT = 25
        
        if self.placeholder.get_visible(): self.placeholder.set_visible(False)

        track_key = None
        if sync_tag: track_key = f"sync:{sync_tag}"
        elif replaces_id and int(replaces_id) > 0: track_key = f"id:{replaces_id}"

        if track_key and track_key in self.active_rows:
            try:
                row = self.active_rows[track_key]
                row.update_content(summary, body, time_str, image_pixbuf, icon_name)
                self.vbox.reorder_child(row, 0)
                return
            except: del self.active_rows[track_key]

        row = NotificationRow(app_name, summary, body, time_str, image_pixbuf, icon_name, on_close_callback=self.on_row_closed)
        row._track_key = track_key
        if track_key: self.active_rows[track_key] = row
        
        self.vbox.pack_start(row, False, False, 0)
        self.vbox.reorder_child(row, 0)
        row.show_all()

        children = self.vbox.get_children()
        if len(children) > HISTORY_LIMIT:
            # Because you reorder new items to 0, the oldest is the last item
            oldest_widget = children[-1]
            
            # Cleanup the tracking dictionary to prevent memory leaks
            if hasattr(oldest_widget, "_track_key") and oldest_widget._track_key:
                if oldest_widget._track_key in self.active_rows:
                    del self.active_rows[oldest_widget._track_key]

            self.vbox.remove(oldest_widget)
            oldest_widget.destroy()
        
        # Update count immediately
        self.check_empty()

    def on_row_closed(self, row):
        if hasattr(row, '_track_key') and row._track_key and row._track_key in self.active_rows:
            del self.active_rows[row._track_key]
        
        # Update count after animation ensures it's gone
        GLib.idle_add(self.check_empty)

    def clear_all_notifications(self, *args):
        children = [c for c in self.vbox.get_children() if isinstance(c, NotificationRow)]
        if not children: return
        
        delay = 0
        for child in children:
            GLib.timeout_add(delay, child.start_dismiss_animation)
            delay += 50
        
        # Clear tracking dict
        self.active_rows.clear()

    def on_dnd_click(self, btn): self.dnd_callback()