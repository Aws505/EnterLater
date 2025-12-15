# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EnterLater is a Linux desktop automation tool that schedules keystrokes (Enter key or text+Enter) to be sent to specific windows at a scheduled time-of-day. It's a single-file Python application with a Tkinter GUI, system tray support, and xdotool integration for window management.

## Running the Application

```bash
# Run directly
python3 EnterLater.py

# Install system dependencies first if needed
sudo apt install xdotool
pip install pystray pillow
```

## Architecture

### Single-File Design
The entire application is contained in `EnterLater.py` (656 lines). All features are implemented in the `EnterLaterApp` class.

### Threading Model
- **Main thread**: Tkinter GUI event loop
- **Timer thread**: Background alarm countdown loop (daemon thread)
- **Keystroke thread**: Executes xdotool commands when alarm fires (daemon thread)
- **Tray icon thread**: Runs pystray in background (daemon thread)

### Window Targeting Modes
The application supports two distinct modes for window targeting:

1. **Live Active Mode** (`use_live_active=True`):
   - Continuously polls active window every 1 second
   - Window target is determined at alarm fire time
   - Updates `live_window_id`, `live_window_title`, `live_window_proc`
   - Polling managed via `root.after()` callbacks

2. **Captured Mode** (`use_live_active=False`):
   - Captures active window once at alarm set time
   - Window target is locked and won't change
   - Uses `target_window_id`, `target_window_title`, `target_window_proc`

### xdotool Integration
All window manipulation and keystroke injection uses xdotool commands via subprocess:
- `xdotool getactivewindow` - Get active window ID
- `xdotool getwindowname <id>` - Get window title
- `xdotool getwindowpid <id>` - Get window PID
- `xdotool windowactivate --sync <id>` - Focus window
- `xdotool type --delay 0 <text>` - Type text
- `xdotool key Return` - Press Enter

### Time Parsing
`parse_time_of_day()` (EnterLater.py:241-293) accepts:
- 12-hour format: `10:01 PM`, `3:00pm` (with/without space)
- 24-hour format: `22:01`, `14:30`
- Always schedules for next occurrence (today or tomorrow)

### State Management
Key state variables in `EnterLaterApp`:
- `timer_running` - Whether alarm is active
- `target_datetime` - When alarm should fire
- `stop_event` - Threading.Event for cancelling timer
- `use_live_active` - Mode toggle (BooleanVar)
- `type_text_first` - Whether to type text before Enter (BooleanVar)

## Platform Requirements

### X11 Dependency
EnterLater requires X11 for xdotool to work. Wayland support is limited and requires compatibility layers. The application makes no Wayland-specific accommodations.

### Optional Dependencies
- `pystray` and `Pillow` - Required for system tray functionality
- Application gracefully degrades if these are missing (tray features disabled)

## Code Modification Guidelines

### Adding Features
When adding features to EnterLater.py:
- Keep everything in the single file unless absolutely necessary
- New features should integrate with the existing `EnterLaterApp` class
- Use daemon threads for background work to ensure clean exit
- Update UI via `root.after()` when calling from background threads
- Check xdotool availability before using (`_xdotool_available()`)

### UI Modifications
- UI is built with Tkinter frames in `_build_ui()` (EnterLater.py:68-137)
- Use StringVar/BooleanVar for data binding to UI elements
- Window is always on top: `root.attributes("-topmost", True)`
- All labels use textvariable bindings for dynamic updates

### Error Handling
- xdotool errors are caught with `subprocess.CalledProcessError`
- Missing dependencies show user-friendly error dialogs
- Window activation failures fall back to whatever is currently active
- Threading uses daemon threads to avoid blocking on exit

## Desktop Integration

The project includes an `install.sh` script that handles installation for any user by:
- Copying files to `~/EnterLater`
- Generating a `.desktop` file with user-specific paths
- Checking dependencies
- Setting proper permissions

The `.desktop.template` file is a reference/template only. The actual desktop file is generated during installation with correct paths.

Installation location: `~/.local/share/applications/EnterLater.desktop`

## Testing Notes

There are no automated tests. Manual testing should verify:
1. Time parsing (12h/24h formats, today/tomorrow logic)
2. Both window modes (live tracking vs captured)
3. Text typing + Enter vs Enter-only
4. Tray icon hide/show/quit
5. Alarm cancellation during countdown
6. Behavior when target window closes (graceful fallback)
7. System sleep/wake during countdown
