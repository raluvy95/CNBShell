import threading
import urllib3
from fabric.widgets.label import Label
from gi.repository import GLib # type: ignore

from src.types.wttr import WEATHER_SYMBOL, WWO_CODE, WttrInResponse

class Weather(Label):
    def __init__(self):
        super().__init__(label=" -°C", style_classes="weather")
        
        # Start the update loop
        self.update()
        
        # Schedule the update to run every 3600 seconds (1 hour)
        GLib.timeout_add_seconds(3600, self.update)

    def update(self):
        # run the network request in a separate thread
        thread = threading.Thread(target=self.fetch_weather, daemon=True)
        thread.start()
        
        # Return True so GLib keeps calling this function
        return True

    def fetch_weather(self):
        try:
            # This blocks, but now it's in a background thread
            resp = urllib3.request("GET", "https://wttr.in?format=j2", timeout=30)
            
            if resp.status == 200:
                w_data: WttrInResponse = resp.json()
                # Schedule the UI update on the main thread
                GLib.idle_add(self.handle_data, w_data)
            else:
                print(f"Failed to fetch weather: {resp.status}")
                
        except Exception as e:
            print(f"Error updating weather: {e}")

    def handle_data(self, data: WttrInResponse):
        current_data = data["current_condition"][0]
        nearest_area = data["nearest_area"][0]
        icon = ""
        try:
            icon = WEATHER_SYMBOL[WWO_CODE[current_data["weatherCode"]]]
        except KeyError:
            pass
        formatted_celsius = current_data["temp_C"] + "°C"
        self.set_text(f"{icon} {formatted_celsius}")
        # City name and country name
        self.set_tooltip_text(f"{nearest_area["areaName"][0]["value"]}, {nearest_area['country'][0]['value']}")