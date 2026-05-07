# ============================================================
# control/command_dispatcher.py — Gesture-to-action dispatcher.
#
# Responsibilities:
#   - Receive a gesture label and confidence score on every frame.
#   - Enforce a per-gesture cooldown so that holding a gesture does
#     not fire the same action repeatedly on every frame.
#   - Map the confirmed gesture to an action string (via config) and
#     delegate execution to the appropriate hardware driver.
#   - Keep the LCD and LED strip synchronised with the current
#     playback state at all times.
# ============================================================

import config


class CommandDispatcher:
    """
    Central coordinator that sits between the gesture classifier and
    the hardware peripherals (audio player, LCD, LED strip).

    Args:
        led   (LEDController): Controls the WS2812B LED strip.
        lcd   (LCDDisplay):    Controls the 16×2 I²C LCD display.
        audio (AudioPlayer):   Controls music playback via pygame.
    """

    def __init__(self, led, lcd, audio):
        self.led   = led
        self.lcd   = lcd
        self.audio = audio

        self._last_gesture   = None   # The gesture seen in the previous frame
        self._cooldown_count = 0      # How many consecutive frames the current gesture has been held
        self._is_playing     = False  # True while a track is actively playing
        self._is_paused      = False  # True while playback is paused (but not stopped)

        self.lcd.show_ready()         # Show the idle/ready message on boot

    # ── Public entry point ───────────────────────────────────

    def dispatch(self, gesture, confidence):
        """
        Called once per frame with the classifier's output.

        Cooldown logic:
          - When the same gesture appears for the first time (or after a
            different gesture), the cooldown counter resets and the action
            fires immediately.
          - While the gesture is held continuously, the counter increments.
            The action is suppressed until COOLDOWN_FRAMES have elapsed,
            preventing rapid-fire repeats from a single sustained gesture.
          - During the cooldown window, the LCD still updates to show the
            detected gesture name and confidence in real time.

        Args:
            gesture    (str):   Gesture label from GestureClassifier, e.g. "THUMBS_UP".
            confidence (float): Confidence score in [0.0, 1.0].
        """
        # ── Cooldown enforcement ──────────────────────────────
        if gesture == self._last_gesture:
            self._cooldown_count += 1
            if self._cooldown_count < config.COOLDOWN_FRAMES:
                # Still within the cooldown window — update the display
                # but do not re-trigger the action.
                if gesture != "NONE":
                    self.lcd.show_gesture(gesture, confidence)
                return
        else:
            # New gesture detected — reset the cooldown counter
            self._cooldown_count = 0
            self._last_gesture   = gesture

        # ── NONE / no hand ───────────────────────────────────
        if gesture == "NONE":
            # No gesture recognised; restore the playback status display
            self._refresh_playback_display()
            return

        # ── Trigger the mapped action ─────────────────────────
        action = config.GESTURE_ACTIONS.get(gesture, "idle")
        if action != "idle":
            self.lcd.show_gesture(gesture, confidence)  # Briefly show gesture name
            self._execute(action)

    # ── Action execution ─────────────────────────────────────

    def _execute(self, action):
        """
        Perform the hardware action that corresponds to the dispatched
        command string, then update the LCD and LED strip to reflect
        the new system state.

        Args:
            action (str): One of the action strings defined in
                          config.GESTURE_ACTIONS (e.g. "play_pause").
        """

        if action == "play_pause":
            self.audio.play_pause()
            if self.audio.is_playing():
                # Playback just started or resumed
                self._is_playing = True
                self._is_paused  = False
                self.led.set_mode("playing")
                self.lcd.show_playing(self.audio.current_track())
            else:
                # Playback was paused
                self._is_playing = False
                self._is_paused  = True
                self.led.set_mode("paused")
                self.lcd.show_paused(self.audio.current_track())
            self.led.flash_action("play_pause")

        elif action == "stop":
            self.audio.stop()
            self._is_playing = False
            self._is_paused  = False
            self.led.set_mode("stopped")
            self.lcd.show_stopped()
            self.led.flash_action("stop")

        elif action == "next_track":
            self.audio.next_track()
            self._is_playing = True
            self._is_paused  = False
            self.led.set_mode("playing")
            self.lcd.show_next_track(self.audio.current_track())
            self.led.flash_action("next_track")

        elif action == "prev_track":
            self.audio.prev_track()
            self._is_playing = True
            self._is_paused  = False
            self.led.set_mode("playing")
            self.lcd.show_prev_track(self.audio.current_track())
            self.led.flash_action("prev_track")

        elif action == "volume_up":
            vol = self.audio.volume_up()
            self.lcd.show_volume_up(vol)
            self.led.flash_action("volume_up")

        elif action == "volume_down":
            vol = self.audio.volume_down()
            self.lcd.show_volume_down(vol)
            self.led.flash_action("volume_down")

    # ── Helpers ──────────────────────────────────────────────

    def _refresh_playback_display(self):
        """
        Restore the LCD to reflect the current playback state.
        Called whenever the gesture returns to NONE so that the
        display doesn't get stuck on the last gesture label.
        """
        if self._is_playing:
            self.lcd.show_playing(self.audio.current_track())
        elif self._is_paused:
            self.lcd.show_paused(self.audio.current_track())
        else:
            self.lcd.show_ready()
