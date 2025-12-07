# EnterLater
_A lightweight Linux utility that fires Enter (or text + Enter) into a window at a scheduled time._

![EnterLater Icon](enterlater.png)

EnterLater is a tiny but powerful desktop automation tool for Linux.
You choose a **time-of-day**, optional **text to type**, and choose whether to target a **specific window** or **whatever is active at alarm time**. Once the alarm triggers, EnterLater sends keystrokes into that window—perfect for:

- Auto-submitting prompts  
- Confirming dialogs  
- Keeping sessions alive  
- Triggering scripts/UI workflows at a set time  

EnterLater includes a GUI, tray icon support, automatic window tracking, and xdotool integration.

## ✨ Features

### Core
- ⏰ Schedule a time-of-day (e.g., 10:01 PM or 22:01)  
- ⌨️ Send Enter, or type text + Enter  
- 🔍 Choose “live active window” or lock a specific window  
- 🪟 Live mode continuously tracks the active window  
- 💡 Automatically adapts if system sleeps and wakes past alarm time  

### GUI
- Always-on-top Timer window  
- Clean & simple Tk-based UI  
- Visual countdown  
- Shows the window being targeted (title + process)  

### System Tray
- Hide to tray  
- Restore GUI from tray  
- Quit from tray  
- Light-blue custom icon (`enterlater.png`)

### Reliability
- Graceful error if xdotool is missing  
- Falls back automatically if a window disappears  
- Multi-threaded alarm loop avoids freezing the GUI  

---

## 📦 Requirements

### System
- Linux (X11-based; Wayland requires xdotool compatibility layer)
- Python 3.8+

### Python packages
```
pip install pystray pillow
```

### System tools
```
sudo apt install xdotool
```

---

## 🚀 Installation

### 1. Create project directory
```
mkdir -p ~/EnterLater
cd ~/EnterLater
```

Place:
- `EnterLater.py`
- `enterlater.png`
- `README.md`

---

## 🖥️ Desktop Launcher Setup

Create:
```
~/.local/share/applications/EnterLater.desktop
```

Contents:
```
[Desktop Entry]
Type=Application
Name=EnterLater
Comment=Fire Enter (or text + Enter) into a window at a specific time
Exec=python3 /home/$USER/EnterLater/EnterLater.py
Icon=/home/$USER/EnterLater/enterlater.png
Terminal=false
Categories=Utility;
StartupNotify=false
```

Refresh:
```
update-desktop-database ~/.local/share/applications 2>/dev/null || true
```

---

## 🧭 Usage Guide

### 1. Launch EnterLater
```
python3 ~/EnterLater/EnterLater.py
```

### 2. Set an Alarm
- Enter a time-of-day (`10:00 PM`, `3:05pm`, `22:30`)
- Optional text to auto-type
- Choose:
  - Type text then press Enter  
  - Use active window at alarm time  

### 3. Target Window Modes

#### Live Active Mode
Tracks whatever window is active.  
At alarm time, that window receives the keystroke.

#### Captured Window Mode
Captures active window at alarm setup time, and always targets that window.

### 4. Tray Usage
- Hide to Tray → minimizes GUI  
- Tray → Show EnterLater / Quit  

---

## 🧩 Architecture

### Scheduling
- Time-of-day parser supports 12h & 24h formats
- If time has passed, schedules for next day

### Alarm Loop
- Independent thread  
- Updates countdown  
- Fires after sleep/wakeup  

### Window Management
- Uses xdotool for:
  - getactivewindow  
  - getwindowname  
  - getwindowpid  
  - windowactivate  
  - key/type  

### Tray
- pystray icon in background thread
- Pillow-generated or PNG icon

---

## 📁 Project Structure
```
EnterLater/
├── EnterLater.py
├── enterlater.png
└── README.md
```

---

## 🔧 Troubleshooting

### xdotool not found
```
sudo apt install xdotool
```

### Tray icon not showing
```
pip install pystray pillow
```
Ensure system tray support is enabled.

### Wayland issues
Wayland restricts synthetic input.  
Switch to X11 for best results.

---

## 📜 License
MIT License

---

## ❤️ Contributions
Want improvements (recurring alarms, custom keystrokes, SVG icons)?  
Just ask!
