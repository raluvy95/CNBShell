import gi
import time
from loguru import logger
from typing import Literal
from collections.abc import Iterable
from fabric.widgets.button import Button
from fabric.core.service import Property
from fabric.utils.helpers import invoke_repeater

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

class ClickableDateTime(Button):
    @Property(tuple[str, ...], "read-write")
    def formatters(self):
        return self._formatters

    @formatters.setter
    def formatters(self, value: str | Iterable[str]):
        if isinstance(value, (tuple, list)):
            self._formatters = tuple(value)
        elif isinstance(value, str):
            self._formatters = (value,)
        
        # Default safety fallback
        if not self._formatters:
            self._formatters = ("%I:%M %p", "%A", "%m-%d-%Y")
            
        # Reset index if out of bounds
        if self._current_index >= len(self._formatters):
            self._current_index = 0
            
        # Update immediately when format changes
        self.do_update_label()
        return

    @Property(int, "read-write")
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value: int):
        self._interval = value
        
        # Clean up old timer if it exists
        if self._repeater_id:
            GLib.source_remove(self._repeater_id)
            self._repeater_id = None
            
        # Start new timer
        # invoke_repeater returns the Source ID (int)
        self._repeater_id = invoke_repeater(self._interval, self.do_update_label)
        return

    def __init__(
        self,
        on_click,
        formatters: str | Iterable[str],
        interval: int = 1000,
        name: str | None = None,
        **kwargs,
    ):
        # Initialize parent first
        super().__init__(**kwargs) # Simplified for brevity, pass your args properly
        self._formatters = ("%H:%M",) # safe default before setter runs
        self._current_index = 0
        self._interval = interval
        self._repeater_id = None

        # 1. Connect signal safely
        if on_click:
            self.connect('clicked', lambda widget: on_click())

        # 2. Set formatters (triggering the setter)
        self.formatters = formatters

        # 3. Start the loop (triggering the setter)
        self.interval = interval
        
        # 4. Force one initial update so we don't wait 1000ms for the first text
        self.do_update_label()

    def do_format(self) -> str:
        if not self._formatters:
            return "..."
        safe_index = self._current_index % len(self._formatters)
        return time.strftime(self._formatters[safe_index])

    def do_update_label(self):
        # CRITICAL: This must return True for GLib.timeout_add to keep repeating.
        # If it returns None or False, the loop stops forever.
        try:
            new_label = self.do_format()

            self.set_label(new_label)
            return True 
        except Exception as e:
            logger.error(f"[DateTime] CRITICAL FAILURE: {e}")
            return True # Keep trying even if it fails once