import sys
from loguru import logger

from src.utils.getrootdir import get_project_root

logger.remove()
logger.add(sys.stderr, level="WARNING")

from fabric import Application
from fabric.utils import monitor_file, get_relative_path, exec_shell_command, logger
from src.statusbar import StatusBar
from src.utils.threads import run_in_thread
from src.utils.colors import Colors

BASE_DIR = get_project_root()
MAIN_STYLE_DIR = BASE_DIR / "styles/main.scss"
DIST_STYLE_DIR = BASE_DIR / "dist/main.css"


def process_and_apply_css(app: Application):
    """Compile and apply CSS in background thread."""
    from gi.repository import GLib # type: ignore

    @run_in_thread
    def _compile():
        logger.info(f"{Colors.INFO}[Main] Compiling CSS")
        output = exec_shell_command(
            f"sass {MAIN_STYLE_DIR} {DIST_STYLE_DIR} --no-source-map"
        )

        if output == "":
            logger.info(f"{Colors.INFO}[Main] CSS applied")
            GLib.idle_add(
                lambda: app.set_stylesheet_from_file(str(DIST_STYLE_DIR))
            )
        else:
            logger.exception(f"{Colors.ERROR}[Main]Failed to compile sass!")
            logger.exception(f"{Colors.ERROR}[Main] {output}")

            GLib.idle_add(lambda: app.set_stylesheet_from_string(""))

    _compile()


class CNBShell(Application):
    def __init__(self):
        super().__init__("CNBShell", StatusBar())

        style_monitor = monitor_file(get_relative_path("styles"))
        style_monitor.connect("changed", lambda *_: process_and_apply_css(self))
        process_and_apply_css(self)
        
        self.run()

if __name__ == "__main__":
    CNBShell()

