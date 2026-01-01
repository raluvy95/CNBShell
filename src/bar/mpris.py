import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk # type:ignore
from fabric.widgets.box import Box
from fabric.widgets.label import Label
# Import the ScrollingLabel we defined above

from src.bar.scrolling import ScrollingLabel
from src.bar.cava_widget import CavaWidget

class MprisPlayerBox(Box):
    def __init__(self, **kwargs):
        super().__init__(
            visible=False, 
            orientation="h", 
            spacing=8,
            name="MPRIS", 
            **kwargs
        )

        self.cava_widget = CavaWidget()
        self.cava_widget.toggle_mode()
        
        # USE CUSTOM SCROLLING LABEL HERE
        self.title_label = ScrollingLabel()

        self.add(self.cava_widget)
        self.add(Label(
            label="󰎇",
            style_classes="icon-label"
        ))
        self.add(self.title_label)

        self.player_proxy = None
        self.current_player_name = None
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        self.scan_for_players()

        self.bus.signal_subscribe(
            "org.freedesktop.DBus",
            "org.freedesktop.DBus",
            "NameOwnerChanged",
            "/org/freedesktop/DBus",
            None,
            Gio.DBusSignalFlags.NONE,
            self.on_dbus_name_changed,
            None
        )

    # ... [scan_for_players and on_list_names_result match previous code] ...
    def scan_for_players(self):
        self.bus.call(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "ListNames",
            None, None, Gio.DBusCallFlags.NONE, -1, None,
            self.on_list_names_result
        )

    def on_list_names_result(self, connection, res):
        try:
            result = connection.call_finish(res)
            names = result.unpack()[0]
            for name in names:
                if name.startswith("org.mpris.MediaPlayer2."):
                    self.connect_to_player(name)
                    return
        except Exception as e:
            print(f"[MprisBox] Error listing names: {e}")

    def on_dbus_name_changed(self, connection, sender_name, object_path, interface_name, signal_name, parameters, user_data):
        name, old_owner, new_owner = parameters.unpack()
        if not name.startswith("org.mpris.MediaPlayer2."):
            return

        if new_owner and not old_owner:
            self.connect_to_player(name)
        elif old_owner and not new_owner:
            if name == self.current_player_name:
                self.disconnect_player()
                self.scan_for_players()

    def disconnect_player(self):
        """Clean up connection and stop scrolling."""
        self.current_player_name = None
        self.player_proxy = None
        
        # STOP SCROLLING TO SAVE RESOURCES
        self.title_label.stop_scrolling()
        
        GLib.idle_add(self.set_visible, False)

    def connect_to_player(self, bus_name):
        if self.current_player_name == bus_name:
            return

        try:
            self.player_proxy = Gio.DBusProxy.new_sync(
                self.bus,
                Gio.DBusProxyFlags.NONE,
                None,
                bus_name,
                "/org/mpris/MediaPlayer2",
                "org.mpris.MediaPlayer2.Player",
                None
            )
            self.current_player_name = bus_name
            self.player_proxy.connect("g-properties-changed", self.on_properties_changed)
            
            self.update_title()
            GLib.idle_add(self.set_visible, True)
            
        except Exception as e:
            print(f"[MprisBox] Failed to connect: {e}")

    def on_properties_changed(self, proxy, changed_properties, invalidated_properties):
        metadata = changed_properties.lookup_value("Metadata", GLib.VariantType("a{sv}"))
        if metadata:
            self.update_title_from_metadata(metadata)

    def update_title(self):
        if not self.player_proxy: 
            return
        metadata = self.player_proxy.get_cached_property("Metadata")
        if metadata:
            self.update_title_from_metadata(metadata)

    def update_title_from_metadata(self, metadata_variant):
        try:
            data = metadata_variant.unpack()
            title = data.get("xesam:title")
            
            if title:
                if isinstance(title, GLib.Variant):
                    title = title.unpack()
                text = str(title).strip()
            else:
                text = "Unknown"

            # USE CUSTOM SETTER
            GLib.idle_add(self.title_label.set_scrolling_text, text)
            
        except Exception as e:
            print(f"[MprisBox] Metadata error: {e}")