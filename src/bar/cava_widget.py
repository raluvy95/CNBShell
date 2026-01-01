import os
import tempfile
import subprocess
import threading
import gi
import cairo

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class CavaWidget(Gtk.DrawingArea):
    def __init__(self, bars=10, height=30, spacing=4, color=(1, 1, 1, 1)):
        super().__init__()
        self.set_size_request(bars * (10 + spacing), height)
        self.bars = bars
        self.bar_heights = [0] * bars
        self.spacing = spacing
        self.color = color 
        
        self.cava_process = None
        self.stop_event = threading.Event()
        
        self.connect("destroy", self.cleanup)
        self.connect("draw", self.on_draw)
        
        # Delay start slightly to let UI settle
        GLib.timeout_add(1000, self.start_cava)

    def start_cava(self):
        config_text = f"""
        [general]
        bars = {self.bars}
        framerate = 60
        [output]
        method = raw
        raw_target = /dev/stdout
        data_format = ascii
        ascii_max_range = 100
        bar_delimiter = 59
        frame_delimiter = 10
        """
        
        self.config_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        self.config_file.write(config_text)
        self.config_file.close()

        cmd = ["cava", "-p", self.config_file.name]
        
        try:
            self.cava_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, 
                text=True, bufsize=1
            )
            threading.Thread(target=self._read_cava_output, daemon=True).start()
        except FileNotFoundError:
            print("Error: 'cava' not installed.")

    def _read_cava_output(self):
        while not self.stop_event.is_set() and self.cava_process:
            try:
                line = self.cava_process.stdout.readline()
                if not line: break
                values = line.strip().split(';')
                if len(values) >= self.bars:
                    self.bar_heights = [int(v)/100.0 for v in values[:self.bars]]
                    GLib.idle_add(self.queue_draw)
            except: pass

    def on_draw(self, widget, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        bar_w = (w - (self.bars - 1) * self.spacing) / self.bars
        
        cr.set_source_rgba(*self.color)
        for i, height_factor in enumerate(self.bar_heights):
            bar_h = h * height_factor
            if bar_h < 1: bar_h = 1 # Minimum 1px so it's visible when silent
            cr.rectangle(i * (bar_w + self.spacing), h - bar_h, bar_w, bar_h)
            cr.fill()

    def cleanup(self, *args):
        self.stop_event.set()
        if self.cava_process: self.cava_process.terminate()
        if hasattr(self, 'config_file'): os.remove(self.config_file.name)