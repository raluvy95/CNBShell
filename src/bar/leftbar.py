from fabric.widgets.box import Box

from src.bar.workspace import Workspace
from src.bar.activewindow import HyprlandActiveWindowWithIcon
from src.bar.mpris import MprisPlayerBox

class LeftBar(Box):
    def __init__(self):
        super().__init__(
        orientation="h",
        h_align="start",
        children=[
            Workspace(),
            HyprlandActiveWindowWithIcon(),
            MprisPlayerBox()
        ],
        spacing=10,
        name="LEFT")
    