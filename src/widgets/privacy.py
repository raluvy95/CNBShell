import json
import subprocess
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from gi.repository import GLib # type: ignore
from src.utils.threads import run_in_thread

class PrivacyIndicator(Box):
    def __init__(self, **kwargs):
        super().__init__(
            style_classes="privacyind",
            spacing=0,
            orientation="h",
            visible=False,
            **kwargs)
        
        self.set_no_show_all(True)

        self.mic_button = Button(
            name="privacy-mic",
            visible=False,
            label="󰍬"
        )
        
        self.screen_button = Button(
            name="privacy-screen",
            visible=False,
            label=""
        )

        self.add(self.screen_button)
        self.add(self.mic_button)

        self.poll_interval = 1500
        GLib.timeout_add(self.poll_interval, self.check_privacy_status)
        self.check_privacy_status()

    def check_privacy_status(self):
        self.fetch_privacy_status()
        return True

    @run_in_thread
    def fetch_privacy_status(self):
        try:
            result = subprocess.run(
                ["pw-dump"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                return

            data = json.loads(result.stdout)
            
            mic_apps = set()
            screen_apps = set()

            for obj in data:
                if obj.get("type") != "PipeWire:Interface:Node":
                    continue
                
                props = obj.get("info", {}).get("props", {})
                media_class = props.get("media.class", "")
                
                # --- BETTER NAME RESOLUTION ---
                # check these keys in order until we find a non-empty string
                app_name = (
                    props.get("application.name") or 
                    props.get("node.description") or 
                    props.get("node.nick") or 
                    props.get("media.name") or 
                    "Unknown Application"
                )

                # Check Microphone
                if media_class == "Stream/Input/Audio":
                    # Ignore the volume mixer itself and cava
                    if app_name not in ["pavucontrol", "WirePlumber", "PipeWire", "cava"]:
                         mic_apps.add(app_name)

                # Check Screenshare
                if media_class == "Stream/Input/Video":
                    screen_apps.add(app_name)

            GLib.idle_add(self.update_ui, mic_apps, screen_apps)

        except Exception as e:
            print(f"PrivacyIndicator Error: {e}")

    def update_ui(self, mic_apps, screen_apps):
        """
        Updates UI visibility and sets tooltips based on the apps found.
        """
        # --- Microphone Update ---
        is_mic_active = len(mic_apps) > 0
        if self.mic_button.get_visible() != is_mic_active:
            self.mic_button.set_visible(is_mic_active)
            if is_mic_active:
                self.mic_button.add_style_class("active")
            else:
                self.mic_button.remove_style_class("active")
        
        # Set Mic Tooltip
        if is_mic_active:
            self.mic_button.set_tooltip_text(f"{', '.join(mic_apps)}")

        # --- Screenshare Update ---
        is_screen_active = len(screen_apps) > 0
        if self.screen_button.get_visible() != is_screen_active:
            self.screen_button.set_visible(is_screen_active)
            if is_screen_active:
                self.screen_button.add_style_class("active")
            else:
                self.screen_button.remove_style_class("active")

        # Set Screen Tooltip
        if is_screen_active:
            self.screen_button.set_tooltip_text(f"{', '.join(screen_apps)}")

        # --- Container Visibility ---
        should_show = is_mic_active or is_screen_active
        if self.get_visible() != should_show:
            self.set_visible(should_show)
        
        return False