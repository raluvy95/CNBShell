import toml_rs
from src.utils.getrootdir import get_project_root

class ConfigParser:
    def __init__(self):
        p = get_project_root() / "shell.toml"
        if not p.exists():
            p.touch(exist_ok=True)
        with open(p, "rb") as f:
            self.conf = toml_rs.load(f)

        self.clock = self.conf.get("clock", {'format': "%x %H:%M"})


SHELL_CONFIG = ConfigParser()

__all__ = ["SHELL_CONFIG"]