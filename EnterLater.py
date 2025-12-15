#!/usr/bin/env python3
import subprocess
import threading
import time
from datetime import datetime, timedelta
from tkinter import (
    Tk, StringVar, BooleanVar,
    Frame, Label, Entry, Button, Checkbutton, BOTH, X, LEFT, RIGHT
)
from tkinter import messagebox

import sys

# Tray icon deps
try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    pystray = None
    Image = None
    ImageDraw = None
    ImageFont = None


class EnterLaterApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("EnterLater")
        self.root.resizable(False, False)

        # Keep window on top
        self.root.attributes("-topmost", True)

        # State
        self.target_datetime = None
        self.timer_running = False
        self.timer_thread = None
        self.stop_event = threading.Event()

        # Target / window tracking
        self.target_window_id = None
        self.target_window_title = None
        self.target_window_proc = None

        # Live active window tracking (for "use active at fire time" mode)
        self.live_window_id = None
        self.live_window_title = None
        self.live_window_proc = None
        self.window_poll_after_id = None

        # Track last external (non-EnterLater) window for captured mode
        self.last_external_window_id = None
        self.last_external_window_title = None
        self.last_external_window_proc = None
        self.external_window_poll_after_id = None

        # Tray icon
        self.tray_icon = None

        # Tk variables
        self.time_input = StringVar(value="10:00 PM")  # default example
        self.text_to_type = StringVar(value="")
        self.type_text_first = BooleanVar(value=False)
        self.use_live_active = BooleanVar(value=True)  # toggle for live vs captured

        self.status_text = StringVar(value="Alarm not set")
        self.countdown_text = StringVar(value="--:--:--")
        self.target_time_label_text = StringVar(value="No target time")
        self.target_window_label_text = StringVar(value="No target window")

        self._build_ui()
        self._init_tray_icon()
        self._start_polling_external_window()

    def _build_ui(self):
        padding = {"padx": 10, "pady": 5}

        main_frame = Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, **padding)

        # Time-of-day field
        row1 = Frame(main_frame)
        row1.pack(fill=X, pady=3)
        Label(row1, text="Fire at time (e.g. 10:01 PM):").pack(side=LEFT)
        Entry(row1, textvariable=self.time_input, width=14).pack(side=RIGHT)

        # Text field
        row2 = Frame(main_frame)
        row2.pack(fill=X, pady=3)
        Label(row2, text="Text to type (optional):").pack(side=LEFT)
        Entry(row2, textvariable=self.text_to_type, width=24).pack(side=RIGHT)

        # Checkbox: type text first?
        row3 = Frame(main_frame)
        row3.pack(fill=X, pady=3)
        Checkbutton(
            row3,
            text="Type text then press Enter (otherwise: Enter only)",
            variable=self.type_text_first
        ).pack(side=LEFT)

        # Mode toggle
        row3b = Frame(main_frame)
        row3b.pack(fill=X, pady=3)
        Checkbutton(
            row3b,
            text="Use active window at alarm time (track live)",
            variable=self.use_live_active
        ).pack(side=LEFT)

        # Target time display
        row4 = Frame(main_frame)
        row4.pack(fill=X, pady=3)
        Label(row4, text="Target time:").pack(side=LEFT)
        Label(row4, textvariable=self.target_time_label_text).pack(side=RIGHT)

        # Target window display
        row4b = Frame(main_frame)
        row4b.pack(fill=X, pady=3)
        Label(row4b, text="Target window:").pack(side=LEFT)
        Label(
            row4b,
            textvariable=self.target_window_label_text,
            wraplength=260,
            justify="right"
        ).pack(side=RIGHT)

        # Countdown + status
        row5 = Frame(main_frame)
        row5.pack(fill=X, pady=3)
        Label(row5, text="Countdown:").pack(side=LEFT)
        Label(row5, textvariable=self.countdown_text, font=("Helvetica", 14, "bold")).pack(side=RIGHT)

        row6 = Frame(main_frame)
        row6.pack(fill=X, pady=3)
        Label(row6, textvariable=self.status_text, wraplength=260).pack(side=LEFT)

        # Buttons
        row7 = Frame(main_frame)
        row7.pack(fill=X, pady=5)
        Button(row7, text="Set Alarm", command=self.start_alarm, width=10).pack(side=LEFT, padx=2)
        Button(row7, text="Cancel", command=self.cancel_alarm, width=8).pack(side=LEFT, padx=2)
        Button(row7, text="Hide to Tray", command=self.hide_to_tray, width=12).pack(side=LEFT, padx=2)
        Button(row7, text="Quit", command=self.quit_app, width=8).pack(side=RIGHT, padx=2)

    # --- Tray icon -----------------------------------------------------------

    def _create_tray_image(self):
        """Create a simple PIL image for the tray icon."""
        if Image is None or ImageDraw is None:
            return None

        size = 64
        img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # Circle background
        radius = size // 2 - 4
        center = (size // 2, size // 2)
        draw.ellipse(
            [
                (center[0] - radius, center[1] - radius),
                (center[0] + radius, center[1] + radius),
            ],
            fill=(70, 160, 220, 255),  # nicer light blue
        )

        text = "E"

        # Load a default font
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        # Get text size using textbbox (new Pillow)
        if font is not None:
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            except AttributeError:
                # Fallback for older Pillow versions
                w, h = draw.textsize(text, font=font)
        else:
            w, h = 10, 10  # fallback if font load fails

        # Center text
        draw.text(
            (center[0] - w / 2, center[1] - h / 2),
            text,
            fill=(255, 255, 255, 255),
            font=font,
        )

        return img

    def _init_tray_icon(self):
        if pystray is None:
            # No tray support; GUI will still work
            self.status_text.set(
                "Alarm not set (tray features require 'pystray' and 'Pillow')."
            )
            return

        image = self._create_tray_image()
        if image is None:
            return

        menu = pystray.Menu(
            pystray.MenuItem('Show EnterLater', self._tray_show),
            pystray.MenuItem('Quit', self._tray_quit)
        )

        self.tray_icon = pystray.Icon("EnterLater", image, "EnterLater", menu)

        # Run tray icon in its own thread
        def run_tray():
            self.tray_icon.run()

        t = threading.Thread(target=run_tray, daemon=True)
        t.start()

    def _tray_show(self, icon, item):
        self.root.after(0, self.show_window)

    def _tray_quit(self, icon, item):
        self.root.after(0, self.quit_app)

    def show_window(self):
        self.root.deiconify()
        # Re-apply topmost bounce to ensure it comes to front
        self.root.attributes("-topmost", True)
        self.root.after(100, lambda: self.root.attributes("-topmost", True))

    def hide_to_tray(self):
        if pystray is None or self.tray_icon is None:
            messagebox.showerror(
                "Tray not available",
                "System tray support requires 'pystray' and 'Pillow'.\n\n"
                "Install with:\n  pip install pystray pillow"
            )
            return
        self.root.withdraw()

    # --- Time parsing --------------------------------------------------------

    def parse_time_of_day(self, text: str) -> datetime:
        """
        Accepts:
          - '22:01'
          - '10:01 PM'
          - '3:00 pm'
          - '10:01pm' (no space)
        Returns a datetime for the *next occurrence* of that time (today or tomorrow).
        """
        raw = text.strip()
        if not raw:
            raise ValueError("Time cannot be empty.")

        now = datetime.now()

        # Normalize: remove spaces, uppercase
        norm = raw.upper().replace(" ", "")

        # Try to detect AM/PM
        is_12h = norm.endswith("AM") or norm.endswith("PM")

        if is_12h:
            period = norm[-2:]         # AM/PM
            time_part = norm[:-2]      # e.g. '10:01'
            # Insert a space again for strptime
            time_str_for_parse = f"{time_part} {period}"
            try:
                t = datetime.strptime(time_str_for_parse, "%I:%M %p").time()
            except ValueError:
                raise ValueError("Invalid 12-hour time format. Try like '10:01 PM' or '3:00 PM'.")
        else:
            # 24-hour format e.g. 22:01
            try:
                t = datetime.strptime(norm, "%H:%M").time()
            except ValueError:
                raise ValueError("Invalid 24-hour time format. Try '22:01' or '10:01 PM'.")

        candidate = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=t.hour,
            minute=t.minute,
            second=0,
            microsecond=0,
        )

        # If the time has already passed today, schedule for tomorrow.
        # (If system sleeps *past* the target, the loop still fires it on wake.)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)

        return candidate

    # --- Window capture / tracking ------------------------------------------

    def _capture_active_window(self):
        """
        Capture the last external (non-EnterLater) window for targeting.
        Used when "use_live_active" is OFF.
        """
        # Use the stored last external window
        if self.last_external_window_id is None:
            self.target_window_id = None
            self.target_window_title = None
            self.target_window_proc = None
            self.target_window_label_text.set("No external window found (will use active window at fire time)")
            return False

        # Copy the tracked external window info
        self.target_window_id = self.last_external_window_id
        self.target_window_title = self.last_external_window_title
        self.target_window_proc = self.last_external_window_proc

        # Build label text
        if self.target_window_proc:
            label = f"{self.target_window_title} — {self.target_window_proc}"
        else:
            label = f"{self.target_window_title} (process unknown)"

        self.target_window_label_text.set(label)
        return True

    def _track_active_window(self):
        """
        Polls the current active window while:
          - timer is running, and
          - use_live_active is True

        Updates label so you always see which window will be targeted
        in "live active window" mode.
        """
        if not (self.timer_running and self.use_live_active.get()):
            return

        try:
            win_id_proc = subprocess.run(
                ["xdotool", "getactivewindow"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
                text=True,
            )
            win_id_str = win_id_proc.stdout.strip()
            self.live_window_id = int(win_id_str) if win_id_str else None
        except (subprocess.CalledProcessError, ValueError):
            self.live_window_id = None
            self.live_window_title = None
            self.live_window_proc = None
            self.target_window_label_text.set("Active window unknown")
        else:
            # Get title
            title = "Unknown title"
            try:
                title_proc = subprocess.run(
                    ["xdotool", "getwindowname", str(self.live_window_id)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    text=True,
                )
                if title_proc.stdout.strip():
                    title = title_proc.stdout.strip()
            except subprocess.CalledProcessError:
                pass
            self.live_window_title = title

            # Get PID / process
            proc_desc = None
            try:
                pid_proc = subprocess.run(
                    ["xdotool", "getwindowpid", str(self.live_window_id)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    text=True,
                )
                pid_str = pid_proc.stdout.strip()
                if pid_str:
                    ps_proc = subprocess.run(
                        ["ps", "-p", pid_str, "-o", "comm="],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        check=True,
                        text=True,
                    )
                    pname = ps_proc.stdout.strip()
                    if pname:
                        proc_desc = f"{pname} (PID {pid_str})"
            except subprocess.CalledProcessError:
                pass
            self.live_window_proc = proc_desc

            # Update label
            if self.live_window_id is None:
                self.target_window_label_text.set("Active window unknown")
            else:
                if self.live_window_proc:
                    label = f"[LIVE] {self.live_window_title} — {self.live_window_proc}"
                else:
                    label = f"[LIVE] {self.live_window_title} (process unknown)"
                self.target_window_label_text.set(label)

        # Schedule next poll
        self.window_poll_after_id = self.root.after(1000, self._track_active_window)

    def _start_tracking_active_window(self):
        if self.window_poll_after_id is not None:
            self.root.after_cancel(self.window_poll_after_id)
            self.window_poll_after_id = None
        self._track_active_window()

    def _stop_tracking_active_window(self):
        if self.window_poll_after_id is not None:
            self.root.after_cancel(self.window_poll_after_id)
            self.window_poll_after_id = None

    # --- External window tracking (for captured mode) -----------------------

    def _poll_external_window(self):
        """
        Continuously tracks the active window. If it's NOT the EnterLater window,
        stores it as the last external window for use in captured mode.
        """
        try:
            # Get active window
            win_id_proc = subprocess.run(
                ["xdotool", "getactivewindow"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
                text=True,
            )
            win_id_str = win_id_proc.stdout.strip()
            if not win_id_str:
                # Schedule next poll and return
                self.external_window_poll_after_id = self.root.after(1000, self._poll_external_window)
                return

            active_window_id = int(win_id_str)

            # Get our own window ID to compare
            our_window_id = None
            try:
                our_window_id_proc = subprocess.run(
                    ["xdotool", "search", "--name", "^EnterLater$"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    text=True,
                )
                # May return multiple lines; take the first
                our_window_id_str = our_window_id_proc.stdout.strip().split('\n')[0]
                if our_window_id_str:
                    our_window_id = int(our_window_id_str)
            except (subprocess.CalledProcessError, ValueError, IndexError):
                pass

            # If active window is NOT our window, store it
            if our_window_id is None or active_window_id != our_window_id:
                self.last_external_window_id = active_window_id

                # Get title
                try:
                    title_proc = subprocess.run(
                        ["xdotool", "getwindowname", str(active_window_id)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        check=True,
                        text=True,
                    )
                    self.last_external_window_title = title_proc.stdout.strip() or "Unknown title"
                except subprocess.CalledProcessError:
                    self.last_external_window_title = "Unknown title"

                # Get process info
                self.last_external_window_proc = None
                try:
                    pid_proc = subprocess.run(
                        ["xdotool", "getwindowpid", str(active_window_id)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        check=True,
                        text=True,
                    )
                    pid_str = pid_proc.stdout.strip()
                    if pid_str:
                        ps_proc = subprocess.run(
                            ["ps", "-p", pid_str, "-o", "comm="],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL,
                            check=True,
                            text=True,
                        )
                        proc_name = ps_proc.stdout.strip()
                        if proc_name:
                            self.last_external_window_proc = f"{proc_name} (PID {pid_str})"
                except subprocess.CalledProcessError:
                    pass

        except (subprocess.CalledProcessError, ValueError):
            pass

        # Schedule next poll
        self.external_window_poll_after_id = self.root.after(1000, self._poll_external_window)

    def _start_polling_external_window(self):
        """Start polling for external windows."""
        if self.external_window_poll_after_id is not None:
            self.root.after_cancel(self.external_window_poll_after_id)
            self.external_window_poll_after_id = None
        self._poll_external_window()

    def _stop_polling_external_window(self):
        """Stop polling for external windows."""
        if self.external_window_poll_after_id is not None:
            self.root.after_cancel(self.external_window_poll_after_id)
            self.external_window_poll_after_id = None

    # --- Alarm / timer logic -------------------------------------------------

    def start_alarm(self):
        if self.timer_running:
            messagebox.showinfo("Already set", "Alarm is already running.")
            return

        # Check xdotool exists (graceful error)
        if not self._xdotool_available():
            messagebox.showerror(
                "xdotool not found",
                "EnterLater requires xdotool.\n\nInstall it with:\n\nsudo apt install xdotool"
            )
            return

        try:
            target = self.parse_time_of_day(self.time_input.get())
        except ValueError as e:
            messagebox.showerror("Invalid time", str(e))
            return

        self.target_datetime = target
        self.stop_event.clear()
        self.timer_running = True

        pretty_target = self.target_datetime.strftime("%Y-%m-%d %I:%M %p")
        self.target_time_label_text.set(pretty_target)

        # Window mode
        if self.use_live_active.get():
            # Live active mode: keep tracking current active window
            self.target_window_id = None  # not used in this mode
            self.status_text.set("Alarm set. Will fire into the active window at alarm time.")
            self._start_tracking_active_window()
        else:
            # Capture once
            self._stop_tracking_active_window()
            self._capture_active_window()
            self.status_text.set("Alarm set. Will fire into the captured window at alarm time.")

        self._update_countdown_label()

        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.timer_thread.start()

    def _timer_loop(self):
        while not self.stop_event.is_set():
            now = datetime.now()
            remaining = (self.target_datetime - now).total_seconds()
            if remaining <= 0:
                break

            self.root.after(0, self._update_countdown_label)
            time.sleep(1)

        if self.stop_event.is_set():
            return

        # Time reached (even if system slept past it, this will run on wake)
        self.root.after(0, self._alarm_triggered)

    def _alarm_triggered(self):
        self.timer_running = False
        self._stop_tracking_active_window()
        self.status_text.set("Alarm firing keystroke...")
        self.countdown_text.set("00:00:00")

        threading.Thread(target=self._perform_keystroke, daemon=True).start()

    def cancel_alarm(self):
        if not self.timer_running:
            self.status_text.set("Alarm not set")
            self.countdown_text.set("--:--:--")
            self.target_time_label_text.set("No target time")
            self.target_window_label_text.set("No target window")
            self._stop_tracking_active_window()
            return

        self.stop_event.set()
        self.timer_running = False
        self._stop_tracking_active_window()
        self.status_text.set("Alarm cancelled.")
        self.countdown_text.set("--:--:--")
        self.target_time_label_text.set("No target time")
        self.target_window_label_text.set("No target window")

    def quit_app(self):
        self.stop_event.set()
        self._stop_tracking_active_window()
        self._stop_polling_external_window()
        # Stop tray icon if present
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.destroy()
        sys.exit(0)

    def _update_countdown_label(self):
        if not self.timer_running or not self.target_datetime:
            self.countdown_text.set("--:--:--")
            return

        now = datetime.now()
        remaining = int((self.target_datetime - now).total_seconds())
        if remaining < 0:
            remaining = 0

        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        self.countdown_text.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    # --- Keystroke logic -----------------------------------------------------

    def _perform_keystroke(self):
        text = self.text_to_type.get()
        do_type = self.type_text_first.get() and bool(text.strip())

        try:
            window_id_to_use = None

            if self.use_live_active.get():
                # Live mode: just grab current active window right now
                try:
                    win_id_proc = subprocess.run(
                        ["xdotool", "getactivewindow"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        check=True,
                        text=True,
                    )
                    win_id_str = win_id_proc.stdout.strip()
                    if win_id_str:
                        window_id_to_use = int(win_id_str)
                except (subprocess.CalledProcessError, ValueError):
                    window_id_to_use = None
            else:
                # Captured mode
                window_id_to_use = self.target_window_id

            # Try to activate window (if known)
            if window_id_to_use is not None:
                try:
                    subprocess.run(
                        ["xdotool", "windowactivate", "--sync", str(window_id_to_use)],
                        check=True
                    )
                except subprocess.CalledProcessError:
                    # If activation fails, fall back to whatever is active
                    pass

            if do_type:
                subprocess.run(["xdotool", "type", "--delay", "0", text], check=True)
                subprocess.run(["xdotool", "key", "Return"], check=True)
            else:
                subprocess.run(["xdotool", "key", "Return"], check=True)

            self.root.after(0, lambda: self.status_text.set("Keystroke sent. Alarm not set."))

        except subprocess.CalledProcessError as e:
            self.root.after(
                0,
                lambda: self.status_text.set(f"Error sending keys via xdotool (exit {e.returncode}).")
            )
        except FileNotFoundError:
            self.root.after(
                0,
                lambda: self.status_text.set("xdotool not found. Install with: sudo apt install xdotool")
            )

    # --- xdotool presence ----------------------------------------------------

    def _xdotool_available(self) -> bool:
        try:
            subprocess.run(
                ["xdotool", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return True
        except FileNotFoundError:
            return False


def main():
    root = Tk()
    app = EnterLaterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
