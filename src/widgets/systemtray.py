from loguru import logger
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.button import Button
from fabric.system_tray.service import (
    SystemTray as SystemTrayService,
    SystemTrayItem as SystemTrayItemService,
)
import gi
from gi.repository import GLib, Gtk # type:ignore

watcher: SystemTrayService | None = None


def get_tray_watcher() -> SystemTrayService:
    global watcher
    if not watcher:
        watcher = SystemTrayService()
    return watcher


class SystemTrayItem(Button):
    def __init__(self, item: SystemTrayItemService, icon_size: int, **kwargs):
        super().__init__(visible=False, **kwargs)
        self._item = item
        self._icon_size = icon_size
        self._image = Image()
        self.set_image(self._image)

        self._item.changed.connect(self.do_update_properties)
        self.connect("button-press-event", self.on_clicked)

        self.do_update_properties()

    def do_update_properties(self, *_):
        # Safety check for invalid items
        if hasattr(self._item, "__len__") and len(self._item) < 1:
            self.set_visible(False)
            return
        
        pixbuf = self._item.get_preferred_icon_pixbuf(self._icon_size)
        icon_name = self._item.icon_name
        
        should_show = False
        
        # LOGIC: Only show if we have a valid image source
        if pixbuf is not None:
            self._image.set_from_pixbuf(pixbuf)
            should_show = True
        elif icon_name:
            self._image.set_from_icon_name(icon_name, self._icon_size)
            # Verify icon exists in theme to avoid empty buttons
            if Gtk.IconTheme.get_default().has_icon(icon_name):
                should_show = True
            
        if should_show:
            if not self.is_visible():
                self.set_visible(True)
        else:
            if self.is_visible():
                self.set_visible(False)

        # Tooltip logic
        tooltip = self._item.tooltip
        self.set_tooltip_markup(
            tooltip.description or 
            tooltip.title or 
            (self._item.title.title() if self._item.title else None) or 
            "Unknown"
        )
        return

    def on_clicked(self, _, event):
        match event.button:
            case 1:
                try:
                    self._item.activate_for_event(event)
                except Exception as e:
                    logger.warning(f"[SystemTray] Activate failed: {e}")
            case 3:
                self._item.invoke_menu_for_event(event)


class SystemTray(Box):
    def __init__(self, icon_size: int = 16, **kwargs):
        # Handle style classes
        style_classes = kwargs.pop("style_classes", [])
        if isinstance(style_classes, str):
            style_classes = [style_classes]
        if "systray" not in style_classes:
            style_classes.append("systray")

        super().__init__(visible=False, style_classes=style_classes, spacing=5, **kwargs)
        
        self._icon_size = icon_size
        self._items: dict[str, SystemTrayItem] = {}

        self._watcher = get_tray_watcher()
        self._watcher.connect("item-added", self.on_item_added)
        self._watcher.connect("item-removed", self.on_item_removed)
        
        for identifier in self._watcher.items.keys():
            self.on_item_added(None, identifier)
            
        # IMPORTANT: Schedule the visibility check to run AFTER the bar initializes
        # This prevents the parent window's "show_all" from overriding our hidden state.
        GLib.idle_add(self._update_visibility)

    def _update_visibility(self):
        """
        Check if ANY child is actually visible. 
        If no children are visible, hide the Box.
        """
        any_visible = False
        children = self.get_children()
        
        for child in children:
            if child.get_visible():
                any_visible = True
                break

        if any_visible:
            if not self.is_visible():
                self.set_visible(True)
        else:
            if self.is_visible():
                self.set_visible(False)
        
        return False  # Return False to stop GLib.idle_add from repeating

    def _on_child_notify_visible(self, *_):
        # When a child changes visibility, re-check the parent immediately
        self._update_visibility()

    def on_item_added(self, _, item_identifier: str):
        item = self._watcher.items.get(item_identifier)
        if not item or not item.get_id():
            return

        if item_identifier in self._items:
            return

        item_button = SystemTrayItem(item, self._icon_size)
        item_button.connect("notify::visible", self._on_child_notify_visible)
        
        self.add(item_button)
        self._items[item.identifier] = item_button
        
        # Re-check visibility
        self._update_visibility()

    def on_item_removed(self, _, item_identifier):
        item_button = self._items.get(item_identifier)
        if not item_button:
            return

        self.remove(item_button)
        self._items.pop(item_identifier)
        
        self._update_visibility()


__all__ = ["SystemTray", "SystemTrayItem", "get_tray_watcher"]