import datetime
import calendar
from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import Gtk, GLib  # <--- Import GLib here

# Assuming this is your custom import
from src.popup.datetime import ClickableDateTime

class Time(Box):
    def __init__(self):
        super().__init__(
            orientation="h",
            spacing=15,
            h_align="center",
            children=[
                ClickableDateTime(lambda: None, "%H:%M:%S", style_classes="bigclock"),
                ClickableDateTime(lambda: None, "%A %d %B %Y")
            ]
        )

class Calendar(Box):
    def __init__(self, **kwargs):
        super().__init__(
            orientation="v",
            spacing=8,
            style_classes=["calendar-root"],
            h_align="center",
            v_align="center",
            children=[
                Time()
            ],
            **kwargs
        )

        self.current_date = datetime.date.today()
        self.view_year = self.current_date.year
        self.view_month = self.current_date.month
        self.selected_date = self.current_date

        # --- HEADER ---
        self.header = CenterBox(style_classes=["calendar-header"])
        
        self.btn_prev = Button(label="←", on_clicked=self.prev_month, style_classes=["cal-nav-btn"])
        self.btn_next = Button(label="→", on_clicked=self.next_month, style_classes=["cal-nav-btn"])
        
        self.btn_title = Button(
            label="", 
            on_clicked=self.jump_to_today, 
            style_classes=["cal-title-btn"],
            tooltip_text="Jump to Today"
        )

        self.header.start_children = [self.btn_prev]
        self.header.center_children = [self.btn_title]
        self.header.end_children = [self.btn_next]

        # --- WEEKDAYS ---
        self.weekdays = Box(orientation="h", spacing=4, style_classes=["cal-weekdays"], h_align="fill")
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            self.weekdays.add(Label(label=day, style_classes=["cal-day-name"], h_expand=True))

        # --- GRID ---
        self.grid = Box(orientation="v", spacing=4, style_classes=["cal-grid"], h_align="fill")

        self.add(self.header)
        self.add(self.weekdays)
        self.add(self.grid)

        self.update_view()
        
        GLib.timeout_add_seconds(5, self._check_day_change)

    def _check_day_change(self):
        """Checks if the date has changed (midnight)."""
        new_today = datetime.date.today()
        
        if new_today != self.current_date:
            # Check if the user is currently looking at the "old" current month
            # If so, we should update the view to the "new" current month.
            was_viewing_current = (self.view_year == self.current_date.year and 
                                   self.view_month == self.current_date.month)

            self.current_date = new_today

            if was_viewing_current:
                self.view_year = self.current_date.year
                self.view_month = self.current_date.month
            
            # If the user selected 'today', update selection to the new 'today'
            if self.selected_date == self.current_date - datetime.timedelta(days=1):
                 self.selected_date = self.current_date

            self.update_view()
            
        return True # Return True to keep the timeout running loop

    def update_view(self):
        # Update Title Button Text
        month_name = calendar.month_name[self.view_month]
        self.btn_title.set_label(f"{month_name} {self.view_year}")

        self.grid.children = [] 
        month_matrix = calendar.monthcalendar(self.view_year, self.view_month)

        for week in month_matrix:
            row = Box(orientation="h", spacing=4, h_align="fill")
            
            for day in week:
                if day == 0:
                    btn = Button(
                        label=" ", 
                        style_classes=["cal-day-btn", "empty-btn"], 
                        h_expand=True,
                        on_clicked=lambda *_: None
                    )
                    row.add(btn)
                else:
                    btn_classes = ["cal-day-btn"]
                    
                    if (day == self.current_date.day and 
                        self.view_month == self.current_date.month and 
                        self.view_year == self.current_date.year):
                        btn_classes.append("cal-today")

                    if (day == self.selected_date.day and
                        self.view_month == self.selected_date.month and
                        self.view_year == self.selected_date.year):
                        btn_classes.append("selected-day")

                    btn = Button(
                        label=str(day),
                        style_classes=btn_classes,
                        on_clicked=lambda b, d=day: self.on_day_clicked(d),
                        h_expand=True 
                    )
                    row.add(btn)
            self.grid.add(row)

    def prev_month(self, *args):
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else:
            self.view_month -= 1
        self.update_view()

    def next_month(self, *args):
        if self.view_month == 12:
            self.view_month = 1
            self.view_year += 1
        else:
            self.view_month += 1
        self.update_view()

    def jump_to_today(self, *args):
        self.view_year = self.current_date.year
        self.view_month = self.current_date.month
        self.selected_date = self.current_date
        self.update_view()

    def on_day_clicked(self, day):
        self.selected_date = datetime.date(self.view_year, self.view_month, day)
        self.update_view()