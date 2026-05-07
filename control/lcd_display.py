# ============================================================
# control/lcd_display.py — 16×2 I²C LCD display driver.
#
# Wraps the RPLCD CharLCD class and provides one clearly-named
# method for every UI state in the application. All methods
# pad their output to exactly 16 characters per line so that
# switching between messages never leaves stale characters on
# the display.
#
# Hardware: any PCF8574-based 16×2 LCD module.
# Default I²C address: 0x27 (set in config.py).
# ============================================================

from RPLCD.i2c import CharLCD
import os
import config


def _vol_bar(vol_float, width=8):
    """
    Render a simple ASCII progress bar representing a volume level.

    Example output for vol_float=0.5, width=8:  [====----]

    Args:
        vol_float (float): Volume in [0.0, 1.0].
        width     (int):   Total number of bar segments (default 8).

    Returns:
        str: A string of the form "[====----]" with exactly width inner chars.
    """
    filled = round(vol_float * width)
    return "[" + "=" * filled + "-" * (width - filled) + "]"


def _short_name(path, maxlen=16):
    """
    Extract the filename (without extension) from a full file path
    and truncate it to fit within one LCD line.

    Args:
        path   (str): Full file path, e.g. "assets/music/my_song.mp3".
        maxlen (int): Maximum number of characters to return (default 16).

    Returns:
        str: Truncated filename without extension, e.g. "my_song".
    """
    name = os.path.splitext(os.path.basename(path))[0]
    return name[:maxlen]


class LCDDisplay:
    """
    High-level display controller for the 16×2 I²C LCD.

    Every public method represents a distinct application state
    (e.g. playing, paused, volume up) and writes the appropriate
    two-line message to the screen.
    """

    def __init__(self):
        self.lcd = CharLCD(
            i2c_expander="PCF8574",          # I²C GPIO expander chip on the LCD backpack
            address=config.LCD_ADDRESS,      # Typically 0x27; verify with i2cdetect -y 1
            port=1,                          # I²C bus 1 (standard on Raspberry Pi)
            cols=config.LCD_COLS,            # 16 columns
            rows=config.LCD_ROWS,            # 2 rows
            dotsize=8,                       # 5×8 dot-matrix characters
            auto_linebreaks=False,           # Disable automatic wrapping; we handle it manually
        )
        self.clear()

    # ── Low-level write ──────────────────────────────────────

    def show(self, line1="", line2=""):
        """
        Write two lines of text to the display.

        Each line is left-justified and padded (or truncated) to exactly
        16 characters. Calling lcd.clear() before writing prevents ghost
        characters from a previous longer message remaining on screen.

        Args:
            line1 (str): Text for the top row (max 16 chars).
            line2 (str): Text for the bottom row (max 16 chars).
        """
        self.lcd.clear()
        self.lcd.write_string(line1.ljust(16)[:16])
        self.lcd.crlf()
        self.lcd.write_string(line2.ljust(16)[:16])

    def clear(self):
        """Clear all characters from the display."""
        self.lcd.clear()

    # ── System states ────────────────────────────────────────

    def show_ready(self):
        """Display the idle/standby screen shown when no gesture is active."""
        self.show("Gesture System", "   Ready...   ")

    def show_startup(self):
        """Display the boot/initialisation screen shown on startup."""
        self.show("Gesture System", " Initializing ")

    def show_goodbye(self):
        """Display the shutdown screen shown before powering off."""
        self.show("Gesture System", "   Goodbye!   ")

    # ── Gesture feedback ─────────────────────────────────────

    def show_gesture(self, gesture, confidence):
        """
        Show the currently detected gesture and its confidence score.

        Line 1: Gesture name prefixed with '>' (truncated to 15 chars).
        Line 2: ASCII bar followed by the numeric percentage.

        Example:
            >THUMBS_UP
            [==========]  87%

        Args:
            gesture    (str):   Gesture label, e.g. "THUMBS_UP".
            confidence (float): Model confidence in [0.0, 1.0].
        """
        pct = int(confidence * 100)
        bar = _vol_bar(confidence, width=10)
        self.show(f">{gesture[:15]}", f"{bar} {pct:2d}%")

    # ── Playback control states ──────────────────────────────

    def show_playing(self, track_path=""):
        """
        Display the 'now playing' screen.

        Line 1: "> Now Playing"
        Line 2: Track filename (without extension, truncated to 16 chars).

        Args:
            track_path (str): Full path to the current audio file.
        """
        name = _short_name(track_path) if track_path else "Music"
        self.show("> Now Playing", name)

    def show_paused(self, track_path=""):
        """
        Display the paused state screen.

        Line 1: "|| Paused"
        Line 2: Track filename.

        Args:
            track_path (str): Full path to the current audio file.
        """
        name = _short_name(track_path) if track_path else "Music"
        self.show("|| Paused", name)

    def show_stopped(self):
        """
        Display the stopped state screen.
        Also prompts the user with the gesture needed to resume.
        """
        self.show("[] Stopped", "Show OPEN_PALM")

    def show_next_track(self, track_path=""):
        """
        Display the 'skipping to next track' transition screen.

        Args:
            track_path (str): Full path to the new (next) track.
        """
        name = _short_name(track_path) if track_path else "Next"
        self.show(">> Next Track", name)

    def show_prev_track(self, track_path=""):
        """
        Display the 'returning to previous track' transition screen.

        Args:
            track_path (str): Full path to the new (previous) track.
        """
        name = _short_name(track_path) if track_path else "Prev"
        self.show("<< Prev Track", name)

    # ── Volume states ────────────────────────────────────────

    def show_volume_up(self, vol_float):
        """
        Display the volume-increased confirmation screen.

        Line 1: "Vol+ " followed by ASCII bar (e.g. "Vol+ [====----]")
        Line 2: Numeric percentage, right-aligned.

        Args:
            vol_float (float): New volume level in [0.0, 1.0].
        """
        pct = int(vol_float * 100)
        bar = _vol_bar(vol_float, width=8)
        self.show(f"Vol+ {bar}", f"     {pct:3d}%")

    def show_volume_down(self, vol_float):
        """
        Display the volume-decreased confirmation screen.

        Args:
            vol_float (float): New volume level in [0.0, 1.0].
        """
        pct = int(vol_float * 100)
        bar = _vol_bar(vol_float, width=8)
        self.show(f"Vol- {bar}", f"     {pct:3d}%")

    # ── Error / warning states ───────────────────────────────

    def show_no_music(self):
        """Display a warning when no audio files are found in assets/music/."""
        self.show("! No Music File", "Add mp3/wav to")

    def show_error(self, msg=""):
        """
        Display a generic error message.

        Args:
            msg (str): Short error description (max 16 chars).
        """
        self.show("! Error", msg[:16])

    # ── Cleanup ──────────────────────────────────────────────

    def close(self):
        """Clear the display before shutdown."""
        self.clear()
