# src/utils/theme_manager.py
from pathlib import Path
from threading import Timer
from typing import Optional  # Added for type hinting
from gi.repository import GLib # type: ignore
from fabric import Application
from fabric.utils import exec_shell_command, logger
from src.utils.colors import Colors
from src.utils.threads import run_in_thread

_debounce_timer = None

def apply_theme(
    app: Application, 
    theme_name: str, 
    accent: Optional[str],  # Allow None
    style_src: Path, 
    dist_path: Path
):
    """
    Pure logic: Receives data -> Updates Bridge -> Compiles -> Applies.
    Does NOT read config files.
    """
    global _debounce_timer
    
    if _debounce_timer:
        _debounce_timer.cancel()

    @run_in_thread
    def _task():
        try:
            # 1. UPDATE BRIDGE (_vars.scss)
            
            # Logic: If accent is provided (and not empty), override it.
            # Otherwise, just load the theme as-is.
            if accent and accent.strip():
                forward_line = f'@forward "patterns/{theme_name}" with ($accent: {accent} !default);'
            else:
                forward_line = f'@forward "patterns/{theme_name}";'

            vars_content = f"""
// Generated from SHELL_CONFIG
{forward_line}
"""
            vars_file = style_src / "_vars.scss"
            
            # Smart Write (IO Optimization)
            if not vars_file.exists() or vars_file.read_text() != vars_content:
                with open(vars_file, "w") as f:
                    f.write(vars_content)

            # 2. COMPILE SASS
            main_scss = style_src / "main.scss"
            output = exec_shell_command(
                f"sass {main_scss} {dist_path} --no-source-map --load-path={style_src}"
            )

            # 3. VERIFY & APPLY
            if dist_path.exists():
                css_data = dist_path.read_text().strip()
                if css_data:
                    GLib.idle_add(lambda: app.set_stylesheet_from_file(str(dist_path)))
                    # Log differently based on whether accent was used
                    if accent:
                        logger.info(f"{Colors.INFO}[Theme] Applied: {theme_name} ({accent})")
                    else:
                        logger.info(f"{Colors.INFO}[Theme] Applied: {theme_name} (Default Accent)")
                else:
                    logger.warning(f"{Colors.WARNING}[Theme] Compiled CSS is empty.")
            else:
                logger.error(f"{Colors.ERROR}[Theme] Sass failed:\n{output}")

        except Exception as e:
            logger.exception(f"{Colors.ERROR}[Theme] Update failed: {e}")

    _debounce_timer = Timer(0.2, _task)
    _debounce_timer.start()