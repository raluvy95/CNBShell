from gi.repository import GLib # type: ignore
from fabric.widgets.label import Label
from fabric.widgets.box import Box

class ScrollingLabel(Label):
    def __init__(self, max_chars=28, scroll_interval=500, fixed_height=24, fixed_width=-1, **kwargs):
        super().__init__(**kwargs,
                         ellipsization="none",
                         style_classes="scroll-text",
                         v_align="center",
                         v_expand=False,
                         line_wrap=None,
                         max_chars_width=max_chars,
                         width_chars=max_chars, # Forces GTK size
                         size=[ fixed_width, fixed_height ])
        
        self.max_chars = max_chars
        self.set_width_chars(max_chars)
        self.set_max_width_chars(max_chars)
        self.set_ellipsize(3)
        self.scroll_interval = scroll_interval
        self.full_text = ""
        self.display_text = ""
        self.scroll_source_id = None

        self.set_yalign(0.5)
        self.set_xalign(0.0)


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