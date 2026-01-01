from fabric.hyprland.widgets import HyprlandLanguage
from fabric.utils import FormattedString
from fabric.utils import exec_shell_command
from src.utils.languages import EMOJI_LANGUAGES

class Hyprlang(HyprlandLanguage):
    def __init__(self, **kwargs):
        super().__init__(
            formatter=FormattedString(
                "{get_emoji(language)}",
                get_emoji=self.get_emoji_and_update_tooltip
            ),
            name="hyprlang",
            **kwargs
        )
        
        self.connect('clicked', lambda *_: self.on_click())

    def get_emoji_and_update_tooltip(self, lang):   

        try:
            code = lang[:2].upper()
            emoji = EMOJI_LANGUAGES[code].value
        except (KeyError, AttributeError, IndexError):
            emoji = lang

        self.set_tooltip_text(lang[:3].upper())

        return emoji

    def on_click(self):
        exec_shell_command("hyprctl switchxkblayout current next > /dev/null")


    
