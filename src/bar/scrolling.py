from gi.repository import GLib # type:ignore
from fabric.widgets.label import Label

class ScrollingLabel(Label):
    def __init__(self, max_chars=12, scroll_interval=500, **kwargs):
        super().__init__(**kwargs)
        self.max_chars = max_chars
        self.scroll_interval = scroll_interval
        self.full_text = ""
        self.display_text = ""
        self.scroll_source_id = None

    def set_scrolling_text(self, text):
        """Sets the text and starts scrolling if needed."""
        # Clean up previous timer
        self.stop_scrolling()

        self.full_text = text

        if len(text) > self.max_chars:
            # Add spacing between the end and start of the loop
            self.display_text = text + " " * 2
            # Set initial slice
            self.set_label(self.display_text[:self.max_chars])
            # Start timer
            self.scroll_source_id = GLib.timeout_add(self.scroll_interval, self._scroll_step)
        else:
            self.set_label(text)

    def _scroll_step(self):
        """Rotates the text by one character."""
        if not self.display_text:
            return False
            
        # Rotate: move first char to the end
        self.display_text = self.display_text[1:] + self.display_text[0]
        # Update the visible label
        self.set_label(self.display_text[:self.max_chars])
        return True # Keep timer running

    def stop_scrolling(self):
        """Stops the GLib timer."""
        if self.scroll_source_id:
            GLib.source_remove(self.scroll_source_id)
            self.scroll_source_id = None