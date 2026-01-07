![logo](./assets/cnbshelllogo.png)

<h1 align=center>CNBShell</h1>

A ready to use bar/shell for Hyprland based on [Fabric](https://github.com/Fabric-Development/fabric) and GTK3 written in Python. It is only intended to work on my laptop (Asus TUF Gaming F15).

Design inspired by [Tsumiki](https://github.com/rubiin/Tsumiki) and various posts I saw on r/unixporn

# Features

- System monitor
- Privacy indicator
- System tray
- Workspace indicator
- Time and calendar popup
- Notification viewer, independent from any notification daemon and doesn't replace it.
- Mpris with cava integration
- Basic weather


>[!IMPORTANT]
>Some features are AI generated. They are tested, modified by me and work on my machine. If you do not like my project because I used AI, don't complain and don't use my project

# Installing

## Required system dependencies

`cava`, `mako`, `gtk3`, `dart-sass`, `dbus` 

If you use `pipewire`, you need to get `pipewire-pulse` as this project uses libpulse python library. 

I use `mako` for notification daemon, specifically to toggle do not distrub button.

## Setting up virtual environment

You must initialize Python virtual environment to use my project

```sh
python3 -m venv .venv
```

Install required python dependencies. Make sure you are inside Python virtual environment
```sh
pip install -r requirements.txt
```

Execute the program via helper run or normal python program
```sh
./run # Recommended as you can execute from any directory in shell

# or

python3 main.py
```

# Configuring
Currently, the only you can customize without editing Python and SCSS files is the clock format and that's it.


>[!NOTE]
>I don't have a plan on expanding configuration as this bar is only intended for my use.


Here's the full example of config
```toml
[clock]
format = "%T"
```

# Developement
Enforce a basic [Semantic Commit Messages](https://gist.github.com/joshbuchea/6f47e86d2510bce28f8e7f42ae84c716)

Since this project is heavly developed and I am currently using it. Some features and fixes are AI generated because... why not