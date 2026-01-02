from fabric.widgets.box import Box

from src.widgets.systemtray import SystemTray
from src.widgets.privacy import PrivacyIndicator
from src.widgets.hyprlang import Hyprlang
from src.widgets.systemmonitor import SystemMonitor
from src.widgets.notification import NotificationIndicator

class RightBar(Box):
    def __init__(self):
        super().__init__(
        orientation="h",
        h_align="end",
        spacing=10,
        children=[
            SystemMonitor(),
            PrivacyIndicator(),
            Hyprlang(),
            SystemTray(icon_size=16, style_classes="systray", spacing=5),
            NotificationIndicator()
        ],
        name="RIGHT")
        