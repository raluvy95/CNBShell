import glob
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from gi.repository import GLib # type: ignore

class KeyboardStatus(Box):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.numlock_label = Label(label="󰎤", visible=True)
        self.add(self.numlock_label)

        self.led_path: str | None = self.find_numlock_path()

        if self.led_path:
            print(self.led_path)
            GLib.timeout_add(150, self.check_status)
        else:
            print("No NumLock LED found.")

    def find_numlock_path(self) -> str | None:
        # Find the first file ending in '::numlock/brightness'
        paths = glob.glob("/sys/class/leds/*::numlock/brightness")
        return paths[0] if paths else None

    def check_status(self):
        if not self.led_path:
            return False # Stop polling if path is lost

        try:
            with open(self.led_path, 'r') as f:
                content = f.read().strip()
                is_on = (content == '1')
                
                self.numlock_label.set_text("󰎤" if is_on else "󰎦")
                    
        except Exception as e:
            print(f"Error reading LED: {e}")
            
        return True # Return True to keep the loop running