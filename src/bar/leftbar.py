from fabric.widgets.box import Box

from src.bar.workspace import Workspace
from src.bar.activewindow import HyprlandActiveWindowWithIcon
from src.bar.cava_widget import CavaWidget

class LeftBar(Box):
    def __init__(self):
        super().__init__(
        orientation="h",
        h_align="start",
        children=[
            Workspace(),
            HyprlandActiveWindowWithIcon(),
            CavaWidget()
        ],
        spacing=10,
        name="LEFT")
    