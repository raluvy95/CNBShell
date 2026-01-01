import json
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

        # 2. Connection
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
        """
        The Magic Fix: Manually map 'Windows Class' -> 'Icon Name'
        Add any app that is missing an icon to this list.
        """
        if not win_class: return "desktop"
        
        # 1. Normalize
        cls = win_class.lower()
        
        # 2. The Map (Add your missing apps here)
        mapping = {
            "code": "visual-studio-code",
            "code-url-handler": "visual-studio-code",
            "kitty": "terminal",
            "foot": "terminal", 
            "alacritty": "Alacritty",
            "spotify": "spotify-client",
            "google-chrome": "google-chrome",
            "chromium": "chromium-browser",
            "discord": "discord",
            "thunar": "system-file-manager",
            "nautilus": "org.gnome.Nautilus",
            "org.gnome.nautilus": "org.gnome.Nautilus"
        }
        
        return mapping.get(cls, win_class)

    def update_ui(self, win_class, win_title):
        # 1. Text
        if not win_class:
            self.label.set_label("Desktop")
            self.icon.set_from_icon_name("desktop", self.icon_size)
            return
        
        self.label.set_label(truncate(str(win_class).capitalize(), 40))
        self.icon.set_visible(True)

        # 2. Icon Lookup
        icon_name = self.get_icon_name(win_class)
        theme = Gtk.IconTheme.get_default()
        
        # Strategy A: Try the mapped name (e.g. 'visual-studio-code')
        if theme.has_icon(icon_name) and icon_name is not None:
            self.icon.set_from_icon_name(icon_name, self.icon_size)
            return

        # Strategy B: Try lowercased class (e.g. 'audacity')
        if theme.has_icon(win_class.lower()):
            self.icon.set_from_icon_name(win_class.lower(), self.icon_size)
            return

        # Strategy C: Try exact class (e.g. 'Audacity')
        if theme.has_icon(win_class):
            self.icon.set_from_icon_name(win_class, self.icon_size)
            return
            
        # Strategy D: Fallback
        self.icon.set_from_icon_name("application-x-executable", self.icon_size)