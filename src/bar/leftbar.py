from fabric.widgets.box import Box

from src.widgets.workspace import Workspace
from src.widgets.activewindow import HyprlandActiveWindowWithIcon
from src.widgets.mpris import MprisPlayerBox

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
    