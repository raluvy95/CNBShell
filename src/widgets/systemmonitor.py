from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button # Imported Button
from loguru import logger
import psutil
import threading
import time

from gi.repository import GLib, Gtk  # type:ignore

from src.config import SHELL_CONFIG

# Inherit from Button to make the entire widget clickable
class SystemMonitor(Button):
    def __init__(self):
        self.cpu_label = Label("cpu")
        self.mem_label = Label("mem")
        self.temp_label = Label("temp", style_classes="temp-icon")
        self.fan_label = Label("fan")
        self.must_always_show_info = SHELL_CONFIG.sysmon.get("always_show_info", False)
        
        # We create a Box to hold the labels (preserving your original layout)
        content_box = Box(
            orientation="h",
            spacing=15,
            children=[
                self.cpu_label,
                self.mem_label,
                self.temp_label,
                self.fan_label
            ]
        )
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_valign(Gtk.Align.CENTER)

        # Initialize the Button with the Box as its child
        super().__init__(
            child=content_box,
            style_classes="sysmon",
            # This lambda handles the click event asynchronously
            on_clicked=self._on_clicked
        )

        threading.Thread(target=self.update_stats, daemon=True).start()

    def _on_clicked(self, _):
        execution = SHELL_CONFIG.sysmon.get("exec_on_click", "")
        if not execution:
            return
        else:
            GLib.spawn_command_line_async(execution)

    def update_temp(self):
        sensor_data = psutil.sensors_temperatures()
        if not sensor_data:
           self.temp_label.set_text(" --°C")
           return

        # Priority list for CPU temperature keys on Linux
        priority_keys = ["coretemp", "k10temp", "tctl", "cpu_thermal", "thinkpad"]
    
        # Find the first available key from our priority list
        found_key = next((k for k in priority_keys if k in sensor_data), None)
    
        # Fallback: if no priority key is found, just take the first available sensor
        if not found_key:
            found_key = next(iter(sensor_data))

        entries = sensor_data[found_key]
        # Usually, the first entry (Package/Die) is the overall CPU temp
        current_temp = int(entries[0].current)
    
        # Build Tooltip
        tooltip_lines = []
        for entry in entries:
            label = entry.label or "Sensor"
            tooltip_lines.append(f"{label}: <b>{int(entry.current)}°C</b>")
    
        self.temp_label.set_tooltip_markup("\n".join(tooltip_lines))

        # UI Logic
        if current_temp >= 90:
            self.temp_label.set_text(f" {current_temp}°C")
            self.temp_label.add_style_class("warning")
        else:
            label_text = f" {current_temp}°C" if self.must_always_show_info else ""
            self.temp_label.set_text(label_text)
            self.temp_label.remove_style_class("warning")

    def update_mem(self):
        virt_mem = psutil.virtual_memory()
        tooltip = "<b>Memory:</b>\n"
        # Kept your division by 1028, though standard is 1024
        formatted_used = '%.2f' % (virt_mem.used / 1028 / 1028 / 1028) + "G"
        formatted_free = '%.2f' % (virt_mem.free / 1028 / 1028 / 1028) + "G"
        formatted_perc = f"{virt_mem.percent}󰏰"

        self.mem_label.set_text("")
        tooltip += f"Used: {formatted_used} {formatted_perc}\nFree: {formatted_free}\n"

        swap_mem = psutil.swap_memory()
        if swap_mem.total == 0:
            tooltip += "No swap memory"
        else:
            tooltip += "\n<b>Swap:</b>\n"
            formatted_swap_used = '%.2f' % (swap_mem.used / 1028 / 1028 / 1028) + "G"
            formatted_swap_free = '%.2f' % (swap_mem.free / 1028 / 1028 / 1028) + "G"
            tooltip += f"Used: {formatted_swap_used} ({swap_mem.percent}󰏰)\nFree: {formatted_swap_free}"
        self.mem_label.set_tooltip_markup(tooltip)


        if virt_mem.percent >= 70.0:
            self.mem_label.set_text(f" {formatted_perc}")
            self.mem_label.add_style_class("warning")
        else:
            if self.must_always_show_info:
                self.mem_label.set_text(f" {formatted_perc}")
            self.mem_label.remove_style_class("warning")

    def update_cpu(self):
        perc_per_cpu = psutil.cpu_percent(percpu=True)
        avg_perc = round(sum(perc_per_cpu) / len(perc_per_cpu), 1)

        is_cpu_consoooooooooming = avg_perc >= 60 or any(core > 80 for core in perc_per_cpu)

        self.cpu_label.set_text(f"󰍛")

        tooltip = ''
        ii = 0
        for i in perc_per_cpu:
            tooltip = tooltip + f"Core {ii} <b>{i}󰏰</b>\n"
            ii += 1
        
        self.cpu_label.set_tooltip_markup(tooltip)

        if is_cpu_consoooooooooming:
            self.cpu_label.set_text(f"󰍛 {avg_perc}󰏰")
            self.cpu_label.add_style_class("warning")
        else:
            if self.must_always_show_info:
                self.cpu_label.set_text(f"󰍛 {avg_perc}󰏰")
            self.cpu_label.remove_style_class("warning")

    def _get_cpu_fan_rpm(self) -> int:
        """
        Fetches the current CPU fan speed as an integer.
        Returns 0 if no fan is found or if the sensor is unavailable.
        """
        try:
            fans = psutil.sensors_fans()
            if not fans:
                logger.warning("No fan found. Will always return zero")
                return 0

            for device in fans.values():
                for entry in device:
                    if 'cpu' in (entry.label or '').lower():
                        return int(entry.current)

            first_device_name = next(iter(fans))
            return int(fans[first_device_name][0].current)
        
        except (IndexError, KeyError, StopIteration):
            logger.warning("Couldn't find a fan. Will always return zero")
            return 0
        
    def update_fan(self):
        fan = self._get_cpu_fan_rpm()

        self.fan_label.set_text(f"󰈐 {'' if fan == 0 else fan}")

    def update_stats(self):
        time_sleep = SHELL_CONFIG.sysmon.get("interval", 2)
        if not isinstance(time_sleep, int) or isinstance(time_sleep, bool):
            logger.warning(f"Expected int in \"interval\", got {type(time_sleep).__name__}")
            logger.warning("Setting interval to 2 seconds anyways")
            time_sleep = 2
        while True:
            try:
                GLib.idle_add(self.update_temp)
                GLib.idle_add(self.update_mem)
                GLib.idle_add(self.update_cpu)
                GLib.idle_add(self.update_fan)
            except Exception as e:
                logger.error(f"Error in SystemMonitor loop: {e}")
            
            time.sleep(time_sleep)