from fabric.widgets.box import Box

from src.bar.systemtray import SystemTray
from src.bar.privacy import PrivacyIndicator
from src.bar.systemmonitor import SystemMonitor
from src.bar.notification import NotificationIndicator

class RightBar(Box):
    def __init__(self):
        super().__init__(
        orientation="h",
        h_align="end",
        spacing=10,
        children=[
            SystemMonitor(),
            PrivacyIndicator(),
            SystemTray(icon_size=16, style_classes="systray", spacing=5),
            NotificationIndicator()
        ],
        name="RIGHT")
        