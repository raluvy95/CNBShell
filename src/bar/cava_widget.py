import os
import tempfile
import subprocess
import threading
import textwrap
import math
import gi
import cairo
import atexit

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class CavaWidget(Gtk.DrawingArea):
    def __init__(self, bars=25, height=20, spacing=4, framerate=60):
        super().__init__()
        # Ensure we request enough space
        self.set_size_request(bars * (10 + spacing), height)
        
        # Configuration
        self.bars = bars
        self.bar_heights = [0] * bars
        self.spacing = spacing
        self.framerate = framerate
        self.radius = 4  # Corner radius
        
        # Visual Settings
        self.use_gradient = True
        self.gradient_colors = ["#89b4fa", "#eba0ac"] # Start, End
        self.solid_color = "#cba6f7"
        
        # Process State
        self.cava_process = None
        self.stop_event = threading.Event()
        
        self.connect("destroy", self.cleanup)
        self.connect("draw", self.on_draw)
        
        # Start Cava
        GLib.timeout_add(100, self.start_cava)

    def start_cava(self):
        # 1. Config text setup
        config_text = textwrap.dedent(f"""
            [general]
            bars = {self.bars}
            framerate = {self.framerate}
            mode = normal
            channels = mono
            [output]
            method = raw
            raw_target = /dev/stdout
            data_format = ascii
            ascii_max_range = 100
            bar_delimiter = 59
            frame_delimiter = 10
        """).strip()
        
        # 2. Create the file (using delete=False so we can inspect it if needed)
        self.config_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        self.config_file.write(config_text)
        self.config_file.close()

        print(f"DEBUG: Config file created at: {self.config_file.name}")
        print(f"DEBUG: Checking if file exists: {os.path.exists(self.config_file.name)}")

        cmd = ["cava", "-p", self.config_file.name]
        
        try:
            # 3. CHANGED: Capture stderr to see errors
            self.cava_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, # Capture errors!
                text=True, 
                bufsize=1
            )
            
            # Check immediately if it crashed
            try:
                # Wait 0.1s to see if it dies immediately
                stdout, stderr = self.cava_process.communicate(timeout=0.2)
                if self.cava_process.returncode is not None and self.cava_process.returncode != 0:
                    print(f"ERROR: Cava crashed with code {self.cava_process.returncode}")
                    print(f"STDERR:\n{stderr}")
                    return
            except subprocess.TimeoutExpired:
                # This is GOOD! It means Cava is still running.
                # We can continue to the reading thread.
                pass

            # If we are here, Cava is running fine. Start reading output.
            threading.Thread(target=self._read_cava_output, daemon=True).start()

        except FileNotFoundError:
            print("Error: 'cava' command not found in PATH.")
        except Exception as e:
            print(f"Error starting cava: {e}")

    def _cleanup_config_file(self):
        """Safely remove the file if it exists"""
        if hasattr(self, 'config_file') and os.path.exists(self.config_file.name):
            try:
                os.remove(self.config_file.name)
            except OSError:
                pass

    def cleanup(self, *args):
        # Your normal widget cleanup
        self.stop_event.set()
        if self.cava_process: 
            self.cava_process.terminate()
        
        # Call our file cleanup helper
        self._cleanup_config_file()

    def _read_cava_output(self):
        while not self.stop_event.is_set() and self.cava_process:
            try:
                line = self.cava_process.stdout.readline()
                if not line: break
                values = line.strip().split(';')
                # Ensure we only take exactly 'self.bars' amount of data
                if len(values) >= self.bars:
                    self.bar_heights = [int(v)/100.0 for v in values[:self.bars]]
                    GLib.idle_add(self.queue_draw)
            except Exception as e:
                pass

    def hex_to_rgb(self, hex_color):
        """Helper to convert hex string to (r, g, b) 0-1 floats"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    
    def toggle_mode(self):
        """Call this to switch between gradient and solid"""
        self.use_gradient = not self.use_gradient
        self.queue_draw()

    def draw_rounded_rect(self, cr, x, y, w, h, r):
        """Helper to draw a rounded rectangle path"""
        # Ensure radius isn't larger than half the width/height
        r = min(r, w / 2, h / 2)
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def on_draw(self, widget, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        
        # Calculate bar width based on available space and requested count
        # (This keeps them responsive, or you can fix the width)
        total_spacing = (self.bars - 1) * self.spacing
        bar_w = (w - total_spacing) / self.bars
        
        # CENTERING LOGIC
        # If the bars become very thin, you might want to cap the width and center the block
        # For now, we assume they fill the width. If you want a fixed bar width centered:
        # bar_w = 10 # fixed px
        # total_content_width = (bar_w * self.bars) + total_spacing
        # start_x = (w - total_content_width) / 2
        start_x = 0 # Currently filling full width

        # PREPARE SOURCE (Gradient or Solid)
        if self.use_gradient:
            gradient = cairo.LinearGradient(0, 0, w, 0) # Left to right
            gradient.add_color_stop_rgb(0, *self.hex_to_rgb(self.gradient_colors[0]))
            gradient.add_color_stop_rgb(1, *self.hex_to_rgb(self.gradient_colors[1]))
            cr.set_source(gradient)
        else:
            cr.set_source_rgb(*self.hex_to_rgb(self.solid_color))

        # DRAW BARS
        for i, height_factor in enumerate(self.bar_heights):
            bar_h = h * height_factor
            if bar_h < 1: bar_h = 1 # Minimum visibility
            
            x = start_x + i * (bar_w + self.spacing)
            y = h - bar_h
            
            # Use custom rounded rect helper
            self.draw_rounded_rect(cr, x, y, bar_w, bar_h, self.radius)
            cr.fill()

    def cleanup(self, *args):
        self.stop_event.set()
        if self.cava_process: 
            self.cava_process.terminate()