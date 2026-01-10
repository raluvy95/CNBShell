import json
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf # type: ignore

from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.hyprland.service import Hyprland
from fabric.utils import bulk_connect

class HyprlandActiveWindowWithIcon(Box):
    def __init__(self, icon_size=16, height=24, **kwargs):
        super().__init__(
            spacing=8,
            style_classes="active-window",
            size=(-1, height),
            **kwargs
        )

        # 1. Widgets (Icon Only)
        self.icon_size = icon_size
        self.icon = Image(size=self.icon_size)
        
        # No Label, just the Icon
        self.children = [self.icon]

        # 2. Setup "The Guard"
        self.setup_icon_protection()

        # 3. Connection
        self.connection = Hyprland()
        bulk_connect(
            self.connection,
            {
                "event::activewindow": self.on_active_window,
                "event::closewindow": self.on_close_window,
            },
        )

        if self.connection.ready:
            self.do_initialize()
        else:
            self.connection.connect("event::ready", lambda *_: self.do_initialize())

    def setup_icon_protection(self):
        self.gtk_settings = Gtk.Settings.get_default()
        self.icon_theme = Gtk.IconTheme.get_default()
        
        self.good_theme_name = self.gtk_settings.props.gtk_icon_theme_name
        
        current_path = self.icon_theme.get_search_path()
        required_paths = [
            "/usr/share/icons", 
            "/usr/local/share/icons",
            os.path.expanduser("~/.local/share/icons"),
            os.path.expanduser("~/.icons")
        ]
        self.good_search_path = list(set(current_path + required_paths))
        
        self.enforce_icon_state("Initial Setup")

        self.gtk_settings.connect("notify::gtk-icon-theme-name", self.on_theme_changed)
        self.icon_theme.connect("changed", self.on_theme_changed)

    def enforce_icon_state(self, reason):
        self.icon_theme.set_search_path(self.good_search_path)
        current_name = self.gtk_settings.props.gtk_icon_theme_name
        if current_name != self.good_theme_name:
            print(f"[Auto-Fix] Reverting theme from '{current_name}' to '{self.good_theme_name}' (Reason: {reason})")
            self.gtk_settings.props.gtk_icon_theme_name = self.good_theme_name

    def on_theme_changed(self, *args):
        self.enforce_icon_state("Detected Interference")
        self.do_initialize()

    def do_initialize(self):
        try:
            resp = self.connection.send_command("j/activewindow").reply.decode()
            data = json.loads(resp)
            if not data:
                self.update_ui("")
            else:
                self.update_ui(data.get("class", ""))
        except:
            self.update_ui("")

    def on_active_window(self, _, event):
        if len(event.data) < 2: return
        self.update_ui(event.data[0])

    def on_close_window(self, _, event):
        self.do_initialize()

    def get_icon_name(self, win_class):
        if not win_class: return "desktop"
        cls = win_class.lower()
        mapping = {
            "code": "visual-studio-code",
            "code-url-handler": "visual-studio-code",
            "kitty": "kitty",
            "foot": "terminal",
            "terminal-ltr": "terminal",
            "alacritty": "Alacritty",
            "spotify": "spotify-client",
            "google-chrome": "google-chrome",
            "chromium": "chromium-browser",
            "discord": "discord",
            "steam-ltr": "steam",
            "thunar": "system-file-manager",
            "nautilus": "org.gnome.Nautilus",
            "org.gnome.Nautilus": "org.gnome.Nautilus"
        }
        return mapping.get(cls, win_class)

    def update_ui(self, win_class):
        self.icon.set_visible(True)

        # 1. Check for empty class (Desktop)
        if not win_class:
            self.icon.set_from_icon_name("desktop", self.icon_size)
            return

        # 2. Resolve Icon Name
        icon_name = self.get_icon_name(win_class)
        theme = Gtk.IconTheme.get_default()
        
        # Strategy A: Mapped name
        if theme.has_icon(icon_name) and icon_name is not None:
            self.icon.set_from_icon_name(icon_name, self.icon_size)
            return

        # Strategy B: Lowercase class
        if theme.has_icon(win_class.lower()):
            self.icon.set_from_icon_name(win_class.lower(), self.icon_size)
            return

        # Strategy C: Exact class
        if theme.has_icon(win_class):
            self.icon.set_from_icon_name(win_class, self.icon_size)
            return
            
        # Strategy D: Fallback
        self.icon.set_from_icon_name("application-x-executable", self.icon_size)