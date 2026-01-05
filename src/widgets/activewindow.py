import json
import os # Don't forget this!
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf # type: ignore

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from fabric.hyprland.service import Hyprland
from fabric.utils import truncate, bulk_connect

class HyprlandActiveWindowWithIcon(Box):
    def __init__(self, icon_size=16, **kwargs):
        super().__init__(spacing=8,
                         style_classes="active-window",
                         **kwargs)

        # 1. Widgets
        self.icon_size = icon_size
        self.icon = Image(size=self.icon_size)
        self.label = Label(label="Desktop", style_classes="wintitle")
        self.children = [self.icon, self.label]

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

    # I wish Steam won't pollute Gtk environment variable
    def setup_icon_protection(self):
        """
        Saves the working state and creates a listener to revert 
        changes if Steam tries to break them.
        """
        self.gtk_settings = Gtk.Settings.get_default()
        self.icon_theme = Gtk.IconTheme.get_default()
        
        # 1. Capture the 'Good' State (User's preferred theme)
        self.good_theme_name = self.gtk_settings.props.gtk_icon_theme_name
        
        # 2. Define the robust Search Path
        current_path = self.icon_theme.get_search_path()
        required_paths = [
            "/usr/share/icons", 
            "/usr/local/share/icons",
            os.path.expanduser("~/.local/share/icons"),
            os.path.expanduser("~/.icons")
        ]
        self.good_search_path = list(set(current_path + required_paths))
        
        # 3. Apply immediately
        self.enforce_icon_state("Initial Setup")

        # 4. Watch for Steam interference (The Fix)
        # If Steam changes the theme name, this triggers:
        self.gtk_settings.connect("notify::gtk-icon-theme-name", self.on_theme_changed)
        # If Steam resets the icon object, this triggers:
        self.icon_theme.connect("changed", self.on_theme_changed)

    def enforce_icon_state(self, reason):
        # Force the path
        self.icon_theme.set_search_path(self.good_search_path)
        
        # Force the theme name (if it drifted)
        current_name = self.gtk_settings.props.gtk_icon_theme_name
        if current_name != self.good_theme_name:
            print(f"[Auto-Fix] Reverting theme from '{current_name}' to '{self.good_theme_name}' (Reason: {reason})")
            self.gtk_settings.props.gtk_icon_theme_name = self.good_theme_name

    def on_theme_changed(self, *args):
        """
        Triggered when Steam launches and tries to mess up GTK.
        """
        self.enforce_icon_state("Detected Interference")
        # Force a UI refresh to redraw any broken icons immediately
        self.do_initialize()

    def do_initialize(self):
        try:
            resp = self.connection.send_command("j/activewindow").reply.decode()
            data = json.loads(resp)
            if not data:
                self.update_ui("", "")
            else:
                self.update_ui(data.get("class", ""), data.get("title", ""))
        except:
            self.update_ui("", "")

    def on_active_window(self, _, event):
        if len(event.data) < 2: return
        self.update_ui(event.data[0], event.data[1])

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

    def update_ui(self, win_class, win_title):
        # 1. Text
        if not win_class:
            self.label.set_label("Desktop")
            self.icon.set_from_icon_name("desktop", self.icon_size)
            return
        
        self.label.set_label(truncate(str(win_title), 40))
        self.icon.set_visible(True)

        # 2. Icon Lookup
        icon_name = self.get_icon_name(win_class)
        theme = Gtk.IconTheme.get_default()
        
        # Strategy A
        if theme.has_icon(icon_name) and icon_name is not None:
            self.icon.set_from_icon_name(icon_name, self.icon_size)
            return

        # Strategy B
        if theme.has_icon(win_class.lower()):
            self.icon.set_from_icon_name(win_class.lower(), self.icon_size)
            return

        # Strategy C
        if theme.has_icon(win_class):
            self.icon.set_from_icon_name(win_class, self.icon_size)
            return
            
        # Strategy D
        self.icon.set_from_icon_name("application-x-executable", self.icon_size)