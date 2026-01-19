import gi
import urllib.parse
import os
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, GdkPixbuf # type:ignore
from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.image import Image
from fabric.widgets.wayland import WaylandWindow as Window
from src.widgets.scrolling import ScrollingLabel
from src.widgets.cava_widget import CavaWidget

from PIL import Image as PILImage, ImageFilter

class MprisViewerWin(Window):
    def __init__(self, parent_widget, **kwargs):
        super().__init__(
            title="MprisViewer",
            anchor="top left", layer="top", margin="5px 0px 0px 50px", exclusivity="none",
            visible=False, all_visible=False, name="MPRIS_VIEWER", **kwargs
        )

        self.parent_widget = parent_widget
        self.metadata = {}
        self.length = 0
        self.dragging = False
        
        # --- UI ELEMENTS ---
        self.cover_art = Image(name="cover-art", size=80)
        
        self.title_label = ScrollingLabel(max_chars=24) 
        self.artist_label = Label(label="-", style_classes="artist", h_align="start")
        self.album_label = Label(label="", style_classes="album", h_align="start")

        text_box = Box(
            orientation="v", 
            spacing=2,
            children=[self.title_label, self.artist_label, self.album_label]
        )

        # Progress Bar (Seek)
        self.position_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.position_scale.set_draw_value(False)
        self.position_scale.set_range(0, 100)
        self.position_scale.set_margin_top(4)
        
        # FIX: Connect interactions to prevent slider fighting
        self.position_scale.connect("change-value", self.on_seek)
        self.position_scale.connect("button-press-event", self.on_drag_start)
        self.position_scale.connect("button-release-event", self.on_drag_end)
        
        self.time_label = Label(label="00:00 / 00:00", style_classes="time-label")

        # Controls
        self.btn_prev = Button(label="󰒮", on_clicked=lambda *_: self.send_command("Previous"))
        self.btn_play = Button(label="", on_clicked=lambda *_: self.send_command("PlayPause"))
        self.btn_next = Button(label="󰒭", on_clicked=lambda *_: self.send_command("Next"))

        controls_box = Box(
            orientation="h",
            spacing=15,
            h_align="center",
            children=[self.btn_prev, self.btn_play, self.btn_next]
        )

        # Layout
        top_section = Box(
            orientation="h", 
            spacing=10,
            children=[self.cover_art, text_box]
        )

        self.main_box = Box(
            orientation="v",
            spacing=8,
            style_classes="popup-frame",
            children=[
                top_section,
                Box(orientation="v", spacing=2, children=[self.position_scale, self.time_label]),
                controls_box
            ]
        )
        
        self.add(self.main_box)
        self.show_all()
        self.set_visible(False)

        self.timeout_id = None

    def on_show(self):
        self.update_status()
        self.update_position()
        if self.timeout_id is None:
            self.timeout_id = GLib.timeout_add(1000, self.update_position)

    def on_hide(self):
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None

    # --- FIX: Drag Handlers ---
    def on_drag_start(self, *_):
        self.dragging = True
        return False # Propagate event

    def on_drag_end(self, *_):
        self.dragging = False
        return False # Propagate event

    def update_ui(self, metadata):
        self.metadata = metadata
        
        title = str(self.unwrap(metadata.get("xesam:title", "Unknown")))
        artists = self.unwrap(metadata.get("xesam:artist", ["Unknown"]))
        if isinstance(artists, list):
            artists = ", ".join(artists)
        elif isinstance(artists, GLib.Variant): 
            artists = str(artists.unpack())
        album = str(self.unwrap(metadata.get("xesam:album", "")))

        self.title_label.set_scrolling_text(title)
        self.artist_label.set_text(str(artists))
        self.album_label.set_text(album)

        art_url = str(self.unwrap(metadata.get("mpris:artUrl", "")))
        self.load_cover(art_url)

        # Update Length
        self.length = int(self.unwrap(metadata.get("mpris:length", 0)))
        if self.length > 0:
            self.position_scale.set_range(0, self.length)
        
        self.update_status()
        self.update_position()

    def update_status(self):
        if not self.parent_widget.player_proxy:
            return

        try:
            status = self.parent_widget.player_proxy.get_cached_property("PlaybackStatus")
            if status:
                status_str = status.unpack()
                if status_str == "Playing":
                    self.btn_play.set_label("")
                else:
                    self.btn_play.set_label("")
        except Exception:
            pass

    def update_position(self):
        """Polls position and length via direct DBus call and updates slider."""
        if not self.parent_widget.player_proxy:
            return True

        try:
            # CHANGE: Use GetAll to fetch Metadata, Status, and Position in one go.
            # This ensures that if the 'length' was missed during the track change signal,
            # it self-corrects within 1 second.
            res = self.parent_widget.bus.call_sync(
                self.parent_widget.current_player_name,
                "/org/mpris/MediaPlayer2",
                "org.freedesktop.DBus.Properties",
                "GetAll",
                GLib.Variant("(s)", ("org.mpris.MediaPlayer2.Player",)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            
            properties = res.unpack()[0] # Unpack dictionary {str: variant}

            # 1. Update Position
            pos_val = 0
            if "Position" in properties:
                pos_val = properties["Position"]
                # Some players wrap it in a Variant, others don't when unpacked from GetAll
                if isinstance(pos_val, GLib.Variant):
                    pos_val = pos_val.unpack()

            # 2. Update Status (Play/Pause Icon)
            if "PlaybackStatus" in properties:
                status = properties["PlaybackStatus"]
                if isinstance(status, GLib.Variant):
                    status = status.unpack()
                
                if status == "Playing":
                    self.btn_play.set_label("")
                else:
                    self.btn_play.set_label("")

            # 3. Update Length (The Fix for your glitch)
            # We check the metadata specifically for the length property
            if "Metadata" in properties:
                meta = properties["Metadata"]
                if isinstance(meta, GLib.Variant):
                    meta = meta.unpack()
                
                # Extract length safely
                new_length = 0
                if "mpris:length" in meta:
                    val = meta["mpris:length"]
                    if isinstance(val, GLib.Variant):
                        val = val.unpack()
                    new_length = int(val)
                
                # If length changed (track change), update the slider range immediately
                if new_length > 0 and new_length != self.length:
                    self.length = new_length
                    self.position_scale.set_range(0, self.length)

            # 4. Update Slider Visuals
            # Only update slider visually if user IS NOT dragging it
            if not self.dragging:
                self.position_scale.set_value(pos_val)
            
            cur_str = self.format_time(pos_val)
            tot_str = self.format_time(self.length)
            self.time_label.set_text(f"{cur_str} / {tot_str}")
            
        except Exception as e:
            # Fallback for display
            print(f"Polling Error: {e}")
            tot_str = self.format_time(self.length)
            self.time_label.set_text(f"--:-- / {tot_str}")
        
        return True

    def on_seek(self, scale, scroll_type, value):
        if self.parent_widget.player_proxy:
             track_id = self.unwrap(self.metadata.get("mpris:trackid", ""))
             try:
                 self.parent_widget.player_proxy.call_sync(
                     "SetPosition",
                     GLib.Variant("(ox)", (track_id, int(value))),
                     Gio.DBusCallFlags.NONE,
                     -1,
                     None
                 )
             except Exception as e:
                 print(f"Seek failed: {e}")

    def send_command(self, command):
        if self.parent_widget.player_proxy:
            try:
                self.parent_widget.player_proxy.call_sync(
                    command, None, Gio.DBusCallFlags.NONE, -1, None
                )
                self.update_status()
            except Exception as e:
                print(f"Command {command} failed: {e}")

    def load_cover(self, url):
        # 1. Reset Defaults
        if not url:
            self.cover_art.set_from_icon_name("audio-x-generic", Gtk.IconSize.DIALOG)
            self.main_box.set_style("background-image: none; background-color: #1e1e2e;") 
            return

        if url.startswith("file://"):
            path = urllib.parse.unquote(url[7:])
            
            if os.path.exists(path):
                # 2. Set the sharp cover art (foreground)
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 80, 80, True)
                    self.cover_art.set_from_pixbuf(pixbuf)
                except:
                    pass

                # 3. Generate Optimized Blur
                try:
                    blur_path = "/tmp/fabric_mpris_blur.jpg"
                    
                    with PILImage.open(path) as img:
                        img.thumbnail((300, 300))
                        
                        # FIX: Convert to RGB to support JPEG format
                        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                            img = img.convert("RGB")
                        
                        # Apply Blur
                        blurred = img.filter(ImageFilter.GaussianBlur(20))
                        blurred.save(blur_path, quality=80) 

                    # 4. Set CSS
                    css = f"""
                        background-image: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url("file://{blur_path}");
                        background-size: cover;
                        background-position: center;
                        background-repeat: no-repeat;
                        border-radius: 12px;
                    """
                    self.main_box.set_style(css)
                except Exception as e:
                    print(f"Blur Error: {e}")

    def unwrap(self, val):
        if isinstance(val, GLib.Variant):
            return val.unpack()
        return val

    # --- FIX: Hours support ---
    def format_time(self, microseconds):
        if not microseconds or microseconds < 0:
            return "00:00"
        
        seconds = int(microseconds / 1000000)
        
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        
        return f"{minutes:02d}:{seconds:02d}"

# --- MprisPlayerBox ---
class MprisPlayerBox(EventBox):
    def __init__(self, **kwargs):
        super().__init__(
            events=["button-press", "enter-notify-event", "leave-notify-event"],
            visible=False, 
            name="MPRIS", 
            tooltip_text="Click to open",
            **kwargs
        )

        self.children_box = Box(
            orientation="h",
            spacing=8,
            style_classes="mpris-inner"
        )

        self.cava_widget = CavaWidget()
        self.cava_widget.toggle_mode()

        self.win = None
        
        self.title_label = ScrollingLabel()
        self.icon_label = Label(label="󰎇", style_classes="icon-label")

        self.children_box.add(self.cava_widget)
        self.children_box.add(self.icon_label)
        self.children_box.add(self.title_label)
        self.add(self.children_box)

        self.player_proxy = None
        self.current_player_name = None
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        self.connect('button-press-event', self.toggle_win)
        
        self.bus.signal_subscribe(
             "org.freedesktop.DBus", "org.freedesktop.DBus", "NameOwnerChanged",
             "/org/freedesktop/DBus", None, Gio.DBusSignalFlags.NONE,
             self.on_dbus_name_changed, None
        )

        self.scan_for_players()

    # Lazy loading
    def toggle_win(self, _, __):
        # I am not sure this will clean up memory
        if self.win is not None:
            self.win.on_hide() 
            self.win.close()
            self.win.destroy()
            self.win = None
            
        else:
            self.win = MprisViewerWin(parent_widget=self)
            self.win.show_all()
            self.win.on_show()
            
            # If we have cached metadata, push it to the new window immediately
            if self.player_proxy:
                metadata = self.player_proxy.get_cached_property("Metadata")
                if metadata:
                    # We need to unwrap strictly for the window
                    data = metadata.unpack()
                    self.win.update_ui(data)

    def scan_for_players(self):
        self.bus.call("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "ListNames", None, None, Gio.DBusCallFlags.NONE, -1, None, self.on_list_names_result)

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
        self.current_player_name = None
        self.player_proxy = None
        self.title_label.stop_scrolling()
        if self.win is not None:
            # close win
            self.toggle_win(None, None)
        self.set_visible(False)

    def connect_to_player(self, bus_name):
        if self.current_player_name == bus_name: return
        try:
            self.player_proxy = Gio.DBusProxy.new_sync(self.bus, Gio.DBusProxyFlags.NONE, None, bus_name, "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player", None)
            self.current_player_name = bus_name
            self.player_proxy.connect("g-properties-changed", self.on_properties_changed)
            self.update_title()
            GLib.idle_add(self.set_visible, True)
        except Exception as e:
            print(f"[MprisBox] Failed to connect: {e}")

    def on_properties_changed(self, proxy, changed_properties, invalidated_properties):
        metadata = changed_properties.lookup_value("Metadata", GLib.VariantType("a{sv}"))
        if metadata: 
            self.update_from_metadata(metadata)
        status = changed_properties.lookup_value("PlaybackStatus", GLib.VariantType("s"))
        if status and self.win is not None:
            GLib.idle_add(self.win.update_status)

    def update_title(self):
        if not self.player_proxy: return
        metadata = self.player_proxy.get_cached_property("Metadata")
        if metadata: self.update_from_metadata(metadata)

    def update_from_metadata(self, metadata_variant):
        try:
            data = metadata_variant.unpack()
            title = data.get("xesam:title")
            if isinstance(title, GLib.Variant): title = title.unpack()
            text = str(title).strip() if title else "Unknown"
            
            GLib.idle_add(self.title_label.set_scrolling_text, text)
            if self.win is not None:
                GLib.idle_add(self.win.update_ui, data)
        except Exception as e:
            print(f"[MprisBox] Metadata error: {e}")