from fabric.widgets.box import Box

from src.config import SHELL_CONFIG
from src.widgets.systemtray import SystemTray
from src.widgets.privacy import PrivacyIndicator
from src.widgets.hyprlang import Hyprlang
from src.widgets.notification import NotificationIndicator
from src.widgets.systemmonitor import SystemMonitor
from src.widgets.weather import Weather

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
            SystemTray(icon_size=16, spacing=5),
            *( [Weather()] if SHELL_CONFIG.weather.get("enable", True) else [] ),
            NotificationIndicator()
        ],
        name="RIGHT")
        