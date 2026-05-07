# ============================================================
# control/led_controller.py — WS2812B LED strip controller.
#
# Provides four continuous animation modes driven by a background
# thread, plus short one-shot flash animations that play in
# response to gesture actions.
#
# Animation modes:
#   "playing"  — Rainbow-chase: colours cycle around the strip.
#   "paused"   — Breathing: teal colour pulses in and out slowly.
#   "stopped"  — Fade-out: red dims to off over ~20 frames.
#   "idle"     — All LEDs off.
#
# Flash animations (triggered by flash_action):
#   volume_up    — Green pixels sweep left-to-right.
#   volume_down  — Orange pixels sweep right-to-left.
#   next_track   — Blue pixels sweep left-to-right.
#   prev_track   — Yellow pixels sweep right-to-left.
#   play_pause   — Two white flashes.
#   stop         — One red flash.
# ============================================================

import threading
import time
import math
import board
import neopixel
import config


def _wheel(pos):
    """
    Convert a position on a 256-step colour wheel to an (R, G, B) tuple.

    The wheel transitions smoothly through: green → yellow → red →
    magenta → blue → cyan → green.

    Args:
        pos (int): Position in [0, 255].

    Returns:
        tuple: (R, G, B) each in [0, 255].
    """
    pos = pos % 256
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)


