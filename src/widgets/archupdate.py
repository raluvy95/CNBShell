from fabric.widgets.button import Button
from fabric.widgets.wayland import WaylandWindow as Window

from fabric.widgets.label import Label
from fabric.widgets.box import Box
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib #type:ignore
import json
from src.utils.checkupdate import checkupdate_main
import threading
from typing import TypedDict, List, Optional

class PackageUpdate(TypedDict):
    name: str
    old_version: str
    new_version: str
    # Optional in case a line fails to parse correctly and returns 'raw'
    raw: Optional[str]

class UpdateWin(Window):
    def __init__(self):
        
        # Main container - Renamed to avoid GObject property collision
        self.main_box = Box(
            orientation="vertical",
            spacing=10,
            style_classes="main-container"
        )
        
        self.header = Label(
            label="Pending Updates",
            style_classes="header-label"
        )
        
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_min_content_height(400)
        self.scrolled_window.set_min_content_width(350)
        self.scrolled_window.add(self.listbox)
        
        self.main_box.add(self.header)
        self.main_box.pack_start(self.scrolled_window, True, True, 0)
        
        # Initialize the window WITH the content already inside
        super().__init__(
            title="System Updates",
            name="update-window",
            style_classes="update-window",
            visible=False,
            all_visible=True,
            layer="top",
            anchor="top right",
            margin="10px 10px 0px 0px",
            child=self.main_box  # <-- This stops Fabric from freaking out!
        )
        self.set_default_size(350, 400)

    def update_list(self, json_data):
        """Populates the listbox with update information."""
        # Clear existing rows
        for child in self.listbox.get_children():
            self.listbox.remove(child)
            
        if not json_data:
            empty_label = Label(label="Your CachyOS is up to date! 🐧", style_classes="header-label")
            self.listbox.add(empty_label)
        else:
            for pkg in json_data:
                row = self._create_row(pkg)
                self.listbox.add(row)
        
        self.show_all()

    def _create_row(self, pkg: dict) -> Gtk.ListBoxRow:
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        row_box.get_style_context().add_class("update-row")
        row_box.set_margin_start(10)
        row_box.set_margin_end(10)
        row_box.set_margin_top(5)
        row_box.set_margin_bottom(5)
        
        name = Label(label=pkg.get("name", "Unknown"), style_classes="pkg-name")
        name.set_halign(Gtk.Align.START)
        
        version = Label(label=f"{pkg.get('old_version')} → {pkg.get('new_version')}", style_classes="pkg-version")
        version.set_halign(Gtk.Align.END)
        version.set_hexpand(True)
        
        row_box.add(name)
        row_box.add(version)
        
        row = Gtk.ListBoxRow()
        row.add(row_box)
        return row


class ArchUpdate(Button):
    def __init__(self, **kwargs):
        super().__init__(style_classes="archupdate")
        self.connect('clicked', self.on_click)
        self.set_label("󰣇")
        self.on_init()
        self.update_window = None
        self.data: Optional[List[PackageUpdate]] = None
    
    def refresh_ui_with_json(self, json_str):
        decoded_data: List[PackageUpdate] = json.loads(json_str)
        
        self.data = decoded_data
        if len(self.data) == 0:
            self.set_label(f"󰣇")
            self.set_tooltip_text("No updates avaliable")
            return False
        # Update your labels/lists here
        self.set_label(f"󰣇 {len(self.data)}")
        self.set_tooltip_text(f"Found {len(self.data)} updates!")
        return False
    
    # GTK signals pass the widget that emitted them, so we must accept it
    def on_click(self, button=None):
        if not self.update_window:
            self.update_window = UpdateWin()
            
        if self.update_window.get_visible():
            self.update_window.hide()
        else:
            self.update_window.update_list(self.data)
            # .present() shows the window and forces Wayland to give it focus
            self.update_window.present()

    def on_init(self, widget=None):
        # This starts in the background immediately
        self.set_label("")
        self.set_tooltip_text("Checking for updates...")

        def wait_for_result():
            future = checkupdate_main(with_aur=False)
            result = future.result() # This blocks the POOL thread, not the UI
            GLib.idle_add(self.refresh_ui_with_json, result)

        threading.Thread(target=wait_for_result, daemon=True).start()