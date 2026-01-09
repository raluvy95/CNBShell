import threading
import urllib3
from fabric.widgets.label import Label
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.button import Button
from fabric.widgets.scrolledwindow import ScrolledWindow  # Added ScrolledWindow
from gi.repository import GLib # type: ignore

# Assuming your types exist in src.types.wttr
from src.types.wttr import WEATHER_SYMBOL, WEATHER_SYMBOL_GTK, WWO_CODE, WttrInResponse, HourlyForecast

def format_time(time_str: str) -> str:
    """Converts '300' to '03:00'"""
    return f"{time_str.zfill(4)[:2]}:{time_str.zfill(4)[2:]}"

class HourlyWeather(Box):
    def __init__(self, data: HourlyForecast):
        super().__init__(orientation="v", spacing=4, style_classes="hourly-card")
        
        time_label = Label(format_time(data["time"]), style_classes="hourly-time")
        
        icon = Image(size=32)
        # Fallback to a generic icon if code mapping fails
        icon_name = WEATHER_SYMBOL_GTK.get(WWO_CODE.get(data["weatherCode"], "113"), "weather-clear")
        icon.set_from_icon_name(icon_name)
        
        temp_label = Label(f"{data['tempC']}°", style_classes="hourly-temp")
        
        self.children = [time_label, icon, temp_label]

class CurrentWeather(Box):
    def __init__(self, data: WttrInResponse):
        super().__init__(orientation="v", spacing=8, style_classes="current-weather")
        
        current = data["current_condition"][0]
        today = data["weather"][0]
        astronomy = today["astronomy"][0]

        # --- Top Section: Big Temp & Icon ---
        top_box = Box(orientation="h", spacing=12, h_align="center")
        
        icon_name = WEATHER_SYMBOL_GTK.get(WWO_CODE.get(current["weatherCode"], "113"), "weather-clear")
        big_icon = Image(size=48, icon_name=icon_name, icon_size=48)
        
        temp_box = Box(orientation="v")
        temp_label = Label(f"{current['temp_C']}°C", style_classes="big-temp")
        feels_like = Label(f"Feels like {current['FeelsLikeC']}°C", style_classes="feels-like")
        temp_box.children = [temp_label, feels_like]
        
        top_box.children = [big_icon, temp_box]
        
        # --- Stats Grid (Wind, Moon, Snow) ---
        stats_box = Box(orientation="h", spacing=16, h_align="center", style_classes="stats-row")
        
        # Helper to make small stats column
        def make_stat(icon, text, subtext=""):
            return Box(orientation="v", children=[
                Label(icon, style_classes="stat-icon"),
                Label(text, style_classes="stat-text"),
                Label(subtext, style_classes="stat-sub") if subtext else Box()
            ])

        # Wind
        wind_txt = f"{current['windspeedKmph']}km/h {current['winddir16Point']}"
        stats_box.add(make_stat("", wind_txt, "Wind")) # Nerd font icon for wind

        # Moon
        stats_box.add(make_stat("", astronomy['moon_phase'], "Moon"))

        # Daily Snow/Rain Logic (Max probability of the day)
        # We iterate hourly data to find max chances
        max_rain = max(int(h['chanceofrain']) for h in today['hourly'])
        max_snow = max(int(h['chanceofsnow']) for h in today['hourly'])
        
        if max_snow > 0 or float(today['totalSnow_cm']) > 0.0:
            snow_txt = f"{max_snow}%"
            if float(today['totalSnow_cm']) > 0:
                snow_txt += f" ({today['totalSnow_cm']}cm)"
            stats_box.add(make_stat("", snow_txt, "Snow"))
        elif max_rain > 0:
            stats_box.add(make_stat("", f"{max_rain}%", "Rain"))

        self.children = [top_box, stats_box]

class WeatherWindow(Window):
    def __init__(self, parent, data: WttrInResponse | None = None):
        super().__init__(
            name="WEATHER",
            layer="top",
            anchor="top right",
            margin="10px 10px 0px 0px", # Added margin right for aesthetics
            visible=False,
            all_visible=False,
            exclusive=True # Optional: keeps it above other windows
        )

        self.parent = parent
        
        # Main container
        self.box = Box(
            orientation="v",
            style_classes="weather-view",
            spacing=12,
            size=(340, -1) # Fixed size helps with scrolling
        )
        self.add(self.box)

        # Render immediately if data exists, else show loader
        if data:
            self.render_data(data)
        else:
            self.render_loading()

    def render_loading(self):
        self.box.children = [
            Box(v_align="center", h_align="center", children=[Label("Loading Weather...")])
        ]

    def render_data(self, data: WttrInResponse):
        # 1. Clear previous content
        self.box.children = []

        # 2. Add Current Weather Section
        self.box.add(CurrentWeather(data))

        # 3. Add Divider
        self.box.add(Box(style_classes="divider", size=(300, 1)))

        # 4. Hourly Forecast inside ScrolledWindow
        scroll = ScrolledWindow(
            min_content_size=(300, 120),
            max_content_size=(300, 120),
            h_expand=True,
            v_expand=False,
        )
        
        # Horizontal box for hourly items
        hourly_box = Box(orientation="h", spacing=12)
        
        # Add today's hourly data
        # Note: Wttr.in sometimes returns 3-hour intervals. 
        # If you want smooth scrolling, ensure enough items exist.
        for hourly in data["weather"][0]["hourly"]:
            hourly_box.add(HourlyWeather(hourly))
            
        scroll.add(hourly_box)
        self.box.add(scroll)

    def on_data_update(self, data: WttrInResponse):
        # Called when window is open and new data arrives
        self.render_data(data)

class Weather(Button):
    def __init__(self):
        super().__init__(label=" -°C", style_classes="weather")
        
        self.data: None | WttrInResponse = None
        self.window: WeatherWindow | None = None
        
        self.connect("clicked", self.toggle_window)
        
        # Initial update
        self.update()
        # Schedule update every hour
        GLib.timeout_add_seconds(3600, self.update)

    def update(self):
        thread = threading.Thread(target=self.fetch_weather, daemon=True)
        thread.start()
        return True

    def fetch_weather(self):
        try:
            # Added &tp=1 to get true hourly data (optional, remove if you want 3h intervals)
            resp = urllib3.request("GET", "https://wttr.in?format=j1", timeout=30)
            
            if resp.status == 200:
                w_data: WttrInResponse = resp.json()
                GLib.idle_add(self.handle_data, w_data)
            else:
                print(f"Failed to fetch weather: {resp.status}")
        except Exception as e:
            print(f"Error updating weather: {e}")

    def toggle_window(self, *_):
        if self.window:
            self.window.hide()
            self.window.destroy()
            self.window = None
        else:
            # Pass existing data directly to constructor
            self.window = WeatherWindow(self, self.data)
            self.window.show_all()

    def handle_data(self, data: WttrInResponse):
        self.data = data
        
        # Update the button label
        current = data["current_condition"][0]
        icon = WEATHER_SYMBOL.get(WWO_CODE.get(current["weatherCode"], "113"), "")
        self.set_label(f"{icon} {current['temp_C']}°C")
        
        # If window is open, update it live
        if self.window:
            self.window.on_data_update(data)