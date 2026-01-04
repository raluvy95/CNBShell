from gi.repository import GLib # type: ignore
from fabric.widgets.label import Label

class ScrollingLabel(Label):
    def __init__(self, max_chars=16, scroll_interval=500, fixed_height=24, **kwargs):
        # Initialize parent
        super().__init__(**kwargs)
        
        self.max_chars = max_chars
        self.scroll_interval = scroll_interval
        self.full_text = ""
        self.display_text = ""
        self.scroll_source_id = None
        
        # 1. Enforce specific CSS to remove extra padding
        current_style = kwargs.get("style", "")
        base_style = "padding: 0px; margin: 0px;" 
        self.set_style(base_style + current_style)

        # 2. Force a fixed height if provided (e.g., 24px for a bar)
        if fixed_height:
            self.set_size_request(-1, fixed_height) # -1 = auto width, fixed height

    def set_scrolling_text(self, text):
        """Sets the text and starts scrolling if needed."""
        self.stop_scrolling()
        self.full_text = text

        if len(text) > self.max_chars:
            self.display_text = text + " " * 2
            self.set_label(self.display_text[:self.max_chars])
            self.scroll_source_id = GLib.timeout_add(self.scroll_interval, self._scroll_step)
        else:
            self.set_label(text)

    def _scroll_step(self):
        if not self.display_text:
            return False
        self.display_text = self.display_text[1:] + self.display_text[0]
        self.set_label(self.display_text[:self.max_chars])
        return True

    def stop_scrolling(self):
        if self.scroll_source_id:
            GLib.source_remove(self.scroll_source_id)
            self.scroll_source_id = None