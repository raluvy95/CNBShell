from fabric.widgets.box import Box
from fabric.widgets.label import Label
import psutil
import threading
import time

from gi.repository import GLib # type: ignore

class SystemMonitor(Box):
    def __init__(self):
        self.cpu_label = Label("cpu")
        self.mem_label = Label("mem")
        self.temp_label = Label("temp")
        self.net_label = Label("net")
        super().__init__(
            orientation="h",
            spacing=15,
            children=[
                self.cpu_label,
                self.mem_label,
                self.temp_label
            ],
            style_classes="sysmon"
        )

        threading.Thread(target=self.update_stats, daemon=True).start()

    def update_temp(self):
        tooltip = ''
        sensor_temp = psutil.sensors_temperatures()
        current_temp = sensor_temp["coretemp"][0].current
        for i in sensor_temp["coretemp"]:
            if i.label.startswith("Core"):
                tooltip = tooltip + f"{i.label} <b>{int(i.current)}°C</b>\n"
            else:
                pass

        self.temp_label.set_tooltip_markup(tooltip)
        self.temp_label.set_text(f"")

        if current_temp >= 90:
            self.temp_label.set_text(f" {current_temp}°C")
            self.temp_label.add_style_class("warning")
        else:
            self.temp_label.remove_style_class("warning")

    def update_mem(self):
        virt_mem = psutil.virtual_memory()
        tooltip = "<b>Memory:</b>\n"
        formatted_used = '%.2f' % (virt_mem.used / 1028 / 1028 / 1028) + "G"
        formatted_free = '%.2f' % (virt_mem.free / 1028 / 1028 / 1028) + "G"
        formatted_perc = f"{virt_mem.percent}󰏰"

        self.mem_label.set_text("")
        tooltip += f"Used: {formatted_used} {formatted_perc}\nFree: {formatted_free}\n"

        swap_mem = psutil.swap_memory()
        if swap_mem == 0:
            tooltip += "No swap memory"
        else:
            tooltip += "\n<b>Swap:</b>\n"
            formatted_swap_used = '%.2f' % (swap_mem.used / 1028 / 1028 / 1028) + "G"
            formatted_swap_free = '%.2f' % (swap_mem.free / 1028 / 1028 / 1028) + "G"
            tooltip += f"Used: {formatted_swap_used} ({swap_mem.percent}󰏰)\nFree: {formatted_swap_free}"
        self.mem_label.set_tooltip_markup(tooltip)


        if virt_mem.percent >= 70.0:
            self.mem_label.set_text(" " + formatted_perc)
            self.mem_label.add_style_class("warning")
        else:
            self.mem_label.remove_style_class("warning")

    def update_cpu(self):
        perc = psutil.cpu_percent()
        perc_per_cpu = psutil.cpu_percent(percpu=True)
        is_cpu_consoooooooooming = len(list(filter(lambda x: x > 80, perc_per_cpu))) >= 1 or perc >= 60

        self.cpu_label.set_text(f"󰍛")

        tooltip = ''
        ii = 0
        for i in perc_per_cpu:
            tooltip = tooltip + f"Core {ii} <b>{i}󰏰</b>\n"
            ii += 1
        
        self.cpu_label.set_tooltip_markup(tooltip)

        if is_cpu_consoooooooooming:
            self.cpu_label.set_text(f"󰍛 {perc}󰏰")
            self.cpu_label.add_style_class("warning")
        else:
            self.cpu_label.remove_style_class("warning")

    def update_stats(self):
        while True:
            GLib.idle_add(self.update_temp)
            GLib.idle_add(self.update_mem)
            GLib.idle_add(self.update_cpu)
            time.sleep(2)
