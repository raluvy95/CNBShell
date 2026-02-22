# src/utils/config.py (or wherever ConfigParser is)
import toml_rs
from src.utils.getrootdir import get_project_root

class ConfigParser:
    def __init__(self):
        self.path = get_project_root() / "shell.toml"
        if not self.path.exists():
            self.path.touch(exist_ok=True)
        self.reload()

    def reload(self):
        """Reloads the TOML file into memory."""
        with open(self.path, "rb") as f:
            self.conf = toml_rs.load(f)
        
        # Expose sections as properties for easy access
        self.clock = self.conf.get("clock", {'format': "%x %H:%M"})
        self.theme = self.conf.get("theme", {}) # defaults to empty dict if missing
        self.weather = self.conf.get("weather", {'enable': True})
        self.sysmon = self.conf.get("sysmon", {})
        self.general = self.conf.get("general", {})

# Global Instance
SHELL_CONFIG = ConfigParser()