class LEDController:
    """
    Manages the WS2812B LED strip using a persistent background animation
    thread. The active animation mode can be changed at any time via
    set_mode(). Short confirmatory flash animations can be overlaid on
    top of the current mode via flash_action().

    The background thread ticks every 50 ms (~20 fps), which is fast
    enough for smooth animations while leaving the main thread free.
    """

    def __init__(self):
        # Initialise the NeoPixel strip.
        # board.MOSI maps to GPIO 10 (SPI MOSI, physical pin 19).
        # brightness is handled in software here; LED_BRIGHTNESS/255
        # converts the 0-255 config value to the 0.0-1.0 range neopixel expects.
        self.pixels = neopixel.NeoPixel(
            board.MOSI,
            config.LED_COUNT,
            brightness=config.LED_BRIGHTNESS / 255,
            auto_write=False,              # Batch updates with pixels.show()
            pixel_order=neopixel.GRB       # WS2812B uses GRB byte order
        )

        self._mode     = "idle"   # Current background animation mode
        self._step     = 0        # Frame counter used by animations for timing
        self._flashing = False    # True while a flash animation is running
        self._running  = True     # Set to False to stop the background thread
        self._lock     = threading.Lock()

        # Start the background animation loop
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        self._all_off()           # Ensure strip starts dark

    # ── Public API ───────────────────────────────────────────

    def set_mode(self, mode):
        """
        Switch to a new background animation mode.

        Resets the frame counter so the new animation starts from the
        beginning. Has no effect if the mode is already active.

        Args:
            mode (str): One of "playing", "paused", "stopped", "idle".
        """
        if mode != self._mode:
            self._mode = mode
            self._step = 0

    def flash_action(self, action):
        """
        Trigger a short one-shot flash animation in a new daemon thread.

        The flash runs independently of the background loop. While
        self._flashing is True the background loop yields so the flash
        has exclusive control of the strip.

        Args:
            action (str): The action name to visualise (e.g. "volume_up").
        """
        threading.Thread(
            target=self._flash_worker,
            args=(action,),
            daemon=True
        ).start()

    def close(self):
        """Stop the background thread and turn off all LEDs."""
        self._running = False
        time.sleep(0.15)   # Give the thread one tick to exit cleanly
        self._all_off()

    # ── Background animation loop ────────────────────────────

    def _loop(self):
        """
        Background thread: runs the active animation mode at ~20 fps.
        Yields to flash animations by checking self._flashing each tick.
        """
        while self._running:
            if not self._flashing:
                if   self._mode == "playing": self._rainbow_chase()
                elif self._mode == "paused":  self._breathe(0, 200, 180)
                elif self._mode == "stopped": self._fade_out()
                # "idle" mode intentionally does nothing — LEDs stay off
                self._step += 1
            time.sleep(0.05)   # ~20 fps tick rate

    # ── Animation primitives ─────────────────────────────────

    def _set_all(self, color):
        """Set every pixel to the same colour and push to the strip."""
        with self._lock:
            self.pixels.fill(color)
            self.pixels.show()

    def _all_off(self):
        """Turn off all pixels."""
        self._set_all((0, 0, 0))

    def _rainbow_chase(self):
        """
        Rainbow-chase animation for 'playing' mode.

        Each pixel is assigned a hue offset based on its position,
        then the whole pattern rotates by incrementing self._step.
        Multiplying _step by 4 speeds up the rotation.
        """
        with self._lock:
            for i in range(config.LED_COUNT):
                hue = (i * 256 // config.LED_COUNT + self._step * 4) % 256
                self.pixels[i] = _wheel(hue)
            self.pixels.show()

    def _breathe(self, r, g, b):
        """
        Breathing (pulsing) animation for 'paused' mode.

        Brightness follows a sine wave that oscillates between 10% and
        100% of the specified base colour. The period of one full breath
        is approximately 2π / 0.08 ≈ 78 frames ≈ 3.9 seconds.

        Args:
            r, g, b (int): Base colour components in [0, 255].
        """
        t  = self._step * 0.08
        br = 0.1 + (math.sin(t) + 1) / 2 * 0.9   # Maps sine to [0.1, 1.0]
        self._set_all((int(r * br), int(g * br), int(b * br)))

    def _fade_out(self):
        """
        Red fade-out animation for 'stopped' mode.

        Starts at full red (255, 0, 0) and decreases brightness by 12
        per frame (~21 frames / ~1 second to reach black). Automatically
        transitions to 'idle' mode once the strip is fully dark.
        """
        fade = max(0, 255 - self._step * 12)
        self._set_all((fade, 0, 0))
        if fade == 0:
            self._mode = "idle"   # Animation complete; switch to idle

    # ── Flash worker ─────────────────────────────────────────

    def _flash_worker(self, action):
        """
        Execute a one-shot flash animation for the given action.

        Sets self._flashing = True for the duration so the background
        loop does not overwrite the flash pixels. The finally block
        ensures the flag is always cleared even if an exception occurs.

        Animation descriptions:
          volume_up    : Green pixels fill left-to-right, then clear.
          volume_down  : Orange pixels fill right-to-left, then clear.
          next_track   : Blue pixels fill left-to-right, then clear.
          prev_track   : Yellow pixels fill right-to-left, then clear.
          play_pause   : Strip flashes white twice.
          stop         : Strip flashes red once.

        Args:
            action (str): Action name string.
        """
        self._flashing = True
        try:
            n = config.LED_COUNT

            if action == "volume_up":
                # Green sweep left → right
                with self._lock:
                    for i in range(n):
                        self.pixels[i] = (0, 255, 80)
                        self.pixels.show()
                        time.sleep(0.04)
                    time.sleep(0.1)
                    self.pixels.fill((0, 0, 0))
                    self.pixels.show()

            elif action == "volume_down":
                # Orange sweep right → left
                with self._lock:
                    for i in range(n - 1, -1, -1):
                        self.pixels[i] = (255, 60, 0)
                        self.pixels.show()
                        time.sleep(0.04)
                    time.sleep(0.1)
                    self.pixels.fill((0, 0, 0))
                    self.pixels.show()

            elif action == "next_track":
                # Blue sweep left → right
                with self._lock:
                    for i in range(n):
                        self.pixels[i] = (80, 160, 255)
                        self.pixels.show()
                        time.sleep(0.04)
                    time.sleep(0.1)
                    self.pixels.fill((0, 0, 0))
                    self.pixels.show()

            elif action == "prev_track":
                # Yellow sweep right → left
                with self._lock:
                    for i in range(n - 1, -1, -1):
                        self.pixels[i] = (255, 200, 0)
                        self.pixels.show()
                        time.sleep(0.04)
                    time.sleep(0.1)
                    self.pixels.fill((0, 0, 0))
                    self.pixels.show()

            elif action in ("play_pause", "stop"):
                # play_pause: two white flashes; stop: one red flash
                times = 2 if action == "play_pause" else 1
                color = (255, 255, 255) if action == "play_pause" else (255, 0, 0)
                for _ in range(times):
                    self._set_all(color)
                    time.sleep(0.12)
                    self._set_all((0, 0, 0))
                    time.sleep(0.08)

        finally:
            # Always release the flash lock so the background loop can resume
            self._flashing = False
