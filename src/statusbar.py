from fabric.widgets.centerbox import CenterBox
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box

from src.config import SHELL_CONFIG
from src.bar.leftbar import LeftBar
from src.bar.rightbar import RightBar
from src.popup.datetime import ClickableDateTime
from src.popup.calendar import Calendar

class ClockPopup(Window):
    def __init__(self):
        super().__init__(
            anchor="top",
            layer="top",
            visible=False,
            title="CNBSHELL-popup",
            margin="5px 0px 0px 0px",
            all_visible=False,
            exclusivity="none",
            name="POPUP"
        )

        self.content_box = Box(
            orientation="h",
            spacing=10,
            children= [
                Calendar()
            ]
        )

        self.children = self.content_box

class StatusBar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            layer="top",
            anchor="left top right",
            exclusivity="auto",
            visible=False,
            **kwargs
        )

        self.clockmenu = ClockPopup()
        self.datetime = ClickableDateTime(self.on_click,
                                    (SHELL_CONFIG.clock['format'], "%A %d %B %Y %T"),
                                    style_classes="calendar")
        self.box = CenterBox(
            orientation="h",
            start_children=LeftBar(),
            center_children=self.datetime,
            end_children=RightBar(),
            name="ROOT"
        )

        # ensure the CenterBox receives an iterable of children
        self.children = self.box
        self.show_all()
        
    def on_click(self, _, event):
        if event.button == 1:
            self.toggle_menu()

    def toggle_menu(self):
        if self.clockmenu.is_visible():
            self.clockmenu.hide()
        else:
            self.clockmenu.show_all()