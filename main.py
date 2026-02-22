import sys
import setproctitle
from argparse import ArgumentParser
from gi.repository import Gio # type:ignore

setproctitle.setproctitle("cnbshell")

from src.config import SHELL_CONFIG  # <--- YOUR CONFIG CLASS
from loguru import logger

if SHELL_CONFIG.general.get("debug", False):
    logger.debug("Enabled debugging info")
else:
    logger.remove()
    logger.add(sys.stderr, level="WARNING")

from fabric import Application
from fabric.utils import monitor_file
from src.statusbar import StatusBar
from src.utils.getrootdir import get_project_root

# Import the centralized config and the dumb theme applicator
from src.utils.theme_manager import apply_theme

# --- CONSTANTS ---
BASE_DIR = get_project_root()
STYLE_SRC = BASE_DIR / "styles"
DIST_CSS = BASE_DIR / "dist/main.css"
SHELL_CONFIG_FILE = BASE_DIR / "shell.toml"

parser = ArgumentParser()
parser.add_argument("-v", "--version", action="store_true", help="Show version")
__version__ = "1.0.0"

class CNBShell(Application):
    def __init__(self):
        super().__init__("CNBShell", StatusBar())

        # 1. Monitor shell.toml
        self.config_monitor = monitor_file(str(SHELL_CONFIG_FILE))
        self.config_monitor.connect("changed", self.on_config_change)

        # 2. Monitor SCSS
        self.style_monitor = monitor_file(str(STYLE_SRC))
        self.style_monitor.connect("changed", self.on_style_change)

        # Initial Load
        self.trigger_theme_update()
        
        self.run()

    def trigger_theme_update(self):
        """Pull fresh data from SHELL_CONFIG and apply it."""
        # Defaults exist here if config is missing keys
        t_name = SHELL_CONFIG.theme.get("name", "catppuccin-mocha")
        t_accent = SHELL_CONFIG.theme.get("accent")
        t_transparency = SHELL_CONFIG.theme.get("transparency", False);
        
        apply_theme(self, t_name, t_accent, t_transparency, STYLE_SRC, DIST_CSS)

    def on_config_change(self, monitor, file, other_file, event_type):
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            # CRITICAL: Reload the config object first!
            SHELL_CONFIG.reload() 
            logger.info("[Config] Reloaded SHELL_CONFIG from disk")
            self.trigger_theme_update()

    def on_style_change(self, monitor, file, other_file, event_type):
        filename = file.get_basename()
        if filename in ["_vars.scss", "main.css", ".fuse_hidden"] or filename.startswith("."):
            return

        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            # Just re-apply existing config logic
            self.trigger_theme_update()

if __name__ == "__main__":
    args = parser.parse_args()
    if args.version:
        print(f"CNBShell v{__version__}")
    else:
        CNBShell()