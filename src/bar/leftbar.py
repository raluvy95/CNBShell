from fabric.widgets.box import Box
from fabric.hyprland.widgets import HyprlandActiveWindow
from fabric.utils import FormattedString, truncate

from src.bar.workspace import Workspace
from src.bar.hyprlang import Hyprlang
from src.bar.cava_widget import CavaWidget

class LeftBar(Box):
    def __init__(self):
        super().__init__(
        orientation="h",
        h_align="start",
        children=[
            Workspace(),
            Hyprlang(),
            CavaWidget(
                    bars=10,               # Number of bars
                    height=20,             # Height in pixels
                    spacing=3,             # Space between bars
                    color=(0.8, 0.8, 0.8, 1) # RGBA: Light Grey
            ),
            HyprlandActiveWindow(
                formatter=FormattedString(
                    "{'Desktop' if not win_title else truncate(win_class, 20)}",
                    truncate=truncate,
                ),
                style_classes="wintitle"
            )
        ],
        spacing=10,
        name="LEFT")
    